# src/interfaces/telegram/keyboards/main.py

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def create_main_keyboard() -> ReplyKeyboardMarkup:
    """Создание основной клавиатуры"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🔍 Семантический поиск"),
                KeyboardButton(text="🎯 Точный поиск")
            ],
            [
                KeyboardButton(text="❓ Помощь")
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False
    )