from re import search
from typing import TYPE_CHECKING

from disnake import MessageInteraction, TextInputStyle, ModalInteraction
from disnake.ui import Button, Modal, TextInput

from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import EmbedUI, ChisatoBot

_t = ChisatoLocalStore.load("./cogs/moderation/ban.py")


class RemoveWarningButton(Button):
    class _IncludedModal(Modal):
        def __init__(self, interaction: MessageInteraction) -> None:
            super().__init__(
                title=_t.get("warn.remove.warn.modal.title", locale=interaction.guild_locale),
                components=[
                    TextInput(
                        label=_t.get(
                            "warn.remove.warn.modal.option.label",
                            locale=interaction.guild_locale
                        ),
                        placeholder=_t.get(
                            "warn.remove.warn.modal.option.placeholder",
                            locale=interaction.guild_locale
                        ),
                        custom_id="reason_remove_warning",
                        style=TextInputStyle.short,
                        max_length=256,
                    ),
                ]
            )

        async def callback(self, interaction: ModalInteraction) -> None:
            bot: "ChisatoBot" = interaction.bot  # type: ignore
            reason: str = interaction.text_values["reason_remove_warning"]

            description: str = interaction.message.embeds[0].description
            match = search(r'\*\*(?:Номер случая|Номер справи|Case number):\*\* `(\d+)`', description)
            case_number: int = int(match.group(1))

            embed: "EmbedUI" = await bot.databases.moderation.remove_global_warn(
                guild=interaction.guild,
                moderator=interaction.author,
                case_number=case_number,
                reason=reason,
                locale=interaction.guild_locale
            )

            await interaction.response.edit_message(embed=embed, view=None)

    def __init__(self) -> None:
        super().__init__(
            label="warn.remove.warn.component.label",
            emoji="<:ProtectionOFF222222222222222222:1114655406174773268>",
            custom_id='remove_warning', row=2
        )

    async def callback(self, interaction: MessageInteraction) -> None:
        await interaction.response.send_modal(modal=self._IncludedModal(interaction))
