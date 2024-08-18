from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast, TypeAlias

from disnake import (
    ApplicationCommandInteraction,
    HTTPException,
    TextChannel,
    Thread,
    VoiceChannel,
    StageChannel,
    MessageInteraction,
    Localized, User, Message, Locale
)
from disnake.ext.commands import Param, Context, is_owner
from disnake.utils import format_dt
from lavamystic import (
    Player,
    Playable,
    TrackEndEventPayload,
    PlayerUpdateEventPayload,
    Pool,
    Node,
    WebsocketClosedEventPayload,
    TrackStuckEventPayload, NodeStatus
)
from loguru import logger

from utils.basic import CogUI, EmbedUI, EmbedErrorUI, View
from utils.handlers.entertainment.music import WARN_ICON
from utils.handlers.entertainment.music.decorators import (
    in_voice,
    has_nodes,
    with_bot,
    in_home,
    in_text_channel
)
from utils.handlers.entertainment.music.enums import FromSourceEmoji
from utils.handlers.entertainment.music.generators import PlayerEmbed
from utils.handlers.entertainment.music.tools import ConvertTime, if_uri
from utils.handlers.entertainment.music.views import PlayerButtons, SelectTrackView
from utils.handlers.entertainment.music.views.pagination import QueuePagination
from utils.handlers.entertainment.music.views.playlists import Playlists
from utils.handlers.pagination import DeleteMessageButton
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

Channel: TypeAlias = TextChannel | Thread | VoiceChannel | StageChannel
_t = ChisatoLocalStore.load(__file__)


class Music(CogUI):
    def __init__(self, bot: ChisatoBot) -> None:
        self._empty_voice_task: asyncio.Task | None = None

        super().__init__(bot)

    async def setup_hook(self) -> None:
        try:
            await Pool.connect(
                nodes=[
                    Node(
                        uri="http://localhost:2333",
                        password="youshallnotpass",
                        identifier="Epsilon"
                    )
                ],
                client=self.bot,
                cache_capacity=1024
            )
        except Exception as e:
            logger.critical(f"An error was thrown when connecting to the music servers: {e}")

    async def cog_load(self) -> None:
        await self.bot.wait_until_first_connect()
        await self.setup_hook()

    def cog_unload(self) -> None:
        asyncio.create_task(Pool.close())
        for player in self.bot.voice_clients:
            player: Player
            if player:
                asyncio.create_task(self.player_exception(player))
                asyncio.create_task(player.disconnect())

    @CogUI.slash_command(name="music")
    async def __music(self, interaction: ApplicationCommandInteraction) -> ...:
        ...

    @staticmethod
    async def player_exception(player: Player) -> None:
        try:
            await player.namespace.message.delete()
        except (HTTPException, AttributeError):
            pass

        try:
            await player.namespace.thread.delete()
        except (HTTPException, AttributeError):
            pass

        try:
            player.namespace.karaoke_task.cancel()
        except (HTTPException, AttributeError):
            pass
        except Exception as e:
            logger.warning(f"{type(e).__name__}: {e}")

    @CogUI.listener("on_mystic_track_end")
    async def on_mystic_tack_end(self, payload: TrackEndEventPayload) -> None:
        if payload.player:
            PlayerButtons.stop_karaoke(payload.player)
            payload.player.add_to_namespace({
                "karaoke_data": None,
            })

            for member in payload.player.channel.members:
                if not member.bot:
                    await self.bot.databases.music.add_last_track(
                        member=member, track=payload.track
                    )

            if not payload.player.queue and not payload.player.auto_queue and not payload.player.current:
                await self.player_exception(payload.player)

    @CogUI.listener("on_mystic_track_stuck")
    async def on_mystic_track_stuck(self, payload: TrackStuckEventPayload) -> None:
        await payload.player.skip()

    @CogUI.listener("on_mystic_player_destroyed")
    async def on_mystic_player_destroyed(self, player: Player) -> None:
        return await self.player_exception(player)

    @CogUI.listener("on_mystic_connection_lost")
    async def lava_connection_lost(self, players: list[Player]) -> None:
        for player in players:
            if player:
                await self.player_exception(player)
                await player.disconnect()

    @classmethod
    async def _task_backend(cls, player: Player) -> None:
        await asyncio.sleep(60)
        await player.disconnect()

    def empty_members_start(self, player: Player) -> None:
        try:
            self._empty_voice_task = asyncio.create_task(self._task_backend(player))
        except (RuntimeError, RuntimeWarning):
            pass

    def empty_members_cancel(self) -> None:
        try:
            self._empty_voice_task.cancel()
        except AttributeError:
            pass

    @CogUI.listener("on_mystic_player_update")
    async def on_mystic_player_update(self, payload: PlayerUpdateEventPayload) -> None:
        if payload.player:
            if len(payload.player.channel.members) == 1:
                return self.empty_members_start(payload.player)

            self.empty_members_cancel()

    @CogUI.listener("on_mystic_websocket_closed")
    @CogUI.listener("on_mystic_inactive_player")
    async def on_websocket_close(self, player: WebsocketClosedEventPayload | Player) -> None:
        if isinstance(player, WebsocketClosedEventPayload):
            player = player.player

        if not player:
            return

        await self.player_exception(player)
        await player.disconnect()

    @staticmethod
    async def _after_select_track(interaction: MessageInteraction, track: Playable) -> None:
        player = cast(Player, interaction.guild.voice_client)  # type: ignore

        if not player:
            player = await Player.connect_to_channel(
                interaction.author.voice.channel,
                home=interaction.channel,
                karaoke=False
            )

        if len(player.queue) >= 150:
            await interaction.edit_original_response(
                embed=EmbedErrorUI(
                    description=_t.get("music.error.queue_limit", interaction.guild_locale),
                    member=interaction.author
                ),
                view=None
            )
            return

        await player.queue.put_wait(track)

        await interaction.edit_original_response(
            embed=EmbedUI(
                title=_t.get("music.title", locale=interaction.guild_locale),
                description=_t.get(
                    "music.track.add_to_queue",
                    locale=interaction.guild_locale,
                    values=(track.title, track.author)
                )
            ).set_thumbnail(track.artwork),
            view=None
        )

        if not player.playing:
            await player.play(player.queue.get())
        else:
            player.dispatch_message_update()

    @CogUI.listener("on_message")
    async def on_thread_message(self, message: Message) -> any:
        if isinstance(message.author, User) or message.author.bot:
            return

        if player := message.guild.voice_client:  # type: ignore
            player: Player
            if (
                    hasattr(player.namespace, "thread")
                    and player.namespace.thread
                    and player.namespace.thread.id == message.channel.id
            ):
                if (
                        not message.author.voice.channel
                        or message.author.voice.channel.id != player.channel.id
                ):
                    return

                if message.content.startswith(f"volume"):
                    if (
                            (sort := list(map(int, message.content.split(" ")[1:])))
                            and len(sort) == 1
                            and 0 < sort[0] <= 200
                    ):
                        last_volume = player.volume
                        await player.set_volume(sort[0])
                        await message.reply(
                            embed=EmbedUI(
                                title=_t.get(
                                    "music.success.title",
                                    locale=message.guild.preferred_locale
                                ),
                                description=_t.get(
                                    "music.volume.change",
                                    locale=message.guild.preferred_locale,
                                    values=(str(message.author), last_volume, player.volume)
                                )
                            )
                        )
                    return

                elif message.content == "queue":
                    view, embed = await QueuePagination.generate(queue=player.queue, author=message.author)
                    if view and embed:
                        new_message = await message.reply(embed=embed, view=view)
                        view.add_cache(new_message)
                    return

                elif message.content == "skip":
                    await message.reply(
                        embed=EmbedUI(
                            title=_t.get(
                                "music.success.title",
                                locale=message.guild.preferred_locale
                            ),
                            description=_t.get(
                                "music.skip",
                                locale=message.guild.preferred_locale,
                                values=(
                                    str(message.author),
                                    player.current.title,
                                    player.current.author,
                                    player.current.uri
                                )
                            )
                        )
                    )
                    await player.skip()
                    return

                elif message.content == "stop":
                    return await player.disconnect()

                else:
                    if embed := await if_uri(
                            message.guild,
                            message.author,
                            message.content,
                            message.author.voice.channel,
                            message.channel
                    ):
                        return await message.reply(embed=embed)

                    view = SelectTrackView(message, self.bot, message.content, self._after_select_track)
                    new = await message.reply(
                        embed=EmbedUI(
                            title=_t.get("music.title", locale=message.guild.preferred_locale),
                            description=_t.get("music.select_track", locale=message.guild.preferred_locale)
                        ),
                        view=view
                    )

                    view.set_message(new)

    @CogUI.listener("on_mystic_message_update")
    async def lava_message_update(self, player: Player) -> None:
        if not player or not player.current:
            return

        embeds = await PlayerEmbed.generate(player)
        try:
            await player.namespace.message.edit(
                embeds=embeds,
                attachments=[],
                view=PlayerButtons.from_player(player)
            )
        except AttributeError:
            asyncio.create_task(self._send_message_task(player, embeds))
        except HTTPException as e:
            logger.warning(f"{HTTPException.__name__}: {e}")
            asyncio.create_task(self._send_message_task(player, embeds))

    @classmethod
    def _generate_handbook_embed(cls, locale: Locale) -> EmbedUI:
        return EmbedUI(
            title=_t.get(
                "music.handbook.title", locale=locale
            ),
            description=_t.get(
                "music.handbook.description", locale=locale
            )
        ).set_footer(
            icon_url=WARN_ICON,
            text=_t.get("music.handbook.footer", locale=locale)
        )

    @classmethod
    async def _send_message_task(cls, player: Player, embeds: list[EmbedUI]):
        player.add_to_namespace({
            "message": (message := await player.namespace.home.send(
                embeds=embeds, view=PlayerButtons.from_player(player)
            )),
            "thread": (thread := await message.create_thread(
                name=_t.get("music.thread.name", locale=player.guild.preferred_locale)
            ))
        })

        await thread.send(
            embed=cls._generate_handbook_embed(
                locale=player.guild.preferred_locale
            )
        )

    @__music.sub_command(
        name="play", description=Localized(
            "music.play.command.description",
            data=_t.get("music.play.command.description")
        )
    )
    @in_text_channel()
    @in_voice()
    @has_nodes()
    @with_bot()
    @in_home()
    async def play(
            self,
            interaction: ApplicationCommandInteraction,
            query: str = Param(
                name=Localized("запрос", data=_t.get("music.play.command.option.query")),
                description=Localized(
                    "music.play.command.option.query.description",
                    data=_t.get("music.play.command.option.query.description")
                )
            )
    ) -> None:
        if embed := await if_uri(
                guild=interaction.guild, author=interaction.author,
                query=query, channel=interaction.author.voice.channel,
                text_channel=interaction.channel  # type: ignore
        ):
            return await interaction.response.send_message(embed=embed)

        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("music.title", locale=interaction.guild_locale),
                description=_t.get("music.select_track", locale=interaction.guild_locale)
            ),
            view=SelectTrackView(interaction, self.bot, query, self._after_select_track)
        )

    @__music.sub_command(
        name="last", description=Localized(
            "🎶 Музыка: Последние прослушивания!",
            data=_t.get("music.last_listened.description")
        )
    )
    async def lasted(
            self,
            interaction: ApplicationCommandInteraction
    ) -> None:
        tracks: list[list[Playable, int]] = await self.bot.databases.music.get_last_tracks(interaction.author)
        if tracks:
            await interaction.response.send_message(
                embed=EmbedUI(
                    title=_t.get("music.last_listened.title", locale=interaction.guild_locale),
                    description="\n".join(
                        (
                            f"{i}. {getattr(FromSourceEmoji, track[0].source).value} "
                            f"`[{ConvertTime.format(track[0].length)}] `"
                            f"[`{track[0].title} - {track[0].author}`]({track[0].uri}) "
                            f"{format_dt(track[1], style='R')}"
                        ) for i, track in enumerate(tracks, 1)
                    )
                ),
                view=View(
                    timeout=120,
                    interaction=interaction
                ).add_item(DeleteMessageButton())
            )
        else:
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get("music.error.not_found_last_listened", locale=interaction.guild_locale),
                    member=interaction.author
                )
            )

    @__music.sub_command(
        name="playlists",
        description=Localized(
            "🎶 Музыка: Плейлисты!",
            data=_t.get("music.playlists.description")
        )
    )
    @has_nodes()
    async def playlist_setting(
            self,
            interaction: ApplicationCommandInteraction
    ) -> None:
        await interaction.send(
            embed=EmbedUI(
                title=_t.get("music.playlists.title", locale=interaction.guild_locale)
            ).set_footer(text=_t.get("music.playlists.footer", locale=interaction.guild_locale)),
            view=await Playlists.generate(interaction)
        )

    @CogUI.context_command(name="reload_nodes", aliases=["rn"])
    @is_owner()
    async def reload_nodes(
            self, ctx: Context
    ) -> None:
        for _, node in Pool.nodes.items():
            try:
                await node.connect(client=self.bot)
            except Exception as e:
                logger.warning(f"Lavalink raised {e} ({type(e).__name__})")

        await ctx.send("Success")

    @CogUI.context_command(name="players", aliases=["pl"])
    @is_owner()
    async def _players(self, ctx: Context) -> None:
        players_total = 0

        for _, node in Pool.nodes.items():
            if node.status == NodeStatus.CONNECTED:
                players_total += node.player_count

        await ctx.send(str(players_total))


def setup(bot: ChisatoBot) -> None:
    return bot.add_cog(Music(bot))
