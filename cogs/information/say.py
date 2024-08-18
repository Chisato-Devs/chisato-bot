import json

from disnake import Localized, ui, MessageInteraction, TextInputStyle, Embed, errors, \
    ModalInteraction, MessageCommandInteraction, ApplicationCommandInteraction, Forbidden, HTTPException

from utils.basic import CogUI, ChisatoBot, View, EmbedUI, EmbedErrorUI, CommandsPermission
from utils.consts import SUCCESS_EMOJI, ERROR_EMOJI
from utils.enviroment import env
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load(__file__)
test_text = """```json
{
  "content": "Hello",
  "embeds": [
    {
      "title": "Hello",
      "description": "Hello",
      "author": {
        "name": "Hello"
      },
      "color": 5814783
    },
    {
      "title": "Hello",
      "description": "Hello",
      "author": {
        "name": "Hello"
      },
      "color": 5814783
    }
  ]
}
```"""


class EmbedTrueFalse(View):
    def __init__(
            self, bot: ChisatoBot,
            interaction: MessageInteraction | ApplicationCommandInteraction
    ) -> None:
        self.bot = bot
        self._interaction = interaction

        super().__init__(timeout=None, store=_t, interaction=interaction)

    @ui.button(label="say.yes", emoji=SUCCESS_EMOJI)
    async def embed_yes(self, _, interaction: MessageInteraction) -> None:
        await interaction.response.send_modal(
            ModalReply(bot=self.bot, modal_type=True, interaction=interaction)
        )

    @ui.button(label="say.no", emoji=ERROR_EMOJI)
    async def embed_no(self, _, interaction: MessageInteraction) -> None:
        await interaction.response.send_modal(
            ModalReply(bot=self.bot, modal_type=False, interaction=interaction)
        )


class EmbedAdvancedCreateButtons(View):
    def __init__(
            self, bot: ChisatoBot,
            interaction: MessageInteraction | ApplicationCommandInteraction
    ) -> None:
        self.bot = bot
        self._interaction = interaction
        super().__init__(timeout=None, store=_t, interaction=interaction)

    @ui.button(label="say.button.label.inject_json", emoji="<:Edit:1116358712794296460>")
    async def button_start(self, _, interaction: MessageInteraction) -> None:
        await interaction.response.send_modal(ModalAdvancedInput(bot=self.bot, interaction=interaction))

    @ui.button(
        label="say.button.label.constructor_json", url="https://discohook.org", emoji="<:Link:1142817574644633742>"
    )
    async def constructor(self, *args, **kwargs) -> ...: ...


class ModalAdvancedInput(ui.Modal):
    def __init__(self, bot: "ChisatoBot", interaction: MessageInteraction) -> None:
        self.bot = bot
        self._interaction = interaction

        super().__init__(
            title=_t.get(
                "say.modal.advanced_input.placeholder", locale=self._interaction.guild_locale
            ),
            components=[
                ui.TextInput(
                    label=_t.get(
                        "say.modal.advanced_input.title", locale=self._interaction.guild_locale
                    ),
                    placeholder='{}',
                    custom_id='json_input',
                    style=TextInputStyle.paragraph,
                ),
            ]
        )

    async def callback(self, interaction: ModalInteraction):
        await interaction.response.defer(ephemeral=True)
        inputted_text = interaction.text_values["json_input"]

        try:
            inputted_text_dict = json.loads(inputted_text)
        except Exception as e:
            _ = e
            return await interaction.followup.send(
                embed=EmbedErrorUI(
                    description=_t.get(
                        "say.modal.callback.json_error_embed.description", locale=interaction.guild_locale
                    ),
                    member=interaction.author
                ),
                ephemeral=True
            )

        try:
            webhook = await interaction.channel.create_webhook(name=interaction.author.display_name)
        except errors.HTTPException as e:
            if "Maximum number of webhooks reached (15)" in str(e):
                return await interaction.followup.send(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "say.modal.callback.webhook_limit_embed.description", locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )
            else:
                return await interaction.followup.send(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "say.modal.callback.json_error_embed.description", locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )

        for embed_data in inputted_text_dict["embeds"]:
            embed = Embed.from_dict(embed_data)
            try:
                await webhook.send(embed=embed, avatar_url=interaction.author.display_avatar.url)
            except Exception as e:
                _ = e
                await webhook.delete()
                return await interaction.followup.send(
                    embed=EmbedErrorUI(
                        description=_t.get(
                            "say.modal.callback.json_error_embed.description", locale=interaction.guild_locale
                        ),
                        member=interaction.author
                    ),
                    ephemeral=True
                )

        await webhook.delete()
        await interaction.followup.send(
            _t.get("say.modal.callback.success", locale=interaction.guild_locale),
            ephemeral=True
        )


class ModalReply(ui.Modal):
    def __init__(
            self, bot: ChisatoBot, modal_type: bool,
            interaction: ApplicationCommandInteraction | MessageInteraction
    ) -> None:
        self.bot = bot
        self._type = modal_type
        self._interaction = interaction

        match modal_type:
            case True:
                components = [
                    ui.TextInput(
                        label=_t.get("say.modal.reply.yes.option.title", locale=self._interaction.guild_locale),
                        placeholder='Text',
                        custom_id='title_input',
                        style=TextInputStyle.single_line,
                        max_length=256,
                        required=False
                    ),

                    ui.TextInput(
                        label=_t.get("say.modal.reply.yes.option.description", locale=self._interaction.guild_locale),
                        placeholder='Text',
                        custom_id='description_input',
                        style=TextInputStyle.paragraph,
                        max_length=4000,
                        required=False
                    ),
                    ui.TextInput(
                        label=_t.get("say.modal.reply.yes.option.color", locale=self._interaction.guild_locale),
                        placeholder='#ffffff',
                        custom_id='color_input',
                        style=TextInputStyle.single_line,
                        max_length=7,
                        required=False
                    ),

                    ui.TextInput(
                        label=_t.get("say.modal.reply.yes.option.image", locale=self._interaction.guild_locale),
                        placeholder='https://i.imgur.com/QArOcZb.jpeg',
                        custom_id='embed_image_input',
                        style=TextInputStyle.single_line,
                        max_length=512,
                        required=False
                    ),

                    ui.TextInput(
                        label=_t.get("say.modal.reply.yes.option.footer", locale=self._interaction.guild_locale),
                        placeholder='Text',
                        custom_id='footer_input',
                        style=TextInputStyle.single_line,
                        max_length=2048,
                        required=False
                    ),
                ]
                super().__init__(
                    title=_t.get("say.modal.reply.yes.title", locale=self._interaction.guild_locale),
                    components=components
                )

            case False:
                super().__init__(
                    title=_t.get("say.modal.reply.no.title", locale=self._interaction.guild_locale),
                    components=[
                        ui.TextInput(
                            label=_t.get("say.modal.reply.no.label", locale=self._interaction.guild_locale),
                            placeholder=_t.get("say.modal.reply.no.placeholder", locale=self._interaction.guild_locale),
                            custom_id='text_input',
                            style=TextInputStyle.paragraph,
                            max_length=4000,
                        ),
                    ]
                )

    async def callback(self, interaction: ModalInteraction):
        match self._type:
            case True:
                await interaction.response.defer(ephemeral=True)
                inputted_title = interaction.text_values["title_input"]
                inputted_description = interaction.text_values["description_input"]
                inputted_color = interaction.text_values["color_input"]
                inputted_image = interaction.text_values["embed_image_input"]
                inputted_footer = interaction.text_values["footer_input"]

                try:
                    embed = Embed(
                        color=int(inputted_color.replace('#', '0x'), 16) if inputted_color else env.COLOR
                    )
                    embed.title = inputted_title if inputted_title else ""
                    embed.description = inputted_description if inputted_description else "ㅤ"

                    if inputted_image:
                        embed.set_image(url=inputted_image)

                    embed.set_footer(text=inputted_footer)

                    help_webhook = await interaction.channel.create_webhook(name=interaction.author.display_name)
                    await help_webhook.send(embed=embed, avatar_url=interaction.author.display_avatar.url)
                    await help_webhook.delete()

                    await interaction.followup.send(
                        _t.get("say.modal.callback.success", locale=self._interaction.guild_locale)
                    )

                except Forbidden:
                    return await interaction.followup.send(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "say.modal.callback.missing_permissions.description", locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ),
                        ephemeral=True
                    )

                except HTTPException as e:
                    if "Maximum number of webhooks reached (15)" in str(e):
                        return await interaction.followup.send(
                            embed=EmbedErrorUI(
                                description=_t.get(
                                    "say.modal.callback.webhook_limit_embed.description",
                                    locale=interaction.guild_locale
                                ),
                                member=interaction.author
                            ),
                            ephemeral=True
                        )
                    else:
                        return await interaction.followup.send(
                            embed=EmbedErrorUI(
                                description=_t.get(
                                    "say.modal.reply.no.embed.error.invalid_image_link",
                                    locale=self._interaction.guild_locale
                                ),
                                member=interaction.author
                            )
                        )
                except ValueError:
                    return await interaction.followup.send(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "say.modal.reply.no.embed.error.invalid_color",
                                locale=self._interaction.guild_locale
                            ),
                            member=interaction.author
                        ),
                        ephemeral=True
                    )

            case False:
                await interaction.response.defer(ephemeral=True)

                inputted_text = interaction.text_values["text_input"]
                try:
                    whelp_webhook = await interaction.channel.create_webhook(name=interaction.author.display_name)
                except Forbidden:
                    return await interaction.followup.send(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "say.modal.callback.missing_permissions.description", locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ),
                        ephemeral=True
                    )

                await whelp_webhook.send(inputted_text, avatar_url=interaction.author.display_avatar.url)
                await whelp_webhook.delete()

                await interaction.followup.send(
                    _t.get("say.modal.callback.success", locale=self._interaction.guild_locale)
                )


class Say(CogUI):

    @CogUI.slash_command(name="say")
    async def __say(self, interaction: ApplicationCommandInteraction) -> ...: ...

    @__say.sub_command(
        name="default",
        description=Localized(
            "📢 Сказать от имени бота: отправка сообщения для обычных пользователей!",
            data=_t.get("say.command.default.description")
        )
    )
    @CommandsPermission.decorator(view_audit_log=True)
    async def default(self, interaction: MessageCommandInteraction) -> None:
        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("say.embed.create_embed.title", locale=interaction.guild_locale),
                description=_t.get("say.embed.create_embed.description", locale=interaction.guild_locale)
            ),
            view=EmbedTrueFalse(bot=self.bot, interaction=interaction),
            ephemeral=True
        )

    @__say.sub_command(
        name="advanced",
        description=Localized(
            "📢 Сказать от имени бота: отправка сообщения для продвинутых пользователей!",
            data=_t.get("say.command.advanced.description")
        )
    )
    @CommandsPermission.decorator(view_audit_log=True)
    async def advanced(self, interaction: MessageCommandInteraction) -> None:
        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("say.embed.create_message.title", locale=interaction.guild_locale),
                description=_t.get(
                    "say.embed.create_message.advanced.description", locale=interaction.guild_locale
                ) + "\n" + test_text
            ),
            view=EmbedAdvancedCreateButtons(bot=self.bot, interaction=interaction),
            ephemeral=True
        )


def setup(bot: "ChisatoBot") -> None:
    bot.add_cog(Say(bot))
