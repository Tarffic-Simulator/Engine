"""Use case for listing preprocessed geographic areas."""

from __future__ import annotations

from ..ports import GeographicAreaRepository
from ...domain.models import GeographicArea


class ListGeographicAreasUseCase:
    def __init__(self, repository: GeographicAreaRepository) -> None:
        self.repository = repository

    def execute(self) -> list[GeographicArea]:
        return self.repository.list()
