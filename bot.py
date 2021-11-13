import logging
from typing import List
import telegram.ext as botAPI
from modules.base import BotModule


class Bot:
    def __init__(self, bot_token: str) -> None:
        self.TOKEN = bot_token
        self.updater = botAPI.Updater(self.TOKEN)
        self.modules = []
        self.dispatcher = self.updater.dispatcher

    def start(self) -> None:
        self.updater.start_polling()

    def stop(self) -> None:
        self.updater.stop()

    def add_modules(self, modules: List[type]) -> None:
        for module in modules:
            new_module = module(self.dispatcher)
            if isinstance(new_module, BotModule):
                new_module.load_handlers()
                self.modules.append(new_module)
            else:
                logging.log(0, f"Tried to add module {new_module}, which is not an instance of BotModule")
                del new_module
