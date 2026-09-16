# Build a process

The complete minimal process is executable as `examples/minimal_process.py`.

--8<-- "examples/minimal_process.py"

The example is structurally tested without requiring a native runtime. A deployment passes package and runtime JSON paths to `Runtime` or the `run` convenience function.

Keep transport URLs, service names, and buffer policy in runtime JSON. Keep algorithm behavior in the `Node` subclass.
