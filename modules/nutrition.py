"""
Nutrition Module for Bot

Classes:
    NutritionModule - bot module itself
    FoodItem - food item with it's properties
    FoodHistory - dated collection of instances of FoodItem class
    NutritionFacts - contains nutrients values, has overwritten arithmetics
"""
import logging
import re

import mysql.connector
import telegram.ext as bot_api
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursor
from telegram import ReplyMarkup
from telegram.ext import Filters
from telegram.ext.callbackqueryhandler import CallbackQueryHandler
from telegram.ext.conversationhandler import ConversationHandler
from telegram.ext.messagehandler import MessageHandler
from telegram.inline.inlinekeyboardbutton import InlineKeyboardButton
from telegram.inline.inlinekeyboardmarkup import InlineKeyboardMarkup
from telegram.update import Update

from modules.base import BotModule
from config import SQL_DATABASE


class NutritionModule(BotModule):
    def __init__(self, dispatcher: bot_api.Dispatcher):
        super().__init__(
            dispatcher,
            [
                ConversationHandler(
                    entry_points=[MessageHandler(Filters.regex(r'^add food'), self._add_food_entry)],
                    states={
                        "SPECIFY_NAME": [MessageHandler(Filters.text, callback=self._add_food_state_name)],
                        "SPECIFY_GRAMS": [MessageHandler(Filters.text, callback=self._add_food_state_grams)],
                        "CHOOSE_ITEM": [CallbackQueryHandler(callback=self._add_food_state_choose_item)],
                        "SPECIFY_CALORIES": [
                            MessageHandler(Filters.text, callback=self._add_food_state_calories)],
                        "SPECIFY_PFC": [MessageHandler(Filters.text, callback=self._add_food_state_pfc)]
                    },
                    fallbacks=[MessageHandler(Filters.regex(r'^add food'), self._add_food_entry)]
                ),
                MessageHandler(Filters.regex(r'^food stats'), self._food_stats)
            ]
        )

        self.database: MySQLConnection = mysql.connector.connect(
            host=SQL_DATABASE['host'],
            user=SQL_DATABASE['user'],
            password=SQL_DATABASE['password']
        )

        self.dbcursor: MySQLCursor = self.database.cursor()
        # self.food_history = FoodHistory()

    def _food_stats(self, update: Update, context: bot_api.CallbackContext):
        self.dbcursor.execute("USE nutrition_module")
        logging.log(logging.INFO, f"{update.message.from_user.name} Requested Food Stats")
        self.dbcursor.execute('''SELECT 
            time(time), name, grams,
            calories * grams / 100 AS calories,
            protein * grams / 100 AS protein,
            fats * grams / 100 AS fats,
            carbohydrates * grams / 100 AS carbohydrates
            FROM history_303245273
            INNER JOIN food_dictionary
            ON food_dictionary.id = history_303245273.food_id
            WHERE date(time) = current_date();''')
        today_records = self.dbcursor.fetchall()

        self.dbcursor.execute("""SELECT
            SUM(calories * grams / 100) AS calories,
            SUM(protein * grams / 100) AS protein,
            SUM(fats * grams / 100) AS fats,
            SUM(carbohydrates * grams) / 100 AS carbohydrates
            FROM history_303245273
            INNER JOIN food_dictionary
            ON food_dictionary.id = history_303245273.food_id
            WHERE date(time) = current_date();""")
        today_totals = self.dbcursor.fetchone()

        message = "\n".join([
            "*--TODAY STATS--*",
            "*Eaten:*",
            "\n".join(map(lambda x: "{}: {} {}g {}cal ({}p {}f {}c)".format(*x).zfill(2), today_records)),
            "*Total:* {}cal\nprotein - {}g\nfats - {}g\ncarbs - {}g".format(*today_totals).zfill(2)
        ])

        update.message.reply_text(message, parse_mode="markdown")
        logging.log(logging.INFO, f"Responded:\n{message}")

    def _add_food_entry(self, update: Update, context: bot_api.CallbackContext):
        self.dbcursor.execute("USE nutrition_module")
        dbcursor = self.dbcursor
        user_id = update.message.from_user.id
        user_name = update.message.from_user.name
        text = update.message.text
        chat_id = update.message.chat_id
        context.chat_data['food_item'] = Object()

        context.chat_data['user_id'] = user_id

        dbcursor.execute("SELECT COUNT(1) FROM users WHERE user_id = %s", (user_id,))
        user_exists = bool(dbcursor.fetchone()[0])

        if not user_exists:
            query = '''CREATE TABLE history_%s (
                id INT NOT NULL AUTO_INCREMENT,
                time datetime not null default(current_timestamp),
                food_id INT NOT NULL,
                grams INT,
                PRIMARY KEY (id),
                FOREIGN KEY (food_id) REFERENCES food_dictionary(id)
                )'''
            dbcursor.execute(query, (user_id,))
            dbcursor.execute("INSERT INTO users (user_id, user_name) VALUES (%s, %s)", (user_id, user_name))
            self.database.commit()

        match = re.match(r'^add food *(\w+) *(\d+gr)', text)
        food = context.chat_data['food_item']
        if match:
            food.name = match[1]
            food.grams = int(match[2][:-2])

            dbcursor.execute("SELECT * FROM food_dictionary WHERE name = %s", (food.name,))
            buttons = []
            for food_item in dbcursor.fetchall():
                food_id, name, calories, protein, fats, carbs, added_by_user = food_item
                button = InlineKeyboardButton(f"{name}: {calories}cal ({protein}p, {fats}f, {carbs}c)",
                                              callback_data=f"FOOD_ID:{food_id}")
                buttons.append([button])
            buttons.append([InlineKeyboardButton("Add my own food item", callback_data="ADD_NEW")])

            context.bot.send_message(chat_id, "Which food do you want to add?",
                                     reply_markup=InlineKeyboardMarkup(buttons))
            return "CHOOSE_ITEM"

        match = re.match(r'^add food *(\w+)', text)
        if match:
            food.name = match[1]

            context.bot.send_message(chat_id, "Specify grams")
            return "SPECIFY_GRAMS"

        context.bot.send_message(chat_id, "Specify food name")
        return "SPECIFY_NAME"

    @staticmethod
    def _add_food_state_name(update: Update, context: bot_api.CallbackContext):
        text = update.message.text
        chat_id = update.message.chat_id
        food = context.chat_data['food_item']

        food.name = text.strip()
        context.bot.send_message(chat_id, "Specify grams")
        return "SPECIFY_GRAMS"

    def _add_food_state_grams(self, update: Update, context: bot_api.CallbackContext):
        text = update.message.text
        chat_id = update.message.chat_id
        food = context.chat_data['food_item']
        dbcursor = self.dbcursor

        food.grams = int(text.strip())

        dbcursor.execute("SELECT * FROM food_dictionary WHERE name = %s", (food.name,))
        buttons = []
        for food_item in dbcursor.fetchall():
            food_id, name, calories, protein, fats, carbs, added_by_user = food_item
            button = InlineKeyboardButton(f"{name}: {calories}cal ({protein}p, {fats}f, {carbs}c)",
                                          callback_data=f"FOOD_ID:{food_id}")
            buttons.append([button])
        buttons.append([InlineKeyboardButton("Add my own food item", callback_data="ADD_NEW")])

        context.bot.send_message(chat_id, "Which food do you want to add?", reply_markup=InlineKeyboardMarkup(buttons))
        return "CHOOSE_ITEM"

    def _add_food_state_choose_item(self, update: Update, context: bot_api.CallbackContext):
        food = context.chat_data['food_item']
        user_id = context.chat_data['user_id']
        dbcursor = self.dbcursor

        answer = update.callback_query.data

        update.callback_query.message.edit_reply_markup()

        match = re.match(r'FOOD_ID:(\d+)', answer)
        if match:
            food_id = int(match[1])
            dbcursor.execute("INSERT INTO history_%s (food_id, grams) VALUES (%s, %s)", (user_id, food_id, food.grams))
            self.database.commit()
            dbcursor.execute("SELECT name FROM food_dictionary WHERE id = %s", (food_id,))
            update.callback_query.message.edit_text(f"{dbcursor.fetchone()[0]} was successfully added")
            return -1

        if answer == "ADD_NEW":
            update.callback_query.message.edit_text("Ok. Specify calories")
            return "SPECIFY_CALORIES"

    @staticmethod
    def _add_food_state_calories(update: Update, context: bot_api.CallbackContext):
        text = update.message.text
        chat_id = update.message.chat_id
        food = context.chat_data['food_item']

        food.calories = int(text.strip())
        context.bot.send_message(chat_id, "Specify protein, fats and carbohydrates")
        return "SPECIFY_PFC"

    def _add_food_state_pfc(self, update: Update, context: bot_api.CallbackContext):
        text = update.message.text
        chat_id = update.message.chat_id
        food = context.chat_data['food_item']
        user_id = context.chat_data['user_id']
        dbcursor = self.dbcursor

        match = re.match(r'([+-]?([0-9]*[.])?[0-9]+) ([+-]?([0-9]*[.])?[0-9]+) ([+-]?([0-9]*[.])?[0-9]+)', text)
        if match:
            food.protein = float(match[1])
            food.fats = float(match[3])
            food.carbohydrates = float(match[5])

            dbcursor.execute('''INSERT INTO food_dictionary 
            (name, calories, protein, fats, carbohydrates, added_by_user) 
            VALUES (%s, %s, %s, %s, %s, %s)''',
                             (food.name, food.calories, food.protein, food.fats, food.carbohydrates, user_id))
            self.database.commit()

            food_id = dbcursor.lastrowid

            dbcursor.execute("INSERT INTO history_%s (food_id, grams) VALUES (%s, %s)", (user_id, food_id, food.grams))
            self.database.commit()
            context.bot.send_message(chat_id, "Food was successfully added")
            return -1


class Object:
    pass
