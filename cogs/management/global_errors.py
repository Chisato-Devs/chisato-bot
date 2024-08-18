from asyncio import wait_for, to_thread
from functools import cache
from typing import TYPE_CHECKING, Callable, Optional, Union

from disnake import ApplicationCommandInteraction, errors, InteractionTimedOut
from disnake.ext.commands import MissingPermissions, MissingAnyRole, CommandOnCooldown, NSFWChannelRequired, Context
from loguru import logger

from utils.basic import CogUI, IntFormatter, EmbedErrorUI, EmbedUI
from utils.enviroment import env
from utils.exceptions import DoesntHaveAgreedRole, errors as custom_errors
from utils.exceptions.trace import Trace
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot
    from disnake.ext.commands import Bot

_t = ChisatoLocalStore.load(__file__)


class GlobalErrorsCog(CogUI):
    def __init__(self, bot: 'ChisatoBot') -> None:
        super().__init__(bot)

        self.error_handling: dict[Union[errors, custom_errors], Callable] = {
            CommandOnCooldown: self._commands_on_cooldown,
            MissingAnyRole: self._missing_permission,
            MissingPermissions: self._missing_permission,
            NSFWChannelRequired: self._nsfw_required,
            DoesntHaveAgreedRole: self._missed_roles,
            InteractionTimedOut: self._timed_out
        }

    async def cog_load(self) -> None:
        await self.bot.wait_until_first_connect()
        if env.MAIN_ID != self.bot.user.id:
            logger.info("Do you want to get a full stack of bugs? (5 seconds to answer)")
            try:
                user_input = await wait_for(to_thread(input), timeout=5)
            except TimeoutError:
                logger.info("Receipt of the response was suspended. Full error stack included")
                self.bot.disable_errors = True
            else:
                if user_input not in ["No", "-", "Нет"]:
                    self.bot.disable_errors = True

    @CogUI.context_command(name="disable_errors", aliases=['de'])
    async def disable_errors(self, ctx: Context) -> None:
        await ctx.message.delete()
        match self.bot.disable_errors:
            case True:
                self.bot.disable_errors = False
                await ctx.send('Успешное включение обработки ошибок')
            case False:
                self.bot.disable_errors = True
                await ctx.send('Успешное отключение обработки ошибок')

    @cache
    def get_handler(self, error_type: errors) -> Optional[Callable]:
        return self.error_handling.get(error_type)

    @staticmethod
    async def _commands_on_cooldown(
            interaction: ApplicationCommandInteraction, error: Union[errors, custom_errors]
    ) -> None:
        await interaction.followup.send(embed=EmbedErrorUI(
            description=_t.get(
                "global_errs.cooldown", locale=interaction.guild_locale,
                values=(
                    f"`{IntFormatter(error.retry_after).convert_timestamp(locale=interaction.guild_locale)}`",
                )
            ),
            member=interaction.author
        ))

    @staticmethod
    async def _timed_out(
            interaction: ApplicationCommandInteraction, error: Union[errors, custom_errors]
    ) -> None:
        await interaction.followup.send(embed=(embed := EmbedErrorUI(
            description=_t.get(
                "global_errs.timed_out", locale=interaction.guild_locale
            ),
            member=interaction.author
        )))
        bot: Union["ChisatoBot", "Bot"] = interaction.bot

        filled_options = ""
        for filled_option in interaction.filled_options.items():
            filled_options += f"{filled_option[0]}: {repr(filled_option[1])}"

        await bot.webhooks.post(
            {
                'embed': embed,
                'content': f"Опции: \n{filled_options}\n\n"
                           f"User: `{interaction.author}` "
                           f"| Command: `{interaction.application_command.name}` "
                           f"| Guild: `{interaction.guild} [{interaction.guild.id}]`"
            },
            type='command'
        )

    @staticmethod
    async def _missed_roles(
            interaction: ApplicationCommandInteraction, error: Union[errors, custom_errors]
    ) -> None:
        await interaction.followup.send(embed=EmbedErrorUI(
            description=_t.get(
                "global_errs.missed_roles", locale=interaction.guild_locale,
                values=(", ".join([role.mention for role in error.required_roles]),)
            ),
            member=interaction.author
        ))

    @staticmethod
    async def _missing_permission(
            interaction: ApplicationCommandInteraction
    ) -> None:
        await interaction.followup.send(embed=EmbedErrorUI(
            description=_t.get(
                "global_errs.insufficient_permissions", locale=interaction.guild_locale
            ),
            member=interaction.author
        ))

    @staticmethod
    async def _nsfw_required(
            interaction: ApplicationCommandInteraction
    ) -> None:
        await interaction.followup.send(embed=EmbedErrorUI(
            description=_t.get(
                "global_errs.not_in_nsfw", locale=interaction.guild_locale
            ),
            member=interaction.author
        ))

    @CogUI.listener()
    async def on_global_slash_error(self, interaction: ApplicationCommandInteraction, error: Exception):
        error = getattr(error, "original", error)
        await interaction.response.defer(ephemeral=True)

        if handler := self.get_handler(type(error)):
            interaction.responded = True
            if isinstance(error, CommandOnCooldown) or isinstance(error, DoesntHaveAgreedRole):
                return await handler(interaction=interaction, error=error)
            await handler(interaction=interaction)

    @CogUI.listener(name="on_didnt_respond_interaction")
    async def didnt_respond(
            self, interaction: ApplicationCommandInteraction, exception: Exception
    ) -> Exception | None:
        try:
            await interaction.followup.send(
                embed=(embed := EmbedUI(
                    description=_t.get(
                        key="technical_error", locale=interaction.guild_locale,
                        values=(
                            interaction.author.name, f"{type(exception).__name__}: {exception}"
                        )
                    ),
                    color=env.COLOR
                ))
            )
        except Exception as e:
            return e

        await Trace.generate(exception, interaction, embed)


def setup(bot: 'ChisatoBot') -> None:
    bot.add_cog(GlobalErrorsCog(bot))
