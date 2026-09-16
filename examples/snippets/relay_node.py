from ktnode import Context, NextStep, Node, ReadMode


class Relay(Node):
    def step(self, ctx: Context) -> NextStep:
        messages = ctx.get("in", ReadMode.ONE)
        if not messages:
            return NextStep.RECOVERABLE
        ctx.set("out", messages[0].payload)
        return NextStep.CONTINUE
