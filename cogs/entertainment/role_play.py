from random import choice

from disnake import Member, ApplicationCommandInteraction, Localized, OptionChoice
from disnake.ext.commands import Param
from loguru import logger

from utils.basic import ChisatoBot
from utils.basic import CogUI, EmbedUI, EmbedErrorUI
from utils.exceptions import DecodeJsonError
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load(__file__)

SOLO_OPTIONS = [
    OptionChoice(
        name=Localized(
            "😃 Улыбнуться",
            data=_t.get("rp.option.action.choice.smile")
        ),
        value="smile"
    ),
    OptionChoice(
        name=Localized(
            "🛌 Заснуть",
            data=_t.get("rp.option.action.choice.sleep")
        ),
        value="sleep"
    ),
    OptionChoice(
        name=Localized(
            "😁 Обрадоваться",
            data=_t.get("rp.option.action.choice.happy")
        ),
        value="happy"
    ),
    OptionChoice(
        name=Localized(
            "🫠 Скучать",
            data=_t.get("rp.option.action.choice.bored")
        ),
        value="bored"
    ),
    OptionChoice(
        name=Localized(
            "🥹 Плакать",
            data=_t.get("rp.option.action.choice.cry")
        ),
        value="cry"
    ),
    OptionChoice(
        name=Localized(
            "🪩 Танцевать",
            data=_t.get("rp.option.action.choice.dance")
        ),
        value="dance"
    ),
    OptionChoice(
        name=Localized(
            "🫣 Испытать неудобство",
            data=_t.get("rp.option.action.choice.facepalm")
        ),
        value="facepalm"
    ),
    OptionChoice(
        name=Localized(
            "😊 Застесняться",
            data=_t.get("rp.option.action.choice.blush")
        ),
        value="blush"
    ),
    OptionChoice(
        name=Localized(
            "🤔 Думать",
            data=_t.get("rp.option.action.choice.think")
        ),
        value="think"
    )
]

DUO_OPTIONS = [
    OptionChoice(
        name=Localized(
            "🩸 Укусить",
            data=_t.get("rp.option.action.choice.bite")
        ),
        value="bite"
    ),
    OptionChoice(
        name=Localized(
            "🍏 Покормить",
            data=_t.get("rp.option.action.choice.feed")
        ),
        value="feed"
    ),
    OptionChoice(
        name=Localized(
            "🫳 Подержать за руку",
            data=_t.get("rp.option.action.choice.handhold")
        ),
        value="handhold"
    ),
    OptionChoice(
        name=Localized(
            "🫸 Дать пять",
            data=_t.get("rp.option.action.choice.highfive")
        ),
        value="highfive"
    ),
    OptionChoice(
        name=Localized(
            "👊 Ударить",
            data=_t.get("rp.option.action.choice.kick")
        ),
        value="kick"
    ),
    OptionChoice(
        name=Localized(
            "🤗 Обнять",
            data=_t.get("rp.option.action.choice.hug")
        ),
        value="hug"
    ),
    OptionChoice(
        name=Localized(
            "💋 Поцеловать",
            data=_t.get("rp.option.action.choice.kiss")
        ),
        value="kiss"
    ),
    OptionChoice(
        name=Localized(
            "🫳 Погладить",
            data=_t.get("rp.option.action.choice.pat")
        ),
        value="pat"
    ),
    OptionChoice(
        name=Localized(
            "🔫 Выстрелить",
            data=_t.get("rp.option.action.choice.shoot")
        ),
        value="shoot"
    ),
    OptionChoice(
        name=Localized(
            "😊 Щекотать",
            data=_t.get("rp.option.action.choice.tickle")
        ),
        value="tickle"
    ),
    OptionChoice(
        name=Localized(
            "🫳 Потрогать",
            data=_t.get("rp.option.action.choice.touch")
        ),
        value="touch"
    ),
    OptionChoice(
        name=Localized(
            "👋 Помахать",
            data=_t.get("rp.option.action.choice.wave")
        ),
        value="wave"
    ),
    OptionChoice(
        name=Localized(
            "🫵 Бросить",
            data=_t.get("rp.option.action.choice.yeet")
        ),
        value="yeet"
    ),
    OptionChoice(
        name=Localized(
            "😉 Подмигнуть",
            data=_t.get("rp.option.action.choice.wink")
        ),
        value="wink"
    )
]


class RolePlay(CogUI):

    @staticmethod
    async def get_url(name: str):
        try:
            async with ChisatoBot.from_cache().session.get(
                    f"https://nekos.best/api/v2/{name}"
            ) as response:
                return (await response.json())["results"][0]["url"]
        except Exception as e:
            logger.warning(f"Nekos Best Api threw an exception {type(e).__name__}: {e}")
            raise DecodeJsonError("Neko services returned an error")

    def checks(self, interaction: ApplicationCommandInteraction, member: Member) -> EmbedErrorUI:
        if interaction.author.id == member.id:
            return EmbedErrorUI(
                description=_t.get(
                    key="rp.embed.error.cannot_specify_self", locale=interaction.guild_locale
                ),
                member=interaction.author
            )

        if member.id == self.bot.user.id:
            return EmbedErrorUI(
                description=_t.get(
                    key="rp.embed.error.cannot_specify_bot", locale=interaction.guild_locale
                ),
                member=interaction.author
            )

    @CogUI.slash_command(
        name="roleplay",
        dm_permission=False,
        description=Localized(
            "\uD83C\uDFAD Ролевые действия!",
            data=_t.get("rp.command.description")
        )
    )
    async def _rp(self, interaction: ApplicationCommandInteraction) -> ...:
        ...

    @_rp.sub_command(
        name="duo",
        description=Localized(
            "\uD83C\uDFAD Ролевые действия: Вместе!",
            data=_t.get("rp.command.duo.description")
        )
    )
    async def duo(
            self,
            interaction: ApplicationCommandInteraction,
            member: Member = Param(
                name=Localized("участник", data=_t.get("rp.option.member.name")),
                description=Localized(
                    "- выбери с кем хочешь совершить действие",
                    data=_t.get("rp.option.member.description")
                )
            ),
            action: str = Param(
                name=Localized(
                    "действие",
                    data=_t.get("rp.option.action.name")
                ),
                description=Localized(
                    "- выбери действие, которое хочешь совершить",
                    data=_t.get("rp.option.action.description")
                ),
                choices=DUO_OPTIONS
            )
    ) -> None:
        if embed := self.checks(interaction, member):
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await interaction.response.send_message(
            embed=EmbedUI(
                description=_t.get(
                    key=f"rp.action.{action}.description",
                    locale=interaction.guild_locale,
                    values=(
                        interaction.author.mention,
                        member.mention
                    )
                )
            ).set_image(
                url=await self.get_url(action)
            ).set_footer(
                text=choice(_t.get(key=f"rp.action.{action}.quote", locale=interaction.guild_locale))
            )
        )

    @_rp.sub_command(
        name="solo",
        description=Localized(
            "\uD83C\uDFAD Ролевые действия: Одиночные!",
            data=_t.get("rp.command.solo.description")
        )
    )
    async def solo(
            self,
            interaction: ApplicationCommandInteraction,
            action: str = Param(
                name=Localized(
                    "действие",
                    data=_t.get("rp.option.action.name")
                ),
                description=Localized(
                    "- выбери действие, которое с кем-то совершить",
                    data=_t.get("rp.option.action_multiple.description")
                ),
                choices=SOLO_OPTIONS
            )
    ) -> None:
        await interaction.response.send_message(
            embed=EmbedUI(
                description=_t.get(
                    key=f"rp.action.{action}.description",
                    locale=interaction.guild_locale,
                    values=(
                        interaction.author.mention,
                    )
                )
            ).set_image(
                url=await self.get_url(action)
            ).set_footer(
                text=choice(_t.get(key=f"rp.action.{action}.quote", locale=interaction.guild_locale))
            )
        )

    @_rp.sub_command(
        name="custom",
        description=Localized(
            "\uD83C\uDFAD Ролевые действия: Свое действие!",
            data=_t.get("rp.command.custom.description")
        )
    )
    async def custom(
            self,
            interaction: ApplicationCommandInteraction,
            action: str = Param(
                name=Localized(
                    "действие",
                    data=_t.get("rp.option.action.name")
                ),
                description=Localized(
                    "- напиши действие (попил чаю и т.п.)",
                    data=_t.get("rp.option.action_custom.description")
                ),
                max_length=2048
            ),
            image: str = Param(
                name=Localized(
                    "действие-на-основе",
                    data=_t.get("rp.option.action_with.name")
                ),
                description=Localized(
                    "- выбери действие на основе, которого ты хочешь совершить",
                    data=_t.get("rp.option.action_with.description")
                ),
                choices=DUO_OPTIONS + SOLO_OPTIONS
            ),
            quote: str = Param(
                name=Localized(
                    "цитата",
                    data=_t.get("rp.option.quote.name")
                ),
                description=Localized(
                    "- напиши цитату, которую хочешь использовать",
                    data=_t.get("- напиши цитату, которую хочешь использовать")
                ),
                max_length=1028
            )
    ) -> None:
        await interaction.response.send_message(
            embed=EmbedUI(
                description=f"{interaction.author.mention}, {action}"
            ).set_image(
                url=await self.get_url(image)
            ).set_footer(
                text=quote
            )
        )


def setup(bot: "ChisatoBot") -> None:
    return bot.add_cog(RolePlay(bot))
