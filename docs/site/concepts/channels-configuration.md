# Channels and configuration

Channels are named in package metadata and bound to transports in runtime JSON. Python code addresses only the logical channel name.

```python
messages = ctx.get("in", ReadMode.ONE)
ctx.set("out", messages[0].payload)
```

Use `ReadMode.COUNT` with a positive `count` for a single-source channel. `ReadMode.ALL_AVAILABLE` supports single- and multi-source inputs. Multi-source inputs reject `ONE` and `COUNT` at the native boundary.

V2 callbacks can inspect `ctx.config()`, `ctx.config_revision()`, and a `ConfigUpdate`. The SDK does not invent configuration updates or silently accept unsupported capability combinations.
