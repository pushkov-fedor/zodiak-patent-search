# src/infrastructure/gigachat/client.py

import base64
import json
import logging
import uuid
from dataclasses import dataclass
from typing import List, Optional

import aiohttp
import urllib3
from aiohttp import ClientTimeout

# Отключаем предупреждения о небезопасном SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from src.infrastructure.gigachat.config import GigaChatConfig
from src.infrastructure.gigachat.prompts import (
    PATENT_ANALYSIS_SYSTEM_PROMPT,
    PATENT_ANALYSIS_USER_PROMPT,
)

logger = logging.getLogger(__name__)


@dataclass
class PatentAnalysis:
    description: str
    advantages: List[str]
    disadvantages: List[str]
    applications: List[str]

    def to_dict(self) -> dict:
        """Преобразование в словарь для форматирования"""
        return {
            "description": self.description,
            "advantages": self.advantages,
            "disadvantages": self.disadvantages,
            "applications": self.applications
        }


class GigaChatClient:
    """Клиент для работы с GigaChat API"""

    def __init__(self, config: GigaChatConfig):
        self.config = config
        self.timeout = ClientTimeout(total=config.timeout)

    async def _get_auth_token(self) -> Optional[str]:
        """Получение токена авторизации"""
        try:
            headers = {
                "Authorization": f"Basic {self.config.client_secret}",  # client_secret это и есть Authorization key
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json"
            }

            payload = {
                "scope": self.config.scope
            }

            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    self.config.auth_url,
                    headers=headers,
                    data=payload,
                    verify_ssl=False
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(
                            f"Error getting auth token: {response.status}, "
                            f"message={text}, "
                            f"url={response.url}"
                        )
                        return None

                    data = await response.json()
                    return data.get("access_token")

        except Exception as e:
            logger.error(f"Exception during auth token request: {str(e)}")
            return None

    async def ensure_token(self) -> bool:
        """Проверка и обновление токена при необходимости"""
        token = await self._get_auth_token()
        if not token:
            return False
        self.config._access_token = token
        return True

    async def summarize_patent(self, patent_text: str) -> Optional[dict]:
        """Суммаризация информации о патенте"""
        if not await self.ensure_token():
            return {
                "status": "error",
                "summary": "Не удалось получить доступ к сервису анализа",
                "error": "Authentication failed"
            }

        payload = {
            "model": "GigaChat",
            "messages": [
                {
                    "role": "system",
                    "content": PATENT_ANALYSIS_SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": PATENT_ANALYSIS_USER_PROMPT.format(
                        patent_text=patent_text
                    )
                }
            ],
            "temperature": 1,
            "max_tokens": 1500
        }

        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=self.config.headers,
                    json=payload,
                    verify_ssl=False
                ) as response:
                    if response.status != 200:
                        text = await response.text()
                        logger.error(
                            f"Error during summarization: {response.status}, "
                            f"message={text}"
                        )
                        return {
                            "status": "error",
                            "summary": "Сервис анализа временно недоступен",
                            "error": f"HTTP {response.status}: {text}"
                        }

                    data = await response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    logger.info(
                        "Получен ответ от GigaChat:\n"
                        f"Raw response: {content}\n"
                        f"{'-' * 80}"
                    )
                    
                    try:
                        # Пытаемся распарсить JSON из ответа
                        analysis_dict = json.loads(content)
                        
                        # Проверяем наличие всех необходимых полей
                        required_fields = {"description", "advantages", "disadvantages", "applications"}
                        if not all(field in analysis_dict for field in required_fields):
                            missing = required_fields - set(analysis_dict.keys())
                            logger.error(f"Отсутствуют обязательные поля: {missing}")
                            return {
                                "status": "error",
                                "summary": "Некорректный формат ответа от сервиса анализа",
                                "error": f"Отсутствуют поля: {', '.join(missing)}"
                            }
                        
                        # Создаем объект PatentAnalysis из словаря
                        analysis = PatentAnalysis(**analysis_dict)
                        
                        return {
                            "status": "success",
                            "summary": analysis.to_dict()
                        }
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse GigaChat response as JSON: {e}")
                        return {
                            "status": "error",
                            "summary": "Не удалось разобрать ответ от сервиса анализа",
                            "error": f"JSON parse error: {str(e)}\nContent: {content[:200]}..."
                        }
                
        except Exception as e:
            logger.error(f"Error during patent summarization: {e}")
            return {
                "status": "error",
                "summary": "Произошла ошибка при анализе патента",
                "error": str(e)
            }