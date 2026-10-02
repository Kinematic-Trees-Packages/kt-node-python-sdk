# Channels and configuration

Channels are named in package metadata and bound to transports in runtime JSON. Python code addresses only the logical channel name.

```python
from ktnode import Get, Set

value = Get(ctx, "in")
if value is not None:
    Set(ctx, "out", value)
```

`Get` reads the datatype from the node package. `ReadMode.ONE` returns one
decoded value or `None`. Batch modes return `Received` objects so source IDs and
remote timestamps remain available. Use `ReadMode.COUNT` with a positive
`count` for a single-source channel. `ReadMode.ALL_AVAILABLE` supports single-
and multi-source inputs. Multi-source inputs reject `ONE` and `COUNT` at the
native boundary.

Use `ctx.get_raw`, `ctx.set_raw`, and `ctx.set_raw_from` only when deliberately
working with encoded bytes.

V2 callbacks can inspect `ctx.config()`, `ctx.config_revision()`, and a `ConfigUpdate`. The SDK does not invent configuration updates or silently accept unsupported capability combinations.
