from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from disnake import MessageInteraction, TextInputStyle, ModalInteraction
from disnake.ui import Modal, TextInput

from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.handlers.entertainment.music.containers.edit import EditContainer

_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")


class EditPlaylist(Modal):
    def __init__(
            self,
            interaction: MessageInteraction,
            container: EditContainer,
            callback: Callable[[ModalInteraction], any]
    ) -> None:
        self._interaction = interaction
        self._bot: ChisatoBot = interaction.bot  # type: ignore
        self._container = container
        self._done_callback = callback

        super().__init__(
            title=_t.get(
                "music.playlists.edit",
                locale=interaction.guild_locale
            ),
            components=[
                TextInput(
                    label=_t.get(
                        "music.playlists.name",
                        locale=interaction.guild_locale
                    ),
                    placeholder="...",
                    style=TextInputStyle.short,
                    max_length=100,
                    custom_id="playlists.modal.edit.name"
                )
            ]
        )

    async def callback(self, interaction: ModalInteraction, /) -> None:
        self._container.name = interaction.text_values["playlists.modal.edit.name"]
        await self._done_callback(interaction)
