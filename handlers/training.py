import mysql.connector
from mysql.connector import MySQLConnection
from mysql.connector.cursor import MySQLCursor
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler, CommandHandler

from config import MYSQL_HOST, MYSQL_PASSWORD, MYSQL_USER
from typing import cast
from logging import log, INFO

database: MySQLConnection = mysql.connector.connect(
    host=MYSQL_HOST,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD)

dbcursor: MySQLCursor = database.cursor()


async def add_exercise_entry(update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
    global dbcursor
    dbcursor.execute("USE training_module")
    await if_first_use(update, context)

    await update.message.reply_text("Specify exercise name")
    return "SPECIFY NAME"


async def add_exercise_specify_name(update: Update,
                                    context: ContextTypes.DEFAULT_TYPE):
    chat_data = cast(dict, context.chat_data)
    text = update.message.text
    chat_data["name"] = text

    chat_data["groups_buttons"] = [
        [InlineKeyboardButton("Chest", callback_data="Chest")],
        [InlineKeyboardButton("Back", callback_data="Back")], [InlineKeyboardButton("Legs", callback_data="Legs")],
        [InlineKeyboardButton("Shoulders", callback_data="Shoulders")],
        [InlineKeyboardButton("Biceps", callback_data="Biceps")],
        [InlineKeyboardButton("Triceps", callback_data="Triceps")],
        [InlineKeyboardButton("Abs", callback_data="Abs")]
    ]

    await update.message.reply_text("Specify muscle groups",
                                    reply_markup=InlineKeyboardMarkup(
                                        chat_data["groups_buttons"]))
    chat_data["groups"] = []
    chat_data["groups_buttons"].append(
        [InlineKeyboardButton("That's all", callback_data="STOP")])
    return "SPECIFY GROUPS"


async def add_exercise_specify_groups(update: Update,
                                      context: ContextTypes.DEFAULT_TYPE):
    chat_data = cast(dict, context.chat_data)
    muscle_group = update.callback_query.data
    for button in chat_data["groups_buttons"]:
        if button[0].text == muscle_group:
            chat_data["groups_buttons"].remove(button)
            break

    if muscle_group == "STOP":
        await update.callback_query.message.edit_text(
            f"Muscle groups: {', '.join(chat_data['groups'])}")
        await context.bot.send_message(
            update.callback_query.message.chat.id,
            "Specify difficulty",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Beginner", callback_data="Beginner")],
                 [
                     InlineKeyboardButton("Intermediate",
                                          callback_data="Intermediate")
                 ],
                 [InlineKeyboardButton("Advanced", callback_data="Advanced")],
                 [InlineKeyboardButton("Any", callback_data="Any")]]))
        return "SPECIFY DIFFICULTY"
    else:
        chat_data["groups"].append(muscle_group)
        await update.callback_query.message.edit_text(
            f"Specify muscle groups ({', '.join(chat_data['groups'])})",
            reply_markup=InlineKeyboardMarkup(chat_data["groups_buttons"]))


async def add_exercise_specify_difficulty(update: Update,
                                          context: ContextTypes.DEFAULT_TYPE):
    chat_data = cast(dict, context.chat_data)
    chat_data["difficulty"] = update.callback_query.data
    await update.callback_query.message.edit_text(
        "You can add a link to this exercise",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Add", callback_data="add")], 
             [InlineKeyboardButton("Skip", callback_data="skip")]]))
    return "ADD_LINK"


async def add_exercise_add_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    match update.callback_query.data:
        case "add":
            await update.callback_query.message.edit_text(
                "Send me the link",
                reply_markup=InlineKeyboardMarkup([]))
            return "ADD_TO_DATABASE"
        case "skip":
            return await add_exercise_add_to_database(update, context)


async def add_exercise_add_to_database(update: Update,
                                       context: ContextTypes.DEFAULT_TYPE):
    global dbcursor
    chat_data = cast(dict, context.chat_data)
    try:
        link = update.message.text
        message = update.message
        dbcursor.execute(
            f"""INSERT INTO exercises_%s (name, muscle_group, difficulty, link) 
        VALUES (%s, %s, %s, %s)""",
            (message.from_user.id, chat_data["name"], ' '.join(
                chat_data["groups"]), chat_data["difficulty"], link))

        await message.reply_text("Exercise added")
    except Exception:
        link = "No link"
        dbcursor.execute(
            f"""INSERT INTO exercises_%s (name, muscle_group, difficulty, link) 
        VALUES (%s, %s, %s, %s)""",
            (update.callback_query.from_user.id, chat_data["name"], ' '.join(
                chat_data["groups"]), chat_data["difficulty"], link))

        await update.callback_query.message.reply_text("Exercise added")
    return -1


async def generate_training(update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
    global dbcursor
    user_id = update.message.from_user.id
    dbcursor.execute("USE training_module")
    await if_first_use(update, context)

    dbcursor.execute("SELECT * FROM exercises_%s ORDER BY RAND() LIMIT 9",
                     (user_id, ))

    message_text = "\n".join(
            list(map(lambda x: " - ".join(list(map(lambda y: f"**{str(y)}**", x))[1:]),
             dbcursor.fetchall())))
    log(INFO, f"Message text: {message_text}")

    if message_text == "":
        await update.message.reply_text("You have no swampy exercises :(")
    else:
        await update.message.reply_text(f"**YOUR SWAMPY TRAINING:\n{message_text}", parse_mode='Markdown')
    return -1


async def if_first_use(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global dbcursor
    user_id, user_name = update.message.from_user.id, update.message.from_user.name
    dbcursor.execute("SELECT COUNT(1) FROM users WHERE user_id = %s",
                     (user_id, ))
    user_exists = bool(dbcursor.fetchone()[0])
    if user_exists:
        return

    dbcursor.execute("INSERT INTO users (user_id, user_name) VALUES (%s, %s)",
                     (user_id, user_name))
    dbcursor.execute(
        """CREATE TABLE exercises_%s (
        id INT NOT NULL AUTO_INCREMENT,
        name VARCHAR(255) NOT NULL,
        muscle_group VARCHAR(255),
        difficulty ENUM('Beginner', 'Intermediate', 'Advanced'),
        link VARCHAR(255),
        PRIMARY KEY (id)
        );""", (user_id, ))
    database.commit()


add_exercise_handler = ConversationHandler(
    entry_points=[CommandHandler('add_exercise', add_exercise_entry)],
    states={
        "SPECIFY NAME":
        [MessageHandler(filters.TEXT, add_exercise_specify_name)],
        "SPECIFY GROUPS": [CallbackQueryHandler(add_exercise_specify_groups)],
        "SPECIFY DIFFICULTY":
        [CallbackQueryHandler(add_exercise_specify_difficulty)],
        "ADD_LINK": [CallbackQueryHandler(add_exercise_add_link)],
        "ADD_TO_DATABASE":
        [MessageHandler(filters.TEXT, add_exercise_add_to_database)]
    },
    fallbacks=[])
generate_training_handler = CommandHandler('generate_training',
                                           generate_training)
