# Error handling and shutdown

Public exceptions are stable enough for application-level handling:

| Exception | Meaning |
| --- | --- |
| `KtError` | Native operation failed |
| `AbiCompatibilityError` | Loaded ABI major is incompatible |
| `UnsupportedCapabilityError` | Required symbol or capability is absent |
| `ClosedResourceError` | Runtime or callback context is no longer valid |
| `ValueError` | Python argument, read-mode, or typed-payload validation failed |

Use `ctx.report_error()` to attach useful detail before returning a fatal outcome. Exceptions raised by callbacks are contained by the SDK and converted to fatal callback results.

For cooperative shutdown, call `ctx.request_close()` inside a callback or `runtime.request_close()` from another thread. Wait for `run()` to return before destroying the runtime. Destroying a running runtime is rejected as busy.
