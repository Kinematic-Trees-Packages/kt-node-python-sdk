from ktnode import (
    ConfigUpdate,
    ConfigUpdateResult,
    Context,
    Get,
    Node,
    NextStep,
    Set,
)


class Robot(Node):
    """Completed acceptance fixture; not the public generated starter."""

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.observed: list[str] = []
        self.config_updates: list[ConfigUpdate] = []
        self.close_count = 0

    def setup(self, ctx: Context) -> NextStep:
        self.calls.append("setup")
        return NextStep.CONTINUE

    def step(self, ctx: Context) -> NextStep:
        self.calls.append("step")
        value = Get(ctx, "example_input")
        if value is not None:
            assert isinstance(value, str)
            self.observed.append(value)
            Set(ctx, "example_output", value)
        return NextStep.CONTINUE

    def close(self, ctx: Context) -> NextStep:
        self.calls.append("close")
        self.close_count += 1
        return NextStep.STOP

    def config_update(
        self, ctx: Context, update: ConfigUpdate
    ) -> ConfigUpdateResult:
        self.calls.append("config_update")
        self.config_updates.append(update)
        return ConfigUpdateResult.ACCEPT
