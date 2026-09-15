"""Safe high-level Python API for the frozen KT Node C ABI."""

from __future__ import annotations

import ctypes
import json
from dataclasses import dataclass
from enum import IntEnum, IntFlag
from typing import Any

from . import abi


class KtError(RuntimeError):
    """Base error raised by the KT Node Python SDK."""


class AbiCompatibilityError(KtError):
    """The loaded native library is incompatible with this SDK."""


class UnsupportedCapabilityError(KtError):
    """The loaded runtime does not provide a requested capability."""


class ClosedResourceError(KtError):
    """A runtime or callback context was used after its lifetime ended."""


class NextStep(IntEnum):
    CONTINUE = abi.KT_ALGORITHM_CONTINUE
    STOP = abi.KT_ALGORITHM_STOP
    RECOVERABLE = abi.KT_ALGORITHM_RECOVERABLE
    FATAL = abi.KT_ALGORITHM_FATAL


class ConfigUpdateResult(IntEnum):
    ACCEPT = abi.KT_CONFIG_UPDATE_ACCEPT
    REJECT_RECOVERABLE = abi.KT_CONFIG_UPDATE_REJECT_RECOVERABLE
    REJECT_FATAL = abi.KT_CONFIG_UPDATE_REJECT_FATAL
    STOP = abi.KT_CONFIG_UPDATE_STOP


class Capability(IntFlag):
    HTTP = abi.KT_CAPABILITY_HTTP
    KT_LAN = abi.KT_CAPABILITY_KT_LAN
    KT_SHM = abi.KT_CAPABILITY_KT_SHM
    WEBRTC = abi.KT_CAPABILITY_WEBRTC


@dataclass(frozen=True)
class RuntimeInfo:
    abi_major: int
    abi_minor: int
    runtime_version: tuple[int, int, int]
    build_id: str
    capabilities: Capability
    creation_api: int


@dataclass(frozen=True)
class Message:
    payload: bytes
    source_id: str | None = None
    remote_time_ns: int | None = None


@dataclass(frozen=True)
class ConfigUpdate:
    old_revision: int
    new_revision: int
    patch: Any
    old_config: Any
    new_config: Any
    changed_paths: Any
    flags: int


def _decode_json(view: abi.KtStringView) -> Any:
    text = abi.view_to_str(view)
    return json.loads(text) if text else None


class Context:
    def __init__(self, lib: ctypes.CDLL, ptr: ctypes.POINTER(abi.KtAlgorithmContext)) -> None:
        self._lib = lib
        self._ptr = ptr
        self._active = True

    def _require_active(self) -> None:
        if not self._active or not self._ptr:
            raise ClosedResourceError("callback context is no longer active")

    def _invalidate(self) -> None:
        self._active = False
        self._ptr = ctypes.POINTER(abi.KtAlgorithmContext)()

    def is_closing(self) -> bool:
        self._require_active()
        out = ctypes.c_uint32(0)
        _check_status(self._lib, self._lib.kt_context_is_closing(self._ptr, ctypes.byref(out)))
        return bool(out.value)

    def request_close(self) -> None:
        self._require_active()
        _check_status(self._lib, self._lib.kt_context_request_close(self._ptr))

    def report_error(self, message: str) -> None:
        self._require_active()
        view, keepalive = abi.string_view(message)
        _check_status(self._lib, self._lib.kt_context_report_error(self._ptr, view))
        _ = keepalive

    def set(self, channel: str, payload: bytes | bytearray | memoryview) -> None:
        self._require_active()
        channel_view, channel_keepalive = abi.string_view(channel)
        payload_view, payload_keepalive = abi.bytes_view(payload)
        error = ctypes.POINTER(abi.KtError)()
        status = self._lib.kt_context_set(self._ptr, channel_view, payload_view, ctypes.byref(error))
        _ = (channel_keepalive, payload_keepalive)
        _check_status(self._lib, status, error)

    def set_from(self, channel: str, source_id: str, payload: bytes | bytearray | memoryview) -> None:
        self._require_active()
        channel_view, channel_keepalive = abi.string_view(channel)
        source_view, source_keepalive = abi.string_view(source_id)
        payload_view, payload_keepalive = abi.bytes_view(payload)
        error = ctypes.POINTER(abi.KtError)()
        status = self._lib.kt_context_set_source(self._ptr, channel_view, source_view, payload_view, ctypes.byref(error))
        _ = (channel_keepalive, source_keepalive, payload_keepalive)
        _check_status(self._lib, status, error)

    def _owned_bytes(self, operation: str) -> bytes:
        self._require_active()
        function = getattr(self._lib, operation, None)
        if function is None:
            raise UnsupportedCapabilityError(f"loaded ABI does not export {operation}")
        output = ctypes.POINTER(abi.KtOwnedBytes)()
        error = ctypes.POINTER(abi.KtError)()
        _check_status(self._lib, function(self._ptr, ctypes.byref(output), ctypes.byref(error)), error)
        if not output:
            return b""
        try:
            return abi.view_to_bytes(self._lib.kt_owned_bytes_view(output))
        finally:
            self._lib.kt_owned_bytes_destroy(ctypes.byref(output))

    def metrics_json(self) -> bytes:
        return self._owned_bytes("kt_context_metrics_json")

    def metrics(self) -> dict[str, object]:
        payload = self.metrics_json()
        return json.loads(payload.decode("utf-8")) if payload else {}

    def config_json(self) -> bytes:
        return self._owned_bytes("kt_context_config_json")

    def config(self) -> Any:
        payload = self.config_json()
        return json.loads(payload.decode("utf-8")) if payload else None

    def config_revision(self) -> int:
        self._require_active()
        function = getattr(self._lib, "kt_context_config_revision", None)
        if function is None:
            raise UnsupportedCapabilityError("loaded ABI does not export kt_context_config_revision")
        return int(function(self._ptr))

    def get(self, channel: str, mode: int = abi.KT_READ_ONE, count: int = 0) -> list[Message]:
        self._require_active()
        channel_view, channel_keepalive = abi.string_view(channel)
        options = abi.KtReadOptionsV1(ctypes.sizeof(abi.KtReadOptionsV1), abi.KT_ABI_VERSION_MAJOR, mode, 0, count, (ctypes.c_uint64 * 4)())
        batch = ctypes.POINTER(abi.KtMessageBatch)()
        error = ctypes.POINTER(abi.KtError)()
        status = self._lib.kt_context_read(self._ptr, channel_view, ctypes.byref(options), ctypes.byref(batch), ctypes.byref(error))
        _ = channel_keepalive
        _check_status(self._lib, status, error)
        if not batch:
            return []
        try:
            messages: list[Message] = []
            for index in range(self._lib.kt_message_batch_count(batch)):
                item = abi.KtMessageViewV1()
                item.struct_size = ctypes.sizeof(abi.KtMessageViewV1)
                item.abi_version = abi.KT_ABI_VERSION_MAJOR
                item_error = ctypes.POINTER(abi.KtError)()
                _check_status(self._lib, self._lib.kt_message_batch_item(batch, index, ctypes.byref(item), ctypes.byref(item_error)), item_error)
                messages.append(Message(abi.view_to_bytes(item.payload), abi.view_to_str(item.source_id) if item.has_source else None, int(item.remote_time_ns) if item.has_remote_time else None))
            return messages
        finally:
            self._lib.kt_message_batch_destroy(ctypes.byref(batch))


class Node:
    def setup(self, ctx: Context) -> NextStep:
        return NextStep.CONTINUE

    def step(self, ctx: Context) -> NextStep:
        return NextStep.STOP

    def close(self, ctx: Context) -> NextStep:
        return NextStep.STOP

    def config_update(self, ctx: Context, update: ConfigUpdate) -> ConfigUpdateResult:
        return ConfigUpdateResult.ACCEPT


class Runtime:
    def __init__(self, package_path: str, runtime_path: str, node: Node, library_path: str | None = None) -> None:
        self._lib = abi.load_library(library_path)
        major = int(self._lib.kt_abi_version_major())
        minor = int(self._lib.kt_abi_version_minor())
        if major != abi.KT_ABI_VERSION_MAJOR:
            raise AbiCompatibilityError(f"unsupported KT Node ABI major {major}, expected {abi.KT_ABI_VERSION_MAJOR}")
        if minor < 0:
            raise AbiCompatibilityError(f"invalid KT Node ABI minor {minor}")
        self._node = node
        self._runtime = ctypes.POINTER(abi.KtRuntime)()
        self._closed = False
        self._user_data = ctypes.py_object(self)
        self._user_data_ptr = ctypes.cast(ctypes.pointer(self._user_data), ctypes.c_void_p)
        self._setup_cb = abi.KtAlgorithmSetupFn(_setup_trampoline)
        self._step_cb = abi.KtAlgorithmStepFn(_step_trampoline)
        self._close_cb = abi.KtAlgorithmCloseFn(_close_trampoline)
        self._config_cb = abi.KtAlgorithmConfigUpdateFn(_config_update_trampoline)
        package_view, self._package_keepalive = abi.string_view(package_path)
        runtime_view, self._runtime_keepalive = abi.string_view(runtime_path)
        error = ctypes.POINTER(abi.KtError)()
        create_v2 = getattr(self._lib, "kt_runtime_create_v2", None)
        if minor >= 2 and create_v2 is not None:
            self._callbacks = abi.KtAlgorithmCallbacksV2(ctypes.sizeof(abi.KtAlgorithmCallbacksV2), abi.KT_ABI_VERSION_MAJOR, self._setup_cb, self._step_cb, self._close_cb, self._config_cb, (ctypes.c_uint64 * 4)())
            options = abi.KtRuntimeOptionsV2(ctypes.sizeof(abi.KtRuntimeOptionsV2), abi.KT_ABI_VERSION_MAJOR, package_view, runtime_view, ctypes.pointer(self._callbacks), self._user_data_ptr, (ctypes.c_uint64 * 4)())
            status = create_v2(ctypes.byref(options), ctypes.byref(self._runtime), ctypes.byref(error))
            creation_api = 2
        else:
            self._callbacks = abi.KtAlgorithmCallbacksV1(ctypes.sizeof(abi.KtAlgorithmCallbacksV1), abi.KT_ABI_VERSION_MAJOR, self._setup_cb, self._step_cb, self._close_cb, (ctypes.c_uint64 * 4)())
            options_v1 = abi.KtRuntimeOptionsV1(ctypes.sizeof(abi.KtRuntimeOptionsV1), abi.KT_ABI_VERSION_MAJOR, package_view, runtime_view, ctypes.pointer(self._callbacks), self._user_data_ptr, (ctypes.c_uint64 * 4)())
            status = self._lib.kt_runtime_create_v1(ctypes.byref(options_v1), ctypes.byref(self._runtime), ctypes.byref(error))
            creation_api = 1
        _check_status(self._lib, status, error)
        self.info = _runtime_info(self._lib, major, minor, creation_api)

    def _require_open(self) -> None:
        if self._closed or not self._runtime:
            raise ClosedResourceError("runtime is closed")

    def require_capability(self, capability: Capability) -> None:
        self._require_open()
        if capability & self.info.capabilities != capability:
            raise UnsupportedCapabilityError(f"runtime does not support {capability.name or int(capability)}")

    def run(self) -> None:
        self._require_open()
        error = ctypes.POINTER(abi.KtError)()
        _check_status(self._lib, self._lib.kt_runtime_run(self._runtime, ctypes.byref(error)), error)

    def request_close(self) -> None:
        self._require_open()
        _check_status(self._lib, self._lib.kt_runtime_request_close(self._runtime))

    def close(self) -> None:
        if self._closed:
            return
        if self._runtime:
            error = ctypes.POINTER(abi.KtError)()
            _check_status(self._lib, self._lib.kt_runtime_destroy(ctypes.byref(self._runtime), ctypes.byref(error)), error)
        self._closed = True

    destroy = close

    @property
    def closed(self) -> bool:
        return self._closed

    def __enter__(self) -> "Runtime":
        self._require_open()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _invoke(self, method: str, ctx_ptr: ctypes.POINTER(abi.KtAlgorithmContext), update: ConfigUpdate | None = None) -> int:
        ctx = Context(self._lib, ctx_ptr)
        try:
            result = getattr(self._node, method)(ctx) if update is None else getattr(self._node, method)(ctx, update)
            return int(result)
        except Exception as exc:
            try:
                ctx.report_error(f"Python node {method} failed: {exc}")
            except Exception:
                pass
            return int(ConfigUpdateResult.REJECT_FATAL if update is not None else NextStep.FATAL)
        finally:
            ctx._invalidate()


def _runtime_info(lib: ctypes.CDLL, major: int, minor: int, creation_api: int) -> RuntimeInfo:
    version = abi.KtVersionV1()
    version.struct_size = ctypes.sizeof(abi.KtVersionV1)
    version.abi_version = abi.KT_ABI_VERSION_MAJOR
    _check_status(lib, lib.kt_runtime_version(ctypes.byref(version)))
    capabilities = abi.KtCapabilitiesV1()
    capabilities.struct_size = ctypes.sizeof(abi.KtCapabilitiesV1)
    capabilities.abi_version = abi.KT_ABI_VERSION_MAJOR
    _check_status(lib, lib.kt_runtime_capabilities_v1(ctypes.byref(capabilities)))
    return RuntimeInfo(major, minor, (version.major, version.minor, version.patch), abi.view_to_str(lib.kt_runtime_build_id()), Capability(capabilities.bits), creation_api)


def run(package_path: str, runtime_path: str, node: Node, library_path: str | None = None) -> None:
    with Runtime(package_path, runtime_path, node, library_path=library_path) as runtime:
        runtime.run()


def _runtime_from_user_data(user_data: ctypes.c_void_p) -> Runtime:
    return ctypes.cast(user_data, ctypes.POINTER(ctypes.py_object)).contents.value


def _setup_trampoline(user_data: ctypes.c_void_p, ctx: ctypes.POINTER(abi.KtAlgorithmContext)) -> int:
    return _runtime_from_user_data(user_data)._invoke("setup", ctx)


def _step_trampoline(user_data: ctypes.c_void_p, ctx: ctypes.POINTER(abi.KtAlgorithmContext)) -> int:
    return _runtime_from_user_data(user_data)._invoke("step", ctx)


def _close_trampoline(user_data: ctypes.c_void_p, ctx: ctypes.POINTER(abi.KtAlgorithmContext)) -> int:
    return _runtime_from_user_data(user_data)._invoke("close", ctx)


def _config_update_trampoline(user_data: ctypes.c_void_p, ctx: ctypes.POINTER(abi.KtAlgorithmContext), raw: ctypes.POINTER(abi.KtConfigUpdateV1)) -> int:
    if not raw:
        return int(ConfigUpdateResult.REJECT_FATAL)
    value = raw.contents
    update = ConfigUpdate(int(value.old_revision), int(value.new_revision), _decode_json(value.patch_json), _decode_json(value.old_config_json), _decode_json(value.new_config_json), _decode_json(value.changed_paths_json), int(value.flags))
    return _runtime_from_user_data(user_data)._invoke("config_update", ctx, update)


def _check_status(lib: ctypes.CDLL, status: int, error: ctypes.POINTER(abi.KtError) | None = None) -> None:
    if status == abi.KT_STATUS_OK:
        return
    message = ""
    code = int(status)
    if error:
        try:
            code = int(lib.kt_error_code(error))
            message = abi.view_to_str(lib.kt_error_message(error))
        finally:
            lib.kt_error_destroy(ctypes.byref(error))
    if not message:
        message = abi.view_to_str(lib.kt_status_name(status)) or f"KT status {status}"
    exception = AbiCompatibilityError if code == abi.KT_STATUS_UNSUPPORTED_ABI else KtError
    raise exception(message)
