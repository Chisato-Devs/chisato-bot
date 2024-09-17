from __future__ import annotations

import asyncio
from asyncio import sleep
from itertools import islice
from typing import cast, Final

from disnake import NotFound, MessageInteraction, SelectOption, ui, Guild
from disnake.ui import Item
from harmonize import Player
from harmonize.enums import LoopStatus
from loguru import logger

from utils.basic import View, EmbedUI, EmbedErrorUI
from utils.exceptions import NotFoundPlaylists
from utils.handlers.entertainment.music.decorators import in_voice_button, has_nodes_button, with_bot_button
from utils.handlers.entertainment.music.filters import FILTERS, FROM_FILTER
from utils.handlers.entertainment.music.views.pagination import QueuePagination
from utils.handlers.entertainment.music.views.playlists.addons import Select
from utils.i18n import ChisatoLocalStore

__all__ = (
    "PlayerButtons",
)

_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")


class PlayerButtons(View):
    def __init__(self, guild: Guild) -> None:
        self._guild = guild
        self._from_value = FILTERS.copy()

        super().__init__(timeout=None, store=_t, guild=self._guild)

    @classmethod
    def from_player(cls, player: Player, /) -> PlayerButtons:
        self = cls(player.guild)
        self.set_loop_emoji(player)
        self.set_karaoke_emoji(player)
        self.set_placeholder_filter(
            FROM_FILTER.copy().get(player.filters[0] if player.filters else "", "clear")
        )

        return self

    def set_placeholder_filter(self, filer_name: str) -> None:
        if item := self.get_item("music.filters"):
            for i in item.options:
                if i.value == filer_name:
                    i.default = True
                else:
                    i.default = False

    def on_error(self, error: Exception, item: Item, interaction: MessageInteraction) -> None:
        error = getattr(error, "original", error)
        if isinstance(error, NotFound):
            pass
        else:
            raise error from error

    BLACK_LIST_FILTERS: Final[list[str]] = ["nightcore", "slowed"]

    @ui.string_select(
        placeholder="music.filters.label",
        custom_id="music.filters", row=0,
        options=[
            SelectOption(
                label="Clear", value="clear",
                emoji="<:EnergyRestricted:1209962876664815626>",
                default=True
            ),
            SelectOption(
                label="Nightcore", value="nightcore",
                emoji="<:Energy:1209962939054821426>"
            ),
            SelectOption(
                label="Boost", value="boost",
                emoji="<:Energy:1209962939054821426>"
            ),
            SelectOption(
                label="Metal", value="metal",
                emoji="<:Energy:1209962939054821426>"
            ),
            SelectOption(
                label="Slowed", value="slowed",
                emoji="<:Energy:1209962939054821426>"
            ),
            SelectOption(
                label="Karaoke", value="karaoke",
                emoji="<:Energy:1209962939054821426>"
            )
        ]
    )
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def filters(self, select: ui.Select, interaction: MessageInteraction) -> None:
        await interaction.response.defer()
        player = cast(Player, interaction.guild.voice_client)
        if not player:
            return

        if select.values[0] == "clear":
            return await player.remove_filters()

        if (
                player.fetch_user_data("karaoke")
                and select.values[0] in self.BLACK_LIST_FILTERS
        ):
            return

        await player.set_filters(filter=self._from_value[select.values[0]])
        interaction.bot.dispatch("harmonize_message_update", player)

    @ui.button(emoji="<:Decreasevolume:1209962872881283092>", custom_id="volume.down", row=1)
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def volume_down(self, _: ui.Button, interaction: MessageInteraction) -> None:
        await interaction.response.defer()
        player = cast(Player, interaction.guild.voice_client)
        if not player:
            return

        volume = max(player.volume - 25, 25)
        if player.volume <= 25:
            self.get_item("volume.down").disabled = True
        else:
            self.get_item("volume.up").disabled = False

        await player.change_volume(volume)
        interaction.bot.dispatch("harmonize_message_update", player)

    @ui.button(emoji="<:VolumeUp:1209962888018661456>", custom_id="volume.up", row=1)
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def volume_up(self, _: ui.Button, interaction: MessageInteraction) -> None:
        await interaction.response.defer()
        player = cast(Player, interaction.guild.voice_client)
        if not player:
            return

        volume = min(player.volume + 25, 200)
        if volume >= 200:
            self.get_item("volume.up").disabled = True
        else:
            self.get_item("volume.down").disabled = False

        await player.change_volume(volume)
        interaction.bot.dispatch("harmonize_message_update", player)

    @ui.button(emoji="<:invoice:1114239254407696584>", custom_id="player.queue", row=1)
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def queue(self, _: ui.Button, interaction: MessageInteraction) -> None:
        player = cast(Player, interaction.guild.voice_client)

        view, embed = await QueuePagination.generate(queue=player.queue, author=interaction.author)
        if embed:
            await interaction.send(view=view, embed=embed, ephemeral=True)
        else:
            await interaction.response.defer()

        interaction.bot.dispatch("harmonize_message_update", player)

    @ui.button(emoji="<:clear_queue:1228356822918762506>", custom_id="clear_queue", row=1)
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def clear_queue(self, _: ui.Button, interaction: MessageInteraction) -> None:
        await interaction.response.defer()
        player = cast(Player, interaction.guild.voice_client)
        if not player:
            return

        player.queue.clear()
        interaction.bot.dispatch("harmonize_message_update", player)

    @ui.button(emoji="<:Shuffle:1209962867042951289>", custom_id="shuffle", row=1)
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def shuffle(self, _: ui.Button, interaction: MessageInteraction) -> None:
        await interaction.response.defer()
        player: Player
        player = cast(Player, interaction.guild.voice_client)  # type: ignore

        player.queue.shuffle()
        interaction.bot.dispatch("harmonize_message_update", player)

    @ui.button(emoji="<:Grid:1209962879797694566>", custom_id="stop", row=2)
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def stop(self, _: ui.Button, interaction: MessageInteraction) -> None:
        await interaction.response.defer()

        player = cast(Player, interaction.guild.voice_client)
        if player:
            self.stop_karaoke(player)
            await player.disconnect()

    @ui.button(emoji="<:previous:1242160741713318051>", custom_id="previous", row=2)
    async def previous(self, _: ui.Button, interaction: MessageInteraction) -> None:
        await interaction.response.defer()
        player: Player
        player = cast(Player, interaction.guild.voice_client)  # type: ignore

        if len(player.queue.history) >= 1:
            player.queue.tracks.insert(0, player.queue.history.pop(0))
            await player.play()

        interaction.bot.dispatch("harmonize_message_update", player)

    @ui.button(emoji="<:Pause:1209962863784108063>", custom_id="pause.resume", row=2)
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def pause(self, _: ui.Button, interaction: MessageInteraction) -> None:
        player = cast(Player, interaction.guild.voice_client)

        if player.paused:
            await player.set_pause(False)
            if player.fetch_user_data("karaoke") and (data := player.fetch_user_data("karaoke_data")):
                player.add_user_data(
                    karaoke_task=asyncio.create_task(
                        self._karaoke_start_task(player, data["lines"])
                    )
                )

                self.get_item("pause.resume").emoji = "<:Pause:1209962863784108063>"
        else:
            self.stop_karaoke(player)
            await player.set_pause(True)
            self.get_item("pause.resume").emoji = "<:Play:1209962865193127997>"

            await interaction.response.edit_message(view=self)

    @ui.button(emoji="<:next:1210030059792900146>", custom_id="next", row=2)
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def next(self, _: ui.Button, interaction: MessageInteraction) -> None:
        await interaction.response.defer()
        player: Player
        player = cast(Player, interaction.guild.voice_client)  # type: ignore

        await player.skip()

    def set_loop_emoji(self, player: Player) -> None:
        item = self.get_item("loop")
        match player.queue.loop:
            case LoopStatus.OFF:
                item.emoji = "<:loop:1228300623141666857>"
            case LoopStatus.TRACK:
                item.emoji = "<:loop_one:1228300624706146324>"
            case LoopStatus.QUEUE:
                item.emoji = "<:loop_all:1228300626283466812>"

    @ui.button(emoji="<:loop:1228300623141666857>", custom_id="loop", row=2)
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def looping(self, _: ui.Button, interaction: MessageInteraction) -> None:
        player = cast(Player, interaction.guild.voice_client)  # type: ignore

        match player.queue.loop:
            case LoopStatus.OFF:
                player.queue.set_loop(LoopStatus.TRACK)
            case LoopStatus.TRACK:
                player.queue.set_loop(LoopStatus.QUEUE)
            case LoopStatus.QUEUE:
                player.queue.set_loop(LoopStatus.OFF)

        self.set_loop_emoji(player)
        await interaction.response.edit_message(view=self)

    @ui.button(emoji="<:empty:1183500325517279244>", custom_id="empty_1", row=3, disabled=True)
    async def empty_1(self, _b: ui.Button, _i: MessageInteraction) -> None:
        ...

    @ui.button(emoji="<:addmusic:1209962871002370145>", custom_id="add_to_playlist", row=3)
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def add_to_playlist(self, _: ui.Button, interaction: MessageInteraction) -> None:
        try:
            await interaction.response.send_message(
                embed=EmbedUI(
                    title=_t.get(
                        "music.playlists.title",
                        locale=interaction.guild.preferred_locale
                    ),
                    description=_t.get(
                        "music.playlist.select.description",
                        locale=interaction.guild.preferred_locale
                    )
                ),
                view=await Select.generate(interaction),
                ephemeral=True
            )
        except NotFoundPlaylists:
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.playlist.error.not_found.description",
                        locale=interaction.guild.preferred_locale
                    ),
                    member=interaction.author
                )
            )

    def set_karaoke_emoji(self, player: Player) -> None:
        item = self.get_item("karaoke")
        if player.fetch_user_data("karaoke"):
            item.emoji = "<:karaoke_on:1242155477270401045>"
        else:
            item.emoji = "<:Microphone:1116363436423647273>"

    @classmethod
    async def _karaoke_start_task(cls, player: Player, lyrics_data: list[dict[str, any]]) -> None:
        while player.connected:
            next_lines = list(
                islice(filter(
                    lambda x: player.last_position <= x.get("timestamp", 0), lyrics_data
                ), 2)
            )

            lines = [
                lyrics_data[lyrics_data.index(next_lines[0]) - 1] if lyrics_data.index(next_lines[0]) != 0 else {},
                *next_lines
            ]

            player.add_user_data(karaoke_need_lines=lines)
            player.client.dispatch("harmonize_message_update", player)

            await sleep(max(lines[0].get("duration") / 1000, 6))
        else:
            logger.debug(f"Player {player.guild.id} karaoke loop (while) finished")

    @classmethod
    def stop_karaoke(cls, player: Player) -> None:
        player.add_user_data(
            karaoke=False,
            karaoke_need_lines=[],
            karaoke_task=None
        )
        if _task := player.fetch_user_data("karaoke_task"):
            _task.cancel()

    @ui.button(emoji="<:karaoke_on:1242155477270401045>", custom_id="karaoke", row=3)
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def karaoke_mode(self, _: ui.Button, interaction: MessageInteraction) -> None:
        player = cast(Player, interaction.guild.voice_client)  # type: ignore
        if FROM_FILTER.get(player.filters[0] if player.filters else None, "") in self.BLACK_LIST_FILTERS:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.karaoke.error.filter.description",
                        locale=interaction.guild.preferred_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        if player.fetch_user_data("karaoke"):
            self.stop_karaoke(player)

            interaction.bot.dispatch("harmonize_message_update", player)
            return await interaction.response.defer()

        data_json: dict[str, any] = player.fetch_user_data("karaoke_data")
        if not data_json:
            data_json: dict[str, any] = await player.node.request(
                "GET",
                path=f"sessions/{player.node.session_id}/players/{player.guild.id}/track/lyrics",
                params={"skipTrackSource": "true"}
            )

        if data_json and isinstance(data_json, dict) and data_json.get("lines"):
            player.add_user_data(
                karaoke=True,
                karaoke_data=data_json,
                karaoke_task=asyncio.create_task(
                    self._karaoke_start_task(player, data_json["lines"])
                )
            )

            self.set_karaoke_emoji(player)
            await interaction.response.edit_message(view=self)
            return
        else:
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.karaoke.error.lyrics_lines_not_found.description",
                        locale=interaction.guild.preferred_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

    @ui.button(emoji="<:text:1241497125989126164>", custom_id="track_text", row=3)
    async def track_text(self, _: ui.Button, interaction: MessageInteraction) -> None:
        player = cast(Player, interaction.guild.voice_client)  # type: ignore

        if not player.fetch_user_data("karaoke_data"):
            data_json: dict[str, any] = await player.node.request(
                "GET",
                path=f"sessions/{player.node.session_id}/players/{player.guild.id}/track/lyrics",
                params={"skipTrackSource": "true"}
            )

            if data_json and data_json.get("text"):
                player.add_user_data(karaoke_data=data_json)
            else:
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "music.karaoke.error.lyrics_text_not_found.description",
                            locale=interaction.guild.preferred_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )

        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get(
                    "music.lyrics.title",
                    locale=interaction.guild.preferred_locale
                ),
                description=player.fetch_user_data("karaoke_data")["text"][:4096]
            ),
            ephemeral=True
        )

    @ui.button(emoji="<:empty:1183500325517279244>", custom_id="empty_4", row=3, disabled=True)
    async def empty_4(self, _b: ui.Button, _i: MessageInteraction) -> None:
        ...
