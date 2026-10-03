from ktnode import Context, Get, Node, NextStep, Set


class Robot(Node):
    """Completed acceptance fixture; not the public generated starter."""

    def step(self, ctx: Context) -> NextStep:
        value = Get(ctx, "text_in")
        if value is not None:
            Set(ctx, "text_out", value)
        return NextStep.CONTINUE
