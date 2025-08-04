# config.py
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")  # @BotFather dan olingan token
DEFAULT_CHANNEL_ID = ""  # Kanal ID si, masalan: @YourChannel