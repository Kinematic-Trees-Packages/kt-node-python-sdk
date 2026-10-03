# Python data-model conformance

This document freezes the manifest-driven typed data-model surface.

## Release matrix

The C ABI transports payloads as opaque bytes. `Get` and `Set` resolve the exact
channel datatype through the generated `kt.messages` codec registry. Explicit
raw operations preserve byte-transparent forwarding when required.

| Datatype class | Python support | Semantic helper |
|---|---|---|
| `kt/speech/string_sample` | natural `str` | explicit generated adapter |
| `kt/scalar/int64_value` | natural `int` | explicit generated adapter |
| arrays and structured datatypes | immutable generated views | `Type.create(...)` for new values |
| `kt/vision/vision_sample` | immutable generated view | RGB helper remains available |
| unregistered datatype | rejected | `MissingCodecError` |

The complete canonical datatype registry remains owned by `kt_messages`. The
SDK never guesses a schema or promotes an unapproved one-field message to a
Python primitive.

## Read and metadata contract

- `Get(..., ReadMode.ONE)` returns one decoded value or `None`.
- Batch `Get` returns `Received` values containing the decoded value and
  optional source/timestamp metadata.
- `ReadMode.ONE` and `ReadMode.COUNT` apply to single-source inputs.
- `ReadMode.ALL_AVAILABLE` applies to single- and multi-source inputs.
- Native multi-source inputs reject `ONE` and `COUNT` with wrong-shape status.
- `Message.source_id` is present only for multi-source samples.
- `Message.remote_time_ns` is present only when the transport supplied a source
  timestamp and it fits signed 64-bit nanoseconds.
- Empty payloads remain valid through `get_raw`; typed `Get` validates the
  declared FlatBuffer identifier.
- Python copies batch payloads, source IDs, and timestamps before destroying the
  borrowed native batch.
- ABI 1.2 write calls do not accept a remote timestamp. Python does not invent
  one; timestamped writes require a future ABI extension.

## Schema compatibility

All typed values validate their generated file identifier. Public immutable
views live under `kt.messages`; raw `flatc` modules live under the private
`kt_messages._flatbuffers` namespace for package-owned encoding internals.

Passing an unchanged immutable view to `Set` reuses its encoded payload without
Python decode/re-encode. Raw forwarding remains byte-for-byte and
schema-agnostic through the explicitly named raw APIs.

## Evidence

- `tests/integration/live_data_model_conformance.py` drives a composite scalar, structured,
  empty, malformed-vision, and large opaque fixture through the real HTTP
  runtime and ABI 1.2/V2 callback boundary with `one`. It verifies write
  copy-in and a 64 MiB RSS-growth bound.
- `tests/unit/test_data_model_conformance.py` covers `one`, `count`, and
  `all_available` marshaling and a 2 MiB payload deterministically at the ABI
  call boundary, independent of transport scheduling.
- `tests/unit/test_data_model_conformance.py` deterministically checks binary copying,
  empty/large payloads, source IDs, and optional timestamps in Python's ABI
  batch marshaling.
- `tests/unit/test_vision_contract.py` checks deterministic VSM1 encode/decode,
  stable malformed-payload rejection, exact 1080p metadata, and bounded peak RSS.
- `tests/unit/test_typed_channels.py` covers natural values, immutable complex
  views, batch metadata, unchanged-view passthrough, missing codecs, malformed
  payloads, direction errors, and wrong output values.
- Rust ABI tests remain authoritative for native multi-source shape rejection,
  timestamp overflow, and batch ownership/thread scope. Python preserves those
  fields without reinterpretation.
