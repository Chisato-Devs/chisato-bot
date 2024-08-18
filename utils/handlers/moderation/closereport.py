from disnake import MessageInteraction, Message, Member, Embed, ApplicationCommandInteraction
from disnake.ui import View, button

from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/moderation/reports.py")


async def close_report(
        report_message: Message, member: Member, status: bool, verdict: str = None,
        interaction: MessageInteraction | ApplicationCommandInteraction = None
) -> None:
    embed: Embed = report_message.embeds[0]
    if interaction:
        locale = interaction.guild_locale
    else:
        locale = member.guild.preferred_locale

    embed.description = embed.description.replace(
        _t.get("reports.close.change.from", locale=locale),
        _t.get("reports.close.change.to.checked", locale=locale)
    ) if status else embed.description.replace(
        _t.get("reports.close.change.from", locale=locale),
        _t.get("reports.close.change.to.declined", locale=locale)
    )

    await report_message.edit(
        embed=embed,
        view=ReportOnCheckedButton(
            member=member,
            status=status,
            interaction=interaction,
            verdict_data={
                "kick": {
                    "label": _t.get("reports.verdict.kick", locale=locale),
                    "emoji": "<:removeuser:1114369700554621010>"
                },
                "timeout": {
                    "label": _t.get("reports.verdict.timeout", locale=locale),
                    "emoji": "<:Volumemuted:1158170369019101305>"
                },
                "warn": {
                    "label": _t.get("reports.verdict.warn", locale=locale),
                    "emoji": "<:ProtectionOFF:1114647772440821954>"
                },
                "ban": {
                    "label": _t.get("reports.verdict.ban", locale=locale),
                    "emoji": "<:Userrestricted:1158170389063663617>"
                }
            }.get(verdict)
        )
    )


class ReportOnCheckedButton(View):
    def __init__(
            self, member: Member, status: bool, verdict_data: dict = None,
            interaction: MessageInteraction | ApplicationCommandInteraction = None
    ) -> None:
        self.member: Member = member

        if interaction:
            self.locale = interaction.guild_locale
        else:
            self.locale = member.guild.preferred_locale

        self.status: bool = status
        self.verdict_data: dict = verdict_data

        super().__init__(timeout=None)
        self.update_buttons()

    def update_buttons(self) -> None:
        self.moderator_name_button.disabled = True

        part = _t.get('reports.checked', locale=self.locale) \
            if self.status else _t.get('reports.declined', locale=self.locale)
        self.moderator_name_button.label = f"{part}: {self.member}"

        if self.verdict_data:
            self.verdict_button.disabled = True
            self.verdict_button.label = self.verdict_data["label"]
            self.verdict_button.emoji = self.verdict_data["emoji"]
        else:
            self.remove_item(self.verdict_button)

    @button(emoji="<:User:1116366794274385940>")
    async def moderator_name_button(self, _, interaction: MessageInteraction) -> None:
        return

    @button(emoji="<:User:1116366794274385940>")
    async def verdict_button(self, _, interaction: MessageInteraction) -> None:
        return
