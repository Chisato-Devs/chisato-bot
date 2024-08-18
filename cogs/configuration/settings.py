from disnake import ApplicationCommandInteraction, Localized
from disnake.ext.commands import has_permissions

from utils.basic import CogUI, ChisatoBot, EmbedUI
from utils.handlers.management.settings import SettingsView
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load(__file__)


class Settings(CogUI):

    @CogUI.slash_command(
        name="settings",
        description=Localized(
            "🔧 Настройка бота",
            data=_t.get("settings.command.description")
        )
    )
    @has_permissions(administrator=True)
    async def settings_cmd(self, interaction: ApplicationCommandInteraction) -> None:
        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("settings.title", locale=interaction.guild_locale),
                description=_t.get(
                    "settings.embed.description", locale=interaction.guild_locale
                )
            ),
            view=await SettingsView.generate(
                member=interaction.author, interaction=interaction
            )
        )


def setup(bot: ChisatoBot) -> None:
    return bot.add_cog(Settings(bot))
