from typing import Callable, TypeVar, TYPE_CHECKING

from disnake import ApplicationCommandInteraction, Member
from disnake.ext.commands import check, Context

from utils.basic import EmbedErrorUI
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

T = TypeVar("T")
_t = ChisatoLocalStore.load("./cogs/economy/pets.py")


def check_in_fight() -> Callable[[T], T]:
    async def predicate(
            interaction: ApplicationCommandInteraction | Context
    ) -> None | bool:
        bot: "ChisatoBot" = interaction.bot  # type: ignore
        if not bot.databases:
            del interaction
            return

        if await bot.databases.pets.in_fight_check(guild=interaction.guild.id, member=interaction.author.id):
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "pets.error.in_duel", locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        for filled_option in interaction.filled_options:
            if isinstance(filled_option, Member):
                if await bot.databases.pets.in_fight_check(
                        guild=interaction.guild.id, member=filled_option.id
                ):
                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "pets.error.member.in_duel", locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ),
                        ephemeral=True
                    )

        return True

    return check(predicate)


def check_in_game() -> Callable[[T], T]:
    async def predicate(
            interaction: ApplicationCommandInteraction | Context
    ) -> None | bool:
        bot: "ChisatoBot" = interaction.bot  # type: ignore
        if not interaction.bot.databases:  # type: ignore
            del interaction
            return False

        if await bot.databases.economy.in_game(guild=interaction.guild.id, member=interaction.author.id):
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get("game.error.in_game", locale=interaction.guild_locale),
                    member=interaction.author
                ),
                ephemeral=True
            )
            return False
        return True

    return check(predicate)


def check_is_on() -> Callable[[T], T]:
    async def predicate(
            interaction: ApplicationCommandInteraction | Context
    ) -> None | bool:
        bot: "ChisatoBot" = interaction.bot  # type: ignore
        if not bot.databases:
            del interaction
            return

        if (
                (values := await bot.databases.settings.get(guild=interaction.guild.id))
                and values[2]
        ):
            return True
        else:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get("eco.error.is_disabled", locale=interaction.guild_locale),
                    member=interaction.author
                ),
                ephemeral=True
            )

    return check(predicate)


def check_in_fight_button(func: Callable[[T], T]) -> Callable[[T], T]:
    async def wrapper(*args, **kwargs) -> None:
        try:
            interaction = args[2]
        except IndexError:
            interaction = args[1]

        bot: "ChisatoBot" = interaction.bot  # type: ignore

        if not bot.databases:
            del interaction
            return

        if not await bot.databases.pets.in_fight_check(
                guild=interaction.guild.id, member=interaction.author.id
        ):
            await func(*args, **kwargs)
        else:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "pets.error.in_duel", locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

    return wrapper


def check_in_game_button(func: Callable[[T], T]) -> Callable[[T], T]:
    async def wrapper(*args, **kwargs) -> None:
        try:
            interaction = args[2]
        except IndexError:
            interaction = args[1]

        bot: "ChisatoBot" = interaction.bot  # type: ignore

        if not bot.databases:
            del interaction
            return

        if not await bot.databases.economy.in_game(
                guild=interaction.guild.id, member=interaction.author.id
        ):
            return await func(*args, **kwargs)
        else:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get("game.error.in_game", locale=interaction.guild_locale),
                    member=interaction.author
                ),
                ephemeral=True
            )

    return wrapper
