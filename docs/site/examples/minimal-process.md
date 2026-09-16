# Minimal process

This exact file is compiled and exercised by the documentation test suite.

--8<-- "examples/minimal_process.py"

`EchoNode` is transport-neutral. The same `get` and `set` logic can run over HTTP or KT SHM when package and runtime JSON define the corresponding channels.
