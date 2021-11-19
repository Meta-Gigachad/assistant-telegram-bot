# Assistant Telegram Bot
Toy assistant bot, with modular structure.

## Current functionality

* **Generates responses** to all user messages exept specific commands. Uses *"HansAnonymous/DialoGPT-small-shrek"* model for that
* **Translates user voice messages** by using *Google Speech-To-Text API* and responds to them
* Has **Nutrition Module** which stores info about food eaten by *user* and has commands:
  * `add food` - adds eaten food to the user food history. You can use food item that is already added to the database, or add your own
  *  `food stats` - returns information about food eaten today

## Custom Modules

You can add your own modules to the bot. You should inherit it from `modules.base.BotModule` use [telegram.ext](https://python-telegram-bot.readthedocs.io/en/stable/index.html) for it. Here is a sample Module class
```python
from modules.base import BotModule
from telegram.ext import Dispatcher


class SampleModule(BotModule):
    def __init__(self, dispatcher: Dispatcher):
        super().__init__(
            dispatcher,
            [handler_1, handler_2]
        )
```

Then just add your module to the bot
```python
my_bot = Bot(BOT_TOKEN)
my_bot.add_modules([SampleModule, NutritionModule, TrainingModule, SpeechModule])
```
