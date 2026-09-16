"""Minimal transport-neutral KT process used by docs and tests."""

from ktnode import Context, NextStep, Node, ReadMode


class EchoNode(Node):
    """Echo one input payload to the output channel."""

    def step(self, ctx: Context) -> NextStep:
        messages = ctx.get("in", ReadMode.ONE)
        if not messages:
            return NextStep.RECOVERABLE
        ctx.set("out", messages[0].payload)
        return NextStep.CONTINUE
