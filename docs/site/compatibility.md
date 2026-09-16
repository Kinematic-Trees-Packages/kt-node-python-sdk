# Compatibility

## Supported baseline

| Component | Tested contract |
| --- | --- |
| Python | 3.9–3.12 syntax and unit support |
| Python SDK | 0.2.x |
| C ABI | Major 1; frozen contract 1.2 |
| Constructor | V2 for ABI ≥1.2 when exported; V1 fallback |
| KTM packaging | v1.2.20+ v2 manifest contract |
| Proving platform | Ubuntu 24.04, Linux x86_64 |
| Required transports | HTTP, KT SHM |
| Typed data helper | RGB `kt/vision/image_sample` (`VSM1`) |

ABI major 1 is additive: V1 symbols remain available while V2 adds configuration-aware callbacks. ABI-major mismatch raises `AbiCompatibilityError` before runtime creation.

## Not claimed

- Windows or macOS runtime conformance
- ARM runtime conformance
- Typed Python helpers for non-vision canonical datatypes
- Python conformance for KT-LAN or WebRTC
- ROS1, ROS2, DDS, or KT-WAN support
- Hardware or robot deployment
- Compatibility conversion between untested schema revisions

These exclusions are explicit; the SDK does not emulate or silently substitute untested behavior.
