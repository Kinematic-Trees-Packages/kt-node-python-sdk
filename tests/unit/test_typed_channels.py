import ctypes

import pytest

from kt.messages import codec_for
from kt.messages.command import Command
from ktnode import (
    ChannelContract,
    ChannelContractIndex,
    Context,
    Get,
    MissingCodecError,
    PayloadDecodeError,
    ReadMode,
    Received,
    Set,
    UnknownChannelError,
    ValueEncodeError,
    abi,
)


class FakeTypedLib:
    def __init__(self, messages=()):
        self.messages = list(messages)
        self._buffers = []
        self._sources = []
        self.writes = []

    def kt_context_read(self, _context, _channel, _options, out_batch, _out_error):
        ctypes.cast(out_batch, ctypes.POINTER(ctypes.POINTER(abi.KtMessageBatch)))[0] = ctypes.pointer(
            abi.KtMessageBatch()
        )
        return abi.KT_STATUS_OK

    def kt_message_batch_count(self, _batch):
        return len(self.messages)

    def kt_message_batch_item(self, _batch, index, out_item, _out_error):
        payload, source, timestamp = self.messages[index]
        buffer = (ctypes.c_uint8 * len(payload)).from_buffer_copy(payload) if payload else None
        source_bytes = source.encode("utf-8") if source is not None else b""
        self._buffers.append(buffer)
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
        ctypes.cast(batch, ctypes.POINTER(ctypes.POINTER(abi.KtMessageBatch)))[0] = ctypes.POINTER(
            abi.KtMessageBatch
        )()

    def kt_context_set(self, _context, channel, payload, _out_error):
        self.writes.append((abi.view_to_str(channel), None, abi.view_to_bytes(payload)))
        return abi.KT_STATUS_OK

    def kt_context_set_source(self, _context, channel, source, payload, _out_error):
        self.writes.append(
            (abi.view_to_str(channel), abi.view_to_str(source), abi.view_to_bytes(payload))
        )
        return abi.KT_STATUS_OK


def context(*, inputs, outputs, messages=()):
    lib = FakeTypedLib(messages)
    channels = ChannelContractIndex(
        {name: ChannelContract(name, datatype, "input") for name, datatype in inputs.items()},
        {name: ChannelContract(name, datatype, "output") for name, datatype in outputs.items()},
    )
    return Context(lib, ctypes.pointer(abi.KtAlgorithmContext()), channels), lib


def encoded(datatype, value):
    return bytes(codec_for(datatype).encode(value))


def test_get_returns_natural_string_and_none_for_empty_channel():
    ctx, _lib = context(
        inputs={"text": "kt/speech/string_sample"},
        outputs={},
        messages=[(encoded("kt/speech/string_sample", "hello"), None, None)],
    )
    assert Get(ctx, "text") == "hello"

    empty, _lib = context(inputs={"text": "kt/speech/string_sample"}, outputs={})
    assert Get(empty, "text") is None


def test_get_returns_immutable_complex_view():
    original = Command.create(command="move", timestamp=42)
    ctx, _lib = context(
        inputs={"command": "kt/command/command"},
        outputs={},
        messages=[(bytes(original.encoded()), None, None)],
    )
    value = Get(ctx, "command")
    assert isinstance(value, Command)
    assert value.command == "move"
    assert value.timestamp == 42
    with pytest.raises(TypeError, match="immutable.*Command.create"):
        value.command = "mutated"
    ctx._invalidate()
    assert value.command == "move"


def test_batch_get_preserves_transport_metadata():
    payload = encoded("kt/speech/string_sample", "hello")
    ctx, _lib = context(
        inputs={"text": "kt/speech/string_sample"},
        outputs={},
        messages=[(payload, "front", 123), (payload, None, None)],
    )
    values = Get(ctx, "text", ReadMode.ALL_AVAILABLE)
    assert values == [Received("hello", "front", 123), Received("hello")]


def test_set_encodes_natural_and_complex_values_and_preserves_view_payload():
    ctx, lib = context(
        inputs={},
        outputs={"text": "kt/speech/string_sample", "command": "kt/command/command"},
    )
    Set(ctx, "text", "hello")
    command = Command.create(command="stop", timestamp=9)
    before = bytes(command.encoded())
    Set(ctx, "command", command, source_id="planner")
    assert lib.writes[0][0:2] == ("text", None)
    assert codec_for("kt/speech/string_sample").decode(lib.writes[0][2]) == "hello"
    assert lib.writes[1] == ("command", "planner", before)
    assert bytes(command.encoded()) == before


def test_typed_errors_are_channel_and_datatype_specific():
    wrong, _lib = context(inputs={"in": "kt/speech/string_sample"}, outputs={"out": "kt/speech/string_sample"})
    with pytest.raises(UnknownChannelError, match="output, not an input"):
        Get(wrong, "out")
    with pytest.raises(ValueEncodeError, match="channel 'out'.*expects str, received int"):
        Set(wrong, "out", 1)

    missing, _lib = context(inputs={"in": "customer/unknown"}, outputs={})
    with pytest.raises(MissingCodecError, match="customer/unknown"):
        Get(missing, "in")

    malformed, _lib = context(
        inputs={"in": "kt/speech/string_sample"},
        outputs={},
        messages=[(b"not-a-flatbuffer", None, None)],
    )
    with pytest.raises(PayloadDecodeError, match="channel 'in'.*kt/speech/string_sample"):
        Get(malformed, "in")
