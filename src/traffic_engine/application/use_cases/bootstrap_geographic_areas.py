"""Use case for downloading and persisting preprocessed geographic areas."""

from __future__ import annotations

from typing import Iterable, List

from ..ports import GeographicAreaRepository, GeographicAreaSource
from ...domain.models import GeographicArea


class BootstrapGeographicAreasUseCase:
    def __init__(
        self,
        source: GeographicAreaSource,
        repository: GeographicAreaRepository,
    ) -> None:
        self.source = source
        self.repository = repository

    def execute(self, place_names: Iterable[str]) -> List[GeographicArea]:
        areas: List[GeographicArea] = []
        for place_name in place_names:
            area = self.source.fetch(place_name=place_name)
            areas.append(self.repository.save(area))
        return areas
