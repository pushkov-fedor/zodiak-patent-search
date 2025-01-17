# src/interfaces/telegram/handlers/search.py

import logging
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from src.application.services.patent_summarizer import PatentSummarizer
from src.application.use_cases.patent_search import PatentSearchUseCase
from src.infrastructure.cache.patent_cache import PatentCache
from src.infrastructure.utils.text import count_words
from src.interfaces.telegram.keyboards import create_main_keyboard
from src.interfaces.telegram.states import SearchStates
from src.interfaces.telegram.utils.formatters import format_patent_message

logger = logging.getLogger(__name__)

router = Router()


class SearchHandler:
    """Обработчик поисковых запросов"""

    def __init__(
        self,
        search_use_case: PatentSearchUseCase,
        patent_summarizer: PatentSummarizer,
        patent_cache: PatentCache
    ):
        self.search_use_case = search_use_case
        self.patent_summarizer = patent_summarizer
        self.patent_cache = patent_cache
        self._register_handlers()

    def _register_handlers(self) -> None:
        """Регистрация обработчиков"""
        router.message.register(self.cmd_start, Command("start"))
        router.message.register(self.cmd_help, Command("help"))
        router.message.register(
            self.process_search_similar,
            F.text == "🔍 Семантический поиск"
        )
        router.message.register(
            self.process_search_exact,
            F.text == "🎯 Точный поиск"
        )
        router.message.register(
            self.process_help_button,
            F.text == "❓ Помощь"
        )
        router.message.register(
            self.handle_search_query,
            SearchStates.waiting_for_query
        )

    async def cmd_start(self, message: Message, state: FSMContext) -> None:
        """Обработка команды /start"""
        logger.info(f"Получена команда /start от пользователя {message.from_user.id}")
        await message.answer(
            "👋 Привет! Я бот для поиска патентов. Выберите метод поиска:",
            reply_markup=create_main_keyboard()
        )
        await state.set_state(SearchStates.choosing_method)

    async def cmd_help(self, message: Message) -> None:
        """Обработка команды /help"""
        await message.answer(
            "ℹ️ Я могу помочь вам найти патенты по двум методам:\n\n"
            "**🔍 Семантический поиск**: Поиск патентов, похожих по смыслу "
            "на ваше описание.\n"
            "**🎯 Точный поиск**: Поиск патентов по конкретным ключевым словам.\n\n"
            "Используйте кнопки ниже для выбора метода поиска.",
            reply_markup=create_main_keyboard(),
            parse_mode="Markdown"
        )

    async def process_search_similar(
        self,
        message: Message,
        state: FSMContext
    ) -> None:
        """Обработка выбора семантического поиска"""
        await message.answer(
            "🔍 <b>Семантический поиск</b> выбран.\n\n"
            "❗️ Для получения релевантных результатов необходимо ввести "
            "подробное описание (минимум 50 слов).\n\n"
            "✍️ Пожалуйста, введите ваш запрос:",
            parse_mode="HTML",
            reply_markup=create_main_keyboard()
        )
        await state.update_data(search_method="semantic")
        await state.set_state(SearchStates.waiting_for_query)

    async def process_search_exact(
        self,
        message: Message,
        state: FSMContext
    ) -> None:
        """Обработка выбора точного поиска"""
        await message.answer(
            "🎯 *Точный поиск* выбран.\nВведите ваш поисковый запрос.",
            parse_mode="Markdown",
            reply_markup=create_main_keyboard()
        )
        await state.update_data(search_method="exact")
        await state.set_state(SearchStates.waiting_for_query)

    async def process_help_button(self, message: Message) -> None:
        """Обработка нажатия кнопки помощи"""
        await self.cmd_help(message)

    async def handle_search_query(
        self,
        message: Message,
        state: FSMContext
    ) -> None:
        """Обработка поискового запроса"""
        data = await state.get_data()
        method = data.get('search_method')
        query = message.text

        # Проверка длины запроса для семантического поиска
        if method == "semantic" and count_words(query) < 50:
            await message.answer(
                "⚠️ <b>Для семантического поиска необходимо ввести не менее 50 слов.</b>\n\n"
                "Пожалуйста, предоставьте более подробное описание для получения релевантных результатов.",
                parse_mode="HTML",
                reply_markup=create_main_keyboard()
            )
            return

        # Отправляем сообщение о начале поиска
        await message.answer(
            "🔍 <b>Идет поиск и анализ патентов, подождите немного...</b>",
            parse_mode="HTML"
        )

        try:
            if method == "semantic":
                result = await self.search_use_case.search_similar(query)
            else:
                result = await self.search_use_case.search_by_query(query)

            if result.patents:
                await message.answer(
                    f"✨ <b>Найдено патентов:</b> {result.total_count}",
                    parse_mode="HTML"
                )

                # Анализируем каждый найденный патент
                for index, patent in enumerate(result.patents, 1):
                    # Получаем анализ
                    analysis = await self.patent_summarizer.analyze_patent(patent.id, patent.get_full_text())
                    
                    # Форматируем сообщение с учетом анализа
                    messages = format_patent_message(
                        patent=patent,
                        index=index,
                        summary={"status": "success", "summary": analysis} if analysis else None
                    )
                    
                    # Отправляем каждую часть сообщения
                    for msg in messages:
                        await message.answer(msg, parse_mode="HTML")

            else:
                await message.answer(
                    "❌ Патенты не найдены. Попробуйте изменить запрос.",
                    reply_markup=create_main_keyboard()
                )

        except Exception as e:
            logger.error(f"Ошибка при обработке запроса: {e}")
            await message.answer("❌ Произошла ошибка при обработке запроса")

        # В конце поиска отправляем сообщение о возможности нового запроса
        await message.answer(
            "✍️ Введите новый запрос или выберите другой режим поиска:",
            reply_markup=create_main_keyboard(),
            parse_mode="HTML"
        )
        
        # Сохраняем состояние для следующего запроса
        await state.set_state(SearchStates.waiting_for_query)