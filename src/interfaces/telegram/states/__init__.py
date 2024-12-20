# src/interfaces/telegram/states/__init__.py

from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    """Состояния для процесса поиска патентов"""
    choosing_method = State()  # Выбор метода поиска
    waiting_for_query = State()  # Ожидание поискового запроса