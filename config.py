from dotenv import load_dotenv
from os import environ
import logging

load_dotenv()
BOT_TOKEN = environ["BOT_TOKEN"]
MYSQL_HOST = environ["MYSQL_HOST"]
MYSQL_USER = environ["MYSQL_USER"]
MYSQL_PASSWORD = environ["MYSQL_PASSWORD"]
