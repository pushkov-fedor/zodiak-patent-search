# src/bot/main.py

import asyncio
import logging

from src.application.use_cases.patent_search import PatentSearchUseCase
from src.infrastructure.config.settings import settings
from src.infrastructure.rospatent.config import RospatentConfig
from src.infrastructure.rospatent.repository import RospatentRepository
from src.interfaces.telegram.bot import PatentBot


async def main():
    # Настройка логирования
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Инициализация зависимостей
    rospatent_config = RospatentConfig(jwt_token=settings.rospatent_jwt)
    patent_repository = RospatentRepository(rospatent_config)
    search_use_case = PatentSearchUseCase(patent_repository)

    # Создание и запуск бота
    bot = PatentBot(
        token=settings.bot_token,
        search_use_case=search_use_case
    )
    
    await bot.start()


if __name__ == "__main__":
    asyncio.run(main())