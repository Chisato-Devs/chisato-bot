from typing import Callable, TypeVar

from utils.basic import EmbedErrorUI
from utils.i18n import ChisatoLocalStore

T = TypeVar("T")
_t = ChisatoLocalStore.load("./cogs/configuration/rooms.py")


def room_leader_check(func: Callable[[T], T]) -> Callable[[T], T]:
    async def wrapper(*args, **kwargs) -> None:
        try:
            inter = args[2]
        except IndexError:
            inter = args[1]
        if not inter.bot.databases:
            return

        if not await inter.bot.databases.rooms.temp_room_values(guild=inter.guild.id, user=inter.author.id):
            await inter.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get("rooms.error.self_not_leader", locale=inter.guild_locale),
                    member=inter.author
                ),
                ephemeral=True
            )
            return

        await func(*args, **kwargs)

    return wrapper
