# KT Node Python SDK

Tested Python wrapper for the frozen KT Node C ABI. The public API is provided by `ktnode`; raw `ctypes` bindings are internal implementation detail.

```python
from ktnode import Context, Node, NextStep

class EchoNode(Node):
    def step(self, ctx: Context) -> NextStep:
        messages = ctx.get("in")
        if not messages:
            return NextStep.RECOVERABLE
        ctx.set("out", messages[0].payload)
        return NextStep.CONTINUE
```

Build the versioned HTML documentation with `scripts/docs.sh`. The site covers installation, lifecycle, channels, data models, HTTP and KT SHM transports, packaging, deployment, API reference, compatibility, and troubleshooting.
