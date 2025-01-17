# tests/unit/test_search_handler.py

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup

from src.application.use_cases.patent_search import PatentSearchResult
from src.domain.entities.patent import Patent


@pytest.mark.asyncio
async def test_cmd_start(handler):
    # Arrange
    message = AsyncMock(spec=Message)
    message.from_user = Mock(id=1)
    message.answer = AsyncMock()
    state = AsyncMock(spec=FSMContext)

    # Act
    await handler.cmd_start(message, state)

    # Assert
    assert message.answer.await_count == 1
    called_kwargs = message.answer.call_args.kwargs
    assert isinstance(called_kwargs.get('reply_markup'), ReplyKeyboardMarkup)
    assert state.set_state.await_count == 1


@pytest.mark.asyncio
async def test_handle_search_query_exact(handler):
    # Arrange
    message = AsyncMock(spec=Message)
    message.text = "Test Query"
    message.answer = AsyncMock()
    state = AsyncMock(spec=FSMContext)
    state.get_data = AsyncMock(return_value={"search_method": "exact"})

    mock_result = PatentSearchResult(
        query="Test Query",
        total_count=1,
        patents=[
            Patent(
                id="123",
                title="Test Patent",
                publication_date=date(2023, 1, 1),
                application_date=date(2022, 1, 1),
                authors=["Author A"],
                patent_holders=["Holder A"],
                ipc_codes=["IPC1"],
                abstract="Abstract",
                claims="Claims",
                description="Description"
            )
        ]
    )
    handler.search_use_case.search_by_query = AsyncMock(return_value=mock_result)
    handler.patent_summarizer.analyze_patent = AsyncMock(return_value="Test analysis")

    # Act
    await handler.handle_search_query(message, state)

    # Assert
    handler.search_use_case.search_by_query.assert_awaited_once_with("Test Query", search_filter=None)
    assert message.answer.await_count == 5  # 1. Начало поиска, 2. Результаты, 3. Патент, 4. Анализ, 5. Новый запрос
    assert state.set_state.await_count == 1

    # Проверяем, что все вызовы answer были с правильными параметрами
    for call_args in message.answer.call_args_list:
        assert 'parse_mode' in call_args.kwargs  # Проверяем, что во всех вызовах есть parse_mode
        assert call_args.kwargs['parse_mode'] == "HTML"  # Проверяем значение parse_mode