import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

from telegram.ext import ApplicationBuilder
from handlers.nutrition import add_food_handler, food_stats_handler
from handlers.training import add_exercise_handler, generate_training_handler
from handlers.speech import talking_text_handler, talking_voice_handler, who_are_you_from_shrek_handler
from config import BOT_TOKEN

if __name__ == '__main__':

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handlers([
        add_food_handler, food_stats_handler, add_exercise_handler,
        generate_training_handler, who_are_you_from_shrek_handler,
        talking_text_handler, talking_voice_handler
    ])

    application.run_polling()
