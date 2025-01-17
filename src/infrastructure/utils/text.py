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

def format_patent_analysis(analysis_dict: dict) -> str:
    """Форматирует анализ патента для вывода пользователю"""
    if analysis_dict.get("status") == "error":
        return (
            "❌ Ошибка при анализе патента:\n"
            f"{analysis_dict.get('summary')}\n"
            f"Техническая информация: {analysis_dict.get('error')}"
        )

    summary = analysis_dict.get("summary")
    if not summary:
        return "⚠️ Пустой ответ от сервиса анализа"

    formatted_text = [
        "",
        "📝 Описание:",
        summary.get('description', 'Описание отсутствует'),
        ""
    ]

    # Преимущества
    advantages = summary.get('advantages', [])
    if advantages:
        formatted_text.extend([
            "✅ Преимущества:"
        ])
        formatted_text.extend(f"• {adv}" for adv in advantages)
        formatted_text.append("")

    # Недостатки
    disadvantages = summary.get('disadvantages', [])
    if disadvantages:
        formatted_text.extend([
            "⚠️ Недостатки:"
        ])
        formatted_text.extend(f"• {dis}" for dis in disadvantages)
        formatted_text.append("")

    # Области применения
    applications = summary.get('applications', [])
    if applications:
        formatted_text.extend([
            "🎯 Области применения:"
        ])
        formatted_text.extend(f"• {app}" for app in applications)

    return "\n".join(formatted_text)
