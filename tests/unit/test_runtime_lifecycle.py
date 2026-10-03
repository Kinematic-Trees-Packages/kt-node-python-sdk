from __future__ import annotations

import ctypes
import json

import pytest

from ktnode import (
    AbiCompatibilityError,
    Capability,
    ChannelContractIndex,
    ConfigUpdateResult,
    NextStep,
    Node,
    Runtime,
    RuntimeInfo,
    UnsupportedCapabilityError,
    abi,
)
from ktnode.runtime import (
    ConfigUpdate,
    Context,
    _check_status,
    _close_trampoline,
    _config_update_trampoline,
    _runtime_info,
    _setup_trampoline,
    _step_trampoline,
)


class LifecycleLib:
    def __init__(self) -> None:
        self.calls: list[object] = []
        self._payload = b""
        self._buffer = None
        self.destroyed = False

    def kt_status_name(self, status):
        payload = f"status-{status}".encode()
        return abi.KtStringView(payload, len(payload))

    def kt_context_is_closing(self, _ctx, out):
        ctypes.cast(out, ctypes.POINTER(ctypes.c_uint32))[0] = 1
        return 0

    def kt_context_request_close(self, _ctx):
        self.calls.append("context-close")
        return 0

    def kt_context_report_error(self, _ctx, message):
        self.calls.append(("error", abi.view_to_str(message)))
        return 0

    def _owned(self, _ctx, out, _error):
        ctypes.cast(out, ctypes.POINTER(ctypes.POINTER(abi.KtOwnedBytes)))[0] = ctypes.pointer(
            abi.KtOwnedBytes()
        )
        return 0

    kt_context_metrics_json = _owned
    kt_context_config_json = _owned

    def kt_owned_bytes_view(self, _owned):
        self._buffer = (ctypes.c_uint8 * len(self._payload)).from_buffer_copy(self._payload)
        return abi.KtBytesView(self._buffer, len(self._payload))

    def kt_owned_bytes_destroy(self, _owned):
        self.destroyed = True

    def kt_context_config_revision(self, _ctx):
        return 12

    def kt_runtime_run(self, _runtime, _error):
        self.calls.append("run")
        return 0

    def kt_runtime_request_close(self, _runtime):
        self.calls.append("runtime-close")
        return 0

    def kt_runtime_destroy(self, runtime, _error):
        ctypes.cast(runtime, ctypes.POINTER(ctypes.POINTER(abi.KtRuntime)))[0] = ctypes.POINTER(
            abi.KtRuntime
        )()
        self.calls.append("destroy")
        return 0

    def kt_runtime_version(self, out):
        value = ctypes.cast(out, ctypes.POINTER(abi.KtVersionV1)).contents
        value.major, value.minor, value.patch = 2, 3, 4
        return 0

    def kt_runtime_capabilities_v1(self, out):
        ctypes.cast(out, ctypes.POINTER(abi.KtCapabilitiesV1)).contents.bits = (
            abi.KT_CAPABILITY_HTTP | abi.KT_CAPABILITY_KT_SHM
        )
        return 0

    def kt_runtime_build_id(self):
        payload = b"build-7"
        return abi.KtStringView(payload, len(payload))

    def kt_error_code(self, _error):
        return abi.KT_STATUS_UNSUPPORTED_ABI

    def kt_error_message(self, _error):
        payload = b"wrong abi"
        return abi.KtStringView(payload, len(payload))

    def kt_error_destroy(self, _error):
        self.destroyed = True


def context(lib: LifecycleLib) -> Context:
    return Context(
        lib,
        ctypes.pointer(abi.KtAlgorithmContext()),
        ChannelContractIndex({}, {}),
    )


def runtime(lib: LifecycleLib, node: Node | None = None) -> Runtime:
    value = object.__new__(Runtime)
    value._lib = lib
    value._runtime = ctypes.pointer(abi.KtRuntime())
    value._closed = False
    value._channels = ChannelContractIndex({}, {})
    value._node = node or Node()
    value.info = RuntimeInfo(1, 2, (2, 3, 4), "build-7", Capability.HTTP, 2)
    return value


def test_context_lifecycle_metrics_and_config() -> None:
    lib = LifecycleLib()
    ctx = context(lib)
    assert ctx.channels.inputs == {}
    assert ctx.is_closing()
    ctx.request_close()
    ctx.report_error("diagnostic")
    lib._payload = json.dumps({"steps": 4}).encode()
    assert ctx.metrics() == {"steps": 4}
    lib._payload = json.dumps({"mode": "safe"}).encode()
    assert ctx.config() == {"mode": "safe"}
    assert ctx.config_revision() == 12
    assert lib.destroyed
    assert ("error", "diagnostic") in lib.calls


def test_context_rejects_missing_optional_abi_exports() -> None:
    lib = LifecycleLib()
    delattr(LifecycleLib, "kt_context_config_json")
    try:
        with pytest.raises(UnsupportedCapabilityError, match="config_json"):
            context(lib).config_json()
    finally:
        LifecycleLib.kt_context_config_json = LifecycleLib._owned


def test_runtime_owned_lifecycle_and_context_manager() -> None:
    lib = LifecycleLib()
    value = runtime(lib)
    value.run()
    value.request_close()
    assert value.__enter__() is value
    value.__exit__(None, None, None)
    assert value.closed
    value.close()
    assert lib.calls == ["run", "runtime-close", "destroy"]


def test_runtime_callback_dispatch_and_failure_reporting() -> None:
    class RecordingNode(Node):
        def setup(self, ctx):
            self.context = ctx
            return NextStep.CONTINUE

        def step(self, ctx):
            raise RuntimeError("boom")

        def config_update(self, ctx, update):
            self.update = update
            return ConfigUpdateResult.ACCEPT

    lib = LifecycleLib()
    node = RecordingNode()
    value = runtime(lib, node)
    ctx_ptr = ctypes.pointer(abi.KtAlgorithmContext())
    assert value._invoke("setup", ctx_ptr) == NextStep.CONTINUE
    assert not node.context._active
    assert value._invoke("step", ctx_ptr) == NextStep.FATAL
    update = ConfigUpdate(1, 2, [], {}, {}, ["/mode"], 0)
    assert value._invoke("config_update", ctx_ptr, update) == ConfigUpdateResult.ACCEPT
    assert node.update is update
    assert ("error", "Python node step failed: boom") in lib.calls


def test_callback_trampolines_and_config_decode() -> None:
    lib = LifecycleLib()

    class ConfigProbe(Node):
        update: ConfigUpdate | None = None

        def config_update(self, ctx, update):
            self.update = update
            return ConfigUpdateResult.ACCEPT

    probe = ConfigProbe()
    value = runtime(lib, probe)
    owner = ctypes.py_object(value)
    user_data = ctypes.cast(ctypes.pointer(owner), ctypes.c_void_p)
    ctx = ctypes.pointer(abi.KtAlgorithmContext())
    assert _setup_trampoline(user_data, ctx) == NextStep.CONTINUE
    assert _step_trampoline(user_data, ctx) == NextStep.STOP
    assert _close_trampoline(user_data, ctx) == NextStep.STOP
    assert _config_update_trampoline(user_data, ctx, None) == ConfigUpdateResult.REJECT_FATAL

    keepalive = []
    raw = abi.KtConfigUpdateV1()
    raw.old_revision, raw.new_revision = 3, 4
    for field, payload in (
        ("patch_json", "[]"),
        ("old_config_json", "{}"),
        ("new_config_json", '{"mode":"safe"}'),
        ("changed_paths_json", '["/mode"]'),
    ):
        view, encoded = abi.string_view(payload)
        setattr(raw, field, view)
        keepalive.append(encoded)
    assert _config_update_trampoline(user_data, ctx, ctypes.pointer(raw)) == ConfigUpdateResult.ACCEPT
    assert probe.update == ConfigUpdate(
        old_revision=3,
        new_revision=4,
        patch=[],
        old_config={},
        new_config={"mode": "safe"},
        changed_paths=["/mode"],
        flags=0,
    )


def test_runtime_info_and_structured_abi_error() -> None:
    lib = LifecycleLib()
    info = _runtime_info(lib, 1, 2, 2)
    assert info.runtime_version == (2, 3, 4)
    assert info.build_id == "build-7"
    assert info.capabilities == Capability.HTTP | Capability.KT_SHM
    error = ctypes.pointer(abi.KtError())
    with pytest.raises(AbiCompatibilityError, match="wrong abi"):
        _check_status(lib, 3, error)
    assert lib.destroyed
