import logging
from bot import Bot
from modules.nutrition import NutritionModule
from modules.speech import SpeechModule
from config import BOT_TOKEN
from modules.training import TrainingModule

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

jarvis = Bot(BOT_TOKEN)
jarvis.add_modules([NutritionModule, TrainingModule, SpeechModule])

jarvis.start()
