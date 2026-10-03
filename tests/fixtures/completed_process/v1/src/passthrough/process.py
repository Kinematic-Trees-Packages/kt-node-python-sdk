import ktnode as kt


class Process(kt.Node):
    """Completed acceptance fixture; not the public generated starter."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.observed: list[str] = []
        self.config_updates: list[kt.ConfigUpdate] = []
        self.close_count = 0

    def setup(self, ctx: kt.Context) -> kt.NextStep:
        self.calls.append("setup")
        return kt.NextStep.CONTINUE

    def step(self, ctx: kt.Context) -> kt.NextStep:
        self.calls.append("step")
        value = kt.Get(ctx, "example_input")
        if value is not None:
            assert isinstance(value, str)
            self.observed.append(value)
            kt.Set(ctx, "example_output", value)
        return kt.NextStep.CONTINUE

    def close(self, ctx: kt.Context) -> kt.NextStep:
        self.calls.append("close")
        self.close_count += 1
        return kt.NextStep.STOP

    def config_update(
        self, ctx: kt.Context, update: kt.ConfigUpdate
    ) -> kt.ConfigUpdateResult:
        self.calls.append("config_update")
        self.config_updates.append(update)
        return kt.ConfigUpdateResult.ACCEPT
