from typing import Self

from disnake import Member, MessageInteraction, ApplicationCommandInteraction, SelectOption, errors, ui, NotFound, \
    HTTPException

from utils.basic import View, EmbedUI
from utils.handlers.management.settings.views.abstract import SettingModule
from utils.handlers.management.settings.views.sub import BackButton
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./utils/handlers/management/settings/views/view.py")


class PermissionsModule(View, SettingModule):
    __slots__ = (
        "bot",
        "option",
        "member",
        "status",
        "__end",
        "__interaction"
    )

    main_module = True

    commands: list[str] = [
        "moderation.stats",
        "warnings.warn",
        "warnings.list-remove",
        "timeout.add",
        "timeout.remove",
        "role.add",
        "role.remove",
        "clear",
        "ban.add",
        "say.default",
        "say.advanced",
        "money.add",
        "money.remove"
    ]

    class IncludeRoleSelect(View):
        __slots__ = (
            "_interaction", "_bot",
            "_end", "_cmd"
        )

        def __init__(self, interaction: MessageInteraction, member: Member, command: str) -> None:
            self._interaction = interaction
            self._bot: "ChisatoBot" = interaction.bot  # type: ignore
            self._end = False
            self._cmd = command

            super().__init__(
                timeout=300, author=member,
                store=_t, interaction=interaction
            )

        async def on_timeout(self) -> None:
            if not self._end:
                for child in self.children:
                    child.disabled = True

                try:
                    await self._interaction.edit_original_response(view=self)
                except NotFound:
                    pass
                except HTTPException:
                    pass

        @ui.role_select(
            placeholder="settings.perms.role_select.placeholder",
            custom_id="settings_select_roles_commands",
            max_values=5
        )
        async def select_roles(self, select: ui.RoleSelect, interaction: MessageInteraction) -> None:
            self._end = True
            if len(cmds := PermissionsModule.IncludeSelect.get_commands_from_group(self._cmd)) > 0:
                for cmd in cmds:
                    await self._bot.databases.settings.set_permission_to_command(
                        f"{self._cmd}.{cmd}", guild=interaction.guild.id, roles=[role.id for role in select.values]
                    )
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get("settings.success.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "settings.perms.role_select.success.group",
                            locale=interaction.guild_locale,
                            values=(self._cmd, ', '.join(cmds))
                        )
                    ), view=None
                )
            else:
                await self._bot.databases.settings.set_permission_to_command(
                    self._cmd, guild=interaction.guild.id, roles=[role.id for role in select.values]
                )
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get("settings.success.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "settings.perms.role_select.success.command",
                            locale=interaction.guild_locale,
                            values=(
                                self._cmd.split('.')[0],

                                ' ' + self._cmd.split('.')[1]
                                if len(self._cmd.split('.')) == 2 else ''
                            )
                        )
                    ), view=None
                )

    class IncludeSelect(ui.StringSelect):
        __slots__ = (
            "bot", "option", "member", "status",
            "__interaction", "__svc", "__is_group",
            "placeholder_group", "placeholder_commands",
            "options_group",
        )

        def __init__(
                self,
                interaction: MessageInteraction | ApplicationCommandInteraction,
                member: Member
        ) -> None:
            self.bot: 'ChisatoBot' = interaction.bot  # type: ignore
            self.option: SelectOption | None = None
            self.member = member
            self.status: bool = False

            self.__interaction = interaction
            self.__is_group = True

            self.placeholder_group = _t.get(
                "settings.perms.group.placeholder",
                locale=interaction.guild_locale
            )
            self.placeholder_commands = _t.get(
                "settings.perms.command.placeholder",
                locale=interaction.guild_locale
            )

            self.options_group = list(
                set([group.split(".")[0] for group in PermissionsModule.commands if len(group.split(".")) == 2])
            )

            super().__init__(
                placeholder="Пишите в тп",
                options=[
                    SelectOption(
                        label="Ну в плейсхолдере видно",
                        value="BlyatNuYaEbal"
                    )
                ],
                custom_id="CommandsToPermissionsSelect"
            )

        @property
        def this_group(self) -> bool:
            return self.__is_group

        def switch(self) -> None:
            self.__is_group = True if self.__is_group is False else False

        async def set_another(self) -> None:
            await self.set_placeholder()
            await self.set_options()

        async def set_options(self) -> None:
            options = []
            match self.__is_group:
                case False:
                    for command in PermissionsModule.commands:
                        if len(command.split(".")) == 2:
                            options.append(
                                SelectOption(
                                    label=f"{command.split('.')[0]} {command.split('.')[1]}",
                                    value=command, emoji="<:Slash:1170859940349497598>"
                                )
                            )
                            continue

                        options.append(
                            SelectOption(
                                label=f'{command}', value=command, emoji="<:Slash:1170859940349497598>"
                            )
                        )
                case True:
                    for group in self.options_group:
                        options.append(
                            SelectOption(
                                label=f'/{group} [{", ".join(self.get_commands_from_group(group))}]',
                                value=group, emoji="<:Group:1170859937992278016>"
                            )
                        )

            self.options.clear()
            self.options = options

        async def set_placeholder(self) -> None:
            match self.__is_group:
                case False:
                    self.placeholder = self.placeholder_commands
                case True:
                    self.placeholder = self.placeholder_group

        @staticmethod
        def get_command_group(command_name: str) -> list[str]:
            groups_list = []
            for command in PermissionsModule.commands:
                if len(command.split(".")) == 2 and command.split(".")[1] == command_name:
                    groups_list.append(command.split(".")[0])

            return groups_list

        @staticmethod
        def get_commands_from_group(group_name: str) -> list[str]:
            commands = []

            for command in PermissionsModule.commands:
                if command.split(".") and len(command.split(".")) == 2 and command.split(".")[0] == group_name:
                    commands.append(command.split(".")[1])

            return commands

        async def callback(self, interaction: MessageInteraction) -> None:
            await interaction.response.send_message(
                embed=EmbedUI(
                    title=_t.get(
                        "settings.next_set.title",
                        locale=interaction.guild_locale
                    ),
                    description=_t.get(
                        "settings.perms.select_roles.description",
                        locale=interaction.guild_locale,
                        values=(
                            self.values[0].split('.')[0],

                            ' ' + self.values[0].split('.')[1]
                            if len(self.values[0].split('.')) == 2 else ''
                        )
                    )
                ),
                ephemeral=True,
                view=PermissionsModule.IncludeRoleSelect(
                    interaction=interaction, member=interaction.author, command=self.values[0]
                )
            )

    def __init__(
            self, interaction: MessageInteraction | ApplicationCommandInteraction,
            member: Member
    ) -> None:
        self.bot: 'ChisatoBot' = interaction.bot  # type: ignore
        self.option: SelectOption | None = None
        self.member = member
        self.status: bool = False

        self.__interaction = interaction
        self.__end = False

        super().__init__(
            author=member, timeout=300, store=_t,
            interaction=interaction
        )

        self.commands_to_set = self.IncludeSelect(interaction=interaction, member=member)

    @property
    def end(self) -> bool:
        return self.__end

    @end.setter
    def end(self, value: bool) -> None:
        self.__end = value

    async def main_callback(self, interaction: MessageInteraction | ApplicationCommandInteraction) -> None:
        await interaction.response.edit_message(
            embed=EmbedUI(
                title=_t.get("settings.perms.title", locale=interaction.guild_locale),
                description=_t.get("settings.perms.description", locale=interaction.guild_locale)
            ), view=self
        )

    async def initialize_database(self) -> Self:
        self.option = SelectOption(
            label=_t.get("settings.perms.option.label", locale=self.__interaction.guild_locale),
            value=type(self).__name__, emoji='<:Slash:1170859940349497598>'
        )

        await self.commands_to_set.set_another()

        self.add_item(self.commands_to_set)
        self.add_item(BackButton(self.bot, row=1, module=self))

        return self

    @ui.button(
        label="settings.perms.button.switch",
        emoji="<:Minus:1126911673245106217>",
        custom_id="set_ones", row=1
    )
    async def set_on_ones(self, button: ui.Button, interaction: MessageInteraction) -> None:
        self.commands_to_set.switch()

        match self.commands_to_set.this_group:
            case True:
                button.label = _t.get(
                    "settings.perms.button.switch.part",
                    locale=interaction.guild_locale
                )
            case False:
                button.label = _t.get(
                    "settings.perms.button.switch",
                    locale=interaction.guild_locale
                )

        await self.commands_to_set.set_another()
        await interaction.response.edit_message(view=self)

    async def on_timeout(self) -> None:
        if not self.__end:
            for child in self.children:
                child.disabled = True

            try:
                await self.__interaction.edit_original_response(view=self)
            except errors.Forbidden:
                pass
            except errors.NotFound:
                pass
            except errors.HTTPException:
                pass
