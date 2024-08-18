from typing import Callable, TYPE_CHECKING

from disnake import MessageInteraction, ModalInteraction
from disnake.ui import Modal, TextInput

from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")


class DeletePlaylist(Modal):
    def __init__(
            self,
            interaction: MessageInteraction,
            after_callback: Callable[[ModalInteraction], any],
            playlist_name: str
    ) -> None:
        self._interaction = interaction
        self._bot: ChisatoBot = interaction.bot  # type: ignore
        self._after_callback = after_callback

        super().__init__(
            title=_t.get(
                "music.playlists.delete_name",
                locale=interaction.guild_locale
            ),
            custom_id="playlists.modal.delete",
            components=[
                TextInput(
                    label=_t.get(
                        "music.playlists.playlist_name",
                        locale=interaction.guild_locale
                    ),
                    placeholder=playlist_name,
                    max_length=255,
                    custom_id="playlists.check.name"
                )
            ]
        )

    async def callback(self, interaction: ModalInteraction, /) -> None:
        await self._after_callback(interaction)
