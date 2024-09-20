from __future__ import annotations

import secrets
from typing import TypeAlias, cast

from disnake import (
    ui,
    SelectOption,
    MessageInteraction,
    TextChannel,
    Thread,
    VoiceChannel,
    StageChannel,
    ModalInteraction,
    Embed,
    NotFound
)
from harmonize import Player

import utils.basic as _base
from utils.basic import (
    EmbedUI,
    View,
    EmbedErrorUI,
    IntFormatter
)
from utils.basic.services.draw import DrawService
from utils.dataclasses.music import CustomPlaylist
from utils.exceptions import (
    MaximumPlaylist,
    AlreadyCreatedPlaylist
)
from utils.handlers.entertainment.music import SEPARATOR_URI
from utils.handlers.entertainment.music.containers.edit import EditContainer
from utils.handlers.entertainment.music.decorators import (
    has_nodes_button,
    in_voice_button,
    with_bot_button,
    in_text_channel_button
)
from utils.handlers.entertainment.music.generators.queue import QueueGenerator
from utils.handlers.entertainment.music.modals.playlists import (
    EditPlaylist,
    DeletePlaylist
)
from utils.handlers.entertainment.music.views.pagination import QueuePagination
from utils.handlers.entertainment.music.views.playlists.page.utils import ToMain, TrackEditor
from utils.handlers.entertainment.music.views.playlists.utils import Utils
from utils.i18n import ChisatoLocalStore

ChisatoBot = _base.ChisatoBot

Channel: TypeAlias = TextChannel | Thread | VoiceChannel | StageChannel
_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")

__all__ = (
    "ViewPage",
)


class ViewPage(View):
    def __init__(self, interaction: MessageInteraction, playlist: CustomPlaylist) -> None:
        self._interaction = interaction
        self._playlist: CustomPlaylist = playlist

        self._container: EditContainer = EditContainer()

        self._end = False
        self._bot: ChisatoBot = interaction.bot  # type: ignore

        super().__init__(
            timeout=300,
            author=interaction.author,
            store=_t,
            guild=interaction.guild
        )

    @property
    def playlist(self) -> CustomPlaylist:
        return self._playlist

    async def generate_embed(self) -> list[Embed]:
        async with DrawService(self._bot.session) as r:
            user = await ChisatoBot.from_cache().getch_user(self._playlist.owner)
            file = await r.draw_image(
                "playlist_card",
                playlistName=self._playlist.name,
                ownerAvatar=user.display_avatar.url if user else "None",
                ownerName=str(user).upper() if user else "UNKNOWN",
                tracksCount=len(self._playlist.tracks),
                listenedCount=self._playlist.listened if self._playlist.listened < 1_000_000 else IntFormatter(
                    self._playlist.listened
                ).format_number(),
                cardName="closed" if self._playlist.closed else "opened"
            )

        embeds: list[Embed] = [
            EmbedUI(
                title=_t.get(
                    "music.playlist.custom.title", locale=self._interaction.guild_locale,
                    values=(
                        (self._playlist.name[:128] + '.' * 3) if len(
                            self._playlist.name) > 128 else self._playlist.name,
                    )
                )
            ).set_image(file=file)
        ]

        if self.playlist.tracks:
            _, tracks = QueueGenerator.slice_queue(10, queue=self._playlist.tracks.copy())
            strokes: list[str] = QueueGenerator.generate(tracks)
            embeds.append(
                EmbedUI(
                    title=_t.get(
                        "music.short_queue.title",
                        locale=self._interaction.guild_locale
                    ),
                    description="\n".join(strokes[:10]) + ("\n`. . .`" if len(self._playlist.tracks) > 10 else "")
                ).set_image(
                    SEPARATOR_URI
                ).set_footer(
                    icon_url="https://i.ibb.co/T8b3f0h/Hour-Glass.png",
                    text=_t.get(
                        "music.playlist.queue_length.footer",
                        locale=self._interaction.guild_locale
                    ) + QueueGenerator.to_normal_time(
                        sum(map(lambda x: x.length, self._playlist.tracks), 0)
                    )
                )
            )
        return embeds

    @classmethod
    async def generate(
            cls, interaction: MessageInteraction, playlist: CustomPlaylist
    ) -> ViewPage:
        self = cls(interaction, playlist)
        await self._generate_backend()

        return self

    async def _generate_backend(self) -> None:
        if self._interaction.author.id != self._playlist.owner:
            self.remove_item(self.get_item("music.view.playlist.settings"))
        else:
            item = self.get_item("music.view.playlist.settings")
            option = list(filter(lambda x: x.value == "music.playlist.close", item.options))[0]
            option.label = _t.get(
                "music.playlist.options.closed.label" if self._playlist.closed else
                "music.playlist.options.opened.label",
                locale=self._interaction.guild_locale
            )

    async def _edit_name(self, interaction: ModalInteraction) -> None:
        self._playlist = await self._bot.databases.music.edit_playlist(
            uid=self._playlist.id, name=self._container.name
        )
        await interaction.response.edit_message(
            embeds=await self.generate_embed(),
            view=self,
            attachments=[]
        )

    async def _confirm_deleting(self, interaction: ModalInteraction) -> None:
        if self._playlist.name == interaction.text_values["playlists.check.name"]:
            await self._bot.databases.music.remove_playlist(self._playlist.id)

            embed = EmbedUI(
                title=_t.get("music.success.title", locale=interaction.guild_locale),
                description=_t.get(
                    "music.playlist.success.removed",
                    locale=interaction.guild_locale
                )
            )
            embed.set_thumbnail(self._playlist.tracks[0].artwork)

            return await interaction.response.edit_message(
                embed=embed,
                view=ToMain(interaction),
                attachments=[]
            )
        return await interaction.response.edit_message(view=self, attachments=[])

    @ui.select(
        placeholder="music.playlist.options.placeholder",
        custom_id="music.view.playlist.settings",
        options=[
            SelectOption(
                label="music.playlist.options.name.label",
                emoji="<:Edit:1116358712794296460>",
                value="music.playlist.edit.name"
            ),
            SelectOption(
                label="music.playlist.options.closed.label",
                emoji="<:Lock2:1116362293945585804>",
                value="music.playlist.close"
            ),
            SelectOption(
                label="music.playlist.options.tracks.label",
                emoji="<:note:1205907505658728608>",
                value="music.playlist.edit_tracks"
            ),
            SelectOption(
                label="music.playlist.options.delete.label",
                emoji="<:Trashcan:1114376699027660820>",
                value="music.playlist.delete"
            )
        ]
    )
    async def settings_callback(self, select: ui.Select, interaction: MessageInteraction) -> None:
        self.end = True

        match select.values[0]:
            case "music.playlist.edit.name":
                await interaction.response.send_modal(
                    EditPlaylist(
                        interaction=interaction,
                        container=self._container,
                        callback=self._edit_name
                    )
                )
            case "music.playlist.close":
                self._playlist = await self._bot.databases.music.edit_playlist(
                    uid=self._playlist.id, closed=not self._playlist.closed
                )
                await self._generate_backend()
                await interaction.response.edit_message(
                    embeds=await self.generate_embed(),
                    view=self, attachments=[]
                )
            case "music.playlist.edit_tracks":
                await interaction.response.send_message(
                    embed=EmbedUI(
                        title=_t.get(
                            "music.edit_tracks.title",
                            locale=interaction.guild_locale
                        ),
                        description=_t.get(
                            "music.playlist.tracks.edit.description",
                            locale=interaction.guild_locale
                        )
                    ),
                    view=await TrackEditor.generate(self._interaction, interaction, self),
                    ephemeral=True
                )
            case "music.playlist.delete":
                await interaction.response.send_modal(
                    DeletePlaylist(
                        interaction=interaction,
                        after_callback=self._confirm_deleting,
                        playlist_name=self._playlist.name
                    )
                )

    async def interaction_check(self, interaction: MessageInteraction) -> bool | None:
        if interaction.component.custom_id not in [
            "music.view.page.copy_playlist",
            "music.view.page.queue"
        ]:
            return await super().interaction_check(interaction)
        return True

    @ui.button(
        label="music.playlist.copy.label",
        custom_id="music.view.page.copy_playlist",
        emoji="<:Plus:1126911676399243394>"
    )
    async def copy_playlist(self, _, interaction: MessageInteraction) -> None:
        if interaction.author.id != self.playlist.owner and self.playlist.closed:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.playlists.error.is_closed",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        _name = self._playlist.name
        try:
            await self._bot.databases.music.create_playlist(
                name=_name,
                owner=interaction.author,
                tracks=self._playlist.tracks,
                closed=True
            )
        except AlreadyCreatedPlaylist:
            await self._bot.databases.music.create_playlist(
                name=(_name := (_name + " " + secrets.token_hex(6))),
                owner=interaction.author,
                tracks=self.playlist.tracks,
                closed=True
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

        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("music.success.title", locale=interaction.guild_locale),
                description=_t.get(
                    "music.playlist.copy.description",
                    locale=interaction.guild_locale
                )
            ),
            ephemeral=True
        )

        try:
            generated_view = await ViewPage.generate(
                self._interaction,
                await self._bot.databases.music.get_playlist(
                    owner=interaction.author,
                    name=_name
                )
            )
            await self._interaction.edit_original_response(
                embeds=await generated_view.generate_embed(),
                view=generated_view,
                attachments=[]
            )
        except Exception as e:
            _ = e

    @ui.button(
        label="music.playlist.queue.label",
        emoji="<:invoice:1114239254407696584>",
        custom_id="music.view.page.queue"
    )
    async def queue_in_playlist(self, _, interaction: MessageInteraction) -> None:
        if self.playlist.tracks:
            view, embed = await QueuePagination.generate(
                queue=self.playlist.tracks, author=interaction.author, total_time=False
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.playlist.tracks.not_found",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

    @ui.button(
        label="music.playlist.play.label",
        emoji="<:note:1205907505658728608>",
        custom_id="music.view.play"
    )
    @in_text_channel_button
    @in_voice_button
    @has_nodes_button
    @with_bot_button
    async def play_playlist(self, _, interaction: MessageInteraction) -> None:
        player = cast(Player, interaction.guild.voice_client)

        if not self.playlist.tracks:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.playlist.tracks.not_found",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        if not player:
            player: Player = await Player.connect_to_channel(
                interaction.author.voice.channel,
                home=interaction.channel,
                karaoke=False
            )

        if len(player.queue) >= 150:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "music.error.queue_limit",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        try:
            await interaction.response.edit_message(
                embed=EmbedUI(
                    title=_t.get("music.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "music.playlist.play.success_added",
                        locale=interaction.guild_locale,
                        values=(
                            self._playlist.name,
                            await Utils.get_author(self._playlist),
                            IntFormatter(len(self.playlist.tracks)).format_number(),
                            len(self._playlist.tracks[:150 - len(player.queue)])
                        )
                    )
                ).set_thumbnail(self._playlist.tracks[0].artwork_url),
                view=None,
                attachments=[]
            )
        except NotFound:
            return

        player.queue.add(tracks=self._playlist.tracks[:150 - len(player.queue)])

        if not player.is_playing:
            await player.play()
        else:
            interaction.bot.dispatch("on_harmonize_message_update", player)

        await self._bot.databases.music.add_listened_to_playlist(self._playlist.id)
