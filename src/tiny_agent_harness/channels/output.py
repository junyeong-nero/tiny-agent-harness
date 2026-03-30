from typing import Callable

from tiny_agent_harness.schemas import Event


class OutputChannel:
    def __init__(self) -> None:
        self.channels: dict[str, Callable[[str, Event], None]] = {}

    def call(self, event: Event) -> None:
        for channel_name, channel_func in self.channels.items():
            channel_func(channel_name, event)

    def add_channel(
        self, channel_name: str, func: Callable[[str, Event], None]
    ) -> None:
        self.channels[channel_name] = func
