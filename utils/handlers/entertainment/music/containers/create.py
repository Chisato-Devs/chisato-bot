from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harmonize.objects import Track


class CreateContainer:
    def __init__(self):
        self._name: str | None = None
        self._tracks: list[Track] = []
        self._closed: bool = True

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def tracks(self) -> list[Track]:
        return self._tracks

    @tracks.setter
    def tracks(self, value: Track) -> None:
        self._tracks.append(value)

    @property
    def closed(self) -> bool:
        return self._closed

    @closed.setter
    def closed(self, value: bool) -> None:
        self._closed = value
