# Troubleshooting

## Native library discovery

**Symptom:** `Runtime` raises an error loading `libkt_node.so` or one of its native dependencies.

Use `ktm dev` or `ktm test`, or evaluate `ktm env --shell` before manual Python execution. `KTM_KT_NODE_LIBRARY` may point to an explicit library for SDK testing. Do not copy a single `.so` without its declared dependency closure.

## ABI mismatch

**Symptom:** `AbiCompatibilityError` reports an unsupported major.

Install the runtime version declared by the process package. SDK v0.2 requires ABI major 1; ABI 1.2 is the fully proven surface.

## Runtime configuration

**Symptom:** construction fails before callbacks run.

Check that runtime `id` matches package metadata, channel directions match, HTTP methods are valid for route direction, and KT SHM service names are valid. Invalid configurations fail explicitly and do not fall back.

## Missing transport capability

Call `runtime.require_capability(...)` after construction. A runtime compiled without the requested transport raises `UnsupportedCapabilityError`.

## Callback failed

Python exceptions are reported as `Python node <callback> failed: ...` and converted to fatal callback outcomes. Add domain context with `ctx.report_error()` and inspect the original exception.

## Context is closed

A `Context` object cannot be retained after a callback. Copy required data during the callback. Later access raises `ClosedResourceError`.

## Shutdown hangs or returns busy

Request close, wait for the thread running `Runtime.run()` to return, then call `Runtime.close()`. Destroying a running runtime is intentionally rejected.

## SHM peer starts late

KT SHM subscribers wait and rediscover peers. Verify both sides use the same service name and that it satisfies runtime service-name rules.
