from __future__ import annotations

from typing import Callable

from disnake import MessageInteraction, ModalInteraction, TextInputStyle
from disnake.ui import Modal, TextInput

from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")


class GetQuery(Modal):
    def __init__(
            self,
            interaction: MessageInteraction,
            after_callback: Callable[[ModalInteraction], any]
    ) -> None:
        self.interaction = interaction
        self.after_callback = after_callback

        super().__init__(
            title=_t.get(
                "music.playlists.track_get",
                locale=interaction.guild_locale
            ),
            custom_id="playlists.modal.get_query",
            components=[
                TextInput(
                    label=_t.get(
                        "music.playlists.write_query",
                        locale=interaction.guild_locale
                    ),
                    placeholder="...",
                    style=TextInputStyle.short,
                    max_length=128,
                    custom_id="playlists.query"
                )
            ]
        )

    async def callback(self, interaction: ModalInteraction, /) -> None:
        await self.after_callback(interaction)
