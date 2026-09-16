# Runtime and process model

Your Python class implements an algorithm. The native runtime owns scheduling, transport threads, channel buffers, configuration, and shutdown.

```text
package/runtime JSON → libkt_node → ctypes ABI → ktnode.Runtime → your Node
```

`Runtime` negotiates the loaded ABI and selects V2 construction for ABI 1.2 or later when available. V1 remains the compatibility fallback.

Transport selection is intentionally absent from process code. The same `Node` implementation was tested over HTTP and KT SHM by changing runtime JSON only.

See [lifecycle and ownership](lifecycle-ownership.md) before retaining callback objects or coordinating shutdown.
