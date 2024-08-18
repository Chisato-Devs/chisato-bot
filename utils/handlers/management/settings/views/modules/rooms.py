from typing import Self

from disnake import SelectOption, MessageInteraction, ApplicationCommandInteraction, Member, errors, \
    PermissionOverwrite, ui, NotFound

from cogs.configuration.rooms import RoomButtons
from utils.basic import View, EmbedUI, EmbedErrorUI
from utils.consts import ERROR_EMOJI, SUCCESS_EMOJI
from utils.handlers.management.settings.views.abstract import SettingModule
from utils.handlers.management.settings.views.sub import BackButton, EndView
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/configuration/rooms.py")
_st = ChisatoLocalStore.load("./utils/handlers/management/settings/views/view.py")


class RoomsModule(View, SettingModule):
    __slots__ = (
        "status", "__end",
        "bot", "option",
        "__db_object", "__interaction",
        "love_status"
    )

    def __init__(
            self,
            interaction: MessageInteraction | ApplicationCommandInteraction,
            member: Member
    ) -> None:
        self.status = False
        self.bot: 'ChisatoBot' = interaction.bot  # type: ignore
        self.option: SelectOption | None = None
        self.love_status = False

        self.__end = False
        self.__db_object = None
        self.__interaction: MessageInteraction | ApplicationCommandInteraction = interaction

        super().__init__(
            author=member, timeout=300, store=_st,
            interaction=interaction
        )

        self.add_item(BackButton(self.bot, row=1, module=self))

    @property
    def end(self) -> bool:
        return self.__end

    @end.setter
    def end(self, value: bool) -> None:
        self.__end = value

    async def main_callback(self, interaction: MessageInteraction) -> None:
        await self.initialize_database()
        await interaction.response.edit_message(
            embed=EmbedUI(
                title=_t.get("rooms.callback.title", locale=interaction.guild_locale),
                description=_st.get(
                    "settings.rooms.embed.description",
                    locale=interaction.guild_locale
                )
            ), view=self
        )

    async def on_timeout(self) -> None:
        if not self.__end:
            for child in self.children:
                child.disabled = True

            try:
                await self.__interaction.edit_original_response(view=self)
            except errors.InteractionResponded:
                pass
            except errors.HTTPException:
                pass

    async def initialize_database(self) -> Self:
        data_obj = await self.bot.databases.rooms.room_check_find(guild=self.__interaction.guild.id)
        self.status = True if data_obj and data_obj[1] else False
        self.love_status = True if data_obj and data_obj[5] else False
        self.__db_object = data_obj

        option_label = "settings.rooms.option.enable" if self.status else "settings.rooms.option.disable"
        self.option = SelectOption(
            label=_st.get(option_label, locale=self.__interaction.guild_locale),
            emoji=SUCCESS_EMOJI if self.status else ERROR_EMOJI,
            value=self.__class__.__name__
        )

        self.set_buttons()

        return self

    def set_buttons(self) -> None:
        label = "settings.rooms.button.switch.enable" if self.status else "settings.rooms.button.switch.disable"
        self.switch_rooms.label = _st.get(label, locale=self.__interaction.guild_locale)
        self.switch_rooms.emoji = SUCCESS_EMOJI if self.love_status else ERROR_EMOJI

        love_label = "settings.rooms.button.switch.enable.love" if self.love_status \
            else "settings.rooms.button.switch.disable.love"
        self.switch_love_rooms.label = _st.get(love_label, locale=self.__interaction.guild_locale)
        self.switch_love_rooms.emoji = SUCCESS_EMOJI if self.love_status else ERROR_EMOJI

    @ui.button(label="Пиши в тп", emoji=ERROR_EMOJI, custom_id="switch_rooms")
    async def switch_rooms(self, _, interaction: MessageInteraction) -> None:
        self.__end = True
        await self.initialize_database()

        await interaction.response.edit_message(
            embed=EmbedUI(
                title=_t.get("rooms.callback.title", locale=interaction.guild_locale),
                description=_st.get(
                    "settings.rooms.button.switch.deferred",
                    locale=interaction.guild_locale
                )
            ),
            view=None
        )

        if not self.status:
            forbidden_embed = EmbedErrorUI(
                description=_st.get(
                    "settings.rooms.error.forbidden",
                    locale=interaction.guild_locale
                ),
                member=interaction.author
            )

            try:
                category = await interaction.guild.create_category(
                    name=_st.get(
                        "settings.rooms.category_name",
                        locale=interaction.guild.preferred_locale
                    )
                )

            except errors.Forbidden:
                await interaction.edit_original_response(embed=forbidden_embed)
                return None

            try:
                channel_with_message = await interaction.guild.create_text_channel(
                    name=_st.get(
                        "settings.rooms.channel_with_panel",
                        locale=interaction.guild.preferred_locale
                    ),
                    category=category,
                    overwrites={interaction.guild.default_role: PermissionOverwrite(send_messages=False)}
                )
            except errors.Forbidden:
                try:
                    await category.delete()
                except errors.Forbidden:
                    pass
                await interaction.edit_original_response(embed=forbidden_embed)
                return None

            try:
                control_message = await channel_with_message.send(
                    embed=EmbedUI(
                        title=_t.get("rooms.callback.title", locale=interaction.guild.preferred_locale),
                        description=_t.get("private_rooms_panel", locale=interaction.guild.preferred_locale)
                    ),
                    view=RoomButtons(self.bot, guild=interaction.guild)
                )
            except errors.Forbidden:
                try:
                    await category.delete()
                    await channel_with_message.delete()
                except errors.Forbidden:
                    pass
                await interaction.edit_original_response(embed=forbidden_embed)
                return None

            try:
                voice_channel = await interaction.guild.create_voice_channel(
                    name=_st.get(
                        "settings.rooms.voice_name",
                        locale=interaction.guild.preferred_locale
                    ),
                    category=category
                )
            except errors.Forbidden:
                try:
                    await category.delete()
                    await channel_with_message.delete()
                except errors.Forbidden:
                    pass
                await interaction.edit_original_response(embed=forbidden_embed)
                return None

            love_channel = None
            if (
                    (_values := await self.bot.databases.settings.get(guild=interaction.guild.id))
                    and _values[2]
            ):
                try:
                    love_channel = await interaction.guild.create_voice_channel(
                        name=_st.get(
                            "settings.rooms.love_voice_name",
                            locale=interaction.guild.preferred_locale
                        ),
                        category=category
                    )
                except errors.Forbidden:
                    try:
                        await category.delete()
                        await channel_with_message.delete()
                        await voice_channel.delete()
                    except errors.Forbidden:
                        pass
                    await interaction.edit_original_response(embed=forbidden_embed)
                    return None

                love_channel = love_channel.id

            await self.bot.databases.rooms.room_setup_insert(
                guild=interaction.guild.id, voice_channel=voice_channel.id, msg_id=control_message.id,
                category=category.id, text_channel=channel_with_message.id, love_channel=love_channel
            )

            embed = EmbedUI(
                title=_st.get("settings.success.title", locale=interaction.guild_locale),
                description=_st.get(
                    "settings.rooms.button.switch.success",
                    locale=interaction.guild_locale,
                    values=(interaction.author.mention, interaction.author.name)
                ),
                timestamp=interaction.created_at
            )

            await interaction.edit_original_response(
                embed=embed, view=EndView(author=interaction.author, interaction=interaction)
            )

        else:
            settings_values = await self.bot.databases.rooms.room_check_find(guild=interaction.guild.id)

            await self.bot.databases.rooms.room_setup_remove(interaction.guild.id)
            await self.bot.databases.rooms.room_settings_remove(interaction.guild.id)
            await self.bot.databases.rooms.rooms_remove_rooms(interaction.guild.id)

            voice_obj = interaction.guild.get_channel(settings_values[2])
            channel_obj = interaction.guild.get_channel(settings_values[4])
            love_channel_obj = interaction.guild.get_channel(settings_values[5])
            if (
                    voice_obj
                    or channel_obj
                    or love_channel_obj
            ):
                try:
                    try:
                        await voice_obj.category.delete()
                    except AttributeError:
                        await channel_obj.category.delete()
                except (errors.NotFound, errors.Forbidden, errors.HTTPException):
                    pass

                try:
                    await voice_obj.delete()
                except (errors.NotFound, errors.Forbidden, errors.HTTPException, AttributeError):
                    pass

                try:
                    await channel_obj.delete()
                except (errors.NotFound, errors.Forbidden, errors.HTTPException, AttributeError):
                    pass

                try:
                    await love_channel_obj.delete()
                except (errors.NotFound, errors.Forbidden, errors.HTTPException, AttributeError):
                    pass

            await interaction.edit_original_response(
                embed=EmbedUI(
                    title=_st.get("settings.success.title", locale=interaction.guild_locale),
                    description=_st.get(
                        "settings.rooms.button.switch.success.disable",
                        locale=interaction.guild_locale,
                        values=(interaction.author.mention, interaction.author.name)
                    ),
                    timestamp=interaction.created_at
                ),
                view=EndView(author=interaction.author, interaction=interaction)
            )

    @ui.button(
        label="Пиши в тппппппппп",
        row=1, custom_id="switch.love_rooms"
    )
    async def switch_love_rooms(self, _, interaction: MessageInteraction) -> None:
        self.__end = True
        await self.initialize_database()

        if self.status:
            if self.__db_object[5]:
                try:
                    if channel := interaction.guild.get_channel(self.__db_object[5]):
                        await channel.delete()
                except errors.Forbidden:
                    pass

                await self.bot.databases.rooms.room_update_love_room(
                    guild=interaction.guild.id
                )

                await self.initialize_database()
                return await interaction.response.edit_message(view=self)

            if _lc := list(filter(lambda x: x.id == self.__db_object[1], interaction.guild.categories)):
                try:
                    voice_channel = await interaction.guild.create_voice_channel(
                        name=_st.get(
                            "settings.rooms.love_voice_name",
                            locale=interaction.guild.preferred_locale
                        ),
                        category=_lc[0]
                    )
                except errors.Forbidden:
                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_st.get(
                                "settings.rooms.error.forbidden",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        )
                    )

                await self.bot.databases.rooms.room_update_love_room(
                    guild=interaction.guild.id, love_id=voice_channel.id
                )
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_st.get("settings.success.title", locale=interaction.guild_locale),
                        description=_st.get(
                            "settings.rooms.button.love_room.success", locale=interaction.guild_locale,
                            values=(interaction.author.mention, interaction.author.name)
                        ),
                        timestamp=interaction.created_at
                    ),
                    view=EndView(
                        author=interaction.author, interaction=interaction
                    )
                )
            else:
                return await interaction.response.send_message(
                    embed=EmbedErrorUI(
                        description=_st.get(
                            "settings.rooms.button.error.category_deleted",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    )
                )
        else:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_st.get(
                        "settings.rooms.button.error.enable_rooms",
                        locale=interaction.guild_locale
                    ),
                    member=interaction.author
                )
            )

    @ui.button(
        label="settings.rooms.button.resend.label",
        emoji="<:Refresh3:1114986806480478318>", custom_id="resend_message"
    )
    async def resend_message(self, _, interaction: MessageInteraction) -> None:
        self.__end = True
        await self.initialize_database()

        if data_obj := await self.bot.databases.rooms.room_check_find(guild=self.__interaction.guild.id):
            await interaction.response.edit_message(
                embed=EmbedUI(
                    title=_t.get("rooms.callback.title", locale=interaction.guild_locale),
                    description=_st.get(
                        "settings.rooms.button.switch.deferred",
                        locale=interaction.guild_locale
                    )
                ),
                view=None
            )

            channel_obj = interaction.guild.get_channel(data_obj[4])
            if not channel_obj:
                await interaction.edit_original_response(
                    embed=EmbedErrorUI(
                        description=_st.get(
                            "settings.rooms.error.not_found_channel",
                            locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    )
                )
                return

            try:
                await (await channel_obj.fetch_message(data_obj[3])).delete()
            except AttributeError:
                pass
            except NotFound:
                pass

            embed = EmbedUI(
                title=_st.get("settings.success.title", locale=interaction.guild_locale),
                description=_st.get(
                    "settings.rooms.button.resend.success", locale=interaction.guild_locale,
                    values=(interaction.author.mention, interaction.author.name)
                ),
                timestamp=interaction.created_at
            )

            message = await channel_obj.send(
                embed=EmbedUI(
                    title=_t.get("rooms.callback.title", locale=interaction.guild.preferred_locale),
                    description=_t.get("private_rooms_panel", locale=interaction.guild.preferred_locale)
                ),
                view=RoomButtons(self.bot, guild=interaction.guild)
            )

            await self.bot.databases.rooms.room_update_setup(guild=interaction.guild.id, msg_id=message.id)
            await interaction.edit_original_response(
                embed=embed,
                view=EndView(
                    author=interaction.author, interaction=interaction
                )
            )
        else:
            await interaction.response.edit_message(view=self)
