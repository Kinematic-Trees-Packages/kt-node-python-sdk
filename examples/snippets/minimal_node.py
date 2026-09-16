from ktnode import Context, NextStep, Node


class Robot(Node):
    def step(self, ctx: Context) -> NextStep:
        # Read and write named channels; runtime JSON chooses the transport.
        return NextStep.STOP
