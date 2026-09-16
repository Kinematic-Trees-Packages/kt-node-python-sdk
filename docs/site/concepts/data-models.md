# Data models

The C ABI transports opaque bytes. `Context.get`, `set`, and `set_from` preserve payload bytes without validating schemas.

## First-release typed surface

| Surface | Support |
| --- | --- |
| Scalars, arrays, structured records | Opaque bytes |
| Empty and binary payloads | Supported |
| Source IDs and remote timestamps | Preserved on reads when supplied |
| `kt/vision/image_sample` RGB data | Typed helper available |
| Other semantic models | No typed Python helper yet |

Typed vision uses the checked-in `VSM1` FlatBuffer binding. Invalid identifiers raise `ValueError`. The SDK makes no compatibility claim for untested schema versions.

See the [compatibility matrix](../compatibility.md) for explicit exclusions.
