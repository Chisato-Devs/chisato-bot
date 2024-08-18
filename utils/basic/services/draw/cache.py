from typing import Optional

from disnake.ext.tasks import loop


class Cache:
    def __init__(self) -> None:
        self._cac: dict[str, str] = {}

        self._clear.start()

    def put(self, key: str, value: str) -> None:
        self._cac[key] = value

    def get(self, key: str) -> Optional[str]:
        return self._cac.get(key)

    def remove(self, key: str) -> None:
        del self._cac[key]

    @loop(minutes=10)
    async def _clear(self) -> None:
        self._cac.clear()
