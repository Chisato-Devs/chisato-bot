from __future__ import annotations

from math import ceil
from typing import TypeAlias, TYPE_CHECKING

from disnake import (
    ui,
    SelectOption,
    MessageInteraction,
    TextChannel,
    Thread,
    VoiceChannel,
    StageChannel,
    Embed,
    Forbidden,
    HTTPException, ModalInteraction, Locale
)

from utils.basic import (
    View,
    ChisatoBot,
    EmbedUI,
    EmbedErrorUI
)
from utils.exceptions import PlaylistNotFound
from utils.handlers.entertainment.music.enums import FromSourceEmoji
from utils.handlers.entertainment.music.generators.queue import QueueGenerator
from utils.handlers.entertainment.music.modals import GetQuery
from utils.handlers.pagination import PaginatorView
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.handlers.entertainment.music.views.playlists.page import ViewPage
    from harmonize.objects import Track

Channel: TypeAlias = TextChannel | Thread | VoiceChannel | StageChannel
_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")


class TrackEditor(View):
    def __init__(
            self,
            main_interaction: MessageInteraction,
            interaction: MessageInteraction,
            view_page: ViewPage
    ) -> None:
        self._interaction = interaction
        self._main_interaction = main_interaction
        self.view_page: ViewPage = view_page
        self.end = False
        self._bot: ChisatoBot = interaction.bot  # type: ignore

        super().__init__(
            timeout=300,
            author=self._interaction.author,
            store=_t,
            guild=self._interaction.guild
        )

    @classmethod
    async def generate(
            cls,
            main_interaction: MessageInteraction,
            interaction: MessageInteraction,
            view: ViewPage
    ) -> TrackEditor:
        self = cls(main_interaction, interaction, view)
        return self

    class RemoveTrack(PaginatorView):
        def __init__(
                self, embeds: list[Embed], *,
                main_interaction: MessageInteraction,
                interaction: MessageInteraction,
                last_view: TrackEditor,
                from_page_options: dict[int, list[SelectOption]]
        ) -> None:
            self._main_interaction: MessageInteraction = main_interaction
            self._interaction: MessageInteraction = interaction
            self._last_view: TrackEditor = last_view
            self._bot: ChisatoBot = interaction.bot  # type: ignore

            self._from_page_options: dict[int, list[SelectOption]] = from_page_options

            super().__init__(
                embeds=embeds,
                footer=True,
                timeout=300,
                author=interaction.author,
                store=_t
            )

        @classmethod
        def _generate_backend(
                cls, tracks: list[Track], locale: Locale
        ) -> tuple[list[Embed], dict[int, list[SelectOption]]]:
            options: list[SelectOption] = []
            embeds: list[EmbedUI] = []
            strokes: list[str] = []
            _from_page_options: dict[int, list[SelectOption]] = {}

            chunk_size = 20
            num_chunks = ceil(len(tracks) / chunk_size)

            option_description = _t.get(
                "music.playlist.author.part", locale=locale
            )
            title = _t.get(
                "music.track_remove.title", locale=locale
            )
            description = _t.get(
                "music.playlist.track_remove.description", locale=locale
            )

            for chunk_index in range(num_chunks):
                options.clear()
                strokes.clear()

                start_index = chunk_index * chunk_size
                end_index = min(start_index + chunk_size, len(tracks))

                for i, track in enumerate(tracks[start_index:end_index], start=start_index + 1):
                    options.append(
                        SelectOption(
                            label=f"{i}. " + track.title[:32],
                            description=option_description + track.author[:64],
                            value=str(i),
                            emoji=getattr(FromSourceEmoji, track.source).value
                        )
                    )
                    strokes.append(
                        QueueGenerator.generate_stroke(i, track=track)
                    )

                _from_page_options[chunk_index + 1] = options.copy()

                embeds.append(
                    EmbedUI(title=title, description=description + "\n".join(strokes))
                )

            return embeds, _from_page_options

        async def before_edit_message(self, interaction: MessageInteraction) -> any:
            self.remove_tracks_callback.options = self._from_page_options[self.page]

        @classmethod
        async def generate(
                cls, *,
                main_interaction: MessageInteraction,
                interaction: MessageInteraction,
                last_view: TrackEditor
        ) -> tuple[Embed, TrackEditor.RemoveTrack]:
            embeds, from_options = cls._generate_backend(
                last_view.view_page.playlist.tracks, interaction.guild_locale
            )
            self = None

            if embeds:
                self = cls(
                    embeds,
                    main_interaction=main_interaction,
                    interaction=interaction,
                    last_view=last_view,
                    from_page_options=from_options
                )
                await self.before_edit_message(interaction)

            return embeds[0] if embeds else None, self

        @ui.select(
            placeholder="music.playlist.page.track_editor.remove_track",
            custom_id="playlists.page.track_editor.remove_track",
            options=[SelectOption(label="NOT GENERATED")],
        )
        async def remove_tracks_callback(self, select: ui.Select, interaction: MessageInteraction) -> None:
            track = self._last_view.view_page.playlist.tracks[int(select.values[0]) - 1]
            try:
                new_playlist = await self._bot.databases.music.edit_playlist_tracks(
                    uid=self._last_view.view_page.playlist.id, track=track
                )
            except PlaylistNotFound:
                return await interaction.response.edit_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "music.playlist.not_found",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    )
                )

            await interaction.response.edit_message(
                embed=EmbedUI(
                    title=_t.get("music.success.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "music.playlist.success.remove_track",
                        locale=interaction.guild_locale,
                        values=(
                            self._last_view.view_page.playlist.name,
                            track.title, track.author
                        )
                    )
                ),
                view=None
            )

            try:
                from utils.handlers.entertainment.music.views.playlists.page import ViewPage

                new_view = await ViewPage.generate(self._main_interaction, new_playlist)
                await self._main_interaction.edit_original_response(
                    embeds=await new_view.generate_embed(),
                    view=new_view
                )
            except (HTTPException, Forbidden):
                pass

    @ui.button(
        label="music.playlist.remove_track.label",
        emoji="<:Minus:1126911673245106217>", row=0,
        custom_id="playlists.page.track_editor.remove_tracks",
    )
    async def remove_tracks_button(self, _, interaction: MessageInteraction) -> None:
        embed, view = await self.RemoveTrack.generate(
            main_interaction=self._main_interaction,
            interaction=interaction, last_view=self
        )

        if embed and view:
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.playlist.tracks.not_found",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )
            )

    async def _prompt_track_callback(self, interaction: MessageInteraction, track: Track) -> None:
        try:
            new_playlist = await self._bot.databases.music.edit_playlist_tracks(
                uid=self.view_page.playlist.id, track=track, add=True
            )
        except PlaylistNotFound:
            await interaction.edit_original_response(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.playlist.not_found",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )
            )
            return

        await interaction.edit_original_response(
            embed=EmbedUI(
                title=_t.get("music.success.title", locale=interaction.guild_locale),
                description=_t.get(
                    "music.playlist.success.track_added",
                    locale=interaction.guild_locale,
                    values=(
                        self.view_page.playlist.name,
                        track.title, track.author
                    )
                )
            ),
            view=None
        )

        try:
            from utils.handlers.entertainment.music.views.playlists.page import ViewPage

            new_view = await ViewPage.generate(self._main_interaction, new_playlist)
            await self._main_interaction.edit_original_response(
                embeds=await new_view.generate_embed(),
                view=new_view
            )
        except (HTTPException, Forbidden):
            pass

    async def _get_query(self, interaction: ModalInteraction) -> None:
        from utils.handlers.entertainment.music.views import SelectTrackView

        await interaction.response.edit_message(
            embed=EmbedUI(
                title=_t.get(
                    "music.track_add.title",
                    locale=interaction.guild_locale
                ),
                description=_t.get(
                    "music.select_track",
                    locale=interaction.guild_locale
                )
            ),
            view=SelectTrackView(
                interaction=interaction, bot=self._bot,
                query=interaction.text_values["playlists.query"],
                after_select=self._prompt_track_callback
            )
        )

    @ui.button(
        label="music.playlist.add_track.label",
        emoji="<:Plus:1126911676399243394>",
        custom_id="playlists.page.track_editor.add_tracks",
        row=0
    )
    async def add_tracks_button(self, _, interaction: MessageInteraction) -> None:
        await interaction.response.send_modal(
            GetQuery(interaction, self._get_query)
        )
