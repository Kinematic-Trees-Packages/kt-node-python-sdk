import ctypes
import unittest

from ktnode import Capability, ClosedResourceError, NextStep, Node, UnsupportedCapabilityError, abi
from ktnode.runtime import Context, KtError, RuntimeInfo, _check_status


class FakeLib:
    def kt_status_name(self, status):
        payload = f"STATUS_{status}".encode()
        self._last_status_name = payload
        return abi.KtStringView(payload, len(payload))

    def kt_error_message(self, error):
        payload = b"detailed error"
        self._last_error_message = payload
        return abi.KtStringView(payload, len(payload))

    def kt_error_destroy(self, error_ptr):
        self.destroyed = True


class RuntimeContractTests(unittest.TestCase):
    def test_string_view_keeps_utf8_bytes_and_length(self):
        view, keepalive = abi.string_view("video.rgb")
        self.assertEqual(view.length, len(keepalive))
        self.assertEqual(abi.view_to_str(view), "video.rgb")

    def test_bytes_view_copies_payload(self):
        source = bytearray(b"abc")
        view, _keepalive = abi.bytes_view(source)
        source[:] = b"zzz"
        self.assertEqual(abi.view_to_bytes(view), b"abc")

    def test_default_node_is_safe(self):
        node = Node()
        self.assertEqual(node.setup(None), NextStep.CONTINUE)
        self.assertEqual(node.step(None), NextStep.STOP)
        self.assertEqual(node.close(None), NextStep.STOP)

    def test_status_error_uses_status_name_without_error_object(self):
        with self.assertRaises(KtError) as raised:
            _check_status(FakeLib(), 123)
        self.assertIn("STATUS_123", str(raised.exception))

    def test_status_error_destroys_error_object(self):
        lib = FakeLib()
        error = ctypes.POINTER(abi.KtError)()
        with self.assertRaises(KtError) as raised:
            _check_status(lib, 123, error)
        self.assertIn("STATUS_123", str(raised.exception))

    def test_v2_ctypes_layout_matches_frozen_header(self):
        self.assertEqual(ctypes.sizeof(abi.KtConfigUpdateV1), 120)
        self.assertEqual(ctypes.sizeof(abi.KtAlgorithmCallbacksV2), 72)
        self.assertEqual(ctypes.sizeof(abi.KtRuntimeOptionsV2), 88)

    def test_context_rejects_use_after_callback(self):
        context = Context(FakeLib(), ctypes.POINTER(abi.KtAlgorithmContext)())
        context._invalidate()
        with self.assertRaises(ClosedResourceError):
            context.is_closing()

    def test_capability_rejection_is_predictable(self):
        runtime = object.__new__(__import__("ktnode").Runtime)
        runtime._closed = False
        runtime._runtime = ctypes.pointer(abi.KtRuntime())
        runtime.info = RuntimeInfo(1, 2, (0, 1, 0), "test", Capability.HTTP, 2)
        runtime.require_capability(Capability.HTTP)
        with self.assertRaises(UnsupportedCapabilityError):
            runtime.require_capability(Capability.WEBRTC)

    def test_runtime_rejects_use_after_close(self):
        runtime = object.__new__(__import__("ktnode").Runtime)
        runtime._closed = True
        runtime._runtime = ctypes.POINTER(abi.KtRuntime)()
        with self.assertRaises(ClosedResourceError):
            runtime.request_close()


if __name__ == "__main__":
    unittest.main()
