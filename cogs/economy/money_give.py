from typing import TYPE_CHECKING, Union

from disnake import ApplicationCommandInteraction, Member, Localized
from disnake.ext.commands import Param

from utils.basic import CogUI, EmbedErrorUI, EmbedUI, IntFormatter, CommandsPermission
from utils.exceptions import NotEnoughMoney
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from disnake.ext.commands import Bot
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class MoneyGive(CogUI):

    @CogUI.slash_command(name="money")
    async def _money(self, interaction: ApplicationCommandInteraction) -> ...:
        ...

    @_money.sub_command(
        name="add", description=Localized(
            "💰 Деньги: выдача.",
            data=_t.get("money.add.description")
        )
    )
    @CommandsPermission.decorator(administrator=True)
    async def add(
            self, interaction: ApplicationCommandInteraction,
            member: Member = Param(
                name=Localized("участник", data=_t.get("money.add.option.member.name")),
                default=lambda x: x.author,
                description=Localized(
                    "- укажи участника, которому хочешь выдать деньги",
                    data=_t.get("money.add.option.member.description")
                )
            ),
            money: int = Param(
                name=Localized("сумма", data=_t.get("money.add.option.amount.name")),
                description=Localized(
                    "- укажи сумму для выдачи",
                    data=_t.get("money.add.option.amount.description")
                ),
                min_value=30, max_value=10000
            )
    ) -> None:
        if member.bot:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "money.add.error.not_bot",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )
            )

        await self.bot.databases.economy.add_balance(
            guild=interaction.guild.id,
            member=member.id,
            amount=money
        )

        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get(
                    "money.success.title",
                    locale=interaction.guild_locale
                ),
                description=_t.get(
                    "money.add.success",
                    locale=interaction.guild_locale,
                    values=(
                        member.mention, interaction.author.mention, interaction.author,
                        IntFormatter(money).format_number(), money
                    )
                ),
                timestamp=interaction.created_at
            )
        )

    @_money.sub_command(
        name="remove", description=Localized(
            "💰 Деньги: снятие.",
            data=_t.get("money.remove.description")
        )
    )
    @CommandsPermission.decorator(administrator=True)
    async def remove(
            self, interaction: ApplicationCommandInteraction,
            member: Member = Param(
                name=Localized("участник", data=_t.get("money.remove.option.member.name")),
                default=lambda x: x.author,
                description=Localized(
                    "- укажи участника, у которого хочешь снять деньги",
                    data=_t.get("money.remove.option.member.description")
                )
            ),
            money: int = Param(
                name=Localized("сумма", data=_t.get("money.remove.option.amount.name")),
                description=Localized(
                    "- укажи сумму для снятия",
                    data=_t.get("money.remove.option.amount.description")
                ),
                min_value=30, max_value=10000
            )
    ) -> None:
        if member.bot:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "money.remove.error.not_bot",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )
            )

        try:
            await self.bot.databases.economy.remove_balance(
                guild=interaction.guild.id,
                member=member.id,
                amount=money
            )
        except NotEnoughMoney:
            values = await self.bot.databases.economy.values(
                member=member.id,
                guild=interaction.guild.id
            )
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "money.remove.error.not_enough",
                        locale=interaction.guild_locale,
                        values=(values[2],)
                    ),
                    member=interaction.author
                )
            )

        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get(
                    "money.success.title",
                    locale=interaction.guild_locale
                ),
                description=_t.get(
                    "money.remove.success",
                    locale=interaction.guild_locale,
                    values=(
                        member.mention, interaction.author.mention, interaction.author,
                        IntFormatter(money).format_number(), money
                    )
                ),
                timestamp=interaction.created_at
            )
        )


def setup(bot: Union["ChisatoBot", "Bot"]) -> None:
    return bot.add_cog(MoneyGive(bot))
