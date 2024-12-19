# src/config/config.py

import os

from dotenv import load_dotenv

# Загрузить переменные окружения из .env файла
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ROSPATENT_JWT = os.getenv("ROSPATENT_JWT")
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG") 