# src/infrastructure/rospatent/repository.py

import logging
from datetime import date, datetime
from typing import List, Optional

import aiohttp
from aiohttp import ClientTimeout

from src.domain.entities.patent import Patent
from src.domain.entities.search_filter import SearchFilter
from src.domain.repositories.patent_repository import PatentRepository
from src.infrastructure.rospatent.config import RospatentConfig
from src.infrastructure.utils.text import clean_text

logger = logging.getLogger(__name__)


class RospatentRepository(PatentRepository):
    """Реализация репозитория для работы с API Роспатента"""

    def __init__(self, config: RospatentConfig):
        self.config = config
        self.timeout = ClientTimeout(total=config.timeout)

    async def search_by_query(self, query: str, limit: int = 10, search_filter: Optional[SearchFilter] = None) -> List[Patent]:
        """Поиск патентов по запросу"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            url = f"{self.config.base_url}/search"
            payload = {"qn": query, "limit": limit}
            
            # Добавляем фильтры в запрос, если они есть
            if search_filter:
                payload["filter"] = search_filter.to_api_format()

            try:
                async with session.post(url, json=payload, headers=self.config.headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    patents = []
                    for hit in data.get("hits", []):
                        patent_id = hit.get("id")
                        if patent_id:
                            if patent := await self.get_by_id(patent_id):
                                patents.append(patent)
                    
                    return patents

            except aiohttp.ClientError as e:
                logger.error(f"Error during patent search: {e}")
                return []

    async def search_similar(self, text: str, limit: int = 10) -> List[Patent]:
        """Семантический поиск похожих патентов"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            url = f"{self.config.base_url}/similar_search"
            payload = {
                "type_search": "text_search",
                "pat_text": text,
                "count": limit
            }

            try:
                async with session.post(url, json=payload, headers=self.config.headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    patents = []
                    for item in data.get("data", []):
                        patent_id = item.get("id")
                        if patent_id:
                            if patent := await self.get_by_id(patent_id):
                                patents.append(patent)
                    
                    return patents

            except aiohttp.ClientError as e:
                logger.error(f"Error during similar patent search: {e}")
                return []

    async def get_by_id(self, patent_id: str) -> Optional[Patent]:
        """Получение патента по ID"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            url = f"{self.config.base_url}/docs/{patent_id}"

            try:
                async with session.get(url, headers=self.config.headers) as response:
                    response.raise_for_status()
                    data = await response.json()
                    
                    return self._parse_patent_data(data, patent_id)

            except aiohttp.ClientError as e:
                logger.error(f"Error fetching patent {patent_id}: {e}")
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