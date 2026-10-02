from ktnode import Context, Get, NextStep, Node, Set


class Relay(Node):
    def step(self, ctx: Context) -> NextStep:
        value = Get(ctx, "in")
        if value is None:
            return NextStep.RECOVERABLE
        Set(ctx, "out", value)
        return NextStep.CONTINUE
