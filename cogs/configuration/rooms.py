import random

from disnake import (
    Embed,
    SelectOption,
    MessageInteraction,
    ui,
    PermissionOverwrite,
    InviteTarget,
    ModalInteraction,
    utils,
    NotFound,
    errors,
    TextInputStyle,
    Member,
    VoiceState,
    Forbidden,
    HTTPException,
    Guild
)
from disnake.abc import Snowflake
from disnake.ext.tasks import loop
from disnake.ui import Select

from utils.basic import CogUI, ChisatoBot, EmbedUI, View, EmbedErrorUI
from utils.consts import ERROR_EMOJI, SUCCESS_EMOJI
from utils.handlers.management.rooms.decorators import in_voice, room_leader_check, is_not_love_room
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load(__file__)
emojis = [
    "🎮", "💘", "😍", "😘", "💕", "🌺", "🌹", "🌻", "🌷", "🌸", "🌼",
    "🎮", "🚀", "🔫", "👑", "🏆", "🎁", "🌳", "🌲", "🌿", "🌱", "🍃"
]


class ConfigureModal(ui.Modal):
    def __init__(
            self, bot: ChisatoBot, arg: str,
            interaction: MessageInteraction
    ) -> None:
        self.bot = bot
        self.arg = arg
        self._interaction = interaction

        title = None
        components = None

        match self.arg:
            case "edit":
                title = _t.get("configure_modal.title.edit", locale=self._interaction.guild_locale)

                components = [
                    ui.TextInput(
                        label=_t.get("configure_modal.input_label.name", locale=self._interaction.guild_locale),
                        max_length=20,
                        placeholder=_t.get(
                            "configure_modal.input_placeholder.name", locale=self._interaction.guild_locale
                        ),
                        custom_id="name",
                        style=TextInputStyle.short,
                        required=False
                    )
                ]
            case "limit":
                title = _t.get("configure_modal.title.limit", locale=self._interaction.guild_locale)

                components = [
                    ui.TextInput(
                        label=_t.get(
                            "configure_modal.input_label.limit", locale=self._interaction.guild_locale
                        ),
                        max_length=2,
                        placeholder=_t.get(
                            "configure_modal.input_placeholder.limit", locale=self._interaction.guild_locale
                        ),
                        custom_id="limit",
                        style=TextInputStyle.short
                    )
                ]

        super().__init__(
            title=title, components=components, custom_id="change_name_or_limit_modal"
        )

    @in_voice
    @room_leader_check
    async def callback(self, interaction: ModalInteraction) -> None:
        values = await self.bot.databases.rooms.temp_room_values(guild=interaction.guild.id, user=interaction.author.id)
        voice = interaction.guild.get_channel(values[1])
        result = await self.bot.databases.rooms.room_req_check(guild=interaction.guild.id, voice=voice.id)

        if self.arg == "edit":
            if not result:
                name = interaction.text_values["name"]

                if name:
                    await self.bot.databases.rooms.settings_room_insert(
                        guild=interaction.guild.id, user=interaction.author, room_naming=name
                    )
                else:
                    name = f"{random.choice(emojis)} {interaction.author.name}"
                    await self.bot.databases.rooms.settings_room_insert(
                        guild=interaction.guild.id, user=interaction.author, room_naming=0
                    )

                await voice.edit(name=name)
                await interaction.response.send_message(
                    embed=EmbedUI(
                        title=_t.get("rooms.callback.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "rooms.callback.description_edited", locale=interaction.guild_locale, values=(name,)
                        ),
                        timestamp=interaction.created_at
                    ),
                    ephemeral=True
                )
                await self.bot.databases.rooms.room_req_add(guild=interaction.guild.id, voice=voice.id)
            else:
                await interaction.response.send_message(
                    embed=EmbedUI(
                        description=_t.get(
                            "rooms.callback.description_error", locale=interaction.guild_locale,
                            values=(interaction.author.name,)
                        )
                    ),
                    ephemeral=True
                )

        elif self.arg == "limit":
            if not result:
                try:
                    limit = int(interaction.text_values["limit"])
                    if limit < 0:
                        raise ValueError
                except ValueError:
                    return await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "rooms.modal.error.not_int",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ),
                        ephemeral=True
                    )

                if limit:
                    await self.bot.databases.rooms.settings_room_insert(guild=interaction.guild.id,
                                                                        user=interaction.author, limit_user=limit)
                else:
                    await self.bot.databases.rooms.settings_room_insert(guild=interaction.guild.id,
                                                                        user=interaction.author, limit_user=0)

                await voice.edit(user_limit=limit)
                await interaction.response.send_message(
                    embed=EmbedUI(
                        title=_t.get("rooms.callback.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "rooms.callback.description_edited_limit", locale=interaction.guild_locale, values=(limit,)
                        ),
                        timestamp=interaction.created_at
                    ), ephemeral=True
                )
                await self.bot.databases.rooms.room_req_add(guild=interaction.guild.id, voice=voice.id)
            else:
                await interaction.response.send_message(
                    embed=EmbedUI(
                        description=_t.get(
                            "rooms.callback.description_error", locale=interaction.guild_locale,
                            values=(interaction.author.name,)
                        )
                    ),
                    ephemeral=True
                )


class ConfigureSelectUser(ui.UserSelect):
    def __init__(
            self, arg: str, bot: ChisatoBot, placeholder_key: str, interaction: MessageInteraction
    ) -> None:
        self.arg = arg
        self.bot = bot
        self._interaction = interaction

        super().__init__(
            placeholder=_t.get(placeholder_key, locale=interaction.guild_locale),
            custom_id="configure_user_select", min_values=1, max_values=1
        )

    @in_voice
    @room_leader_check
    async def callback(self, interaction: MessageInteraction) -> None:
        values = await self.bot.databases.rooms.temp_room_values(
            guild=interaction.guild.id, user=interaction.author.id
        )
        voice = interaction.guild.get_channel(values[1])
        member = self.values[0]

        if self.arg == "mute":
            if self.values[0].id == interaction.author.id:
                return await interaction.response.edit_message(
                    embed=Embed(
                        description=_t.get(
                            "rooms.callback.description_self_timeout",
                            locale=interaction.guild_locale, values=(interaction.author.name,)
                        )
                    ), view=None
                )

            if member in voice.members:
                if voice.overwrites_for(member).speak is False:
                    await voice.set_permissions(member, speak=True)
                    await interaction.response.edit_message(
                        embed=EmbedUI(
                            title=_t.get("rooms.callback.title", locale=interaction.guild_locale),
                            description=_t.get(
                                "rooms.callback.description_timeout_deleted",
                                locale=interaction.guild_locale, values=(member.mention, member.name,)
                            ),
                            timestamp=interaction.created_at
                        ), view=None
                    )
                else:
                    await voice.set_permissions(member, speak=False)
                    await interaction.response.edit_message(
                        embed=EmbedUI(
                            title=_t.get("rooms.callback.title", locale=interaction.guild_locale),
                            description=_t.get(
                                "rooms.callback.description_timeout_added",
                                locale=interaction.guild_locale, values=(member.mention, member,)),
                            timestamp=interaction.created_at
                        ), view=None
                    )

                await member.move_to(voice)

            else:
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        description=_t.get(
                            "rooms.callback.description_error_none_in_room",
                            locale=interaction.guild_locale, values=(interaction.author.name,)
                        )
                    ), view=None
                )

        elif self.arg == "kick":
            if self.values[0].id == interaction.author.id:
                return await interaction.response.edit_message(
                    embed=EmbedUI(
                        description=_t.get(
                            "rooms.callback.description_error_self_kick",
                            locale=interaction.guild_locale, values=(interaction.author.name,)
                        )
                    ), view=None
                )

            if member in voice.members:
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get("rooms.callback.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "rooms.callback.description_kick_added",
                            locale=interaction.guild_locale, values=(member.mention, member,)
                        ),
                        timestamp=interaction.created_at
                    ),
                    view=None
                )

                await member.edit(voice_channel=None)
            else:
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        description=_t.get(
                            "rooms.callback.description_error_none_in_room",
                            locale=interaction.guild_locale, values=(interaction.author.name,)
                        )
                    ), view=None
                )

        elif self.arg == "access":
            if self.values[0].id == interaction.author.id:
                return await interaction.response.edit_message_message(
                    embed=EmbedUI(
                        description=_t.get(
                            "rooms.callback.description_error_not_self_access",
                            locale=interaction.guild_locale, values=(interaction.author.name,)
                        )
                    ), view=None
                )

            if voice.overwrites_for(member).connect is False:
                await voice.set_permissions(member, connect=True)
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get("rooms.callback.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "rooms.callback.description_access_out_added",
                            locale=interaction.guild_locale, values=(member.mention, member,)
                        ),
                        timestamp=interaction.created_at
                    ), view=None
                )

            else:
                await voice.set_permissions(member, connect=False)

                if member in voice.members:
                    await member.edit(voice_channel=None)

                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get("rooms.callback.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "rooms.callback.description_access_denied",
                            locale=interaction.guild_locale, values=(member.mention, member,)
                        ),
                        timestamp=interaction.created_at
                    ), view=None
                )

        elif self.arg == "new":
            if self.values[0].id == interaction.author.id:
                return await interaction.response.edit_message_message(
                    embed=EmbedUI(
                        description=_t.get(
                            "rooms.callback.description_error_not_self_access",
                            locale=interaction.guild_locale, values=(interaction.author.name,)
                        )
                    ), view=None
                )

            if member in voice.members:
                await self.bot.databases.rooms.room_update_leader(
                    guild=interaction.guild.id, voice=voice.id, new_leader=member.id
                )

                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get("rooms.callback.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "rooms.callback.description_leader_transferred",
                            locale=interaction.guild_locale, values=(member.mention, member,)
                        ),
                        timestamp=interaction.created_at
                    ),
                    view=None
                )
                await voice.edit(overwrites={
                    member: PermissionOverwrite(manage_channels=True)
                })
            else:
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        description=_t.get(
                            "rooms.callback.description_error_none_in_room",
                            locale=interaction.guild_locale, values=(interaction.author.name,)
                        )
                    ), view=None
                )

        elif self.arg == "rebute":
            if self.values[0].id == interaction.author.id:
                return await interaction.response.edit_message(
                    embed=EmbedUI(
                        description=_t.get(
                            "rooms.callback.description_error_edit_self_empty",
                            locale=interaction.guild_locale, values=(interaction.author.name,)
                        )
                    ), view=None
                )

            voice = interaction.guild.get_channel(
                (
                    await self.bot.databases.rooms.temp_room_values(
                        guild=interaction.guild.id, user=interaction.author.id
                    )
                )[1]
            )

            overs = voice.overwrites_for(member)

            if overs and member in voice.members:
                await voice.set_permissions(member, speak=None)
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        title=_t.get("rooms.callback.title", locale=interaction.guild_locale),
                        description=_t.get(
                            "rooms.callback.description_access_void_empty",
                            locale=interaction.guild_locale, values=(member.mention, member,)
                        ),
                        timestamp=interaction.created_at
                    ), view=None
                )

            elif member not in voice.members:
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        description=_t.get(
                            "rooms.callback.description_error_none_in_room",
                            locale=interaction.guild_locale, values=(interaction.author.name,)
                        )
                    ),
                    view=None
                )
            else:
                await interaction.response.edit_message(
                    embed=EmbedUI(
                        description=_t.get(
                            "rooms.callback.description_error_edit_void_empty",
                            locale=interaction.guild_locale, values=(interaction.author.name,)
                        )

                    ), view=None
                )


class RoomButtons(View):
    def __init__(self, bot: "ChisatoBot", guild: Guild, translate: "ChisatoLocalStore" = None) -> None:
        self.bot = bot

        super().__init__(timeout=None, store=_t if not translate else translate, guild=guild)

    class Party(Snowflake):
        class Types:
            poker = 755827207812677713
            betrayal = 773336526917861400
            fishing = 814288819477020702
            chess = 832012774040141894
            letter_tile = 879863686565621790
            word_snack = 879863976006127627
            doodle_crew = 878067389634314250
            checkers = 832013003968348200
            spellcast = 852509694341283871
            watch_together = 880218394199220334
            sketch_heads = 902271654783242291
            ocho = 832025144389533716
            gartic_phone = 1007373802981822582

        def __init__(self, name: str) -> None:
            self.id = getattr(self.Types, name)

    @ui.string_select(
        placeholder="rooms.string_select.placeholder", row=0,
        min_values=1, max_values=1, custom_id="type_activity_select",
        options=[
            SelectOption(
                label="Poker Night (Boost level 1)", value="poker",
                description="rooms.string_select.description_not_more_7", emoji="🃏"
            ),
            SelectOption(
                label="Chess In The Park (Boost Level 1)", value="chess",
                description="rooms.string_select.description_unlimited", emoji="♟️"
            ),
            SelectOption(
                label="Letter League (Boost Level 1)", value="letter_tile",
                description="rooms.string_select.description_not_more_8", emoji="<:league:1099663936053330010>"
            ),
            SelectOption(
                label="SpellCast (Boost Level 1)", value="spellcast",
                description="rooms.string_select.description_not_more_6", emoji="<:spellcast:1099664579144994859>"
            ),
            SelectOption(
                label="Watch Together", value="watch_together",
                description="rooms.string_select.description_unlimited", emoji="<:watch_together:1099665103844024402>"
            ),
            SelectOption(
                label="Checkers In The Park (Boost Level 1)", value="checkers",
                description="rooms.string_select.description_unlimited", emoji="<:checkers:1099665793521819688>"
            ),
            SelectOption(
                label="Blazing 8s (Boost Level 1)", value="ocho",
                description="rooms.string_select.description_not_more_8", emoji="<:blazzing:1099668662891331654>"
            ),
            SelectOption(
                label="Sketch Heads (Boost Level 1)", value="sketch_heads",
                description="rooms.string_select.description_not_more_8", emoji="<:sketch:1099671386642976838>"
            ),
        ]
    )
    @in_voice
    @room_leader_check
    async def activ_callback(self, select: Select, inter: MessageInteraction) -> None:
        voice = inter.guild.get_channel(
            (
                await self.bot.databases.rooms.temp_room_values(
                    guild=inter.guild.id, user=inter.author.id
                )
            )[1]
        )

        await inter.response.send_message(
            await voice.create_invite(
                reason='Activity created for rooms', target_type=InviteTarget.embedded_application,
                target_application=self.Party(select.values[0])
            ),
            ephemeral=True
        )

    @ui.button(emoji="<:Edit:1116358712794296460>", custom_id="editt", row=1)
    @in_voice
    @is_not_love_room
    @room_leader_check
    async def edit(self, _, inter: MessageInteraction) -> None:
        await inter.response.send_modal(
            ConfigureModal(bot=self.bot, arg="edit", interaction=inter)
        )

    @ui.button(emoji="<:Users:1116359383954243684>", custom_id="limit_memberss", row=1)
    @in_voice
    @is_not_love_room
    @room_leader_check
    async def limit_members(self, _, inter: MessageInteraction) -> None:
        await inter.response.send_modal(
            ConfigureModal(bot=self.bot, arg="limit", interaction=inter)
        )

    @ui.button(emoji="<:Lock2:1116362293945585804>", custom_id="closee", row=1)
    @in_voice
    @is_not_love_room
    @room_leader_check
    async def close(self, _, inter: MessageInteraction) -> None:
        voice = inter.guild.get_channel(
            (await self.bot.databases.rooms.temp_room_values(guild=inter.guild.id, user=inter.author.id))[1]
        )

        if voice.overwrites_for(inter.guild.default_role).connect is False:
            await voice.set_permissions(inter.guild.default_role, connect=True)

            await inter.response.send_message(
                embed=EmbedUI(
                    title=_t.get("rooms.callback.title", locale=inter.guild_locale),
                    description=_t.get(
                        "rooms.button.close.embed.opened", locale=inter.guild_locale,
                        values=(inter.author.mention, inter.author)
                    ),
                    timestamp=inter.created_at
                ), ephemeral=True
            )

        else:
            await voice.set_permissions(inter.guild.default_role, connect=False)

            await inter.response.send_message(
                embed=EmbedUI(
                    title=_t.get("rooms.callback.title", locale=inter.guild_locale),
                    description=_t.get(
                        "rooms.button.close.embed.closed", locale=inter.guild_locale,
                        values=(inter.author.mention, inter.author)
                    ),
                    timestamp=inter.created_at
                ),
                ephemeral=True
            )

    @ui.button(emoji="<:OpenEye:1116362800437145692>", custom_id="visionn", row=1)
    @in_voice
    @is_not_love_room
    @room_leader_check
    async def vision(self, _, inter: MessageInteraction) -> None:
        voice = inter.guild.get_channel(
            (await self.bot.databases.rooms.temp_room_values(guild=inter.guild.id, user=inter.author.id))[1]
        )

        overs = voice.overwrites_for(inter.guild.default_role)
        if overs.view_channel is False:
            await voice.set_permissions(inter.guild.default_role, view_channel=True)
            await inter.response.send_message(embed=EmbedUI(
                title=_t.get("rooms.callback.title", locale=inter.guild_locale),
                description=_t.get(
                    "rooms.button.vision.embed.opened", locale=inter.guild_locale,
                    values=(inter.author.mention, inter.author)
                ),
                timestamp=inter.created_at
            ), ephemeral=True)
        else:
            await voice.set_permissions(inter.guild.default_role, view_channel=False)
            await inter.response.send_message(embed=EmbedUI(
                title=_t.get("rooms.callback.title", locale=inter.guild_locale),
                description=_t.get(
                    "rooms.button.vision.embed.closed", locale=inter.guild_locale,
                    values=(inter.author.mention, inter.author)
                ),
                timestamp=inter.created_at
            ), ephemeral=True)

    @ui.button(emoji="<:Microphone:1116363436423647273>", custom_id="mutee", row=1)
    @in_voice
    @is_not_love_room
    @room_leader_check
    async def mute(self, _, inter: MessageInteraction) -> None:
        await inter.response.send_message(
            embed=EmbedUI(
                title=_t.get("rooms.callback.title", locale=inter.guild_locale),
                description=_t.get("rooms.button.mute.embed", locale=inter.guild_locale),
                timestamp=inter.created_at
            ),
            ephemeral=True,
            view=ui.View(timeout=None).add_item(
                ConfigureSelectUser(
                    arg="mute", bot=self.bot, placeholder_key="rooms.user_select.placeholder.mute",
                    interaction=inter
                )
            )
        )

    @ui.button(emoji="<:removeuser:1114369700554621010>", custom_id="remove_memberr", row=2)
    @in_voice
    @is_not_love_room
    @room_leader_check
    async def remove_member(self, _, inter: MessageInteraction) -> None:
        await inter.response.send_message(
            embed=EmbedUI(
                title=_t.get("rooms.callback.title", locale=inter.guild_locale),
                description=_t.get("rooms.button.kick.embed", locale=inter.guild_locale),
                timestamp=inter.created_at
            ),
            ephemeral=True,
            view=ui.View(timeout=None).add_item(
                ConfigureSelectUser(
                    arg="kick", bot=self.bot, interaction=inter,
                    placeholder_key="rooms.user_select.placeholder.kick"
                )
            )
        )

    @ui.button(emoji="<:Key:1116364330812846211>", custom_id="acess_room", row=2)
    @in_voice
    @is_not_love_room
    @room_leader_check
    async def room_access(self, _, inter: MessageInteraction) -> None:
        await inter.response.send_message(
            embed=EmbedUI(
                title=_t.get("rooms.callback.title", locale=inter.guild_locale),
                description=_t.get("rooms.button.access.embed", locale=inter.guild_locale),
                timestamp=inter.created_at
            ),
            ephemeral=True,
            view=ui.View(timeout=None).add_item(
                ConfigureSelectUser(
                    arg="access", bot=self.bot, interaction=inter,
                    placeholder_key="rooms.user_select.placeholder.access"
                )
            )
        )

    @ui.button(emoji="<:fingerprint:1114231400699281528>", custom_id="new_ownerr", row=2)
    @in_voice
    @is_not_love_room
    @room_leader_check
    async def new_owner(self, _, inter: MessageInteraction) -> None:
        await inter.response.send_message(
            embed=EmbedUI(
                title=_t.get("rooms.callback.title", locale=inter.guild_locale),
                description=_t.get("rooms.button.new_owner.embed", locale=inter.guild_locale),
                timestamp=inter.created_at
            ),
            ephemeral=True,
            view=ui.View(timeout=None).add_item(
                ConfigureSelectUser(
                    arg="new", bot=self.bot, interaction=inter,
                    placeholder_key="rooms.user_select.placeholder.new_owner"
                )
            )
        )

    @ui.button(emoji="<:Refresh3:1114986806480478318>", custom_id="rebute", row=2)
    @in_voice
    @is_not_love_room
    @room_leader_check
    async def rebute(self, _, inter: MessageInteraction) -> None:
        await inter.response.send_message(
            embed=EmbedUI(
                title=_t.get("rooms.callback.title", locale=inter.guild_locale),
                description=_t.get("rooms.button.rebute.embed", locale=inter.guild_locale),
                timestamp=inter.created_at
            ),
            ephemeral=True,
            view=ui.View(timeout=None).add_item(
                ConfigureSelectUser(
                    arg="rebute", bot=self.bot, interaction=inter,
                    placeholder_key="rooms.user_select.placeholder.rebute"
                )
            )
        )

    @ui.button(emoji="<:invoice:1114239254407696584>", custom_id="infoo", row=2)
    @in_voice
    @is_not_love_room
    async def info(self, _, inter: MessageInteraction) -> None:
        if check := await self.bot.databases.rooms.temp_room_values_with_channel(
                channel=inter.author.voice.channel.id, guild=inter.guild.id
        ):
            def_perms = inter.author.voice.channel.overwrites_for(inter.guild.default_role)
            embed = EmbedUI(
                title=_t.get("rooms.callback.title", locale=inter.guild_locale),
                description=_t.get(
                    "rooms.button.info.embed.description", locale=inter.guild_locale,
                    values=(
                        inter.author.voice.channel.mention,
                        inter.guild.get_member(check[2]).mention,
                        len(inter.author.voice.channel.members),
                        utils.format_dt(inter.author.voice.channel.created_at, style="f"),
                        SUCCESS_EMOJI if def_perms.view_channel else ERROR_EMOJI,
                        SUCCESS_EMOJI if def_perms.connect else ERROR_EMOJI,
                    ),
                )
            )
        else:
            embed = EmbedErrorUI(
                _t.get("rooms.error.not_in_room", locale=inter.guild_locale),
                member=inter.author
            )

        await inter.response.send_message(embed=embed, ephemeral=True)


class Rooms(CogUI):
    def __init__(self, bot: "ChisatoBot") -> None:
        self.check_message_loop = 0

        super().__init__(bot=bot)

    @loop(minutes=1)
    async def rooms_request_checking(self) -> None:
        if hasattr(self.bot.databases, 'rooms'):
            if rows := await self.bot.databases.rooms.room_req_checker(int(utils.utcnow().timestamp())):
                for row in rows:
                    await self.bot.databases.rooms.room_req_remove(guild=row[0], voice=row[1])

    @loop(seconds=30)
    async def rooms_exception(self) -> None:
        if hasattr(self.bot.databases, 'rooms'):
            for guild in self.bot.guilds:
                if voices := await self.bot.databases.rooms.rooms_voice_channels_fetch(guild=guild.id):
                    for vc in voices:
                        try:
                            if len((voice_obj := guild.get_channel(vc[1])).members) == 0:
                                await voice_obj.delete()
                                await self.bot.databases.rooms.remove_room(guild=guild.id, voice=vc[1])
                        except (Forbidden, NotFound, HTTPException, AttributeError):
                            await self.bot.databases.rooms.remove_room(guild=guild.id, voice=vc[1])

    @CogUI.listener()
    async def on_voice_state_update(self, member: Member, before: VoiceState, after: VoiceState) -> None:
        if not hasattr(self.bot.databases, 'rooms'):
            return None

        if before.channel and after.channel:
            if before.self_deaf or before.self_mute or before.self_video or before.self_stream:
                return
            elif after.self_deaf or after.self_mute or after.self_video or after.self_stream:
                return

        if check := await self.bot.databases.rooms.room_check_find(guild=member.guild.id):
            if (
                    before.channel
                    and before.channel.id != check[2]
                    and len(before.channel.members) == 0
                    and await self.bot.databases.rooms.temp_room_values_with_channel(
                guild=member.guild.id, channel=before.channel.id
            )
            ):
                await self.bot.databases.rooms.remove_room(guild=before.channel.guild.id, voice=before.channel.id)
                try:
                    await before.channel.delete()
                except NotFound:
                    pass

            if after.channel and after.channel.id == check[2]:
                overwrites = {
                    member: PermissionOverwrite(manage_channels=True)
                }

                if result := await self.bot.databases.rooms.settings_values(guild=member.guild.id, user=member.id):
                    private_channel = await member.guild.create_voice_channel(
                        name=result[2] if result[2] else f"{random.choice(emojis)} {member.name}",
                        category=after.channel.category, user_limit=result[3], overwrites=overwrites
                    )
                else:
                    private_channel = await member.guild.create_voice_channel(
                        name=f"{random.choice(emojis)} {member.name}", category=after.channel.category,
                        overwrites=overwrites, user_limit=2
                    )

                await self.bot.databases.rooms.create_room(guild=member.guild.id, voice=private_channel.id, user=member)

                try:
                    await member.move_to(private_channel)
                except errors.HTTPException:
                    pass

            if after.channel and after.channel.id == check[5]:
                if marry_data := await self.bot.databases.economy.get_marry_solo(
                        guild=member.guild, member=member
                ):
                    overwrites = {}
                    if user1 := member.guild.get_member(marry_data[2]):
                        overwrites[user1] = PermissionOverwrite(connect=True, view_channel=True)

                    if user2 := member.guild.get_member(marry_data[3]):
                        overwrites[user2] = PermissionOverwrite(connect=True, view_channel=True)

                    overwrites[member.guild.default_role] = PermissionOverwrite(connect=False, view_channel=False)
                    private_channel = await member.guild.create_voice_channel(
                        name=f"{user1} 💘 {user2}", category=after.channel.category,
                        overwrites=overwrites,
                        user_limit=2
                    )

                    await self.bot.databases.rooms.create_love_room(
                        guild=member.guild.id, voice=private_channel.id, user=member
                    )

                    try:
                        await member.move_to(private_channel)
                    except errors.HTTPException:
                        pass
                else:
                    await member.edit(voice_channel=None)

            if before.channel:
                if not (
                        result := await self.bot.databases.rooms.temp_room_values(
                            guild=member.guild.id, user=member.id
                        )
                ):
                    return

                if (
                        result[2] == member.id
                        and len(before.channel.members) != 0
                        and await self.bot.databases.rooms.temp_room_values_with_channel(
                    guild=member.guild.id, channel=before.channel.id
                )
                ):
                    user = random.choice(before.channel.members)

                    await self.bot.databases.rooms.room_update_leader(
                        guild=member.guild.id, voice=before.channel.id, new_leader=user.id
                    )
                    await before.channel.edit(overwrites={user: PermissionOverwrite(manage_channels=True)})

                    await before.channel.send(
                        embed=EmbedUI(
                            title=_t.get("rooms.callback.title", locale=member.guild.preferred_locale),
                            description=_t.get(
                                "rooms.on_voice.embed.description",
                                locale=member.guild.preferred_locale, values=(user.mention, user,)
                            )
                        )
                    )

    @loop(minutes=1)
    async def check_message(self) -> None:
        if self.check_message_loop > 7:
            return self.check_message.cancel()

        if hasattr(self.bot.databases, 'rooms'):
            if rows := await self.bot.databases.rooms.get_all_settings():
                for row in rows:
                    if guild_obj := self.bot.get_guild(row[0]):
                        try:
                            channel = await guild_obj.fetch_channel(row[4])
                            await channel.fetch_message(row[3])
                        except NotFound:
                            pass
                        except Forbidden:
                            pass
                        except HTTPException:
                            pass
                        else:
                            self.bot.add_view(
                                RoomButtons(bot=self.bot, guild=guild_obj), message_id=row[3]
                            )

        self.check_message_loop += 1

    def cog_unload(self) -> None:
        self.rooms_request_checking.cancel()
        self.rooms_exception.cancel()
        self.check_message.cancel()

    async def cog_load(self) -> None:
        await self.bot.wait_until_first_connect()

        self.check_message.start()
        self.rooms_request_checking.start()
        self.rooms_exception.start()


def setup(bot: ChisatoBot) -> None:
    bot.add_cog(Rooms(bot))
