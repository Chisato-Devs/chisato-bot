from typing import Self

from disnake import MessageInteraction, ApplicationCommandInteraction, Member, SelectOption, ui, errors

from utils.basic import EmbedUI, EmbedErrorUI
from utils.consts import SUCCESS_EMOJI, ERROR_EMOJI
from utils.handlers.management.settings.views.abstract import SettingModule
from utils.handlers.management.settings.views.sub import BackButton
from utils.handlers.pagination import PaginatorView
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./utils/handlers/management/settings/views/view.py")


class BannerModule(PaginatorView, SettingModule):
    __slots__ = (
        "bot",
        "option",
        "member",
        "status",
        "from_page",
        "__now_banner",
        "__interaction"
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

        self.from_page = {
            1: 'green',
            2: 'yellow',
            3: 'pink',
            4: 'blue'
        }

        self.__now_banner: str | None = None
        self.__interaction = interaction
        self.__end = False

        title = _t.get("settings.banner.title", locale=interaction.guild_locale)
        super().__init__(
            author=member, timeout=300, embeds=[
                EmbedUI(
                    title=title
                ).set_image(
                    _t.get(
                        f"settings.banner.{i}.preview_url",
                        locale=interaction.guild_locale
                    )
                )
                for i in self.from_page.values()
            ],
            footer=True, store=_t, interaction=interaction
        )

        self.add_item(BackButton(self.bot, row=2, module=self))

    @property
    def end(self) -> bool:
        return self.__end

    @end.setter
    def end(self, value: bool) -> None:
        self.__end = value

    async def main_callback(self, interaction: MessageInteraction) -> None:
        if interaction.guild.premium_subscription_count <= 6:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "settings.banner.error.min_7",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        await self.initialize_database()
        await interaction.response.edit_message(embed=self.embeds[0], view=self)

    async def initialize_database(self) -> Self:
        data_obj = await self.bot.databases.settings.get(guild=self.__interaction.guild.id)
        self.status = True if data_obj and data_obj[1] else False
        self.__now_banner = data_obj[1] if data_obj and data_obj[1] else None

        self.set_buttons()

        option = "settings.banner.option.disable" if self.status else "settings.banner.option.enable"
        self.option = SelectOption(
            label=_t.get(option, locale=self.__interaction.guild_locale),
            emoji=SUCCESS_EMOJI if self.status else ERROR_EMOJI,
            value=self.__class__.__name__
        )

        return self

    def set_buttons(self) -> None:
        if self.__now_banner == self.from_page[self.page]:
            self.set_banner_button.disabled = True
        else:
            self.set_banner_button.disabled = False

        if self.status:
            self.off_banner_button.disabled = False
        else:
            self.off_banner_button.disabled = True

    async def before_edit_message(self, interaction: MessageInteraction) -> any:
        await self.initialize_database()

    async def on_timeout(self) -> None:
        if not self.__end:
            for child in self.children:
                child.disabled = True

            try:
                await self.__interaction.edit_original_response(view=self)
            except (errors.Forbidden or errors.HTTPException):
                pass

    @ui.button(
        label="settings.banner.button.select.label", emoji=SUCCESS_EMOJI,
        custom_id="set_banner_button", row=1
    )
    async def set_banner_button(self, _, interaction: MessageInteraction) -> None:
        self.__end = True

        if interaction.guild.premium_subscription_count <= 6:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "settings.banner.error.min_7",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        await self.bot.databases.settings.insert(
            guild=interaction.guild.id, banner=self.from_page.get(self.page)
        )

        await self.initialize_database()
        await interaction.response.edit_message(view=self)

    @ui.button(
        label="settings.banner.button.disable.label", emoji=ERROR_EMOJI,
        custom_id="disable_banner_button", row=2
    )
    async def off_banner_button(self, _, interaction: MessageInteraction) -> None:
        self.__end = True

        await self.bot.databases.settings.remove(
            guild=interaction.guild.id, banner=True
        )

        await self.initialize_database()
        await interaction.response.edit_message(view=self)
