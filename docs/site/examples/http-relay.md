# HTTP relay

The live conformance fixture uses the same process logic for HTTP and KT SHM:

--8<-- "examples/snippets/relay_node.py"

HTTP runtime JSON supplies a POST input route and GET output route. The process does not parse URLs or import an HTTP client. See the [complete tested fixture](https://github.com/Kinematic-Trees-Packages/kt-node-python-sdk/blob/main/tests/live_transport_conformance.py).
