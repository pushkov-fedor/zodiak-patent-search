# src/interfaces/telegram/utils/formatters.py

from typing import Any, List


def truncate_text(text: str, max_length: int = 4000) -> str:
    """Обрезает текст до указанной длины и добавляет многоточие"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "...\n\n<i>Полный текст доступен по ссылке на патент</i>"


def format_patent_message(patent: Any, index: int) -> List[str]:
    """Форматирование сообщения с информацией о патенте"""
    # Формируем ссылку на патент
    patent_link = f"https://searchplatform.rospatent.gov.ru/doc/{patent.id}"
    
    # Основная информация всегда будет в первом сообщении
    main_info = (
        f"🔎 <b>Патент #{index}</b>\n"
        f"📑 <b>Номер патента:</b> {patent.id}\n"
        f"🔗 <b>Ссылка:</b> {patent_link}\n"
        f"📑 <b>Название:</b> {patent.title}\n"
        f"📅 <b>Дата публикации:</b> {patent.publication_date}\n"
        f"📅 <b>Дата подачи заявки:</b> {patent.application_date}\n"
        f"👤 <b>Авторы:</b> {', '.join(patent.authors)}\n"
        f"💼 <b>Патентообладатели:</b> {', '.join(patent.patent_holders)}\n"
        f"🔰 <b>МПК:</b> {', '.join(patent.ipc_codes)}\n\n"
        f"📝 <b>Реферат:</b>\n{patent.abstract}"
    )

    # Формируем остальные части с учетом максимального размера сообщения
    parts = [main_info]
    
    if patent.claims:
        parts.append(f"📋 <b>Формула изобретения:</b>\n{truncate_text(patent.claims)}")
        
    if patent.description:
        parts.append(f"📚 <b>Описание:</b>\n{truncate_text(patent.description)}")

    return parts[:4]  # Максимум 4 сообщения на патент