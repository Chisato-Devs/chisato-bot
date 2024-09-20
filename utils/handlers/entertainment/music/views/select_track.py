from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from disnake import (
    ui,
    SelectOption,
    MessageInteraction,
    Message, Interaction, Locale
)
from harmonize.connection import Pool
from harmonize.objects import Track
from loguru import logger

from utils.basic import View
from utils.handlers.entertainment.music.decorators import (
    in_voice_button,
    has_nodes_button,
    with_bot_button
)
from utils.handlers.entertainment.music.enums import FromSourceEmoji, TrackSource
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot
    from harmonize.objects import LoadResult

_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")

__all__ = (
    "SelectTrackView",
)


class SelectTrackView(View):
    def __init__(
            self,
            interaction: Interaction | Message,
            bot: ChisatoBot,
            query: str,
            after_select: Callable[[MessageInteraction, Track], any],
            decorate: bool = True
    ) -> None:
        self._interaction = interaction
        self._locale = interaction.guild.preferred_locale
        self._bot: ChisatoBot = bot
        self._end = False
        self._after_select = after_select
        self._decorate = decorate

        self.query = query
        self.source = TrackSource.Spotify

        self.from_value: dict[str, TrackSource] = {
            "spotify": TrackSource.Spotify,
            "yandex": TrackSource.YandexMusic,
            "vkmusic": TrackSource.VkMusic,
            "soundcloud": TrackSource.SoundCloud,
            "applemusic": TrackSource.AppleMusic,
            "deezer": TrackSource.Deezer
        }
        self._from_track: dict[str, Track] = {}

        super().__init__(store=_t, author=interaction.author, timeout=120, guild=self._interaction.guild)
        self.set_back()

    def set_message(self, value: Message) -> None:
        self._interaction = value

    async def on_timeout(self) -> None:
        if not self._end:
            for child in self.children:
                child.disabled = True

            try:
                if isinstance(self._interaction, MessageInteraction):
                    await self._interaction.edit_original_response(view=self)
                elif isinstance(self._interaction, Message):
                    await self._interaction.edit(view=self)
            except Exception as e:
                logger.warning(f"{e.__class__.__name__}: {e}")
            finally:
                self.set_back()
                self._end = True

    @classmethod
    async def _get_options(
            cls,
            locale: Locale,
            query: str,
            *,
            source: TrackSource
    ) -> tuple[dict[str, Track], list[SelectOption]]:
        node = Pool.get_best_node()
        result: LoadResult = (await node.get_tracks(f"{source.value}{query}"))

        if result.error:
            logger.warning(f"While loading track ({result.error.severity}): {result.error.message}")

        artists_description = _t.get(
            "music.track.select.artists", locale=locale
        )

        from_track = {}
        options = []
        for i, track in enumerate(result.tracks[:25]):
            from_track[str(i)] = track
            options.append(
                SelectOption(
                    emoji="<:note:1205907505658728608>",
                    label=track.title[:99],
                    description=artists_description + track.author[:80],
                    value=str(i)
                )
            )

        return from_track, options

    async def track_generator(self) -> None:
        from_track, options = await self._get_options(
            self._locale, self.query, source=self.source
        )
        self._from_track = from_track

        if item := self.get_item("music.select.track.custom_id"):
            self.select_source.disabled = False
            if options:
                item.disabled = False
                item.options.clear()
                item.options.extend(options)
            else:
                item.disabled = True

    # "music.track.source.not_stable"
    @ui.string_select(
        placeholder="music.select.track.placeholder",
        custom_id="music.select.source.custom_id",
        options=[
            SelectOption(
                label="Spotify",
                emoji=FromSourceEmoji.spotify.value,
                value="spotify"
            ),
            SelectOption(
                label="Apple Music",
                emoji=FromSourceEmoji.applemusic.value,
                value="applemusic"
            ),
            SelectOption(
                label="Yandex Music",
                emoji=FromSourceEmoji.yandexmusic.value,
                value="yandex"
            ),
            SelectOption(
                label="Sound Cloud",
                emoji=FromSourceEmoji.soundcloud.value,
                value="soundcloud"
            ),
            SelectOption(
                label="Vk Music",
                emoji=FromSourceEmoji.vkmusic.value,
                value="vkmusic"
            ),
            SelectOption(
                label="Deezer",
                emoji=FromSourceEmoji.deezer.value,
                value="deezer"
            )
        ]
    )
    async def select_source(self, select: ui.StringSelect, interaction: MessageInteraction) -> None:
        self._end = True
        self.source = self.from_value[select.values[0]]
        for option in select.options:
            option.default = option.value == select.values[0]

        await self.custom_defer(interaction)
        await self.track_generator()

        try:
            await interaction.edit_original_response(view=self)
        except Exception as e:
            logger.warning(f"{e.__class__.__name__}: {e}")

    def set_back(self) -> None:
        for option in self.select_source.options:
            option.default = False

    @in_voice_button
    @with_bot_button
    async def _mirror_callback_decorated(self, select: ui.StringSelect, interaction: MessageInteraction) -> None:
        self._end = True
        await self.custom_defer(interaction)

        await self._after_select(interaction, self._from_track[select.values[0]])
        self.set_back()

    async def _mirror_callback_not_decorated(self, select: ui.StringSelect, interaction: MessageInteraction) -> None:
        self._end = True
        await self.custom_defer(interaction)

        await self._after_select(interaction, self._from_track[select.values[0]])
        self.set_back()

    @ui.string_select(
        placeholder="music.track.select.track",
        options=[SelectOption(label="Сдохло")],
        custom_id="music.select.track.custom_id",
        disabled=True
    )
    @has_nodes_button
    async def select_track(self, select: ui.StringSelect, interaction: MessageInteraction) -> None:
        match self._decorate:
            case True:
                await self._mirror_callback_decorated(select, interaction)  # type: ignore
            case False:
                await self._mirror_callback_not_decorated(select, interaction)
