# src/infrastructure/rospatent/repository.py

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import List, Optional

import aiohttp
from aiohttp import ClientResponseError, ClientTimeout

from src.domain.entities.patent import Patent
from src.domain.entities.search_filter import SearchFilter
from src.domain.repositories.patent_repository import PatentRepository
from src.infrastructure.rospatent.config import RospatentConfig
from src.infrastructure.utils.text import clean_text, count_words

logger = logging.getLogger(__name__)


class RospatentRepository(PatentRepository):
    """Реализация репозитория для работы с API Роспатента"""

    def __init__(self, config: RospatentConfig):
        self.config = config
        self.timeout = ClientTimeout(total=config.timeout)
        self.max_retries = 3  # Максимальное количество повторных попыток
        self.retry_delay = 2  # Начальная задержка перед повторной попыткой (в секундах)

    @asynccontextmanager
    async def _get_session(self):
        """Контекстный менеджер для создания и закрытия сессии"""
        # TODO: убрать verify_ssl=False, когда rospatent вернет валидный сертификат
        connector = aiohttp.TCPConnector(verify_ssl=False)
        
        # Настройка параметров сессии для более стабильной работы
        timeout = ClientTimeout(total=self.config.timeout, 
                               connect=10,  # Увеличиваем таймаут соединения
                               sock_connect=10,  # Увеличиваем таймаут подключения сокета
                               sock_read=self.config.timeout)  # Таймаут чтения сокета
        
        session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            # Отключаем автоматический редирект, будем обрабатывать вручную
            auto_decompress=True,
            trust_env=True
        )
        try:
            yield session
        finally:
            await session.close()

    async def search_by_query(self, query: str, limit: int = 10, search_filter: Optional[SearchFilter] = None) -> List[Patent]:
        """Поиск патентов по запросу"""
        retries = 0
        while retries <= self.max_retries:
            try:
                # Логируем информацию о попытке и окружении
                env_info = {
                    "http_proxy": os.environ.get("http_proxy", "не установлен"),
                    "https_proxy": os.environ.get("https_proxy", "не установлен"),
                    "no_proxy": os.environ.get("no_proxy", "не установлен"),
                }
                logger.debug(f"Попытка выполнения search_by_query (attempt: {retries+1}). Env: {env_info}")
                
                async with self._get_session() as session:
                    url = f"{self.config.base_url}/search"
                    payload = {"qn": query, "limit": limit}
                    
                    if search_filter:
                        payload["filter"] = search_filter.to_api_format()

                    # Логируем полный URL и заголовки (без токена)
                    safe_headers = {k: v for k, v in self.config.headers.items() if k != "Authorization"}
                    safe_headers["Authorization"] = "Bearer ***" 
                    logger.debug(f"Запрос к: {url}, headers: {safe_headers}, payload size: {len(str(payload))}")
                    
                    async with session.post(url, json=payload, headers=self.config.headers) as response:
                        status = response.status
                        logger.debug(f"Получен статус: {status}")
                        
                        if status == 301 or status == 302:
                            # Обрабатываем редирект вручную
                            redirect_url = response.headers.get('Location')
                            logger.debug(f"Перенаправление на: {redirect_url}")
                            
                            if not redirect_url:
                                logger.error("Получен редирект без URL перенаправления")
                                return []
                                
                            # Проверяем, что URL доступен извне
                            if "prod:" in redirect_url or "10.2.40" in redirect_url:
                                logger.error(f"Недопустимый URL перенаправления (внутренний): {redirect_url}")
                                return []
                                
                            # Выполняем запрос к новому URL
                            async with session.post(redirect_url, json=payload, headers=self.config.headers) as redirect_response:
                                redirect_response.raise_for_status()
                                data = await redirect_response.json()
                        else:
                            # Проверяем статус и продолжаем как обычно
                            response.raise_for_status()
                            data = await response.json()
                        
                        # Проверяем ответ на наличие ошибок
                        if isinstance(data, str) and "Failed to establish a connection" in data:
                            logger.error(f"API вернуло ошибку строкой: {data}")
                            if retries < self.max_retries:
                                retry_after = self.retry_delay * (2 ** retries)
                                logger.warning(f"Ошибка соединения к внутреннему сервису, повторная попытка через {retry_after}s")
                                await asyncio.sleep(retry_after)
                                retries += 1
                                continue
                            return []
                            
                        # Проверяем наличие hits в ответе
                        if not data.get("hits"):
                            logger.debug(f"Нет результатов поиска (пустой hits): {data}")
                            return []
                        
                        patents = []
                        for hit in data.get("hits", []):
                            patent_id = hit.get("id")
                            if patent_id:
                                patent_url = f"{self.config.base_url}/docs/{patent_id}"
                                try:
                                    async with session.get(patent_url, headers=self.config.headers) as patent_response:
                                        patent_response.raise_for_status()
                                        patent_data = await patent_response.json()
                                        if patent := self._parse_patent_data(patent_data, patent_id):
                                            patents.append(patent)
                                except aiohttp.ClientError as e:
                                    import traceback
                                    logger.error(f"Error fetching patent {patent_id}: {repr(e)}\n{traceback.format_exc()}")
                                    continue
                        
                        return patents

            except aiohttp.ClientResponseError as e:
                if e.status == 503 and retries < self.max_retries:
                    # Сервис временно недоступен, повторяем запрос
                    retry_after = self.retry_delay * (2 ** retries)  # Экспоненциальная задержка
                    logger.warning(f"Service unavailable (503), retrying in {retry_after}s (attempt {retries+1}/{self.max_retries})")
                    await asyncio.sleep(retry_after)
                    retries += 1
                    continue
                else:
                    import traceback
                    logger.error(f"Client response error during patent search: {repr(e)}\n{traceback.format_exc()}")
                    return []
            except aiohttp.ClientError as e:
                import traceback
                logger.error(f"Error during patent search: {repr(e)}\n{traceback.format_exc()}")
                return []
            except Exception as e:
                import traceback
                logger.error(f"Unexpected error during patent search: {repr(e)}\n{traceback.format_exc()}")
                return []

        logger.error(f"Max retries ({self.max_retries}) exceeded for search_by_query")
        return []

    async def search_similar(self, text: str, limit: int = 10) -> List[Patent]:
        """Семантический поиск похожих патентов"""
        retries = 0
        while retries <= self.max_retries:
            try:
                # Логируем информацию о попытке и окружении
                env_info = {
                    "http_proxy": os.environ.get("http_proxy", "не установлен"),
                    "https_proxy": os.environ.get("https_proxy", "не установлен"),
                    "no_proxy": os.environ.get("no_proxy", "не установлен"),
                }
                logger.debug(f"Попытка выполнения search_similar (attempt: {retries+1}). Env: {env_info}")
                
                async with self._get_session() as session:
                    url = f"{self.config.base_url}/similar_search"
                    payload = {
                        "type_search": "text_search",
                        "pat_text": text,
                        "count": limit
                    }

                    # Добавляем проверку длины текста
                    if count_words(text) < 50:
                        logger.warning(f"Текст запроса содержит менее 50 слов ({count_words(text)}), что может привести к ошибке API")

                    # Логируем полный URL и заголовки (без токена)
                    safe_headers = {k: v for k, v in self.config.headers.items() if k != "Authorization"}
                    safe_headers["Authorization"] = "Bearer ***" 
                    logger.debug(f"Запрос к: {url}, headers: {safe_headers}, payload size: {len(str(payload))}")
                    
                    async with session.post(url, json=payload, headers=self.config.headers) as response:
                        status = response.status
                        logger.debug(f"Получен статус: {status}")
                        
                        if status == 301 or status == 302:
                            # Обрабатываем редирект вручную
                            redirect_url = response.headers.get('Location')
                            logger.debug(f"Перенаправление на: {redirect_url}")
                            
                            if not redirect_url:
                                logger.error("Получен редирект без URL перенаправления")
                                return []
                                
                            # Проверяем, что URL доступен извне
                            if "prod:" in redirect_url or "10.2.40" in redirect_url:
                                logger.error(f"Недопустимый URL перенаправления (внутренний): {redirect_url}")
                                return []
                                
                            # Выполняем запрос к новому URL
                            async with session.post(redirect_url, json=payload, headers=self.config.headers) as redirect_response:
                                redirect_response.raise_for_status()
                                data = await redirect_response.json()
                        else:
                            # Проверяем статус и продолжаем как обычно
                            response.raise_for_status()
                            data = await response.json()
                        
                        # Проверяем ответ на наличие ошибок
                        if isinstance(data, str) and "Failed to establish a connection" in data:
                            logger.error(f"API вернуло ошибку строкой: {data}")
                            if retries < self.max_retries:
                                retry_after = self.retry_delay * (2 ** retries)
                                logger.warning(f"Ошибка соединения к внутреннему сервису, повторная попытка через {retry_after}s")
                                await asyncio.sleep(retry_after)
                                retries += 1
                                continue
                            return []
                            
                        # Ожидаем наличие 'data' в ответе
                        if not data.get("data"):
                            logger.warning(f"Пустой ответ от API, нет ключа 'data': {data}")
                            return []
                        
                        patents = []
                        for item in data.get("data", []):
                            patent_id = item.get("id")
                            if patent_id:
                                patent_url = f"{self.config.base_url}/docs/{patent_id}"
                                try:
                                    async with session.get(patent_url, headers=self.config.headers) as patent_response:
                                        patent_response.raise_for_status()
                                        patent_data = await patent_response.json()
                                        if patent := self._parse_patent_data(patent_data, patent_id):
                                            patents.append(patent)
                                except aiohttp.ClientError as e:
                                    import traceback
                                    logger.error(f"Error fetching patent {patent_id}: {repr(e)}\n{traceback.format_exc()}")
                                    continue
                        
                        return patents

            except aiohttp.ClientResponseError as e:
                if e.status == 503 and retries < self.max_retries:
                    # Сервис временно недоступен, повторяем запрос
                    retry_after = self.retry_delay * (2 ** retries)  # Экспоненциальная задержка
                    logger.warning(f"Service unavailable (503), retrying in {retry_after}s (attempt {retries+1}/{self.max_retries})")
                    await asyncio.sleep(retry_after)
                    retries += 1
                    continue
                else:
                    import traceback
                    logger.error(f"Client response error during similar patent search: {repr(e)}\n{traceback.format_exc()}")
                    return []
            except aiohttp.ClientError as e:
                import traceback
                logger.error(f"Error during similar patent search: {repr(e)}\n{traceback.format_exc()}")
                return []
            except Exception as e:
                import traceback
                logger.error(f"Unexpected error during similar patent search: {repr(e)}\n{traceback.format_exc()}")
                return []

        logger.error(f"Max retries ({self.max_retries}) exceeded for search_similar")
        return []

    async def get_by_id(self, patent_id: str) -> Optional[Patent]:
        """Получение патента по ID"""
        retries = 0
        while retries <= self.max_retries:
            try:
                # Логируем информацию о попытке и окружении
                env_info = {
                    "http_proxy": os.environ.get("http_proxy", "не установлен"),
                    "https_proxy": os.environ.get("https_proxy", "не установлен"),
                    "no_proxy": os.environ.get("no_proxy", "не установлен"),
                }
                logger.debug(f"Попытка выполнения get_by_id (attempt: {retries+1}). Env: {env_info}")
                
                async with self._get_session() as session:
                    url = f"{self.config.base_url}/docs/{patent_id}"

                    # Логируем полный URL и заголовки (без токена)
                    safe_headers = {k: v for k, v in self.config.headers.items() if k != "Authorization"}
                    safe_headers["Authorization"] = "Bearer ***" 
                    logger.debug(f"Запрос к: {url}, headers: {safe_headers}")
                    
                    async with session.get(url, headers=self.config.headers) as response:
                        status = response.status
                        logger.debug(f"Получен статус: {status}")
                        
                        if status == 301 or status == 302:
                            # Обрабатываем редирект вручную
                            redirect_url = response.headers.get('Location')
                            logger.debug(f"Перенаправление на: {redirect_url}")
                            
                            if not redirect_url:
                                logger.error("Получен редирект без URL перенаправления")
                                return None
                                
                            # Проверяем, что URL доступен извне
                            if "prod:" in redirect_url or "10.2.40" in redirect_url:
                                logger.error(f"Недопустимый URL перенаправления (внутренний): {redirect_url}")
                                return None
                                
                            # Выполняем запрос к новому URL
                            async with session.get(redirect_url, headers=self.config.headers) as redirect_response:
                                redirect_response.raise_for_status()
                                data = await redirect_response.json()
                        else:
                            # Проверяем статус и продолжаем как обычно
                            response.raise_for_status()
                            data = await response.json()
                        
                        # Проверяем ответ на наличие ошибок
                        if isinstance(data, str) and "Failed to establish a connection" in data:
                            logger.error(f"API вернуло ошибку строкой: {data}")
                            if retries < self.max_retries:
                                retry_after = self.retry_delay * (2 ** retries)
                                logger.warning(f"Ошибка соединения к внутреннему сервису, повторная попытка через {retry_after}s")
                                await asyncio.sleep(retry_after)
                                retries += 1
                                continue
                            return None
                        
                        return self._parse_patent_data(data, patent_id)

            except aiohttp.ClientResponseError as e:
                if e.status == 503 and retries < self.max_retries:
                    # Сервис временно недоступен, повторяем запрос
                    retry_after = self.retry_delay * (2 ** retries)  # Экспоненциальная задержка
                    logger.warning(f"Service unavailable (503), retrying in {retry_after}s (attempt {retries+1}/{self.max_retries})")
                    await asyncio.sleep(retry_after)
                    retries += 1
                    continue
                else:
                    import traceback
                    logger.error(f"Client response error while fetching patent {patent_id}: {repr(e)}\n{traceback.format_exc()}")
                    return None
            except aiohttp.ClientError as e:
                import traceback
                logger.error(f"Error fetching patent {patent_id}: {repr(e)}\n{traceback.format_exc()}")
                return None
            except Exception as e:
                import traceback
                logger.error(f"Unexpected error fetching patent {patent_id}: {repr(e)}\n{traceback.format_exc()}")
                return None

        logger.error(f"Max retries ({self.max_retries}) exceeded for get_by_id")
        return None

    def _parse_patent_data(self, data: dict, patent_id: str) -> Patent:
        """Парсинг данных патента из ответа API"""
        common = data.get("common", {})
        biblio_ru = data.get("biblio", {}).get("ru", {})
        
        def parse_date(date_str: str) -> Optional[date]:
            if not date_str:
                logger.debug(f"Empty date string for patent {patent_id}")
                return None
            
            date_formats = [
                "%Y-%m-%d",  # формат YYYY-MM-DD
                "%Y%m%d",    # формат YYYYMMDD
                "%Y.%m.%d"   # формат YYYY.MM.DD
            ]
            
            for date_format in date_formats:
                try:
                    return datetime.strptime(date_str, date_format).date()
                except ValueError:
                    continue
                
            logger.error(f"Failed to parse date '{date_str}' for patent {patent_id}")
            return None

        pub_date = parse_date(common.get("publication_date", ""))
        app_date = parse_date(
            common.get("application", {}).get("filing_date", "")
        )

        if not pub_date or not app_date:
            logger.warning(
                f"Missing dates for patent {patent_id}. "
                f"Publication date: {pub_date}, Application date: {app_date}"
            )

        return Patent.create(
            id=patent_id,
            title=clean_text(biblio_ru.get("title", "Название не указано")),
            publication_date=pub_date,
            application_date=app_date,
            authors=[
                clean_text(author.get("name", ""))
                for author in biblio_ru.get("inventor", [])
            ],
            patent_holders=[
                clean_text(holder.get("name", ""))
                for holder in biblio_ru.get("patentee", [])
            ],
            ipc_codes=[
                clean_text(ipc.get("fullname", ""))
                for ipc in common.get("classification", {}).get("ipc", [])
            ],
            abstract=clean_text(data.get("abstract", {}).get("ru", "")),
            claims=clean_text(data.get("claims", {}).get("ru", "")),
            description=clean_text(data.get("description", {}).get("ru", ""))
        )