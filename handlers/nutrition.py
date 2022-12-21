"""
Nutrition Module for Bot

Classes:
    NutritionModule - bot module it
    FoodItem - food item with it's properties
    FoodHistory - dated collection of instances of FoodItem class
    NutritionFacts - contains nutrients values, has overwritten arithmetics
"""
import logging
import re
import time

import mysql.connector
from mysql.connector.connection import MySQLConnection
from mysql.connector.cursor import MySQLCursor
from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from config import MYSQL_HOST, MYSQL_PASSWORD, MYSQL_USER
from typing import cast


class Object:
    pass


while True:
    try:
        database = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
        )
        break

    except mysql.connector.errors.DatabaseError as e:
        logging.log(
            logging.INFO,
            "Nutrition module waits for database to start",
        )
        logging.log(
            logging.INFO,
            e.msg
        )
        time.sleep(1)
        pass

dbcursor: MySQLCursor = database.cursor()


# food_history = FoodHistory()
async def food_stats_callback(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    global dbcursor
    dbcursor.execute("USE nutrition_module")
    logging.log(
        logging.INFO,
        f"{update.message.from_user.name} Requested Food Stats",
    )
    try:
        dbcursor.execute("""SELECT
            time(time), name, grams,
            calories * grams / 100 AS calories,
            protein * grams / 100 AS protein,
            fats * grams / 100 AS fats,
            carbohydrates * grams / 100 AS carbohydrates
            FROM history_303245273
            INNER JOIN food_dictionary
            ON food_dictionary.id = history_303245273.food_id
            WHERE date(time) = current_date();""")
        today_records = dbcursor.fetchall()

        dbcursor.execute("""SELECT
            SUM(calories * grams / 100) AS calories,
            SUM(protein * grams / 100) AS protein,
            SUM(fats * grams / 100) AS fats,
            SUM(carbohydrates * grams) / 100 AS carbohydrates
            FROM history_303245273
            INNER JOIN food_dictionary
            ON food_dictionary.id = history_303245273.food_id
            WHERE date(time) = current_date();""")
        today_totals = dbcursor.fetchone()
        message = "\n".join([
            "*--TODAY STATS--*",
            "*Eaten:*",
            "\n".join(
                map(
                    lambda x: "{}: {} {}g {}cal ({}p {}f {}c)".format(*x).
                    zfill(2),
                    today_records,
                )),
            "*Total:* {}cal\nprotein - {}g\nfats - {}g\ncarbs - {}g".format(
                *today_totals).zfill(2),
        ])
    except Exception:
        message = "Shrek: *growls* You haven't eaten any food today!"

    await update.message.reply_text(message, parse_mode="markdown")
    logging.log(logging.INFO, f"Responded:\n{message}")


async def add_food_entry_callback(update: Update,
                                  context: ContextTypes.DEFAULT_TYPE):
    global dbcursor
    chat_data = cast(dict, context.chat_data)

    dbcursor.execute("USE nutrition_module")
    dbcursor = dbcursor
    user_id = update.message.from_user.id
    user_name = update.message.from_user.name
    text = update.message.text
    chat_id = update.message.chat_id
    chat_data["food_item"] = Object()

    chat_data["user_id"] = user_id

    dbcursor.execute("SELECT COUNT(1) FROM users WHERE user_id = %s",
                     (user_id, ))
    user_exists = bool(dbcursor.fetchone()[0])

    if not user_exists:
        query = """CREATE TABLE history_%s (
            id INT NOT NULL AUTO_INCREMENT,
            time datetime not null default(current_timestamp),
            food_id INT NOT NULL,
            grams INT,
            PRIMARY KEY (id),
            FOREIGN KEY (food_id) REFERENCES food_dictionary(id)
            )"""
        dbcursor.execute(query, (user_id, ))
        dbcursor.execute(
            "INSERT INTO users (user_id, user_name) VALUES (%s, %s)",
            (user_id, user_name),
        )
        database.commit()

    match = re.match(r"^add food *(\w+) *(\d+gr)", text)
    food = chat_data["food_item"]
    if match:
        food.name = match[1]
        food.grams = int(match[2][:-2])

        dbcursor.execute("SELECT * FROM food_dictionary WHERE name = %s",
                         (food.name, ))
        buttons = []
        for food_item in dbcursor.fetchall():
            (
                food_id,
                name,
                calories,
                protein,
                fats,
                carbs,
                added_by_user,
            ) = food_item
            button = InlineKeyboardButton(
                f"{name}: {calories}cal ({protein}p, {fats}f, {carbs}c)",
                callback_data=f"FOOD_ID:{food_id}",
            )
            buttons.append([button])
        buttons.append([
            InlineKeyboardButton("Add my own food item",
                                 callback_data="ADD_NEW")
        ])

        await context.bot.send_message(
            chat_id,
            "Which food do you want to add?",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return "CHOOSE_ITEM"

    match = re.match(r"^add food *(\w+)", text)
    if match:
        food.name = match[1]

        await context.bot.send_message(chat_id, "Specify grams")
        return "SPECIFY_GRAMS"

    await context.bot.send_message(chat_id, "Specify food name")
    return "SPECIFY_NAME"


async def add_food_state_name_callback(update: Update,
                                       context: ContextTypes.DEFAULT_TYPE):
    chat_data = cast(dict, context.chat_data)

    text = update.message.text
    chat_id = update.message.chat_id
    food = chat_data["food_item"]

    food.name = text.strip()
    await context.bot.send_message(chat_id, "Specify grams")
    return "SPECIFY_GRAMS"


async def add_food_state_grams_callback(update: Update,
                                        context: ContextTypes.DEFAULT_TYPE):
    global dbcursor
    chat_data = cast(dict, context.chat_data)

    text = update.message.text
    chat_id = update.message.chat_id
    food = chat_data["food_item"]
    dbcursor = dbcursor

    food.grams = int(text.strip())

    dbcursor.execute("SELECT * FROM food_dictionary WHERE name = %s",
                     (food.name, ))
    buttons = []
    for food_item in dbcursor.fetchall():
        (
            food_id,
            name,
            calories,
            protein,
            fats,
            carbs,
            added_by_user,
        ) = food_item
        button = InlineKeyboardButton(
            f"{name}: {calories}cal ({protein}p, {fats}f, {carbs}c)",
            callback_data=f"FOOD_ID:{food_id}",
        )
        buttons.append([button])
    buttons.append([
        InlineKeyboardButton("Add my own food item", callback_data="ADD_NEW")
    ])

    await context.bot.send_message(
        chat_id,
        "Which food do you want to add?",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return "CHOOSE_ITEM"


async def add_food_state_choose_item_callback(
        update: Update, context: ContextTypes.DEFAULT_TYPE):
    global dbcursor
    chat_data = cast(dict, context.chat_data)
    food = chat_data["food_item"]
    user_id = chat_data["user_id"]

    answer = update.callback_query.data

    await update.callback_query.message.edit_reply_markup()

    match = re.match(r"FOOD_ID:(\d+)", answer)
    if match:
        food_id = int(match[1])
        dbcursor.execute(
            "INSERT INTO history_%s (food_id, grams) VALUES (%s, %s)",
            (user_id, food_id, food.grams),
        )
        database.commit()
        dbcursor.execute("SELECT name FROM food_dictionary WHERE id = %s",
                         (food_id, ))
        await update.callback_query.message.edit_text(
            f"{dbcursor.fetchone()[0]} was successfully added")
        return -1

    if answer == "ADD_NEW":
        await update.callback_query.message.edit_text("Ok. Specify calories")
        return "SPECIFY_CALORIES"


async def add_food_state_calories_callback(update: Update,
                                           context: ContextTypes.DEFAULT_TYPE):
    chat_data = cast(dict, context.chat_data)
    text = update.message.text
    chat_id = update.message.chat_id
    food = chat_data["food_item"]

    food.calories = int(text.strip())
    await context.bot.send_message(chat_id,
                                   "Specify protein, fats and carbohydrates")
    return "SPECIFY_PFC"


async def add_food_state_pfc_callback(update: Update,
                                      context: ContextTypes.DEFAULT_TYPE):
    global dbcursor
    chat_data = cast(dict, context.chat_data)
    text = update.message.text
    chat_id = update.message.chat_id
    food = chat_data["food_item"]
    user_id = chat_data["user_id"]

    match = re.match(
        r"([+-]?([0-9]*[.])?[0-9]+) ([+-]?([0-9]*[.])?[0-9]+) ([+-]?([0-9]*[.])?[0-9]+)",
        text,
    )
    if match:
        food.protein = float(match[1])
        food.fats = float(match[3])
        food.carbohydrates = float(match[5])

        dbcursor.execute(
            """INSERT INTO food_dictionary
        (name, calories, protein, fats, carbohydrates, added_by_user)
        VALUES (%s, %s, %s, %s, %s, %s)""",
            (
                food.name,
                food.calories,
                food.protein,
                food.fats,
                food.carbohydrates,
                user_id,
            ),
        )
        database.commit()

        food_id = dbcursor.lastrowid

        dbcursor.execute(
            "INSERT INTO history_%s (food_id, grams) VALUES (%s, %s)",
            (user_id, food_id, food.grams),
        )
        database.commit()
        await context.bot.send_message(chat_id, "Food was successfully added")
        return -1


add_food_handler = ConversationHandler(
    entry_points=[CommandHandler("add_food", add_food_entry_callback)],
    states={
        "SPECIFY_NAME": [
            MessageHandler(
                filters.TEXT,
                callback=add_food_state_name_callback,
            )
        ],
        "SPECIFY_GRAMS": [
            MessageHandler(
                filters.TEXT,
                callback=add_food_state_grams_callback,
            )
        ],
        "CHOOSE_ITEM":
        [CallbackQueryHandler(callback=add_food_state_choose_item_callback)],
        "SPECIFY_CALORIES": [
            MessageHandler(
                filters.TEXT,
                callback=add_food_state_calories_callback,
            )
        ],
        "SPECIFY_PFC":
        [MessageHandler(filters.TEXT, callback=add_food_state_pfc_callback)],
    },
    fallbacks=[CommandHandler("add_food", add_food_entry_callback)],
)

food_stats_handler = CommandHandler("food_stats", food_stats_callback)
