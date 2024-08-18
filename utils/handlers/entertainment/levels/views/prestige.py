from disnake import ApplicationCommandInteraction, Member, MessageInteraction, errors, ui

from utils.basic import View, EmbedErrorUI
from utils.basic.services.draw import DrawService
from utils.handlers.entertainment.levels.utils import RankCard
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/entertainment/levels.py")

__all__ = (
    "PrestigeView",
)


class PrestigeView(View):
    __slots__ = (
        "_member", "_bot", '_inter', "_end"
    )

    def __init__(self, member: Member, *, interaction: ApplicationCommandInteraction) -> None:
        self._member = member
        self._bot: ChisatoBot = interaction.bot  # type: ignore
        self._inter = interaction

        self._end = False
        super().__init__(author=member, store=_t, interaction=self._inter)

    async def on_timeout(self) -> None:
        if not self._end:
            for child in self.children:
                child.disabled = True

            try:
                await self._inter.edit_original_response(view=self)
            except errors.Forbidden:
                pass
            except errors.HTTPException:
                pass

    @ui.button(label="level.button.make_prestige", emoji='<:Star2:1131445020210245715>')
    async def prestige(self, _, interaction: MessageInteraction) -> None:
        if await self._bot.databases.level.check_now_prestige(
                guild=interaction.guild.id, member=interaction.author.id
        ):
            await self._bot.databases.level.prestige(
                guild=interaction.guild.id, member=interaction.author.id
            )

        if not await DrawService(self._bot.session).get_status():
            return await interaction.response.edit_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "fun.errors.api_error", locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                view=None,
                attachments=[]
            )

        await interaction.response.edit_message(
            file=await RankCard.draw(interaction, member=interaction.author),
            attachments=[], view=None
        )
