import asyncio
from typing import TYPE_CHECKING, TypeVar

from disnake import ApplicationCommandInteraction, Localized, ButtonStyle, Guild, Locale
from disnake.ext.commands import InvokableSlashCommand, InvokableUserCommand, InvokableMessageCommand, Param, \
    SubCommand, InvokableApplicationCommand
from disnake.ui import Button

from utils.basic import CogUI, EmbedUI, EmbedErrorUI
from utils.enviroment import env
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load(__file__)
T = TypeVar("T")


class HelpCog(CogUI):
    def __init__(self, bot: "ChisatoBot") -> None:
        super().__init__(bot=bot)

        self.regular_permissions = {
            "settings": {"help.administrator": True},
            "rank.set": {"help.administrator": True},
            "ban.add": {"help.ban_members": True},
            "clear": {"help.manage_messages": True},
            "role.add": {"help.manage_roles": True},
            "role.remove": {"help.manage_roles": True},
            "timeout.add": {"help.moderate_members": True},
            "timeout.remove": {"help.moderate_members": True},
            "warnings.warn": {"help.view_audit_log": True},
            "warnings.list-remove": {"help.view_audit_log": True},
            "moderation.stats": {"help.view_audit_log": True},
            "say.default": {"help.view_audit_log": True},
            "say.advanced": {"help.view_audit_log": True},
            "money.add": {"help.administrator": True},
            "money.remove": {"help.administrator": True}
        }

    @CogUI.slash_command(name="help")
    async def _help(self, interaction: ApplicationCommandInteraction) -> ...:
        ...

    @staticmethod
    async def help_autocomplete(
            interaction: ApplicationCommandInteraction,
            user_input: str
    ) -> dict[str, str]:
        def translate(item: CogUI) -> str:
            return _t.get(
                f"help.autocomplete.module.{item.__module__.split('.')[1].lower()}",
                locale=interaction.guild_locale
            )

        return {
            translate(item): module
            for module, item in interaction.bot.cogs.items()
            if (
                    translate(item)
                    and item.__module__.split('.')[1] != "management"
                    and user_input.lower() in translate(item).lower()
            )
        }

    async def generate_help(self, cog_item: CogUI, guild: Guild, locale: Locale) -> list[str]:
        cog_name = cog_item.__module__.split('.')[1]
        commands = [
            cmd for item in self.bot.cogs.values()
            if cog_name == item.__module__.split('.')[1]
            for cmd in item.get_application_commands()
            if not cmd.callback.__name__.startswith("_")
        ]

        async def format_command(command: InvokableApplicationCommand) -> str:
            command_name = command.qualified_name.replace(' ', '.')
            roles = ', '.join(
                guild.get_role(role_id).mention
                for role_id in await self.bot.databases.settings.get_permissions(command_name, guild=guild.id)
                if guild.get_role(role_id)
            )

            slash = "" if isinstance(command, (InvokableUserCommand, InvokableMessageCommand)) else "/"
            perms = ", ".join(
                "`" + _t.get(key=key, locale=locale) + "`"
                for key in self.regular_permissions.get(command_name, {}).keys()
            ) or _t.get("help.command.embed.permissions", locale=locale)

            description = (
                command.body.description_localizations.data.get(str(locale).replace("_", "-"), "")[2:]
                if isinstance(command, (InvokableSlashCommand, SubCommand)) else ""
            )

            return _t.get(
                "help.command.embed.permissions.part.1", locale=locale,
                values=(slash, command.qualified_name, roles if roles else perms)
            ) + (description and _t.get("help.command.embed.permissions.part.2", locale=locale, values=(description,)))

        return list(await asyncio.gather(*[format_command(cmd) for cmd in commands]))

    @_help.sub_command(
        name="command",
        description=Localized(
            "💡 Помощь: помощь по командам", data=_t.get("help.command.description")
        )
    )
    async def sub_help(
            self, interaction: ApplicationCommandInteraction,
            cog_name: str = Param(
                name=Localized("модуль", data=_t.get("help.command.option.module.name")),
                description=Localized(
                    "- укажи интересующий тебя модуль команд",
                    data=_t.get("help.command.option.module.description")
                ),
                autocomplete=help_autocomplete
            )
    ) -> None:
        if not self.bot.databases:
            return

        cog_item: str | CogUI = self.bot.cogs.get(cog_name, "INVALID")
        if cog_item == "INVALID":
            await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "help.command.error.incorrect_module", locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        commands_formatted = await self.generate_help(cog_item, interaction.guild, interaction.guild_locale)

        await interaction.edit_original_response(embed=EmbedUI(
            title=_t.get(
                f"help.autocomplete.module.{cog_item.__module__.split('.')[1].lower()}",
                locale=interaction.guild_locale
            ),
            description="\n".join(commands_formatted)
        ))

    @_help.sub_command(
        name="contact",
        description=Localized(
            "💡 Помощь: cвязаться с разработчиками!",
            data=_t.get("help.contact_devs.description"))

    )
    async def contact(self, interaction: ApplicationCommandInteraction) -> None:
        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("help.contact_embed.title", locale=interaction.guild_locale),
                description=_t.get("help.contact_embed.description", locale=interaction.guild_locale)
            ),
            ephemeral=True,
            components=[
                Button(
                    label=_t.get("help.command.contact.button.label", locale=interaction.guild_locale),
                    style=ButtonStyle.url, url=env.GUILD_INVITE
                )
            ]
        )


def setup(bot: "ChisatoBot") -> None:
    return bot.add_cog(HelpCog(bot))
