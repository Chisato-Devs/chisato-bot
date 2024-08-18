import asyncio
from typing import Callable

from disnake import ui, MessageInteraction, ModalInteraction, TextInputStyle

from utils.basic import EmbedErrorUI
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./utils/handlers/management/settings/views/view.py")


class VipeSubmit(ui.Modal):
    def __init__(
            self,
            interaction: MessageInteraction,
            callback: Callable[[ModalInteraction], any]
    ) -> None:
        if not asyncio.iscoroutinefunction(callback):
            raise TypeError("callback must be a coro")

        self._callback = callback
        self._placeholder = _t.get(
            "settings.vipe.submit.modal.placeholder",
            locale=interaction.guild_locale
        )

        super().__init__(
            custom_id="settings.vipe.submit.modal",
            title=_t.get(
                "settings.vipe.submit.modal.title",
                locale=interaction.guild_locale
            ),
            components=[
                ui.TextInput(
                    label=_t.get(
                        "settings.vipe.submit.modal.label",
                        locale=interaction.guild_locale
                    ),
                    placeholder=self._placeholder,
                    max_length=1000,
                    custom_id="settings.vipe.submit.result",
                    style=TextInputStyle.paragraph
                )
            ]
        )

    async def callback(self, interaction: ModalInteraction, /) -> None:
        if interaction.text_values["settings.vipe.submit.result"] == self._placeholder:
            return await self._callback(interaction)

        await interaction.response.send_message(
            embed=EmbedErrorUI(
                description=_t.get(
                    "settings.vipe.error.text",
                    locale=interaction.guild_locale
                ),
                member=interaction.author
            )
        )
