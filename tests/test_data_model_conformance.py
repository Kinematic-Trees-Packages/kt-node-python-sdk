import ctypes
import unittest

from ktnode import Context, ReadMode, abi


class FakeBatchLib:
    """Contract-faithful ABI batch fixture for Python marshaling tests."""

    def __init__(self, messages):
        self.messages = messages
        self.read_options = None
        self._buffers = []
        self._sources = []
        self.destroyed = False

    def kt_context_read(self, _context, _channel, options, out_batch, _out_error):
        options_ptr = ctypes.cast(options, ctypes.POINTER(abi.KtReadOptionsV1))
        self.read_options = abi.KtReadOptionsV1.from_buffer_copy(bytes(options_ptr.contents))
        batch_ptr = ctypes.cast(out_batch, ctypes.POINTER(ctypes.POINTER(abi.KtMessageBatch)))
        batch_ptr[0] = ctypes.pointer(abi.KtMessageBatch())
        return abi.KT_STATUS_OK

    def kt_message_batch_count(self, _batch):
        return len(self.messages)

    def kt_message_batch_item(self, _batch, index, out_item, _out_error):
        payload, source, timestamp = self.messages[index]
        buffer = (ctypes.c_uint8 * len(payload)).from_buffer_copy(payload) if payload else None
        self._buffers.append(buffer)
        source_bytes = source.encode("utf-8") if source is not None else b""
        self._sources.append(source_bytes)
        item = ctypes.cast(out_item, ctypes.POINTER(abi.KtMessageViewV1)).contents
        item.payload = abi.KtBytesView(
            ctypes.cast(buffer, ctypes.POINTER(ctypes.c_uint8)) if buffer else None,
            len(payload),
        )
        item.source_id = abi.KtStringView(source_bytes or None, len(source_bytes))
        item.has_source = int(source is not None)
        item.remote_time_ns = timestamp or 0
        item.has_remote_time = int(timestamp is not None)
        return abi.KT_STATUS_OK

    def kt_message_batch_destroy(self, batch):
        batch_ptr = ctypes.cast(batch, ctypes.POINTER(ctypes.POINTER(abi.KtMessageBatch)))
        batch_ptr[0] = ctypes.POINTER(abi.KtMessageBatch)()
        self.destroyed = True


class DataModelConformanceTests(unittest.TestCase):
    def _context(self, messages):
        lib = FakeBatchLib(messages)
        return Context(lib, ctypes.pointer(abi.KtAlgorithmContext())), lib

    def test_all_available_preserves_binary_payload_source_and_timestamp(self):
        large = bytes(range(256)) * 16384
        context, lib = self._context(
            [
                (b"", None, None),
                (b"\x00scalar\xff", "front/left", None),
                (large, "rear", 123_456_789),
            ]
        )
        messages = context.get("input", ReadMode.ALL_AVAILABLE)
        self.assertEqual([message.payload for message in messages], [b"", b"\x00scalar\xff", large])
        self.assertEqual(messages[0].source_id, None)
        self.assertEqual(messages[1].source_id, "front/left")
        self.assertEqual(messages[1].remote_time_ns, None)
        self.assertEqual(messages[2].source_id, "rear")
        self.assertEqual(messages[2].remote_time_ns, 123_456_789)
        self.assertEqual(lib.read_options.mode, abi.KT_READ_ALL_AVAILABLE)
        self.assertEqual(lib.read_options.count, 0)
        self.assertTrue(lib.destroyed)

    def test_one_and_count_encode_frozen_read_options(self):
        context, lib = self._context([(b"one", None, None)])
        self.assertEqual(context.get("input", ReadMode.ONE)[0].payload, b"one")
        self.assertEqual(lib.read_options.mode, abi.KT_READ_ONE)
        self.assertEqual(lib.read_options.count, 0)

        context, lib = self._context([(b"a", None, None), (b"b", None, None)])
        self.assertEqual(len(context.get("input", ReadMode.COUNT, 2)), 2)
        self.assertEqual(lib.read_options.mode, abi.KT_READ_COUNT)
        self.assertEqual(lib.read_options.count, 2)

    def test_invalid_read_mode_and_count_fail_before_ffi(self):
        context, _lib = self._context([])
        with self.assertRaisesRegex(ValueError, "count must be positive"):
            context.get("input", ReadMode.COUNT, 0)
        with self.assertRaisesRegex(ValueError, "count must be zero"):
            context.get("input", ReadMode.ONE, 1)
        with self.assertRaisesRegex(ValueError, "unsupported read mode"):
            context.get("input", 99)


if __name__ == "__main__":
    unittest.main()
