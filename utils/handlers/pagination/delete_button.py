from disnake import MessageInteraction, ButtonStyle, errors
from disnake.ui import Button


class DeleteMessageButton(Button):
    def __init__(self) -> None:
        super().__init__(
            style=ButtonStyle.grey, emoji="<:Trashcan:1114376699027660820>",
            custom_id='delete_message', row=1
        )

    async def callback(self, interaction: MessageInteraction) -> None:
        try:
            await interaction.response.defer()
            await interaction.followup.delete_message(interaction.message.id)
        except errors.NotFound:
            pass
