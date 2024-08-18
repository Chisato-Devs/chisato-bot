from functools import partial
from typing import Any

from disnake import Localized, ApplicationCommandInteraction, Member, AppCommandInteraction
from disnake.ext.commands import Param, cooldown, BucketType

from utils.basic import ChisatoBot, CogUI, IntFormatter, EmbedErrorUI, EmbedUI
from utils.basic.services.draw import DrawService
from utils.consts import REGULAR_CURRENCY
from utils.dataclasses import Pet
from utils.exceptions import NotEnoughMoney, DoesntHavePet
from utils.handlers.economy import check_is_on, check_in_fight, check_in_game
from utils.handlers.economy.views import ShopView
from utils.handlers.pagination import PaginatorView
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load(__file__)


class SimpleEconomy(CogUI):
    def __init__(self, bot: ChisatoBot) -> None:
        super().__init__(bot)

    @CogUI.slash_command(name=f'economy', dm_permission=False)
    @check_is_on()
    @check_in_game()
    async def _e(self, interaction: AppCommandInteraction) -> None:
        ...

    @_e.sub_command(
        name=f'transactions',
        description=Localized(
            "🪙 Экономика: посмотреть свои траты!",
            data=_t.get("simple.command.transactions.description")
        )
    )
    async def transactions(
            self, interaction: AppCommandInteraction
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        description = _t.get("simple.transactions.history.part", locale=interaction.guild_locale)

        transactions_data = await self.bot.databases.transactions.get_all(
            guild=interaction.guild.id, user=interaction.author.id
        )

        if not transactions_data:
            return await interaction.followup.send(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "simple.transactions.error.not_found",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )
            )

        def format_transaction(*args) -> str:
            return description.format(
                args[0][0] + 1,
                _t.get(args[0][1][3], locale=interaction.guild_locale),
                IntFormatter(args[0][1][2]).format_number(),
                REGULAR_CURRENCY,
                _t.get(args[0][1][4], locale=interaction.guild_locale)
            )

        formatted_transactions = list(
            map(partial(format_transaction), enumerate(transactions_data))
        )

        embeds = [
            EmbedUI(
                title=_t.get("simple.transactions.title", locale=interaction.guild_locale),
                description="\n".join(formatted_transactions[i:i + 10])
            )
            for i in range(0, len(formatted_transactions), 10)
        ]

        await interaction.followup.send(
            embed=embeds[0],
            view=PaginatorView(
                author=interaction.author,
                embeds=embeds,
                footer=True,
                delete_button=True,
                interaction=interaction
            )
        )

    @_e.sub_command(
        name='profile',
        description=Localized(
            "🪙 Экономика: посмотреть профиль!",
            data=_t.get("simple.profile.command.description")
        )
    )
    async def p(
            self,
            interaction: ApplicationCommandInteraction,
            member: Member = Param(
                name=Localized("участник", data=_t.get("simple.option.member.name")),
                description=Localized(
                    "- укажи участника для просмотра профиля",
                    data=_t.get("simple.profile.option.member.description")
                ),
                default=lambda x: x.author
            )

    ) -> None:
        if not await DrawService(self.bot.session).get_status():
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "eco.error.api_error",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        async with DrawService(self.bot.session) as ir:
            try:
                pet = await self.bot.databases.pets.pet_get(guild=interaction.guild.id, member=member.id)
            except DoesntHavePet:
                pet = Pet(
                    name="",
                    emoji="",
                    power=0,
                    stamina=0,
                    mana=0,
                    cost=0,
                    image_link="",
                    level=0
                )

            file = await ir.draw_image(
                "economy_profile",
                userName=member.name,
                userAvatar=member.display_avatar.url,

                moneyOnHands=IntFormatter(money).format_number() if (money := (
                    await self.bot.databases.economy.values(
                        member=member.id,
                        guild=interaction.guild.id
                    )
                )[2]) > 999999 else money,

                topPosition=await self.bot.databases.economy.get_top_position(
                    guild=interaction.guild, member=member
                ),

                petUrl=pet.image_link,
                petStamina=pet.stamina,
                petMana=pet.mana,
                petLevel=pet.level
            )

        await interaction.response.send_message(file=file)

    @_e.sub_command(
        description=Localized(
            "🪙 Экономика: перевести деньги пользователю!",
            data=_t.get("simple.transfer.command.description")
        ),
        name='pay'
    )
    @check_in_fight()
    @cooldown(10, 3600, type=BucketType.member)
    async def pay(
            self,
            interaction: ApplicationCommandInteraction,
            member: Member = Param(
                name=Localized(
                    "участник", data=_t.get("simple.option.member.name")
                ),
                description=Localized(
                    "- укажи пользователя для передачи валюты",
                    data=_t.get("simple.transfer.command.option.member.description")
                )
            ),

            money_count: int = Param(
                name=Localized("кол-во", data=_t.get("simple.option.amount.name")),
                description=Localized(
                    "- укажи кол-во валюты для передачи",
                    data=_t.get("simple.transfer.command.option.amount.description")
                ),
                min_value=1,
                max_value=100000
            )

    ) -> Any:
        await interaction.response.defer(ephemeral=True)
        if member.bot:
            error = EmbedErrorUI(
                description=_t.get(
                    "simple.transfer.error.not_bot",
                    locale=interaction.guild_locale
                ),
                member=interaction.author
            )
            return await interaction.followup.send(embed=error)
        elif member.id == interaction.author.id:
            error = EmbedErrorUI(
                _t.get(
                    "simple.transfer.error.not_author_eq_member",
                    locale=interaction.guild_locale
                ),
                member=interaction.author
            )
            return await interaction.followup.send(embed=error)

        try:
            await self.bot.databases.economy.pay(
                member=interaction.author.id,
                member_pay=member.id,
                guild=interaction.guild.id,
                amount=money_count
            )
            await self.bot.databases.transactions.add(
                guild=interaction.guild.id, user=interaction.author.id, amount=money_count,
                locale_key="simple.transfer.transaction.outgoing", typing=False
            )

            await self.bot.databases.transactions.add(
                guild=interaction.guild.id, user=member.id, amount=money_count,
                locale_key="simple.transfer.transaction.incoming", typing=True
            )

            await interaction.followup.send(
                embed=EmbedUI(
                    title=_t.get("simple.success.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "simple.success.transfer_money",
                        locale=interaction.guild_locale,
                        values=(
                            member.mention, member.name,
                            IntFormatter(money_count).format_number(),
                            REGULAR_CURRENCY,
                        )
                    ),
                    timestamp=interaction.created_at
                )
            )
        except NotEnoughMoney:
            await interaction.followup.send(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "simple.error.transfer.not_enough_money",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )
            )

    @_e.sub_command(
        name="shop",
        description=Localized(
            "🪙 Экономика: магазин предметов",
            data=_t.get("simple.shop.command.description")
        )
    )
    @check_in_fight()
    async def shop(self, interaction: ApplicationCommandInteraction) -> None:
        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get(
                    "simple.shop.title",
                    locale=interaction.guild_locale
                ),
                description=_t.get(
                    "simple.shop.embed.description",
                    locale=interaction.guild_locale
                )
            ),
            view=ShopView(interaction=interaction)
        )

    async def cog_slash_command_error(
            self, interaction: ApplicationCommandInteraction, error: Exception
    ) -> None:
        error = getattr(error, "original", error)
        if isinstance(error, NotEnoughMoney):
            interaction.responded = True

            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "simple.error.target_30",
                        locale=interaction.guild_locale,
                        values=(REGULAR_CURRENCY,)
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )


def setup(bot: 'ChisatoBot') -> None:
    return bot.add_cog(SimpleEconomy(bot))
