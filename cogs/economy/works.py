import asyncio
from random import (
    randint,
    choice
)
from typing import Final

from disnake import (
    SelectOption,
    Localized,
    MessageInteraction,
    Embed,
    ApplicationCommandInteraction
)
from disnake.ext.commands import (
    slash_command,
    cooldown,
    BucketType
)
from disnake.ui import (
    string_select,
    StringSelect,
    button
)

from utils.basic import (
    View,
    ChisatoBot,
    CogUI,
    IntFormatter,
    EmbedErrorUI,
    EmbedUI
)
from utils.consts import REGULAR_CURRENCY
from utils.dataclasses import Work
from utils.exceptions import (
    AlreadyHaveWork,
    DoesntHaveWork
)
from utils.handlers.economy import (
    check_is_on,
    check_in_fight,
    check_in_game
)
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load(__file__)
WORKS_EMOJI: Final[dict[str, str]] = {
    'welder': '<:hammer:1131515651626897428>',
    'lumberjack': '<:treedeciduous:1131516192926998538>',
    'refueler': '<:fuel:1131516479104368651>',
    'miner': '<:gem:1131517233978413136>',
    'programmer': '<:laptop:1131517670072799292>'
}


class WorkAcceptView(View):
    def __init__(
            self,
            work_name: str,
            interaction: MessageInteraction
    ) -> None:
        self.work_name: str = work_name
        self.interaction: MessageInteraction = interaction
        self.bot: ChisatoBot = interaction.bot  # type: ignore

        self.__end: bool = False

        super().__init__(
            timeout=300,
            store=_t,
            interaction=interaction
        )

    @button(
        label="works.view.accept.button.apply.label",
        emoji='<:factory:1131514491977355349>',
        custom_id='work_accept_button'
    )
    async def interview_callback(
            self, _, interaction: MessageInteraction
    ) -> None:
        try:
            await self.bot.databases.works.add(
                member=interaction.author.id, guild=interaction.guild.id, work_type=self.work_name
            )
        except AlreadyHaveWork:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "works.error.already_employed",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        self.__end = True
        works_name_dict = _t.get(
            "works.dict.names", locale=interaction.guild_locale
        )

        await interaction.response.edit_message(
            embed=EmbedUI(
                title=_t.get("works.success.title", locale=interaction.guild_locale),
                description=_t.get(
                    "works.success.employ.title",
                    locale=interaction.guild_locale,
                    values=(works_name_dict[self.work_name],)
                ),
                timestamp=interaction.created_at
            ),
            view=None
        )

    @button(
        label="works.back.label", custom_id="works.back.label",
        emoji='<:ArrowLeft:1114648737730539620>'
    )
    async def back_callback(
            self, _, interaction: MessageInteraction
    ) -> None:
        self.__end = True
        await interaction.response.edit_message(
            embed=await Works.interview(interaction, bot=self.bot),
            view=WorksSelect(interaction=interaction)
        )


class WorksSelect(View):
    def __init__(
            self,
            interaction: ApplicationCommandInteraction | MessageInteraction
    ) -> None:
        self.interaction: ApplicationCommandInteraction | MessageInteraction = interaction
        self.bot: "ChisatoBot" = interaction.bot  # type: ignore

        self.__end: bool = False

        super().__init__(
            timeout=300,
            store=_t,
            interaction=interaction
        )

    @string_select(
        placeholder="works.select.string.placeholder",
        custom_id='works_select_job',
        options=[
            SelectOption(
                label="works.option.welder.label",
                description="works.option.welder.description",
                value='welder',
                emoji='<:hammer:1131515651626897428>'
            ),
            SelectOption(
                label="works.option.lumberjack.label",
                description="works.option.lumberjack.description",
                value='lumberjack',
                emoji='<:treedeciduous:1131516192926998538>'
            ),
            SelectOption(
                label="works.option.refueler.label",
                description="works.option.refueler.description",
                value='refueler',
                emoji='<:fuel:1131516479104368651>'
            ),
            SelectOption(
                label="works.option.miner.label",
                description="works.option.miner.description",
                value='miner',
                emoji='<:gem:1131517233978413136>'
            ),
            SelectOption(
                label="works.option.programmer.label",
                description="works.option.programmer.description",
                value='programmer',
                emoji='<:laptop:1131517670072799292>'
            )
        ]
    )
    async def jobs_callback(
            self, select: StringSelect, interaction: MessageInteraction
    ) -> None:
        work_name, work_count = await self.bot.databases.works.values(
            member=interaction.author.id,
            guild=interaction.guild.id
        )
        if work_name:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "works.error.already_employed",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        self.__end = True
        work: Work = self.bot.databases.works.get_work(select.values[0])

        if work.need_works_count > work_count:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "works.error.insufficient_works",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        works_name_dict = _t.get(
            "works.dict.names",
            locale=interaction.guild_locale
        )
        await interaction.response.edit_message(
            embed=EmbedUI(
                title=f"{WORKS_EMOJI[select.values[0]]} {works_name_dict[select.values[0]]}",
                description=_t.get(
                    "works.preview.stats.description",
                    locale=interaction.guild_locale,
                    values=(
                        works_name_dict[select.values[0]].lower(),
                        work.need_works_count,
                        work.initial_payment, REGULAR_CURRENCY,
                        work.final_payment, REGULAR_CURRENCY,
                        REGULAR_CURRENCY,
                        work.final_premium, REGULAR_CURRENCY,
                    )
                )
            ),
            view=WorkAcceptView(interaction=interaction, work_name=select.values[0])
        )


class Works(CogUI):

    @slash_command(name='works', dm_permission=False)
    @check_is_on()
    @check_in_game()
    @check_in_fight()
    async def _works(self, interaction: ApplicationCommandInteraction) -> ...:
        ...

    @staticmethod
    async def interview(
            interaction: MessageInteraction | ApplicationCommandInteraction, *, bot: 'ChisatoBot'
    ) -> Embed:
        return EmbedUI(
            title=_t.get(
                "works.title",
                locale=interaction.guild_locale
            ),
            description=_t.get(
                "works.choose.work.description",
                locale=interaction.guild_locale,
                values=(
                    (
                        await bot.databases.works.values(
                            member=interaction.author.id, guild=interaction.guild.id
                        )
                    )[1],
                )
            )
        )

    @_works.sub_command(
        name='interview',
        description=Localized(
            "💼 Работы: сходить на собеседование, чтобы устроиться на работу!",
            data=_t.get("works.command.interview.description")
        )
    )
    async def i(
            self, interaction: ApplicationCommandInteraction
    ) -> None:
        await interaction.response.send_message(
            embed=await self.interview(interaction, bot=self.bot),
            view=WorksSelect(interaction=interaction)
        )

    @classmethod
    def _is_premium(cls) -> bool:
        return choice([True, False, False])

    @_works.sub_command(
        name='start-out',
        description=Localized(
            "💼 Работы: выйти на работу! (1 раз в 2 часа)",
            data=_t.get("works.command.start.description")
        )

    )
    @cooldown(1, 3600, type=BucketType.member)
    async def s(
            self, interaction: ApplicationCommandInteraction
    ) -> None:
        work_name, _ = await self.bot.databases.works.values(
            member=interaction.author.id, guild=interaction.guild.id
        )
        if not work_name:
            self.s.reset_cooldown(interaction)
            raise DoesntHaveWork

        work: Work = self.bot.databases.works.get_work(work_name)

        salary = randint(work.initial_payment, work.final_payment)
        tax = round(salary / 100 * 7)
        summary = salary - tax

        if self._is_premium():
            premium_salary = randint(work.initial_premium, work.final_premium)
            summary += premium_salary

            description = _t.get(
                "works.success.worked_outed.with_premium",
                locale=interaction.guild_locale, values=(
                    IntFormatter(salary).format_number(), REGULAR_CURRENCY,
                    IntFormatter(premium_salary).format_number(), REGULAR_CURRENCY,
                    IntFormatter(tax).format_number(), REGULAR_CURRENCY,
                    IntFormatter(summary).format_number(), REGULAR_CURRENCY
                )
            )
        else:
            description = _t.get(
                "works.success.worked_outed",
                locale=interaction.guild_locale, values=(
                    IntFormatter(salary).format_number(), REGULAR_CURRENCY,
                    IntFormatter(tax).format_number(), REGULAR_CURRENCY,
                    IntFormatter(summary).format_number(), REGULAR_CURRENCY
                )
            )

        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("works.title", locale=interaction.guild_locale),
                description=description
            )
        )

        await asyncio.gather(
            self.bot.databases.economy.add_balance(
                guild=interaction.guild.id,
                member=interaction.author.id,
                amount=summary
            ),
            self.bot.databases.transactions.add(
                guild=interaction.guild.id,
                user=interaction.author.id,
                amount=summary,
                typing=True,
                locale_key="works.transactions.success.went_to_work"
            ),
            self.bot.databases.works.count_update(
                guild=interaction.guild.id,
                member=interaction.author.id
            )
        )

    @_works.sub_command(
        name='quit',
        description=Localized(
            "💼 Работы: уволится с работы!",
            data=_t.get("works.quit.command.description")
        )
    )
    async def q(
            self, interaction: ApplicationCommandInteraction
    ) -> None:
        _, work_count = await self.bot.databases.works.values(member=interaction.author.id, guild=interaction.guild.id)
        await self.bot.databases.works.remove(member=interaction.author.id, guild=interaction.guild.id)

        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("works.title", locale=interaction.guild_locale),
                description=_t.get(
                    "works.work_quit.embed.description",
                    locale=interaction.guild_locale,
                    values=(work_count,)
                )
            ),
            ephemeral=True
        )


def setup(bot: ChisatoBot) -> None:
    return bot.add_cog(Works(bot))
