from __future__ import annotations

from typing import cast, TypeAlias, Union

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
from lavamystic import (
    Player,
    Playable,
    Playlist,
    LavalinkLoadException
)

from utils.basic import EmbedUI, EmbedErrorUI
from utils.i18n import ChisatoLocalStore

Channel: TypeAlias = TextChannel | Thread | VoiceChannel | StageChannel
_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")


async def if_uri(
        guild: Guild,
        author: Member,
        query: str,
        channel: Channel = None,
        text_channel: Union[Channel, PartialMessageable] = None
) -> Embed | None:
    if yarl.URL(query).host:
        player: Player = cast(Player, guild.voice_client)

        try:
            tracks = await Playable.search(query)
        except LavalinkLoadException:
            return EmbedErrorUI(
                description=_t.get(
                    "music.error.not_found_tracks",
                    locale=guild.preferred_locale
                ),
                member=author
            )

        if not tracks:
            return EmbedErrorUI(
                description=_t.get(
                    "music.error.not_found_tracks",
                    locale=guild.preferred_locale
                ),
                member=author
            )

        if (
                tracks.tracks[0].source == "youtube"
                if isinstance(tracks, Playlist) else
                tracks[0].source == "youtube"
        ):
            return EmbedErrorUI(
                description=_t.get(
                    "music.error.not_youtube",
                    locale=guild.preferred_locale
                ),
                member=author
            )

        if not player and channel:
            player = await Player.connect_to_channel(channel, home=text_channel, karaoke=False)

        if isinstance(tracks, Playlist):
            embed = EmbedUI(
                title=_t.get("music.title", locale=guild.preferred_locale),
                description=_t.get(
                    "music.playlist.added",
                    locale=guild.preferred_locale,
                    values=(
                        tracks.name,
                        str(tracks.author),
                        str(len(tracks.tracks[:150 - len(player.queue)]))
                    )
                )
            )
            if tracks.artwork:
                embed.set_thumbnail(tracks.artwork)
            tracks = tracks.tracks[:150 - len(player.queue)]
        else:
            embed = EmbedUI(
                title=_t.get("music.title", locale=guild.preferred_locale),
                description=_t.get(
                    "music.track.add_to_queue",
                    locale=guild.preferred_locale,
                    values=(
                        tracks[0].title,
                        tracks[0].author
                    )
                )
            )
            if tracks[0].artwork:
                embed.set_thumbnail(tracks[0].artwork)

        if channel:
            await player.queue.put_wait(tracks)
            if not player.playing:
                await player.play(player.queue.get())
            else:
                player.dispatch_message_update()

        return embed
