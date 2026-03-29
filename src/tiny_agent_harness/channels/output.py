from tiny_agent_harness.schemas import OutputEvent


class OutputChannel:
    def __init__(self) -> None:
        self.channels: dict[str, callable] = {}

    def call(self, event: OutputEvent) -> None:
        for channel_name, channel_func in self.channels.items():
            channel_func(channel_name, event)

    def add_channel(self, channel_name: str, func) -> None:
        self.channels[channel_name] = func
