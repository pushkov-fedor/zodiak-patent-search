# src/interfaces/telegram/bot.py

import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.application.use_cases.patent_search import PatentSearchUseCase
from src.interfaces.telegram.handlers.search import SearchHandler, router


class PatentBot:
    """Основной класс телеграм-бота"""

    def __init__(
        self,
        token: str,
        search_use_case: PatentSearchUseCase,
        log_level: Optional[int] = None
    ):
        # Настройка логирования
        if log_level:
            logging.basicConfig(
                level=log_level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )

        # Инициализация бота и хранилища состояний
        self.bot = Bot(token=token, parse_mode="HTML")
        self.storage = MemoryStorage()
        self.dp = Dispatcher(storage=self.storage)

        # Инициализация обработчиков
        self.search_handler = SearchHandler(search_use_case)
        self.dp.include_router(router)

    async def start(self) -> None:
        """Запуск бота"""
        logging.info("Starting bot...")
        try:
            await self.dp.start_polling(self.bot)
        finally:
            await self.bot.close()