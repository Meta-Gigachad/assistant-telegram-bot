"""
Speech Module

Implements voice message recognition and transformers model for answer generation
"""


import logging
import os
import subprocess

from speech_recognition import Recognizer, AudioFile, UnknownValueError
from telegram import Update

from modules.base import BotModule
from telegram.ext import Dispatcher, MessageHandler, Filters, CallbackContext

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import gc


class SpeechModule(BotModule):
    def __init__(self, dispatcher: Dispatcher, ):
        super().__init__(
            dispatcher,
            [
                MessageHandler(Filters.voice, self.handle_voice),
                MessageHandler(Filters.text, self.handle_text)
            ]
        )
        self.recognizer = Recognizer()

        tokenizer = AutoTokenizer.from_pretrained("HansAnonymous/DialoGPT-small-shrek")
        model = AutoModelForCausalLM.from_pretrained("HansAnonymous/DialoGPT-small-shrek")
        chat_histories = {}
        self.previous_responses = []
        self.response_model = (model, tokenizer, chat_histories)
        gc.collect()

    def handle_voice(self, update: Update, context: CallbackContext):
        voice = update.message.voice.get_file()

        current_directory = os.path.dirname(os.path.abspath(__file__))
        wav_voice_path = current_directory + "\\voice_messages\\recognition.wav"
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-i', voice.file_path, '-y', '-ar', '16000', wav_voice_path])

        update.message.delete()
        sent_message = update.message.reply_text("Listening...")

        with AudioFile(wav_voice_path) as file:
            recognizer = self.recognizer
            try:
                transcription = recognizer.recognize_google(recognizer.record(file))
                sent_message.edit_text(f"*You say:* _{transcription}_", parse_mode='markdown')
            except UnknownValueError:
                sent_message.edit_text(f"Can't hear you")
        logging.log(logging.INFO, f"""Got voice: {update.message.from_user.name} -> {transcription}""")

        chat_id, user_id = update.message.chat_id, update.message.from_user.id
        response = self.generate_response(transcription, user_id)
        context.bot.send_message(chat_id, f"{response}")
        logging.log(logging.INFO, f"""Responded: BOT -> {response}""")

    def handle_text(self, update: Update, context: CallbackContext):
        text = update.message.text
        logging.log(logging.INFO, f"""Got message: {update.message.from_user.name} -> {text}""")

        chat_id, user_id = update.message.chat_id, update.message.from_user.id
        sent_message = context.bot.send_message(chat_id, "_Typing..._", parse_mode='markdown')
        response = self.generate_response(text, user_id)
        sent_message.edit_text(f"{response}")
        logging.log(logging.INFO, f"""Responded: BOT -> {response}""")

    def generate_response(self, message: str, user_id: int):
        model, tokenizer, chat_histories = self.response_model

        new_user_input_ids = tokenizer.encode(message + tokenizer.eos_token, return_tensors='pt')
        try:
            chat_history_ids = chat_histories[user_id]
            bot_input_ids = torch.cat([chat_history_ids, new_user_input_ids],
                                      dim=-1)
        except KeyError:
            bot_input_ids = new_user_input_ids

        chat_history_ids = model.generate(bot_input_ids, max_length=40, pad_token_id=tokenizer.eos_token_id)

        if len(chat_history_ids[0]) > 30:
            chat_histories[user_id] = chat_history_ids[:, len(chat_history_ids[0]):]
        else:
            chat_histories[user_id] = chat_history_ids

        response = tokenizer.decode(chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)
        if response in self.previous_responses or response == message:
            chat_histories[user_id] = chat_history_ids[:, len(chat_history_ids[0]):]
            response = "..."
        if len(self.previous_responses) == 3:
            self.previous_responses.pop(0)
        self.previous_responses.append(response)

        return response
