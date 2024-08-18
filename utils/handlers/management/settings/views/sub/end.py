from typing import TYPE_CHECKING, cast

from disnake import Member, Interaction, errors, MessageInteraction, ui

from utils.basic import View, EmbedUI
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    pass

_t = ChisatoLocalStore.load("./utils/handlers/management/settings/views/view.py")


class EndView(View):
    __slots__ = (
        "bot", "__end",
        "__interaction"
    )

    def __init__(self, author: Member, interaction: Interaction) -> None:
        self.__interaction = interaction
        self.__end = False

        self.bot: 'ChisatoBot' = interaction.bot  # type: ignore

        super().__init__(
            author=author, timeout=300, store=_t,
            interaction=cast(MessageInteraction, interaction)
        )

    async def on_timeout(self) -> None:
        if not self.__end:
            for child in self.children:
                child.disabled = True

            try:
                await self.__interaction.edit_original_response(view=self)
            except (errors.HTTPException or errors.InteractionResponded):
                pass

    @ui.button(
        emoji=f"<:Trashcan:1114376699027660820>",
        label="settings.button.delete.label"
    )
    async def remove_message(self, _, interaction: MessageInteraction) -> None:
        self.__end = True

        try:
            await interaction.response.defer()
            await interaction.followup.delete_message(interaction.message.id)
        except errors.Forbidden:
            pass

    @ui.button(
        emoji=f"<:Arrowright:1114674030331576401>",
        label="settings.button.continue.label"
    )
    async def next(self, _, interaction: MessageInteraction) -> None:
        from utils.handlers.management.settings.views import SettingsView
        self.__end = True

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
