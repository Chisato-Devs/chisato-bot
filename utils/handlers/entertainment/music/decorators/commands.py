from typing import Callable, TypeVar, cast

from disnake import ApplicationCommandInteraction, ui, TextChannel
from disnake.ext.commands import Context, check
from lavamystic import Pool, InvalidNodeException, Player

from utils.basic import EmbedErrorUI
from utils.enviroment import env
from utils.i18n import ChisatoLocalStore

T = TypeVar("T")
_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")

__all__ = (
    "in_voice",
    "with_bot",
    "has_nodes",
    "in_home",
    "in_text_channel"
)


def in_voice() -> Callable[[T], T]:
    async def wrapper(interaction: ApplicationCommandInteraction | Context) -> bool:
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
            return False
        return True

    return check(wrapper)


def has_nodes() -> Callable[[T], T]:
    async def wrapper(interaction: ApplicationCommandInteraction | Context) -> bool:
        try:
            Pool.get_node()
        except InvalidNodeException:
            await interaction.response.send_message(
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
            return False
        else:
            return True

    return check(wrapper)


def with_bot() -> Callable[[T], T]:
    async def wrapper(interaction: ApplicationCommandInteraction | Context) -> bool:
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
            return False
        return True

    return check(wrapper)


def in_home() -> Callable[[T], T]:
    async def wrapper(interaction: ApplicationCommandInteraction | Context) -> bool:
        if (
                (vc := cast(Player, interaction.guild.voice_client))
                and hasattr(vc.namespace, "home")
                and vc.namespace.home
                and vc.namespace.home != interaction.channel
        ):
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.error.not_in_home",
                        locale=interaction.guild_locale,
                        values=(vc.namespace.home.mention,)
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
            return False
        return True

    return check(wrapper)


def in_text_channel() -> Callable[[T], T]:
    async def wrapper(interaction: ApplicationCommandInteraction | Context) -> bool:
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
            return False
        return True

    return check(wrapper)
