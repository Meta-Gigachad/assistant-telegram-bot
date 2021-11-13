from abc import ABC, abstractmethod
from typing import List
import telegram.ext as botAPI


class BotModule(ABC):
    def __init__(self, bot_dispatcher: botAPI.Dispatcher, handlers: List = []) -> None:
        self.bot_dispatcher = bot_dispatcher
        self.handlers = handlers

    def load_handlers(self) -> None:
        for handler in self.handlers:
            self.bot_dispatcher.add_handler(handler)
