import ktnode as kt


class Process(kt.Node):
    def step(self, ctx: kt.Context) -> kt.NextStep:
        # Read and write named channels; runtime JSON chooses the transport.
        return kt.NextStep.STOP
