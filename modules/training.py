import mysql.connector
from mysql.connector import MySQLConnection
from mysql.connector.cursor import MySQLCursor
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import MessageHandler, Filters, CallbackContext, ConversationHandler, CallbackQueryHandler

from config import SQL_DATABASE
from modules.base import BotModule
import telegram.ext as bot_api


class TrainingModule(BotModule):
    def __init__(self, dispatcher: bot_api.Dispatcher):
        super().__init__(
            dispatcher,
            [
                ConversationHandler(
                    entry_points=[MessageHandler(Filters.regex(r'^add exercise'), self.add_exercise_entry)],
                    states={
                        "SPECIFY NAME": [MessageHandler(Filters.text, self.add_exercise_specify_name)],
                        "SPECIFY GROUPS": [CallbackQueryHandler(self.add_exercise_specify_groups)],
                        "SPECIFY DIFFICULTY": [CallbackQueryHandler(self.add_exercise_specify_difficulty)],
                        "ADD_TO_DATABASE": [CallbackQueryHandler(self.add_exercise_add_to_database)]
                    },
                    fallbacks=[]
                ),
                MessageHandler(Filters.regex(r'^generate training'), self.generate_training)
            ]
        )

        self.database: MySQLConnection = mysql.connector.connect(
            host=SQL_DATABASE['host'],
            user=SQL_DATABASE['user'],
            password=SQL_DATABASE['password']
        )

        self.dbcursor: MySQLCursor = self.database.cursor()

    def add_exercise_entry(self, update: Update, context: CallbackContext):
        self.dbcursor.execute("USE training_module")
        self.if_first_use(update, context)

        update.message.reply_text("Specify exercise name")
        return "SPECIFY NAME"

    def add_exercise_specify_name(self, update: Update, context: CallbackContext):
        text = update.message.text
        context.chat_data["name"] = text

        context.chat_data["groups_buttons"] = [
            [InlineKeyboardButton("Chest", callback_data="Chest")],
            [InlineKeyboardButton("Back", callback_data="Back")],
            [InlineKeyboardButton("Legs", callback_data="Legs")],
            [InlineKeyboardButton("Shoulders", callback_data="Shoulders")],
            [InlineKeyboardButton("Biceps", callback_data="Biceps")],
            [InlineKeyboardButton("Triceps", callback_data="Triceps")],
            [InlineKeyboardButton("Abs", callback_data="Abs")]
        ]

        update.message.reply_text("Specify muscle groups",
                                  reply_markup=InlineKeyboardMarkup(context.chat_data["groups_buttons"]))
        context.chat_data["groups"] = []
        context.chat_data["groups_buttons"].append([InlineKeyboardButton("That's all", callback_data="STOP")])
        return "SPECIFY GROUPS"

    def add_exercise_specify_groups(self, update: Update, context: CallbackContext):
        muscle_group = update.callback_query.data
        for button in context.chat_data["groups_buttons"]:
            if button[0].text == muscle_group:
                context.chat_data["groups_buttons"].remove(button)
                break

        if muscle_group == "STOP":
            update.callback_query.message.edit_text(f"Muscle groups: {', '.join(context.chat_data['groups'])}")
            context.bot.send_message(update.callback_query.message.chat.id,
                                     "Specify difficulty", reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Beginner", callback_data="Beginner")],
                    [InlineKeyboardButton("Intermediate", callback_data="Intermediate")],
                    [InlineKeyboardButton("Advanced", callback_data="Advanced")],
                    [InlineKeyboardButton("Any", callback_data="Any")]
                ]))
            return "SPECIFY DIFFICULTY"
        else:
            context.chat_data["groups"].append(muscle_group)
            update.callback_query.message.edit_text(f"Specify muscle groups ({', '.join(context.chat_data['groups'])})",
                                                    reply_markup=InlineKeyboardMarkup(
                                                        context.chat_data["groups_buttons"]))

    def add_exercise_specify_difficulty(self, update: Update, context: CallbackContext):
        context.chat_data["difficulty"] = update.callback_query.data
        update.callback_query.message.edit_text("You can add a link to this exercise",
                                                reply_markup=InlineKeyboardMarkup(
                                                    [[InlineKeyboardButton("Skip", callback_data="Null")]]))
        return "ADD_TO_DATABASE"

    def add_exercise_add_to_database(self, update: Update, context: CallbackContext):
        link = update.callback_query.data
        self.dbcursor.execute(f"""INSERT INTO exercises_%s (name, muscle_group, difficulty, link) 
        VALUES (%s, %s, %s, %s)""",
                              (
                                  update.callback_query.from_user.id,
                                  context.chat_data["name"],
                                  ' '.join(context.chat_data["groups"]),
                                  context.chat_data["difficulty"],
                                  link
                              ))

        update.callback_query.message.edit_text("Exercise added")
        return -1

    def generate_training(self, update: Update, context: CallbackContext):
        self.dbcursor.execute("USE training_module")
        self.if_first_use(update, context)

    def if_first_use(self, update: Update, context: CallbackContext):
        user_id, user_name = update.message.from_user.id, update.message.from_user.name
        self.dbcursor.execute("SELECT COUNT(1) FROM users WHERE user_id = %s", (user_id,))
        user_exists = bool(self.dbcursor.fetchone()[0])
        if user_exists:
            return

        self.dbcursor.execute("INSERT INTO users (user_id, user_name) VALUES (%s, %s)", (user_id, user_name))
        self.dbcursor.execute("""CREATE TABLE exercises_%s (
            id INT NOT NULL AUTO_INCREMENT,
            name VARCHAR(255) NOT NULL,
            muscle_group VARCHAR(255),
            difficulty ENUM('Beginner', 'Intermediate', 'Advanced'),
            link VARCHAR(255),
            PRIMARY KEY (id)
            );""", (user_id,))
        self.database.commit()
