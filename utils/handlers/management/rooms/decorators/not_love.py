from typing import Callable, TypeVar

from utils.basic import EmbedErrorUI
from utils.i18n import ChisatoLocalStore

T = TypeVar("T")
_t = ChisatoLocalStore.load("./cogs/configuration/rooms.py")


def is_not_love_room(func: Callable[[T], T]) -> Callable[[T], T]:
    async def wrapper(*args, **kwargs) -> None:
        try:
            inter = args[2]
        except IndexError:
            inter = args[1]

        if not inter.bot.databases:
            return

        if await inter.bot.databases.rooms.is_love_room(inter):
            await inter.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get("rooms.error.try_setting.love_room", locale=inter.guild_locale),
                    member=inter.author
                ),
                ephemeral=True
            )
            return

        await func(*args, **kwargs)

    return wrapper
