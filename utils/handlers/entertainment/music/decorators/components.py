from typing import Callable, TypeVar

from disnake import ui, TextChannel
from lavamystic import Pool, InvalidNodeException

from utils.basic import EmbedErrorUI
from utils.enviroment import env
from utils.i18n import ChisatoLocalStore

T = TypeVar("T")
_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")

__all__ = (
    "in_voice_button",
    "with_bot_button",
    "has_nodes_button",
    'in_text_channel_button'
)


def in_voice_button(func: Callable[[T], T]) -> Callable[[T], T]:
    async def wrapper(*args, **kwargs) -> None:
        try:
            interaction = args[2]
        except IndexError:
            interaction = args[1]

        if not interaction.author.voice:
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.error.not_in_voice",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
            return
        await func(*args, **kwargs)

    return wrapper


def has_nodes_button(func: Callable[[T], T]) -> Callable[[T], T]:
    async def wrapper(*args, **kwargs) -> None:
        try:
            interaction = args[2]
        except IndexError:
            interaction = args[1]

        try:
            Pool.get_node()
        except InvalidNodeException:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.error.nodes_not_found",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                components=[
                    ui.Button(
                        label=_t.get(
                            "music.support_server",
                            locale=interaction.guild_locale
                        ),
                        url=env.GUILD_INVITE
                    )
                ],
                ephemeral=True
            )
        else:
            await func(*args, **kwargs)

    return wrapper


def with_bot_button(func: Callable[[T], T]) -> Callable[[T], T]:
    async def wrapper(*args, **kwargs) -> None:
        try:
            interaction = args[2]
        except IndexError:
            interaction = args[1]

        if (
                (vc := interaction.guild.voice_client)
                and vc.channel != interaction.author.voice.channel
        ):
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.error.with_bot",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
            return
        await func(*args, **kwargs)

    return wrapper


def in_text_channel_button(func: Callable[[T], T]) -> Callable[[T], T]:
    async def wrapper(*args, **kwargs) -> None:
        try:
            interaction = args[2]
        except IndexError:
            interaction = args[1]

        if (
                not isinstance(interaction.channel, TextChannel)
        ):
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.error.not_in_text_channel",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
            return
        await func(*args, **kwargs)

    return wrapper
