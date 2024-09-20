from __future__ import annotations

from typing import TYPE_CHECKING

import yarl
from disnake import (
    ui,
    SelectOption,
    MessageInteraction,
    ModalInteraction,
    Embed,
    ApplicationCommandInteraction
)
from harmonize.connection import Pool
from harmonize.enums import LoadType

from utils.basic import (
    EmbedUI,
    View,
    EmbedErrorUI
)
from utils.exceptions import (
    MaximumPlaylist,
    AlreadyCreatedPlaylist
)
from utils.handlers.entertainment.music.containers import CreateContainer
from utils.handlers.entertainment.music.decorators import (
    has_nodes_button
)
from utils.handlers.entertainment.music.modals import GetQuery
from utils.handlers.entertainment.music.modals.playlists import (
    CreatePlaylist
)
from utils.handlers.entertainment.music.views.playlists.page import ViewPage
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")


class Create(View):
    DEFAULT_EMOJI: str = "<:Star2:1131445020210245715>"

    def __init__(
            self,
            interaction: MessageInteraction,
            main_interaction: ApplicationCommandInteraction | MessageInteraction
    ) -> None:
        self._interaction = interaction
        self._main_interaction = main_interaction
        self._bot: ChisatoBot = interaction.bot  # type: ignore

        self._container: CreateContainer = CreateContainer()
        self.end = False

        super().__init__(
            interaction=interaction,
            store=_t,
            timeout=300
        )

    @property
    def container(self) -> CreateContainer:
        return self._container

    def from_name(self, container: CreateContainer) -> str:
        return container.name if container.name else _t.get(
            "music.not_specified",
            locale=self._interaction.guild_locale
        )

    def generate_embed(self, container: CreateContainer) -> Embed:
        return EmbedUI(
            title=_t.get("music.playlist_create.title", self._interaction.guild_locale),
            description=_t.get(
                "music.playlist_create.description",
                locale=self._interaction.guild_locale,
                values=(
                    self.from_name(container),
                    str(container.closed),
                    str(len(container.tracks))
                )
            )
        )

    async def _change_name_callback(self, interaction: ModalInteraction) -> None:
        await interaction.response.edit_message(
            embed=self.generate_embed(self._container),
            view=self
        )

    async def _selected_track(self, interaction: MessageInteraction, track: Playable) -> None:
        if len(self.container.tracks) != 50:
            self.container.tracks = track

        await interaction.edit_original_response(
            embed=self.generate_embed(self._container),
            view=self
        )

    @has_nodes_button
    async def _query_from_modal(self, interaction: ModalInteraction) -> None:
        if len(self.container.tracks) == 50:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.error.playlist_tracks_limit",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        await interaction.response.edit_message(
            embed=EmbedUI(
                title=_t.get("music.wait.title", locale=interaction.guild_locale)
            ),
            view=None
        )

        self.end = True
        query = interaction.text_values["playlists.query"]
        if yarl.URL(query).host:
            node = Pool.get_best_node()
            result = await node.get_tracks(query)

            if not result or not result.tracks or result.error:
                await interaction.edit_original_response(
                    embed=self.generate_embed(self._container),
                    view=self
                )
                return

            if result.tracks[0].source_name == "youtube":
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "music.playlists.error.not_youtube",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    )
                )

            if result.load_type == LoadType.PLAYLIST:
                self.container.tracks.extend(result.tracks[:50 - len(self.container.tracks)])
                await interaction.edit_original_response(
                    embed=self.generate_embed(self._container),
                    view=self
                )
                return

            self.container.tracks = result.tracks[0]
            await interaction.edit_original_response(
                embed=self.generate_embed(self._container),
                view=self
            )
            return
        else:
            from utils.handlers.entertainment.music.views.select_track import SelectTrackView

            await interaction.edit_original_response(
                embed=EmbedUI(
                    title=_t.get(
                        "music.music_find.title",
                        locale=interaction.guild_locale
                    ),
                    description=_t.get(
                        "music.select_track",
                        locale=interaction.locale
                    )
                ),
                view=SelectTrackView(interaction, self._bot, query, self._selected_track, False)
            )

    @ui.string_select(
        placeholder="music.create_playlist.placeholder",
        custom_id="playlists.create.info_select",
        options=[
            SelectOption(
                label="music.playlist.change_name",
                value="playlists.create.name",
                emoji=DEFAULT_EMOJI
            ),
            SelectOption(
                label="music.playlist.change_privacy",
                value="playlists.create.open_close",
                emoji=DEFAULT_EMOJI
            ),
            SelectOption(
                label="music.playlist.add_track",
                value="playlists.create.add",
                emoji=DEFAULT_EMOJI
            )
        ]
    )
    async def set_up_playlist(self, select: ui.StringSelect, interaction: MessageInteraction) -> None:
        match select.values[0]:
            case "playlists.create.name":
                return await interaction.response.send_modal(
                    CreatePlaylist(
                        interaction=interaction,
                        container=self._container,
                        callback=self._change_name_callback
                    )
                )

            case "playlists.create.open_close":
                self._container.closed = not self._container.closed
                await interaction.response.edit_message(
                    embed=self.generate_embed(self._container),
                    view=self
                )

            case "playlists.create.add":
                await interaction.response.send_modal(
                    GetQuery(
                        interaction=interaction,
                        after_callback=self._query_from_modal
                    )
                )

    @ui.button(
        label="music.playlist.create.confirm",
        custom_id="playlists.create.button.back",
        emoji="<:Plus:1126911676399243394>"
    )
    async def create_playlist_back(self, _: ui.Button, interaction: MessageInteraction) -> None:
        if self._container.name is None:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.playlist.error.not_name",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        self.end = True

        try:
            await self._bot.databases.music.create_playlist(
                name=self._container.name,
                owner=interaction.author,
                closed=self._container.closed,
                tracks=self._container.tracks
            )
        except MaximumPlaylist:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.playlist.error.not_more_5",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
        except AlreadyCreatedPlaylist:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.playlist.error.already_used_name",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
        else:
            await interaction.response.edit_message(
                embed=EmbedUI(
                    title=_t.get("music.success.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "music.playlist.create.success",
                        locale=interaction.guild_locale
                    )
                ),
                view=None
            )

        try:
            generated_view = await ViewPage.generate(
                self._main_interaction,
                await self._bot.databases.music.get_playlist(
                    owner=interaction.author,
                    name=self._container.name
                )
            )
            await self._main_interaction.edit_original_response(
                embeds=await generated_view.generate_embed(),
                view=generated_view
            )
        except Exception as e:
            _ = e
