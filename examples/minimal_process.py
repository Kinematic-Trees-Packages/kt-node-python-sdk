"""Minimal transport-neutral KT process used by docs and tests."""

from ktnode import Context, Get, NextStep, Node, Set


class EchoNode(Node):
    """Echo one input payload to the output channel."""

    def step(self, ctx: Context) -> NextStep:
        value = Get(ctx, "in")
        if value is None:
            return NextStep.RECOVERABLE
        Set(ctx, "out", value)
        return NextStep.CONTINUE
