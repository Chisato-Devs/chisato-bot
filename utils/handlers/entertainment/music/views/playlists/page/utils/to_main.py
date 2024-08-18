from disnake import ModalInteraction, MessageInteraction, ui

from utils.basic import View, EmbedUI
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/entertainment/music.py")


class ToMain(View):
    def __init__(self, interaction: ModalInteraction | MessageInteraction) -> None:
        self._interaction = interaction
        self._bot: ChisatoBot = interaction.bot  # type: ignore
        self.end = False

        super().__init__(
            timeout=300,
            author=interaction.author,
            store=_t,
            guild=interaction.guild
        )

    @ui.button(
        label="music.playlist.to_main.label",
        custom_id="music.view.playlist.back",
        emoji="<:Arrowright:1114674030331576401>"
    )
    async def back_button(self, _, interaction: MessageInteraction) -> None:
        from utils.handlers.entertainment.music.views.playlists import Playlists

        self.end = True
        await interaction.response.edit_message(
            embed=EmbedUI(
                title=_t.get("music.playlists.title", locale=interaction.guild_locale)
            ).set_footer(text=_t.get("music.playlists.footer", locale=interaction.guild_locale)),
            view=await Playlists.generate(interaction)
        )
