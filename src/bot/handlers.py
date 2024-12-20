# src/bot/handlers.py

import logging

from aiogram import Dispatcher, Router, types
from aiogram.filters import Command, Text
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from src.services.rospatent import (
    get_patent_details,
    search_patents,
    search_patents_similar,
)

router = Router()
logger = logging.getLogger(__name__)

# Определение состояний пользователя
class SearchStates(StatesGroup):
    ChoosingMethod = State()
    WaitingForQuery = State()

def create_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
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
    return keyboard

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
    await message.answer(
        "👋 Привет! Я бот для поиска патентов. Выберите метод поиска:",
        reply_markup=create_main_keyboard()
    )
    await state.set_state(SearchStates.ChoosingMethod)
    logger.debug("Отправлено приветственное сообщение с клавиатурой выбора метода поиска.")

@router.message(Command("help"))
async def cmd_help(message: types.Message):
    logger.info(f"Получена команда /help от пользователя {message.from_user.id}")
    await message.answer(
        "ℹ️ Я могу помочь вам найти патенты по двум методам:\n\n"
        "**🔍 Семантический поиск**: Поиск патентов, похожих по смыслу на ваше описание.\n"
        "**🎯 Точный поиск**: Поиск патентов по конкретным ключевым словам.\n\n"
        "Используйте кнопки ниже для выбора метода поиска.",
        reply_markup=create_main_keyboard(),
        parse_mode="Markdown"
    )
    logger.debug("Отправлено справочное сообщение с клавиатурой выбора метода поиска.")

@router.message(Text(text="🔍 Семантический поиск"))
async def process_search_similar(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await message.answer(
        "🔍 *Семантический поиск* выбран.\nВведите подробное описание вашего запроса (не менее 50 слов).",
        parse_mode="Markdown",
        reply_markup=create_main_keyboard()
    )
    await state.update_data(search_method="semantic")
    await state.set_state(SearchStates.WaitingForQuery)
    logger.info(f"Пользователь {user_id} выбрал Семантический поиск.")

@router.message(Text(text="🎯 Точный поиск"))
async def process_search_exact(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await message.answer(
        "🎯 *Точный поиск* выбран.\nВведите ваш поисковый запрос.",
        parse_mode="Markdown",
        reply_markup=create_main_keyboard()
    )
    await state.update_data(search_method="exact")
    await state.set_state(SearchStates.WaitingForQuery)
    logger.info(f"Пользователь {user_id} выбрал Точный поиск.")

@router.message(Text(text="❓ Помощь"))
async def process_help_button(message: types.Message):
    user_id = message.from_user.id
    await message.answer(
        "ℹ️ *Помощь*\n\n"
        "**🔍 Семантический поиск**: Введите подробное описание вашего запроса (не менее 50 слов), и я найду патенты, похожие по смыслу.\n\n"
        "**🎯 Точный поиск**: Введите конкретные ключевые слова для точного поиска патентов.",
        parse_mode="Markdown",
        reply_markup=create_main_keyboard()
    )
    logger.info(f"Пользователь {user_id} запросил помощь.")

@router.message(SearchStates.WaitingForQuery)
async def handle_search_query(message: types.Message, state: FSMContext):
    """Обработка поискового запроса"""
    user_id = message.from_user.id
    query = message.text
    
    data = await state.get_data()
    method = data.get('search_method')
    
    logger.info(f"Получено сообщение от пользователя {user_id}: {query}")
    
    try:
        if method == "semantic":
            patents = search_patents_similar(query)
        else:
            patents = search_patents(query)
            
        if patents and len(patents) > 0:
            await message.answer("🔍 *Найденные патенты:*", parse_mode="Markdown")
            
            for i, patent in enumerate(patents[:10], start=1):
                patent_id = patent.get('id')
                if not patent_id:
                    continue
                    
                try:
                    details = get_patent_details(patent_id)
                    
                    # Основная информация о патенте
                    main_info = (
                        f"*Патент #{i}*\n\n"
                        f"📑 *Название:* {details.title}\n"
                        f"📅 *Дата публикации:* {details.publication_date}\n"
                        f"📅 *Дата подачи заявки:* {details.application_date}\n"
                        f"👤 *Авторы:* {', '.join(details.authors)}\n"
                        f"💼 *Патентообладатели:* {', '.join(details.patent_holders)}\n"
                        f"🔰 *МПК:* {', '.join(details.ipc_codes)}\n\n"
                        f"📝 *Реферат:*\n{details.abstract}\n\n"
                        f"📋 *Формула изобретения:*\n{details.claims}\n\n"
                        f"📚 *Описание:*\n{details.description}"
                    )
                    
                    # Если текст превышает максимальную длину
                    max_length = 4096
                    if len(main_info) > max_length:
                        # Отправляем текст частями
                        for i in range(0, len(main_info), max_length):
                            chunk = main_info[i:i + max_length]
                            await message.answer(chunk, parse_mode="Markdown")
                    else:
                        # Отправляем всё одним сообщением
                        await message.answer(main_info, parse_mode="Markdown")
                        
                except Exception as e:
                    logger.error(f"Ошибка при получении деталей патента {patent_id}: {e}")
                    continue
                    
            logger.info(f"Отправлены результаты поиска пользователю {user_id}")
            
            # Возвращаемся к ожиданию следующего запроса с тем же методом поиска
            await state.set_state(SearchStates.WaitingForQuery)
            await message.answer(
                f"Введите следующий поисковый запрос или выберите другой метод поиска:",
                reply_markup=create_main_keyboard()
            )
        else:
            await message.answer(
                "❌ Патенты не найдены или произошла ошибка при поиске.\n"
                "Попробуйте другой запрос или выберите другой метод поиска:", 
                reply_markup=create_main_keyboard()
            )
            # Сохраняем текущий метод поиска
            await state.set_state(SearchStates.WaitingForQuery)
            
    except Exception as e:
        logger.error(f"Ошибка при поиске: {e}")
        await message.answer(
            "⚠️ Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.",
            reply_markup=create_main_keyboard()
        )
        # Сохраняем текущий метод поиска даже при ошибке
        await state.set_state(SearchStates.WaitingForQuery)
    
    # Убираем state.clear(), чтобы сохранить выбранный метод поиска

def register_handlers(dispatcher: Dispatcher):
    dispatcher.include_router(router) 