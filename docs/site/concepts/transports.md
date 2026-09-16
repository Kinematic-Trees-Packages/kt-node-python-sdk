# Transports

| Transport | Python v0.2 status |
| --- | --- |
| HTTP | Required and tested |
| KT SHM | Required and tested |
| KT-LAN | Capability advertised; not a Python release gate |
| WebRTC | Capability advertised; not a Python release gate |
| ROS1, ROS2, DDS, KT-WAN | Unsupported by this frozen Python contract |

HTTP tests cover request routing, output observation, external shutdown, and port reuse. KT SHM tests cover late discovery, safe overflow, reconnect, publisher restart, startup ordering, and bounded shutdown.

Call `runtime.require_capability(Capability.HTTP)` or `Capability.KT_SHM` when deployment requires a specific compiled feature. The SDK never falls back to another transport silently.
