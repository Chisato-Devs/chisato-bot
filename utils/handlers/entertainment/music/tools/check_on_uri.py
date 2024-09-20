from __future__ import annotations

from typing import cast, TypeAlias, Union, TYPE_CHECKING

import yarl
from disnake import (
    Guild,
    Member,
    TextChannel,
    Thread,
    VoiceChannel,
    StageChannel,
    Embed, PartialMessageable
)
from harmonize import Player
from harmonize.connection import Pool

from utils.basic import EmbedUI, EmbedErrorUI
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from harmonize.objects import LoadResult

Channel: TypeAlias = TextChannel | Thread | VoiceChannel | StageChannel
_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")


async def if_uri(
        guild: Guild,
        author: Member,
        query: str,
        channel: Channel = None,
        text_channel: Union[Channel, PartialMessageable] = None
) -> Embed | None:
    if not yarl.URL(query).host:
        return

    node = Pool.get_best_node()
    result: LoadResult = await node.get_tracks(query)
    if result.error or not result.tracks:
        return EmbedErrorUI(
            description=_t.get(
                "music.error.not_found_tracks",
                locale=guild.preferred_locale
            ),
            member=author
        )

    if result.tracks[0].source_name == "youtube":
        return EmbedErrorUI(
            description=_t.get(
                "music.error.not_youtube",
                locale=guild.preferred_locale
            ),
            member=author
        )

    player: Player = cast(Player, guild.voice_client)
    if not player and channel:
        player = await Player.connect_to_channel(channel, home=text_channel, karaoke=False)

    if result.playlist_info.name:
        embed = EmbedUI(
            title=_t.get("music.title", locale=guild.preferred_locale),
            description=_t.get(
                "music.playlist.added",
                locale=guild.preferred_locale,
                values=(
                    result.playlist_info.name,
                    str(result.plugin_info.get("author", "Unknown")),
                    str(len(result.tracks[:150 - len(player.queue)]))
                )
            )
        )
        if artwork := result.plugin_info.get("artworkUrl"):
            embed.set_thumbnail(artwork)

        result.tracks = result.tracks.copy()[:150 - len(player.queue)]
        player.queue.add(result)
    else:
        embed = EmbedUI(
            title=_t.get("music.title", locale=guild.preferred_locale),
            description=_t.get(
                "music.track.add_to_queue",
                locale=guild.preferred_locale,
                values=(
                    result.tracks[0].title,
                    result.tracks[0].author
                )
            )
        )
        if artwork := result.tracks[0].artwork_url:
            embed.set_thumbnail(artwork)

        player.queue.add(tracks=result.tracks)

    if not player.is_playing:
        await player.play()
    else:
        player.client.dispatch("harmonize_message_update", player)

    return embed
