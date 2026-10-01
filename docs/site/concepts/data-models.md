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

Typed vision imports the `kt.messages.vision_sample` binding from the separately
versioned `kinematictrees/kt-messages` `data_types` package. Invalid identifiers
raise `ValueError`; the SDK does not own or duplicate generated datatype code.

`from kt.messages import *` imports all 26 schema namespaces. Generated types
remain qualified beneath those namespaces because names such as `Vector3`,
`Transform`, and `Environment` legitimately occur in multiple schemas.

See the [compatibility matrix](../compatibility.md) for explicit exclusions.
