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
    # Обязательные параметры (без значений по умолчанию)
    bot_token: str
    rospatent_jwt: str
    gigachat_client_id: str
    gigachat_client_secret: str
    
    # Необязательные параметры (со значениями по умолчанию)
    log_level: int = logging.INFO
    cache_ttl_hours: int = 24
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Создание настроек из переменных окружения"""
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token:
            raise ValueError("BOT_TOKEN is not set in environment variables")
            
        rospatent_jwt = os.getenv("ROSPATENT_JWT")
        if not rospatent_jwt:
            raise ValueError("ROSPATENT_JWT is not set in environment variables")
            
        gigachat_client_id = os.getenv("GIGACHAT_CLIENT_ID")
        if not gigachat_client_id:
            raise ValueError("GIGACHAT_CLIENT_ID is not set")
            
        gigachat_client_secret = os.getenv("GIGACHAT_CLIENT_SECRET")
        if not gigachat_client_secret:
            raise ValueError("GIGACHAT_CLIENT_SECRET is not set")
            
        log_level_str = os.getenv("LOG_LEVEL", "INFO")
        log_level = getattr(logging, log_level_str.upper(), logging.INFO)
        
        cache_ttl = int(os.getenv("CACHE_TTL_HOURS", "24"))
        
        return cls(
            bot_token=bot_token,
            rospatent_jwt=rospatent_jwt,
            gigachat_client_id=gigachat_client_id,
            gigachat_client_secret=gigachat_client_secret,
            log_level=log_level,
            cache_ttl_hours=cache_ttl
        )


# Создаем глобальный экземпляр настроек
settings = Settings.from_env()