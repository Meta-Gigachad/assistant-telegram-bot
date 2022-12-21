"""
Speech Module

Implements voice message recognition and transformers model for answer generation
"""

import logging
import os
import subprocess
from random import choice

from speech_recognition import Recognizer, AudioFile, UnknownValueError
from telegram import Update

from telegram.ext import MessageHandler, filters, ContextTypes, CommandHandler

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import gc
from pathlib import Path

recognizer = Recognizer()
tokenizer = AutoTokenizer.from_pretrained("HansAnonymous/DialoGPT-small-shrek")
model = AutoModelForCausalLM.from_pretrained(
    "HansAnonymous/DialoGPT-small-shrek")
chat_histories = {}
previous_responses = []
response_model = (model, tokenizer, chat_histories)
gc.collect()


async def talking_voice_callback(update: Update,
                                 context: ContextTypes.DEFAULT_TYPE):
    global recognizer
    voice = await update.message.voice.get_file()

    current_directory = os.path.dirname(os.path.abspath(__file__))
    Path(current_directory + "/../data/voice_messages").mkdir(parents=True, exist_ok=True)
    wav_voice_path = current_directory + f"/../data/voice_messages/recognition{update.message.id}.wav"
    subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', voice.file_path,
        '-y', '-ar', '16000', wav_voice_path
    ])

    await update.message.delete()
    sent_message = await update.message.reply_text("Listening...")

    with AudioFile(wav_voice_path) as file:
        try:
            transcription = recognizer.recognize_google(
                recognizer.record(file))
            await sent_message.edit_text(f"*You say:* _{transcription}_",
                                         parse_mode='markdown')
            logging.log(
                logging.INFO,
                f"""Got voice: {update.message.from_user.name} -> {transcription}"""
            )
            chat_id, user_id = update.message.chat_id, update.message.from_user.id
            response = generate_response(transcription, user_id)
            await context.bot.send_message(chat_id, f"{response}")
            logging.log(logging.INFO, f"""Responded: BOT -> {response}""")
        except UnknownValueError:
            await sent_message.edit_text(f"Can't hear you")


async def talking_text_callback(update: Update,
                                context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    logging.log(logging.INFO,
                f"""Got message: {update.message.from_user.name} -> {text}""")

    chat_id, user_id = update.message.chat_id, update.message.from_user.id
    sent_message = await context.bot.send_message(chat_id,
                                                  "_Typing..._",
                                                  parse_mode='markdown')
    response = await generate_response(text, user_id)
    await sent_message.edit_text(f"{response}")
    logging.log(logging.INFO, f"""Responded: BOT -> {response}""")


async def generate_response(message: str, user_id: int):
    global response_model, previous_responses
    model, tokenizer, chat_histories = response_model

    new_user_input_ids = tokenizer.encode(message + tokenizer.eos_token,
                                          return_tensors='pt')
    try:
        chat_history_ids = chat_histories[user_id]
        bot_input_ids = torch.cat([chat_history_ids, new_user_input_ids],
                                  dim=-1)
    except KeyError:
        bot_input_ids = new_user_input_ids

    chat_history_ids = model.generate(bot_input_ids,
                                      max_length=40,
                                      pad_token_id=tokenizer.eos_token_id)

    if len(chat_history_ids[0]) > 30:
        chat_histories[user_id] = chat_history_ids[:,
                                                   len(chat_history_ids[0]):]
    else:
        chat_histories[user_id] = chat_history_ids

    response = tokenizer.decode(chat_history_ids[:,
                                                 bot_input_ids.shape[-1]:][0],
                                skip_special_tokens=True)
    if response in previous_responses or response == message:
        chat_histories[user_id] = chat_history_ids[:,
                                                   len(chat_history_ids[0]):]
        response = "..."
    if len(previous_responses) == 3:
        previous_responses.pop(0)
    previous_responses.append(response)

    return response


async def who_are_you_from_shrek_callback(update: Update,
                                          context: ContextTypes.DEFAULT_TYPE):
    characters = [
        "Shrek", "Donkey", "Princess Fiona", "Lord Farquaad", "Robin Hood",
        "Puss in Boots", "Fairy Godmother"
    ]
    await update.message.reply_text(f"You are {choice(characters)}")

    return -1


talking_voice_handler = MessageHandler(filters.VOICE, talking_voice_callback)
talking_text_handler = MessageHandler(filters.TEXT, talking_text_callback)
who_are_you_from_shrek_handler = CommandHandler(
    "who_am_i_in_shrek", who_are_you_from_shrek_callback)

