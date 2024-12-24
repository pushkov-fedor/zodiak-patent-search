# src/infrastructure/config/settings.py

import logging
import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


@dataclass
class Settings:
    """Основные настройки приложения"""
    # Токены и ключи
    bot_token: str
    rospatent_jwt: str
    
    # Настройки логирования
    log_level: int = logging.INFO
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Создание настроек из переменных окружения"""
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise ValueError("BOT_TOKEN is not set in environment variables")
            
        rospatent_jwt = os.getenv("ROSPATENT_JWT")
        if not rospatent_jwt:
            raise ValueError("ROSPATENT_JWT is not set in environment variables")
            
        log_level_str = os.getenv("LOG_LEVEL", "INFO")
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        
        return cls(
            bot_token=bot_token,
            rospatent_jwt=rospatent_jwt,
            log_level=log_level
        )


# Создаем глобальный экземпляр настроек
settings = Settings.from_env()