from disnake import Member, MessageInteraction, Embed, ApplicationCommandInteraction, Locale
from disnake.ui import button

from utils.basic import EmbedUI, EmbedErrorUI, View
from utils.handlers.pagination import DeleteMessageButton
from utils.i18n import ChisatoLocalStore

_st = ChisatoLocalStore.load(__file__)


class PaginatorView(View):
    def __init__(
            self,
            embeds: list[Embed | EmbedUI],
            footer: bool,
            author: Member,
            interaction: MessageInteraction | ApplicationCommandInteraction = None,
            delete_button: bool = False,
            timeout: int = None,
            store: ChisatoLocalStore = None
    ) -> None:
        if interaction:
            self._loc = interaction.guild_locale
        else:
            self._loc = author.guild.preferred_locale

        self.embeds = embeds
        self.author = author

        self._t = store

        self.page = 1

        if footer:
            self.set_footers(self.embeds, self._loc)

        super().__init__(
            timeout=timeout, store=store, guild=author.guild if not interaction else None,
            interaction=interaction
        )

        if len(self.embeds) == 1:
            self.button_disables(
                ["pagination.next", "pagination.to_end"], disabled=True
            )
        if delete_button:
            self.add_item(DeleteMessageButton())

    def set_footers(self, embeds: list[Embed], locale: Locale) -> None:
        footer = _st.get("pagination.footer.page", locale=locale)
        for embed in embeds:
            embed.set_footer(
                text=footer.format(self.embeds.index(embed) + 1, len(self.embeds))
            )

    async def interaction_check(self, inter: MessageInteraction) -> bool:
        if self.author.id != inter.author.id:
            embed = EmbedErrorUI(
                description=_st.get(
                    "pagination.its_not_you", locale=inter.locale
                ),
                member=inter.author
            )
            await inter.response.send_message(embed=embed, ephemeral=True)
            return False

        return True

    async def before_edit_message(self, interaction: MessageInteraction) -> any:
        pass

    def button_disables(self, custom_ids: list[str], disabled: bool) -> None:
        for child in self.children:
            if str(child.custom_id) in custom_ids:  # type: ignore
                child.disabled = disabled

    @button(emoji="<:Group6:1114675609835143168>", custom_id='pagination.to_start', disabled=True, row=1)
    async def to_start_button(self, _, interaction: MessageInteraction) -> None:
        self.page = 1

        self.button_disables(custom_ids=['pagination.to_start', 'pagination.back'], disabled=True)
        self.button_disables(custom_ids=['pagination.to_end', 'pagination.next'], disabled=False)

        await self.before_edit_message(interaction)
        await interaction.response.edit_message(embed=self.embeds[self.page - 1], view=self)

    @button(emoji="<:ArrowLeft:1114648737730539620>", custom_id='pagination.back', disabled=True, row=1)
    async def back_button(self, _, interaction: MessageInteraction) -> None:
        self.button_disables(custom_ids=['pagination.to_end', 'pagination.next'], disabled=False)
        self.page -= 1

        if self.page == 1:
            self.button_disables(custom_ids=['pagination.to_start', 'pagination.back'], disabled=True)

        await self.before_edit_message(interaction)
        await interaction.response.edit_message(embed=self.embeds[self.page - 1], view=self)

    @button(emoji="<:Arrowright:1114674030331576401>", custom_id='pagination.next', row=1)
    async def next_button(self, _, interaction: MessageInteraction) -> None:
        self.button_disables(custom_ids=['pagination.to_start', 'pagination.back'], disabled=False)
        self.page += 1

        if self.page == len(self.embeds):
            self.button_disables(custom_ids=['pagination.to_end', 'pagination.next'], disabled=True)

        await self.before_edit_message(interaction)
        await interaction.response.edit_message(embed=self.embeds[self.page - 1], view=self)

    @button(emoji="<:Group7:1114675776541949952>", custom_id='pagination.to_end', row=1)
    async def to_end_button(self, _, interaction: MessageInteraction) -> None:
        self.page = len(self.embeds)

        self.button_disables(custom_ids=['pagination.to_start', 'pagination.back'], disabled=False)
        self.button_disables(custom_ids=['pagination.to_end', 'pagination.next'], disabled=True)

        await self.before_edit_message(interaction)
        await interaction.response.edit_message(embed=self.embeds[self.page - 1], view=self)
