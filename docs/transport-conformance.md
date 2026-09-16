# Python transport conformance

The Python SDK is transport-neutral. Process code uses only `Context.get`,
`Context.set`, and lifecycle methods; runtime JSON owns transport selection.

## First-release matrix

| Transport | Status | Evidence |
|---|---|---|
| HTTP | Required | Live Python relay; POST input, GET output, clean shutdown and port reuse |
| KT SHM | Required | Live Python relay with iceoryx2 peer; late discovery, overflow, echo, clean shutdown |
| WebRTC | Optional/unproven | Advertised by the ABI capability bit, but not a Python release gate |
| KT-LAN | Optional/unproven | Advertised by the ABI capability bit, but not a Python release gate |
| ROS1, ROS2, DDS, KT-WAN | Unsupported for this Python release | No frozen ABI capability bit and no Python conformance fixture |

Unsupported or uncompiled transports fail during runtime configuration or
through `Runtime.require_capability`; the SDK does not substitute another
transport.

## Shared process fixture

`tests/live_transport_conformance.py` uses one `RelayProbe` implementation for
both required transports. Only generated runtime JSON and the external test
driver differ. The fixture proves scalar/blob bytes and the same opaque bytes
used for typed vision payloads; vision encoding semantics are frozen separately
by `tests/test_data_model_conformance.py`.

HTTP proves request routing, output observability, callback lifecycle, clean
shutdown, and port release. KT SHM proves subscriber-before-publisher late
discovery, a burst larger than the configured two-sample safe-overflow buffer,
payload echo, and clean shutdown. Runtime-owned SHM tests additionally freeze
publisher restart, rediscovery, every startup ordering, and bounded shutdown.

## Failure and recovery behavior

- Invalid route direction/method, invalid service names, unsupported TLS HTTP,
  and unavailable transport implementations fail during runtime creation with
  an explicit configuration error.
- HTTP connection attempts before listener startup are retried only by the test
  client; the SDK does not hide connection failure.
- KT SHM subscribers report disconnected/waiting states and reconnect after a
  publisher appears or restarts. The Python process is unchanged.
- SHM safe overflow drops older buffered samples when producers outrun the
  configured capacity. The final marker payload remains observable.
- `Runtime.request_close` and `Runtime.close` use the same lifecycle path for
  every transport; transport threads must stop before destruction returns.

## Acceptance evidence

Validated on 2026-09-16 against ABI 1.2 from the pinned Ubuntu 24.04 builder:

- HTTP live relay: 21-byte opaque scalar/vision marker echoed and observed;
  external close completed and the runtime-owned repeated-port test passed.
- KT SHM live relay: 16 samples burst into a two-sample safe-overflow buffer;
  the final 21-byte marker was echoed after late peer discovery.
- All 14 runtime-owned KT SHM validation/reconnect/restart/startup-order tests
  passed.
- Runtime-owned HTTP event callback, external cancellation, and repeated port
  release tests passed.
- Invalid HTTP method and invalid SHM service fixtures failed at runtime
  creation with explicit diagnostics.
- The complete Python suite passed: 26 tests plus 3 subtests.
