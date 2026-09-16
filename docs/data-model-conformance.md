# Python data-model conformance

This document freezes the data-model surface for the first Python SDK release.

## Release matrix

The C ABI transports payloads as opaque bytes. The first Python release
therefore supports byte-transparent forwarding for any channel datatype, while
typed encode/decode support is intentionally limited to the vision helper
listed below. Schema validation is not performed by `Context.get`, `set`, or
`set_from`.

| Datatype class | Python support | Semantic helper |
|---|---|---|
| scalar bytes (`kt/common/int64_value`) | opaque bytes | not provided |
| structured bytes (`kt/common/blob_sample`, canonical JSON/FlatBuffer payloads) | opaque bytes | not provided |
| arrays and element collections | opaque bytes | unsupported typed helper |
| command, lighting, audio, speech, motor | opaque bytes | unsupported typed helper |
| proprioception, tactile, interoception, exteroception | opaque bytes | unsupported typed helper |
| state, spatial, recording, time, observability | opaque bytes | unsupported typed helper |
| `kt/vision/image_sample` | opaque bytes and typed RGB helper | `make_rgb_image`, `encode_image_sample`, `decode_image_sample_summary` |
| `kt/audition/voice_sample` | opaque bytes only | no canonical schema/helper in this release |

The complete canonical datatype registry remains owned by `kt_messages`.
Types without a semantic helper are explicitly unsupported for typed Python
encoding/decoding; the SDK must not guess their schema.

## Read and metadata contract

- `ReadMode.ONE` and `ReadMode.COUNT` apply to single-source inputs.
- `ReadMode.ALL_AVAILABLE` applies to single- and multi-source inputs.
- Native multi-source inputs reject `ONE` and `COUNT` with wrong-shape status.
- `Message.source_id` is present only for multi-source samples.
- `Message.remote_time_ns` is present only when the transport supplied a source
  timestamp and it fits signed 64-bit nanoseconds.
- Empty payloads are valid opaque messages.
- Python copies batch payloads, source IDs, and timestamps before destroying the
  borrowed native batch.
- ABI 1.2 write calls do not accept a remote timestamp. Python does not invent
  one; timestamped writes require a future ABI extension.

## Schema compatibility

The typed vision helper supports the checked-in `VSM1` file-identifier format
generated from the package's `bow.data.ImageSample` bindings. It rejects
payloads without that identifier. No old/new semantic schema pair is promised
for the first release, so no compatibility conversion is claimed.

Opaque payload forwarding is byte-for-byte and schema-agnostic. Compatibility
of those payloads remains a contract between the producer, consumer, and their
schema versions.

## Evidence

- `tests/live_data_model_conformance.py` drives a composite scalar, structured,
  empty, malformed-vision, and large opaque fixture through the real HTTP
  runtime and ABI 1.2/V2 callback boundary with `one`. It verifies write
  copy-in and a 64 MiB RSS-growth bound.
- `tests/test_data_model_conformance.py` covers `one`, `count`, and
  `all_available` marshaling and a 2 MiB payload deterministically at the ABI
  call boundary, independent of transport scheduling.
- `tests/test_data_model_conformance.py` deterministically checks binary copying,
  empty/large payloads, source IDs, and optional timestamps in Python's ABI
  batch marshaling.
- `tests/test_vision_contract.py` checks deterministic VSM1 encode/decode,
  stable malformed-payload rejection, exact 1080p metadata, and bounded peak RSS.
- Rust ABI tests remain authoritative for native multi-source shape rejection,
  timestamp overflow, and batch ownership/thread scope. Python preserves those
  fields without reinterpretation.
