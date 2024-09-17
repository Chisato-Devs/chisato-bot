from __future__ import annotations

import asyncio
from asyncio import CancelledError
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
from harmonize import Player
from harmonize.connection import Pool, Node
from harmonize.enums import EndReason, NodeStatus
from harmonize.objects import Track
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
        self._lock: asyncio.Lock = asyncio.Lock()

        super().__init__(bot)

    async def setup_hook(self) -> None:
        try:
            Pool.load_node(
                Node(
                    identifier="Epsilon",
                    port=2333,
                    host="localhost",
                    ssl=False,
                    password="youshallnotpass",
                    client=self.bot
                )
            )
        except Exception as e:
            logger.critical(f"An error was thrown when connecting to the music servers: {e}")

    async def cog_load(self) -> None:
        await self.bot.wait_until_first_connect()
        await self.setup_hook()

    def cog_unload(self) -> None:
        for voice_client in self.bot.voice_clients:
            player: Player = cast(Player, voice_client)
            asyncio.gather(
                self.player_exception(player),
                player.disconnect()
            )

        Pool.close_all()

    @CogUI.slash_command(name="music")
    async def __music(self, interaction: ApplicationCommandInteraction) -> ...:
        ...

    @staticmethod
    async def player_exception(player: Player) -> None:
        try:
            await player.fetch_user_data("message").delete()
        except (HTTPException, AttributeError):
            pass

        try:
            await player.fetch_user_data("thread").delete()
        except (HTTPException, AttributeError):
            pass

        try:
            player.fetch_user_data("karaoke_task").cancel()
        except (CancelledError, AttributeError):
            pass
        except Exception as e:
            logger.warning(f"{type(e).__name__}: {e}")

        if guild_tasks := player.fetch_user_data("guild_tasks"):
            for task in guild_tasks.values():
                try:
                    task.cancel()
                except (CancelledError, AttributeError):
                    pass

    @CogUI.listener("on_harmonize_track_start")
    async def track_start_listener(
            self,
            player: Player,
            _track: Track
    ) -> None:
        self.remove_task_from_player("queue_empty", player=player)
        self.bot.dispatch("harmonize_message_update", player)

    @CogUI.listener("on_harmonize_track_end")
    async def track_end_listener(
            self,
            player: Player,
            track: Track,
            _reason: EndReason
    ) -> None:
        PlayerButtons.stop_karaoke(player)
        for member in player.channel.members:
            if not member.bot:
                await self.bot.databases.music.add_last_track(
                    member=member, track=track
                )

    @CogUI.listener("on_harmonize_track_stuck")
    async def on_harmonize_track_stuck(
            self,
            player: Player,
            _track: Track,
            _threshold: int
    ) -> None:
        await player.skip()

    @CogUI.listener("on_harmonize_player_disconnect")
    async def player_disconnect_listener(self, player: Player) -> None:
        return await self.player_exception(player)

    @CogUI.listener("on_harmonize_discord_ws_closed")
    async def ws_close_listener(
            self,
            player: Player,
            code: int,
            reason: str,
            by_remote: bool
    ) -> None:
        await self.player_exception(player)
        await player.disconnect()

        logger.warning(f"Player websocket closed with code {code} by remote {by_remote}. Reason: {reason}")

    @CogUI.listener("on_harmonize_queue_end")
    async def queue_end_listener(self, player: Player) -> None:
        message = player.fetch_user_data("message")
        async with self._lock:
            await message.delete()

        self.save_task_to_player("queue_empty", player=player)

    @classmethod
    async def _task_backend(cls, player: Player) -> None:
        await asyncio.sleep(60)
        await player.disconnect()
        await cls.player_exception(player)

    @classmethod
    def save_task_to_player(cls, name: str, /, *, player: Player) -> None:
        if not (guild_tasks := player.fetch_user_data("guild_tasks")):
            player.add_user_data(guild_tasks={})
            guild_tasks = player.fetch_user_data("guild_tasks")

        guild_tasks[name] = asyncio.create_task(cls._task_backend(player))

    @classmethod
    def remove_task_from_player(cls, name: str, /, *, player: Player) -> None:
        if not (guild_tasks := player.fetch_user_data("guild_tasks")):
            player.add_user_data(guild_tasks={})
            guild_tasks = player.fetch_user_data("guild_tasks")

        if not (task := guild_tasks.get(name)):
            return

        try:
            task.cancel()
            del guild_tasks[name]
        finally:
            logger.debug(f"Removing player task ({name})...")

    @CogUI.listener("on_harmonize_player_update")
    async def player_update_listener(self, player: Player) -> None:
        if len(player.channel.members) == 1:
            return self.save_task_to_player("empty_members", player=player)

        self.remove_task_from_player("empty_members", player=player)

    @staticmethod
    async def _after_select_track(interaction: MessageInteraction, track: Track) -> None:
        player: Player = cast(Player, interaction.guild.voice_client)

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

        player.queue.tracks.append(track)
        await interaction.edit_original_response(
            embed=EmbedUI(
                title=_t.get("music.title", locale=interaction.guild_locale),
                description=_t.get(
                    "music.track.add_to_queue",
                    locale=interaction.guild_locale,
                    values=(track.title, track.author)
                )
            ).set_thumbnail(track.artwork_url),
            view=None
        )

        if not player.is_playing:
            await player.play()
        else:
            interaction.bot.dispatch("on_harmonize_message_update", player)

    @CogUI.listener("on_message")
    async def on_thread_message(self, message: Message) -> any:
        if isinstance(message.author, User) or message.author.bot:
            return

        if player := message.guild.voice_client:  # type: ignore
            player: Player
            if (
                    (thread := player.fetch_user_data("thread"))
                    and thread.id == message.channel.id
            ):
                if (
                        not message.author.voice.channel
                        or message.author.voice.channel.id != player.channel.id
                ):
                    return

                if message.content.startswith(f"volume"):
                    if (
                            (sort := list(map(int, message.content.replace(",", ".").split(" ")[1:])))
                            and len(sort) == 1
                            and 0 < sort[0] <= 200
                    ):
                        last_volume = player.volume
                        await player.change_volume(sort[0])
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
                                    player.queue.current.title,
                                    player.queue.current.author,
                                    player.queue.current.uri
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

    @CogUI.listener("on_harmonize_message_update")
    async def message_update_listener(self, player: Player) -> None:
        if not player or not player.queue.current:
            return

        embeds = await PlayerEmbed.generate(player)
        try:
            async with self._lock:
                message = player.fetch_user_data("message")
                return await message.edit(
                    embeds=embeds,
                    attachments=[],
                    view=PlayerButtons.from_player(player)
                )
        except AttributeError:
            pass
        except HTTPException as e:
            logger.warning(f"{HTTPException.__name__}: {e}")

        async with self._lock:
            await self._send_message_task(player, embeds)

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
        player.add_user_data(
            message=(message := await (player.fetch_user_data("home")).send(
                embeds=embeds,
                view=PlayerButtons.from_player(player)
            )),
            thread=(thread := await message.create_thread(
                name=_t.get(
                    "music.thread.name",
                    locale=player.guild.preferred_locale
                )
            ))
        )

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
        tracks: list[list[Track, int]] = await self.bot.databases.music.get_last_tracks(interaction.author)
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
        for _, node in Pool.get_nodes():
            try:
                await node.connect(force=True)
            except Exception as e:
                logger.warning(f"Lavalink raised {e} ({type(e).__name__})")

        await ctx.send("Success")

    @CogUI.context_command(name="players", aliases=["pl"])
    @is_owner()
    async def _players(self, ctx: Context) -> None:
        players_total = 0

        for _, node in Pool.get_nodes():
            node: Node
            if node.status == NodeStatus.CONNECTED:
                players_total += len(node.players)

        await ctx.send(str(players_total))


def setup(bot: ChisatoBot) -> None:
    return bot.add_cog(Music(bot))
