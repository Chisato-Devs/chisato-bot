from __future__ import annotations

from typing import TypeAlias, cast

from disnake import (
    ui,
    SelectOption,
    MessageInteraction,
    TextChannel,
    Thread,
    VoiceChannel,
    StageChannel
)
from lavamystic import Player

from utils.basic import (
    EmbedUI,
    View,
    EmbedErrorUI,
    ChisatoBot
)
from utils.dataclasses.music import CustomPlaylist
from utils.exceptions import (
    NotFoundPlaylists
)
from utils.handlers.entertainment.music.views.playlists.utils import Utils
from utils.i18n import ChisatoLocalStore

Channel: TypeAlias = TextChannel | Thread | VoiceChannel | StageChannel
_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")

__all__ = (
    "Select",
)


class Select(View):
    def __init__(self, interaction: MessageInteraction) -> None:
        self._interaction = interaction

        self._current = cast(Player, interaction.guild.voice_client).current

        self._end = False
        self._bot: ChisatoBot = interaction.bot  # type: ignore

        self._from_option: dict[str, CustomPlaylist] = {}

        super().__init__(
            timeout=60,
            author=interaction.author,
            store=_t,
            guild=interaction.guild
        )

    @classmethod
    async def generate(cls, interaction: MessageInteraction) -> Select:
        self = cls(interaction=interaction)
        await self._playlist_generator()
        return self

    def _dump_playlist(self, i: int, playlist: CustomPlaylist) -> str:
        self._from_option[str(i)] = playlist
        return str(i)

    async def _playlist_generator(self) -> None:
        self._from_option.clear()
        item: ui.StringSelect = self.get_item("music.playlist.add.select")
        data: list[CustomPlaylist] = await self._bot.databases.music.get_playlists(self._interaction.author)

        if options := Utils.generate_options(
                data, self._from_option
        ):
            item.options = options
        else:
            raise NotFoundPlaylists(
                "Database given empty array"
            )

    @ui.string_select(
        placeholder="music.playlist.select.placeholder",
        custom_id="music.playlist.add.select",
        options=[SelectOption(label="Сдохло!")]
    )
    async def select_playlist(self, select: ui.StringSelect, interaction: MessageInteraction) -> None:
        self._end = True
        playlist = self._from_option.get(select.values[0])

        if not self._current:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.playlist.error.not_found_current",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )
            )

        await self._bot.databases.music.add_track_to_playlist(
            uid=playlist.id, track=self._current
        )

        await interaction.response.edit_message(
            embed=EmbedUI(
                title=_t.get(
                    "music.success.title", locale=interaction.guild_locale
                ),
                description=_t.get(
                    "music.playlist.success.track_added",
                    locale=interaction.guild_locale,
                    values=(
                        playlist.name,
                        self._current.title,
                        self._current.author
                    )
                )
            ).set_thumbnail(
                self._current.artwork
            ),
            view=None
        )
