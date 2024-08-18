from __future__ import annotations

from typing import TypeAlias

from disnake import (
    ui,
    SelectOption,
    MessageInteraction,
    TextChannel,
    Thread,
    VoiceChannel,
    StageChannel,
    ApplicationCommandInteraction, InteractionNotResponded, NotFound
)

from utils.basic import (
    View, ChisatoBot
)
from utils.dataclasses.music import CustomPlaylist
from utils.handlers.entertainment.music.decorators import (
    has_nodes_button
)
from utils.handlers.entertainment.music.views.playlists.addons import Create
from utils.handlers.entertainment.music.views.playlists.page import ViewPage
from utils.handlers.entertainment.music.views.playlists.utils import Utils
from utils.i18n import ChisatoLocalStore

Channel: TypeAlias = TextChannel | Thread | VoiceChannel | StageChannel
_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")

__all__ = (
    "Playlists",
)


class Playlists(View):
    def __init__(self, interaction: ApplicationCommandInteraction) -> None:
        self._interaction = interaction
        self._bot: ChisatoBot = interaction.bot  # type: ignore

        self._from_settings_option: dict[str, CustomPlaylist] = {}
        self._from_last_viewed_option: dict[str, CustomPlaylist] = {}

        self.create_option = SelectOption(
            label=_t.get(
                "music.playlist.create.label",
                locale=interaction.guild_locale
            ),
            emoji="<:Plus:1126911676399243394>",
            value="create_playlist.option"
        )

        super().__init__(
            store=_t,
            timeout=300,
            guild=interaction.guild,
            author=interaction.author
        )

    async def _generate_playlists_settings(self) -> None:
        data: list[CustomPlaylist] = await self._bot.databases.music.get_playlists(
            self._interaction.author
        )

        item = self.get_item("playlists.settings.select")
        item.options = [self.create_option]

        if get_options := Utils.generate_options(
                data, self._from_settings_option
        ):
            item.options = [self.create_option].copy() + get_options
            item.disabled = False

    @classmethod
    async def generate(
            cls, interaction: ApplicationCommandInteraction | MessageInteraction
    ) -> Playlists:
        self = cls(interaction)
        await self._generate_playlists_settings()

        return self

    @ui.select(
        placeholder="music.playlist.select.playlist",
        options=[],
        custom_id="playlists.settings.select"
    )
    @has_nodes_button
    async def playlist_selector(self, select: ui.Select, interaction: MessageInteraction) -> None:
        if select.values[0] == "create_playlist.option":
            self.end = True
            view: Create = Create(interaction=interaction, main_interaction=self._interaction)

            await interaction.response.send_message(
                embed=view.generate_embed(view.container),
                view=view,
                ephemeral=True
            )
            return

        await self.custom_defer(interaction)
        self.end = True

        generated_view = await ViewPage.generate(
            interaction, self._from_settings_option[select.values[0]]
        )
        try:
            await interaction.edit_original_response(
                embeds=await generated_view.generate_embed(),
                view=generated_view
            )
        except InteractionNotResponded:
            pass
        except NotFound:
            pass
