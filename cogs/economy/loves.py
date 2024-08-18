import ast
from datetime import datetime
from typing import TYPE_CHECKING

from asyncpg import Record
from disnake import ApplicationCommandInteraction, Member, MessageInteraction, ui, HTTPException, NotFound, \
    ModalInteraction, Localized, Message
from disnake.ext.commands import Param
from disnake.utils import format_dt

from utils.basic import CogUI, EmbedUI, EmbedErrorUI, View, IntFormatter
from utils.basic.services.draw import DrawService, DEFAULT_AVATAR
from utils.consts import SUCCESS_EMOJI, ERROR_EMOJI, REGULAR_CURRENCY
from utils.exceptions import AlreadyMarried, NotMarried, NotEnoughMoney, MarryNotEnoughMoney
from utils.handlers.pagination import PaginatorView
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)


class LoveViews:
    class Confirm(View):
        __slots__ = (
            "_interaction", "_bot", "_end",
            "_with_married", "_for"
        )

        def __init__(
                self, interaction: ApplicationCommandInteraction | MessageInteraction,
                with_married: Member
        ) -> None:
            self._interaction = interaction
            self._bot: "ChisatoBot" = interaction.bot  # type: ignore

            self._with_married: Member = with_married
            self._for: Member = interaction.author

            self._end = False

            super().__init__(timeout=300, store=_t, guild=interaction.guild)

        async def on_timeout(self) -> None:
            if not self._end:
                for child in self.children:
                    child.disabled = True

                try:
                    await self._interaction.edit_original_response(view=self)
                except NotFound:
                    pass
                except HTTPException:
                    pass

        async def interaction_check(self, interaction: MessageInteraction) -> bool:
            async def send_message() -> None:
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get("eco.error.its_not_mine", locale=interaction.guild_locale),
                        member=interaction.author
                    ), ephemeral=True
                )

            if interaction.component.custom_id == "marry_decline":
                if interaction.author not in [self._with_married, self._for]:
                    await send_message()
                    return False
                return True

            if interaction.author != self._with_married:
                await send_message()
                return False
            return True

        @ui.button(
            label="loves.view.confirm.button.success.label",
            custom_id="marry_accept", emoji=SUCCESS_EMOJI
        )
        async def accept_marry(self, _, interaction: MessageInteraction) -> None:
            self._end = True

            try:
                await self._bot.databases.economy.marry_registry(
                    guild=interaction.guild, members=[self._for, self._with_married]
                )
            except AlreadyMarried:
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "loves.error.any_in_marry", locale=interaction.guild_locale
                        ), member=interaction.author
                    ), ephemeral=True
                )

            await interaction.response.edit_message(
                embed=EmbedUI(
                    title=_t.get("loves.success.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "loves.view.confirm.button.success.married", locale=interaction.guild_locale,
                        values=(self._with_married.mention, self._for.mention)
                    )
                ),
                view=None
            )

        @ui.button(
            label="loves.view.confirm.button.decline.label",
            custom_id="marry_decline", emoji=ERROR_EMOJI
        )
        async def decline_marry(self, _, interaction: MessageInteraction) -> None:
            self._end = True
            if interaction.author == self._for:
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get("loves.success.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "loves.view.confirm.button.decline.marry", locale=interaction.guild_locale,
                            values=(self._for.mention, self._with_married.mention)
                        )
                    ),
                    view=None
                )
                return

            await interaction.response.edit_message(
                embed=EmbedUI(
                    title=_t.get("loves.success.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "loves.view.confirm.button.decline.marry.part", locale=interaction.guild_locale,
                        values=(self._with_married.mention, self._for.mention)
                    )
                ),
                view=None
            )

    class Profile(View):
        __slots__ = (
            "_interaction", "_bot", "_end", "_for"
        )

        def __init__(
                self, interaction: ApplicationCommandInteraction | MessageInteraction
        ) -> None:
            self._interaction = interaction
            self._bot: "ChisatoBot" = interaction.bot  # type: ignore

            self._member: Member = interaction.author
            self._end = False

            super().__init__(timeout=300, author=interaction.author, store=_t, guild=interaction.guild)

        class IncludePagination(PaginatorView):
            __slots__ = (
                "_from_page", "_interaction",
                "_bot", "_end"
            )

            def __init__(self, **kwargs) -> None:
                self._from_page = kwargs.pop("from_page")
                self._interaction = kwargs.get("interaction")
                self._bot: "ChisatoBot" = self._interaction.bot
                self._end = False

                super().__init__(**kwargs)

            async def on_timeout(self) -> None:
                if not self._end:
                    for child in self.children:
                        child.disabled = True

                    try:
                        await self._interaction.edit_original_response(view=self)
                    except NotFound:
                        pass
                    except HTTPException:
                        pass

            @ui.button(emoji=SUCCESS_EMOJI, custom_id="marry_change_card_select", row=1)
            async def change_card_select(self, _, interaction: MessageInteraction) -> None:
                try:
                    await self._bot.databases.economy.marry_set_card(
                        guild=interaction.guild, member=interaction.author, card_name=self._from_page[self.page]
                    )
                except NotMarried:
                    return await interaction.response.send_message(embed=EmbedErrorUI(
                        description=_t.get(
                            "loves.error.now_not_married", locale=interaction.guild_locale
                        ), member=interaction.author
                    ), ephemeral=True)

                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get("loves.success.title", locale=interaction.guild_locale),
                        description=_t.get("loves.view.profile.pagination.select", locale=interaction.guild_locale)
                    ),
                    view=None
                )

        async def on_timeout(self) -> None:
            if not self._end:
                for child in self.children:
                    child.disabled = True

                try:
                    await self._interaction.edit_original_response(view=self)
                except NotFound:
                    pass
                except HTTPException:
                    pass

        @ui.button(
            label="loves.view.profile.change_card",
            emoji='<:Refresh3:1114986806480478318>', custom_id="marry_change_card"
        )
        async def change_card(self, _, interaction: MessageInteraction) -> None:
            try:
                data_list = ast.literal_eval(
                    (await self._bot.databases.economy.get_marry_solo(interaction.guild, interaction.author))[7]
                )
            except TypeError:
                return await interaction.response.send_message(embed=EmbedErrorUI(
                    description=_t.get(
                        "loves.error.now_not_married", locale=interaction.guild_locale
                    ), member=interaction.author
                ), ephemeral=True)

            if len(data_list) > 1:
                from_name = {
                    "love1": "https://i.ibb.co/0QTtTPH/love1.png",
                    "love2": "https://i.ibb.co/TL7Z11X/love2.png",
                    "love3": "https://i.ibb.co/42nN9y2/love3.png",
                    "love4": "https://i.ibb.co/3dy2vns/love4.png"
                }
                from_page = {}

                embeds = []
                title = _t.get("loves.banner.title", locale=interaction.guild_locale)
                for i, data in enumerate(data_list, start=1):
                    from_page[i] = data
                    embeds.append(
                        EmbedUI(title=title).set_image(from_name[data])
                    )

                await interaction.response.send_message(
                    embed=embeds[0], ephemeral=True,
                    view=self.IncludePagination(
                        embeds=embeds, author=interaction.author, footer=True,
                        from_page=from_page, interaction=interaction
                    )
                )
                return

            return await interaction.response.send_message(embed=EmbedErrorUI(
                description=_t.get(
                    "loves.banner.error.more_cards", locale=interaction.guild_locale
                ), member=interaction.author
            ), ephemeral=True)

        class IncludeModal(ui.Modal):
            __slots__ = (
                "_interaction", "_author",
                "_bot", "_typing", "_parent_interaction"
            )

            def __init__(
                    self,
                    interaction: MessageInteraction,
                    parent_interaction: ApplicationCommandInteraction,
                    typing: bool
            ) -> None:
                self._interaction = interaction
                self._parent_interaction = parent_interaction
                self._author = interaction.author

                self._bot: "ChisatoBot" = interaction.bot  # type: ignore

                self._typing = typing

                super().__init__(
                    title=_t.get(
                        "loves.balance.incoming" if typing else
                        "loves.balance.outgoing", locale=interaction.guild_locale
                    ),
                    components=[
                        ui.TextInput(
                            label=_t.get(
                                "loves.profile.modal.components.amount.title",
                                locale=interaction.guild_locale
                            ),
                            placeholder="10000",
                            min_length=1,
                            max_length=6,
                            custom_id="amount"
                        )
                    ], custom_id="marry_balance_actions_modal"
                )

            async def _task(self) -> None:
                embed, _, _, _ = await Love(self._bot).profile_logic(self._interaction)
                embed.set_image(self._interaction.message.embeds[0].image.url)
                await self._parent_interaction.edit_original_response(
                    embed=embed, view=LoveViews.Profile(interaction=self._interaction), attachments=[]
                )

            async def callback(self, interaction: ModalInteraction, /) -> Message | None:
                await interaction.response.defer(ephemeral=True)
                try:
                    amount = int(interaction.text_values['amount'])
                except ValueError:
                    return await interaction.edit_original_response(
                        embed=EmbedErrorUI(
                            _t.get(
                                "loves.balance.error.not_int",
                                locale=interaction.guild_locale
                            ), member=interaction.author
                        )
                    )

                try:
                    await self._bot.databases.economy.update_marry_balance(
                        guild=interaction.guild, member=interaction.author,
                        amount=amount, deposit=self._typing
                    )
                except NotEnoughMoney:
                    return await interaction.edit_original_response(
                        embed=EmbedErrorUI(
                            _t.get(
                                "loves.balance.error.not_enough_money",
                                locale=interaction.guild_locale
                            ), member=interaction.author
                        )
                    )
                except MarryNotEnoughMoney:
                    return await interaction.edit_original_response(
                        embed=EmbedErrorUI(
                            _t.get(
                                "loves.balance.error.marry_not_enough_money",
                                locale=interaction.guild_locale
                            ), member=interaction.author
                        )
                    )
                except NotMarried:
                    return await interaction.edit_original_response(
                        embed=EmbedErrorUI(
                            _t.get(
                                "loves.error.now_not_married", locale=interaction.guild_locale
                            ), member=interaction.author
                        )
                    )
                else:
                    match self._typing:
                        case True:
                            await interaction.edit_original_response(
                                embed=EmbedUI(
                                    title=_t.get("loves.success.title", locale=interaction.guild_locale),
                                    description=_t.get(
                                        "loves.balance.success.true", locale=interaction.guild_locale,
                                        values=(
                                            IntFormatter(amount).format_number(), amount,
                                            interaction.author.mention, interaction.author.name
                                        )
                                    )
                                ),
                                view=None
                            )

                            await self._bot.loop.create_task(self._task())
                        case False:
                            await interaction.edit_original_response(
                                embed=EmbedUI(
                                    title=_t.get("loves.success.title", locale=interaction.guild_locale),
                                    description=_t.get(
                                        "loves.balance.success.false", locale=interaction.guild_locale,
                                        values=(
                                            IntFormatter(amount).format_number(), amount,
                                            interaction.author.mention, interaction.author.name
                                        )
                                    )
                                ),
                                view=None
                            )

                            await self._bot.loop.create_task(self._task())

        async def check_partner(self) -> bool:
            data = await self._bot.databases.economy.get_marry_solo(
                guild=self._interaction.guild, member=self._interaction.author
            )
            return self._interaction.guild.get_member(
                data[2] if self._interaction.author.id != data[2] else data[3]
            ) is None

        @ui.button(
            label="loves.balance.button.deposit.label",
            emoji='<:Plus:1126911676399243394>', custom_id="marry_deposit"
        )
        async def deposit(self, _, interaction: MessageInteraction) -> None:
            self._end = True

            if await self.check_partner():
                return await interaction.response.send_message(embed=EmbedErrorUI(
                    description=_t.get(
                        "loves.balance.error.partner_left", locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ), ephemeral=True)

            await interaction.response.send_modal(self.IncludeModal(
                interaction=interaction, typing=True, parent_interaction=self._interaction
            ))

        @ui.button(
            label="loves.balance.button.withdraw.label",
            emoji='<:Minus:1126911673245106217>', custom_id="marry_withdraw"
        )
        async def withdraw(self, _, interaction: MessageInteraction) -> None:
            self._end = True

            if await self.check_partner():
                return await interaction.response.send_message(embed=EmbedErrorUI(
                    description=_t.get(
                        "loves.balance.error.partner_left", locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ), ephemeral=True)

            await interaction.response.send_modal(self.IncludeModal(
                interaction=interaction, typing=False, parent_interaction=self._interaction
            ))


class Love(CogUI):

    @CogUI.slash_command(name="marry")
    async def _marry(self, interaction: ApplicationCommandInteraction) -> ...:
        ...

    @_marry.sub_command(
        name="getting", description=Localized(
            "💍 Свадьбы: поженится с любимым человеком!",
            data=_t.get("loves.command.getting.description")
        )
    )
    async def getting(
            self, interaction: ApplicationCommandInteraction,
            member: Member = Param(
                name=Localized("участник", data=_t.get("loves.command.getting.option.member.name")),
                description=Localized(
                    "- укажи пользователя, с которым ты хочешь пожениться!",
                    data=_t.get("loves.command.getting.option.member.description")
                )
            )
    ) -> None:
        if interaction.author == member:
            return await interaction.response.send_message(embed=EmbedErrorUI(
                description=_t.get("loves.error.not_self", locale=interaction.guild_locale),
                member=interaction.author
            ), ephemeral=True)

        if member.bot:
            return await interaction.response.send_message(embed=EmbedErrorUI(
                description=_t.get("loves.error.not_bot", locale=interaction.guild_locale),
                member=interaction.author
            ), ephemeral=True)

        if (
                (await self.bot.databases.economy.get_marry_solo(guild=interaction.guild, member=member)) or
                (await self.bot.databases.economy.get_marry_solo(guild=interaction.guild, member=interaction.author))
        ):
            return await interaction.response.send_message(embed=EmbedErrorUI(
                description=_t.get("loves.error.any_in_marry", locale=interaction.guild_locale),
                member=interaction.author
            ), ephemeral=True)

        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("loves.marry.title", locale=interaction.guild_locale),
                description=_t.get(
                    "loves.marry.embed.description", locale=interaction.guild_locale,
                    values=(
                        interaction.author.mention, member.mention,
                        member.mention
                    )
                )
            ),
            view=LoveViews.Confirm(interaction=interaction, with_married=member)
        )

    async def profile_logic(
            self, interaction: ApplicationCommandInteraction | MessageInteraction
    ) -> tuple[EmbedUI, Record, Member | None, Member | None]:
        if not (
                data := await self.bot.databases.economy.get_marry_solo(
                    guild=interaction.guild, member=interaction.author
                )
        ):
            return await interaction.response.send_message(embed=EmbedErrorUI(
                description=_t.get("loves.error.now_not_married", locale=interaction.guild_locale),
                member=interaction.author
            ), ephemeral=True)

        embed = EmbedUI(
            title=_t.get("loves.profile.title", locale=interaction.guild_locale)
        )
        u1 = interaction.guild.get_member(data[2])
        u2 = interaction.guild.get_member(data[3])
        _nf = _t.get("loves.not_found.user.name", locale=interaction.guild_locale)
        embed.add_field(
            name=_t.get("loves.profile.embed.part.1", locale=interaction.guild_locale), inline=False,
            value=f"**{u1.name if u1 else _nf}** & **{u2.name if u2 else _nf}**"
        )

        [embed.add_field(name=name, value=value) for name, value in {
            _t.get("loves.profile.embed.part.2", locale=interaction.guild_locale): format_dt(data[5]),

            _t.get("loves.profile.embed.part.3", locale=interaction.guild_locale):
                IntFormatter((datetime.now().timestamp() - data[5])).convert_timestamp(),

            _t.get("loves.profile.embed.part.4", locale=interaction.guild_locale): f"`{data[4]}`" + REGULAR_CURRENCY
        }.items()]

        return embed, data, u1, u2

    @_marry.sub_command(
        name="profile",
        description=Localized(
            "💍 Свадьбы: посмотреть профиль!",
            data=_t.get("loves.command.profile.description")
        )
    )
    async def profile(self, interaction: ApplicationCommandInteraction) -> None:
        if not await DrawService(self.bot.session).get_status():
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get("eco.error.api_error", locale=interaction.guild_locale),
                    member=interaction.author
                )
            )

        embed, data, u1, u2 = await self.profile_logic(interaction)

        async with DrawService(self.bot.session) as ir:
            file = await ir.draw_image(
                "love_banner",
                bannerName=data[6],
                firstAvatar=u1.display_avatar.url if u1 else DEFAULT_AVATAR,
                secondAvatar=u2.display_avatar.url if u2 else DEFAULT_AVATAR
            )

        embed.set_image(file=file)
        await interaction.response.send_message(embed=embed, view=LoveViews.Profile(interaction=interaction))

    @_marry.sub_command(
        name="discard",
        description=Localized(
            "💍 Свадьбы: развестись!",
            data=_t.get("loves.command.discard.description")
        )
    )
    async def discard(self, interaction: ApplicationCommandInteraction) -> None:
        if not (
                data := await self.bot.databases.economy.get_marry_solo(
                    guild=interaction.guild, member=interaction.author
                )
        ):
            return await interaction.response.send_message(embed=EmbedErrorUI(
                description=_t.get("loves.error.now_not_married", locale=interaction.guild_locale),
                member=interaction.author
            ), ephemeral=True)

        async def add_money(amount: int, user: Member | None) -> None:
            if user:
                await self.bot.databases.economy.add_balance(guild=interaction.guild.id, member=user.id, amount=amount)
                await self.bot.databases.transactions.add(
                    guild=interaction.guild.id, user=user.id, amount=amount,
                    locale_key="loves.command.discard.transaction.share", typing=True
                )

        fraction = data[4] // 2
        if partner := interaction.guild.get_member(data[2] if interaction.author.id != data[2] else data[3]):
            time = datetime.now().timestamp() - data[5]
            await interaction.response.send_message(embed=EmbedUI(
                title=_t.get("loves.success.title", locale=interaction.guild_locale),
                description=_t.get(
                    "loves.command.discard.embed.description", locale=interaction.guild_locale,
                    values=(
                        interaction.author.mention, partner.mention,
                        format_dt(datetime.fromtimestamp(time)),
                        IntFormatter(time).convert_timestamp(),
                        data[4], data[4]
                    )
                )
            ))

            for member in [partner, interaction.author]:
                await add_money(amount=fraction, user=member)
        else:
            await add_money(amount=fraction, user=interaction.author)
            await interaction.response.send_message(
                embed=EmbedUI(
                    title=_t.get("loves.success.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "loves.command.discard.embed.description.with_not_partner",
                        locale=interaction.guild_locale, values=(
                            data[2] if interaction.author.id != data[2] else data[3],
                        )
                    )
                ),
                ephemeral=True
            )

        await self.bot.databases.economy.marry_discard(data[1])


def setup(bot: "ChisatoBot") -> None:
    bot.add_cog(Love(bot))
