# Data models

The C ABI transports opaque bytes. The Python SDK adds manifest-driven typed
access without changing that boundary:

- `Get(ctx, channel)` resolves the channel datatype and returns a natural value
  for an explicitly approved simple datatype or an immutable generated view for
  a complex datatype.
- `Set(ctx, channel, value)` validates and encodes the value for the declared
  output datatype.
- `Context.get_raw`, `set_raw`, and `set_raw_from` retain explicit byte access.

## First-release typed surface

| Surface | Support |
| --- | --- |
| Approved simple datatypes | Natural `str` or `int` values |
| Arrays and structured records | Immutable generated views |
| Empty and binary payloads | Supported |
| Source IDs and remote timestamps | Preserved on reads when supplied |
| `kt/vision/vision_sample` RGB data | Immutable view plus RGB helper |
| Every registered canonical datatype | Typed codec required |

The SDK resolves codecs from the separately versioned
`kinematic-trees/kt-messages` `data_types` package. Invalid identifiers fail as
`PayloadDecodeError`; wrong output values fail as `ValueEncodeError`. The SDK
does not own or duplicate generated datatype code.

`from kt.messages import *` imports all 26 schema namespaces. Generated types
remain qualified beneath those namespaces because names such as `Vector3`,
`Transform`, and `Environment` legitimately occur in multiple schemas.

See the [compatibility matrix](../compatibility.md) for explicit exclusions.
