# src/domain/entities/patent.py

from dataclasses import dataclass
from datetime import date
from typing import List


@dataclass
class Patent:
    """Доменная модель патента"""
    id: str
    title: str
    publication_date: date
    application_date: date
    authors: List[str]
    patent_holders: List[str]
    ipc_codes: List[str]
    abstract: str
    claims: str
    description: str

    @classmethod
    def create(
        cls,
        id: str,
        title: str,
        publication_date: date,
        application_date: date,
        authors: List[str],
        patent_holders: List[str],
        ipc_codes: List[str],
        abstract: str = "",
        claims: str = "",
        description: str = ""
    ) -> "Patent":
        """Фабричный метод для создания объекта патента"""
        return cls(
            id=id,
            title=title,
            publication_date=publication_date,
            application_date=application_date,
            authors=authors,
            patent_holders=patent_holders,
            ipc_codes=ipc_codes,
            abstract=abstract,
            claims=claims,
            description=description
        )