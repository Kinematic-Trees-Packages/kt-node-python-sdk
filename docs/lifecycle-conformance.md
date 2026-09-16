# Python lifecycle and safety conformance

This document records the Python SDK's live conformance boundary for the
frozen KT Node ABI 1.2 contract. The acceptance fixture is
`tests/live_lifecycle_conformance.py`; it loads the real `libkt_node` and
does not substitute Python mocks for runtime behavior.

## Proven lifecycle matrix

| Case | Expected result |
| --- | --- |
| setup continue, step stop | setup → step → close; run succeeds |
| external close before run | setup → close; step is skipped |
| callback close request | setup → close; step is skipped |
| setup stop | setup → close; run succeeds |
| recoverable step then stop | setup → step → step → close |
| fatal setup | callback error with setup detail; close is not called |
| fatal step | callback error with step detail; close is called |
| Python exception in setup/step | exception is contained, reported, and returned as callback error |
| fatal/exception in close | close error is contained and logged; an otherwise successful run remains successful |
| repeated close | idempotent |
| operation after close | deterministic `ClosedResourceError` |
| failed construction | callback owner is released |

The close behavior reflects the native scheduler contract: close runs as
terminal cleanup, and a close failure does not replace the run's primary
result.

## Ownership and concurrency

- `Runtime` retains the Python node and all ctypes callback objects until
  native destruction completes.
- The callback owner is collectible after runtime destruction.
- `Context` is borrowed for one callback only and is invalidated immediately
  when that callback returns.
- Context use from a different thread is rejected by the native ABI.
- Lifecycle callbacks do not overlap. They may execute on different native
  worker threads, so the SDK does not promise permanent thread affinity.
- Destroying a running runtime is rejected as busy. A concurrent
  `request_close()` is allowed and the run thread terminates cleanly before
  destruction.
- Python callback exceptions are caught inside the ctypes trampoline and never
  unwind across the C ABI boundary.
- Python byte payloads passed through `bytes_view` are copied. Native-owned
  error, byte, and batch handles are destroyed by the SDK on every path.

## Stress budget

The acceptance run creates, runs, closes, and destroys 500 real runtimes in a
clean Ubuntu 24.04 container. It must:

- complete without a crash, hang, or double free;
- remain within 64 MiB of maximum-RSS growth;
- leave no usable callback contexts after callback return.

Validated result: 500 iterations passed in 2.621 seconds within the configured
64 MiB growth budget.

