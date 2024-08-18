from typing import TYPE_CHECKING, TypeVar

from disnake import MessageInteraction, ui

from utils.basic import EmbedUI
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_V = TypeVar("_V", bound="View")
_t = ChisatoLocalStore.load("./utils/handlers/management/settings/views/view.py")


class BackButton(ui.Button):
    __slots__ = (
        "bot", "_m"
    )

    def __init__(
            self, bot: 'ChisatoBot', *,
            module: _V, row: int = 0
    ) -> None:
        self.bot = bot
        self._m = module

        super().__init__(
            label="settings.button.back.label",
            emoji="<:ArrowLeft:1114648737730539620>",
            custom_id="back_reports_button", row=row
        )

    async def callback(self, interaction: MessageInteraction) -> None:
        from utils.handlers.management.settings.views import SettingsView

        self._m.end = True
        await interaction.response.edit_message(
            embed=EmbedUI(
                title=_t.get("settings.title", locale=interaction.guild_locale),
                description=_t.get(
                    "settings.embed.description", locale=interaction.guild_locale
                )
            ),
            view=await SettingsView.generate(
                member=interaction.author, interaction=interaction
            )
        )
