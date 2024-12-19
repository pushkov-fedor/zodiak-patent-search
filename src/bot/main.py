# src/bot/main.py

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.handlers import register_handlers
from src.config.config import BOT_TOKEN, LOG_LEVEL

# Настройка логирования
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

async def main():
    # Инициализация бота и диспетчера с хранилищем в памяти для FSM
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация обработчиков
    register_handlers(dp)
    
    try:
        logging.info("Запуск бота")
        await dp.start_polling(bot)
    finally:
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main()) 