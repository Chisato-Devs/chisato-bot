from __future__ import annotations

from asyncio import gather
from typing import TYPE_CHECKING, TypeVar, Self

from disnake import Member, ApplicationCommandInteraction, SelectOption, MessageInteraction, ui, ModalInteraction

from utils.basic import View, EmbedUI
from utils.handlers.management.settings.views.modals import VipeSubmit
from utils.handlers.management.settings.views.modules import LevelsModule, ReportsModule, RoomsModule, EconomyModule, \
    BannerModule, LogsModule
from utils.handlers.management.settings.views.modules.main import WarnsModule, PermissionsModule
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_V = TypeVar("_V", bound=View)
_t = ChisatoLocalStore.load(__file__)


class SettingsView(View):
    class IncludeSelect(ui.StringSelect):
        __slots__ = (
            "_bot", "__parent_view",
            "__components", "__interaction"
        )

        def __init__(
                self,
                bot: ChisatoBot,
                components: dict[str, _V],
                options: list[SelectOption],
                main_modules: bool,
                interaction: ApplicationCommandInteraction | MessageInteraction,
                parent_view: View
        ) -> None:
            self._bot = bot

            self.__components = components
            self.__interaction = interaction
            self.__parent_view = parent_view

            super().__init__(
                options=options,
                placeholder=_t.get("settings.module.main.placeholder", locale=interaction.guild_locale) if main_modules
                else _t.get("settings.module.placeholder", locale=interaction.guild_locale)
            )

        async def callback(self, interaction: MessageInteraction) -> None:
            self.__parent_view.end = True
            await self.__components[self.values[0]].main_callback(interaction=interaction)

    __slots__ = (
        "author", "bot",
        "end", "__interaction"
    )

    def __init__(
            self,
            member: Member,
            bot: ChisatoBot,
            comps: dict[str, _V],
            options: list[SelectOption],
            interaction: ApplicationCommandInteraction | MessageInteraction,
            main_components: dict[str, _V],
            main_options: list[SelectOption]
    ) -> None:
        self.author = member
        self.bot = bot
        self.end = False

        self.__interaction = interaction

        super().__init__(
            author=member, timeout=300,
            store=_t, interaction=interaction
        )

        self.add_item(self.IncludeSelect(
            bot=bot,
            components=main_components,
            options=main_options,
            interaction=interaction,
            parent_view=self,
            main_modules=True
        ))

        self.add_item(self.IncludeSelect(
            bot=bot,
            components=comps,
            options=options,
            interaction=interaction,
            parent_view=self,
            main_modules=False
        ))

    async def _remove_data(self, interaction: ModalInteraction) -> None:
        await interaction.response.edit_message(
            embed=EmbedUI(
                title=_t.get("settings.success.title", locale=interaction.guild_locale),
                description=_t.get(
                    "settings.vipe.success.description",
                    locale=interaction.guild_locale,
                    values=(
                        interaction.author.mention,
                        interaction.author
                    )
                )
            ),
            view=None
        )

        await self.bot.databases.vipe_tables_from_guild(interaction.guild)

    @ui.button(
        label="settings.module.main.vipe.button",
        emoji="<:Trashcan:1114376699027660820>",
        custom_id="settings.database.vipe.button",
        row=3
    )
    async def clear_database(self, _, interaction: MessageInteraction) -> None:
        await interaction.response.send_modal(
            VipeSubmit(interaction, self._remove_data)
        )

        self.end = True

    @classmethod
    async def generate(
            cls,
            member: Member,
            interaction: ApplicationCommandInteraction | MessageInteraction
    ) -> Self:
        components = {}
        main_components = {}

        options = []
        main_options = []

        coroutines = [
            component(
                member=interaction.author, interaction=interaction
            ).initialize_database()

            for component in [
                EconomyModule,
                BannerModule,
                ReportsModule,
                RoomsModule,
                LevelsModule,
                LogsModule,
                PermissionsModule,
                WarnsModule
            ]
        ]

        for comp in await gather(*coroutines):
            (main_components if comp.main_module else components)[comp.__class__.__name__] = comp
            (main_options if comp.main_module else options).append(comp.option)

        return cls(
            member=member,
            interaction=interaction,
            bot=interaction.bot,  # type: ignore
            options=options,
            comps=components,
            main_options=main_options,
            main_components=main_components
        )
