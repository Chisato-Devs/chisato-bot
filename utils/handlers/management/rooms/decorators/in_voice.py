from typing import Callable, TypeVar

from utils.basic import EmbedErrorUI
from utils.i18n import ChisatoLocalStore

T = TypeVar("T")
_t = ChisatoLocalStore.load("./cogs/configuration/rooms.py")


def in_voice(func: Callable[[T], T]) -> Callable[[T], T]:
    async def wrapper(*args, **kwargs) -> None:
        try:
            inter = args[2]
        except IndexError:
            inter = args[1]

        if inter.author.voice:
            await func(*args, **kwargs)
        else:
            await inter.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get("rooms.error.not_in_room", locale=inter.guild_locale),
                    member=inter.author
                ),
                ephemeral=True
            )

    return wrapper
