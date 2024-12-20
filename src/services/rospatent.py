# src/services/rospatent.py

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from src.config.config import ROSPATENT_JWT

logger = logging.getLogger(__name__)

API_URL_SIMILAR_SEARCH = "https://searchplatform.rospatent.gov.ru/patsearch/v0.2/similar_search"
API_URL_SEARCH = "https://searchplatform.rospatent.gov.ru/patsearch/v0.2/search"

def clean_text(text: Optional[str]) -> str:
    """Очищает текст от XML и HTML тегов"""
    if not text:
        return ""
        
    # Удаляем XML и HTML теги
    text = re.sub(r'<[^>]+>', '', text)
    
    # Удаляем множественные пробелы и переносы строк
    text = re.sub(r'\s+', ' ', text)
    
    # Удаляем пробелы в начале и конце
    text = text.strip()
    
    return text

@dataclass
class PatentDetails:
    id: str
    title: str
    publication_date: str
    application_date: str
    authors: list[str]
    patent_holders: list[str]
    ipc_codes: list[str]
    abstract: str
    claims: str
    description: str
    
    @classmethod
    def from_json(cls, data: dict, patent_id: str) -> 'PatentDetails':
        """Создает объект PatentDetails из JSON данных"""
        # Извлекаем нужные поля
        common = data.get("common", {})
        biblio_ru = data.get("biblio", {}).get("ru", {})
        abstract_ru = clean_text(data.get('abstract', {}).get('ru', ''))
        claims_ru = clean_text(data.get('claims', {}).get('ru', ''))
        description_ru = clean_text(data.get('description', {}).get('ru', ''))
        
        # Формируем объект с деталями патента
        return cls(
            id=patent_id,
            title=biblio_ru.get("title", "Название не указано"),
            publication_date=common.get("publication_date", "Дата публикации не указана"),
            application_date=common.get("application", {}).get("filing_date", "Дата заявки не указана"),
            authors=[author.get("name", "") for author in biblio_ru.get("inventor", [])],
            patent_holders=[holder.get("name", "") for holder in biblio_ru.get("patentee", [])],
            ipc_codes=[ipc.get("fullname", "") for ipc in common.get("classification", {}).get("ipc", [])],
            abstract=abstract_ru,
            claims=claims_ru,
            description=description_ru
        )

def get_patent_details(patent_id: str) -> PatentDetails:
    """Получение детальной информации о патенте по его ID"""
    url = f"https://searchplatform.rospatent.gov.ru/patsearch/v0.2/docs/{patent_id}"
    headers = {
        "Authorization": f"Bearer {ROSPATENT_JWT}",
        "Content-Type": "application/json"
    }
    
    try:
        logger.debug(f"Запрос деталей патента {patent_id}")
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if logger.isEnabledFor(logging.DEBUG):
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            logger.debug(f"Получены данные патента:\n{formatted_json}")
            
        return PatentDetails.from_json(data, patent_id)
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при получении деталей патента {patent_id}: {e}")
        raise
    except (KeyError, ValueError) as e:
        logger.error(f"Ошибка при обработке данных патента {patent_id}: {e}")
        raise

def search_patents_similar(query: str, limit: int = 10) -> list[dict]:
    """Семантический поиск патентов"""
    url = API_URL_SIMILAR_SEARCH
    headers = {
        "Authorization": f"Bearer {ROSPATENT_JWT}",
        "Content-Type": "application/json"
    }
    
    data = {
        "type_search": "text_search",
        "pat_text": query,
        "count": limit
    }
    
    try:
        logger.debug(f"Запрос семантического поиска: {query[:100]}...")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        if logger.isEnabledFor(logging.DEBUG):
            formatted_json = json.dumps(result, indent=2, ensure_ascii=False)
            logger.debug(f"Получен ответ API:\n{formatted_json}")
            
        # Получаем массив документов из поля data и извлекаем только ID
        patents = [{"id": patent.get("id")} for patent in result.get("data", [])]
            
        logger.info(f"Найдено {len(patents)} патентов для запроса: '{query}'")
        return patents
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при выполнении семантического поиска: {e}")
        return []
    except ValueError as e:
        logger.error(f"Ошибка при разборе JSON ответа: {e}")
        return []

def search_patents(query: str, limit: int = 10) -> list:
    headers = {
        "Authorization": f"Bearer {ROSPATENT_JWT}",
        "Content-Type": "application/json"
    }
    payload = {
        "qn": query,
        "limit": limit
    }
    try:
        logger.debug(f"Отправка запроса к API Роспатент. Method: search, Query: {query}, Limit: {limit}")
        response = requests.post(API_URL_SEARCH, json=payload, headers=headers)
        logger.debug(f"Получен ответ от API Роспатент: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        
        if logger.isEnabledFor(logging.DEBUG):
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            logger.debug("Полный ответ API:\n%s", formatted_json)
        
        patents = []
        for hit in data.get("hits", []):
            patent_data = process_patent_data(hit)
            patents.append(patent_data)
            
        logger.info(f"Найдено {len(patents)} патентов для запроса: '{query}'")
        return patents
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при обращении к API Роспатент: {e}")
        return []
    except ValueError as e:
        logger.error(f"Ошибка при разборе JSON ответа: {e}")
        return []

def process_patent_data(hit: Dict[str, Any]) -> Dict[str, str]:
    """Обработка данных одного патента"""
    # Получаем данные из разных возможных структур ответа
    snippet = hit.get('snippet', {})
    
    # Для семантического поиска title находится в snippet
    title = (
        snippet.get('title') or 
        hit.get('title', 'Название не указано')
    ).replace("<em>", "").replace("</em>", "")
    
    # Получаем описание из snippet если есть
    description = (
        snippet.get('description', 'Описание отсутствует')
    ).replace("<em>", "").replace("</em>", "")
    
    # Получаем авторов и патентообладателей
    inventor = snippet.get('inventor', '')
    patentee = snippet.get('patentee', '')
    
    # Получаем классификацию
    classification = snippet.get('classification', {})
    ipc_codes = classification.get('ipc', '') if isinstance(classification, dict) else classification

    patent = {
        "id": hit.get('id', 'ID не указан'),
        "title": title,
        "publication_date": hit.get('publication_date', 'Дата не указана'),
        "description": description,
        "inventor": inventor,
        "patentee": patentee,
        "ipc": ipc_codes
    }
    
    logger.debug(
        "Обработан патент:\n"
        f"ID: {patent['id']}\n"
        f"Название: {title}\n"
        f"Дата публикации: {patent['publication_date']}\n"
        f"Автор: {inventor}\n"
        f"Патентообладатель: {patentee}\n"
        f"МПК: {ipc_codes}"
    )
    
    return patent 