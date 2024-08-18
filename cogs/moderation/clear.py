from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from disnake import Member, ApplicationCommandInteraction, Forbidden, HTTPException, Message, Localized
from disnake.ext.commands import Param

from utils.basic import EmbedErrorUI, EmbedUI, CogUI, CommandsPermission
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class ClearCog(CogUI):

    @CogUI.slash_command(
        name="clear", description=Localized("🗑️ Очистка: удаление сообщений.", data=_t.get("clear.command.description"))
    )
    @CommandsPermission.decorator(manage_messages=True)
    async def clear_cmd(
            self,
            interaction: ApplicationCommandInteraction,
            amount: int = Param(
                name=Localized("кол-во", data=_t.get("clear.command.option.amount.name")),
                description=Localized(
                    "- укажи количество сообщений для очистки.",
                    data=_t.get("clear.command.option.amount.description")
                ),
                min_value=2,
                max_value=100
            ),
            days_ago: int = Param(
                name=Localized("дни", data=_t.get("clear.command.option.day.name")),
                description=Localized(
                    "- укажи последние дни для очистки сообщений.",
                    data=_t.get("clear.command.option.day.description")
                ),
                min_value=1,
                max_value=14,
                default=14
            ),
            member: Member = Param(
                name=Localized("пользователь", data=_t.get("clear.command.option.member.name")),
                description=Localized(
                    "- укажи пользователя у которого хочешь очистить сообщения.",
                    data=_t.get("clear.command.option.member.description")
                ),
                default=None
            )
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        args = [None, lambda m: True]

        if days_ago:
            days_ago_dt_obj: datetime = datetime.now() - timedelta(days=days_ago)
            args[0] = days_ago_dt_obj

        if member:
            args[1] = lambda m: m.author == member

        try:
            messages: list[Message] = await interaction.channel.purge(
                limit=amount,
                after=args[0],
                check=args[1]
            )
        except Forbidden:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("clear.command.callback.error.forbidden", locale=interaction.guild_locale), interaction.author
            )

            await interaction.edit_original_response(embed=embed)

        except HTTPException:
            embed: EmbedErrorUI = EmbedErrorUI(
                _t.get("clear.command.callback.error.http", locale=interaction.guild_locale),
                interaction.author
            )

            await interaction.edit_original_response(embed=embed)
        else:
            embed: EmbedUI = EmbedUI(
                title=_t.get("clear.success", locale=interaction.guild_locale),
                description=_t.get(
                    "clear.command.callback.success.embed.description", locale=interaction.guild_locale,
                    values=(interaction.author.mention, interaction.author, amount)
                )
            )

            if days_ago:
                embed.description += _t.get(
                    "clear.command.callback.success.embed.description.part.1", locale=interaction.guild_locale,
                    values=(days_ago,)
                )

            if member:
                embed.description += _t.get(
                    "clear.command.callback.success.embed.description.part.2", locale=interaction.guild_locale,
                    values=(member.mention, member.name)
                )

            embed.description += _t.get(
                "clear.command.callback.success.embed.description.part.3", locale=interaction.guild_locale,
                values=(len(messages),)
            )

            await interaction.edit_original_response(embed=embed)


def setup(bot: 'ChisatoBot') -> None:
    bot.add_cog(ClearCog(bot))
