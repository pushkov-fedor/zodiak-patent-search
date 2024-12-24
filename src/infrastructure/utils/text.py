# src/infrastructure/utils/text.py

import re
from typing import Optional


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

def count_words(text: str) -> int:
    """Подсчет количества слов в тексте"""
    return len(text.split())
