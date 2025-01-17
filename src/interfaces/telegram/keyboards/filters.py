from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


def create_filter_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для настройки фильтров"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🌍 Страны поиска", callback_data="filter_countries"),
                InlineKeyboardButton(text="📑 Коды МПК", callback_data="filter_ipc")
            ],
            [
                InlineKeyboardButton(text="📋 Коды СПК", callback_data="filter_cpc"),
                InlineKeyboardButton(text="📅 Период", callback_data="filter_dates")
            ],
            [
                InlineKeyboardButton(text="✅ Применить фильтры", callback_data="apply_filters"),
                InlineKeyboardButton(text="❌ Сбросить фильтры", callback_data="reset_filters")
            ]
        ]
    )


def create_skip_keyboard() -> ReplyKeyboardMarkup:
    """Создание клавиатуры с кнопкой пропуска"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⏭️ Пропустить")]],
        resize_keyboard=True,
        one_time_keyboard=True
    ) 