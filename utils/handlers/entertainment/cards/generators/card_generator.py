from collections import defaultdict

from disnake import MessageInteraction, ApplicationCommandInteraction, File

from utils.basic import ChisatoBot, EmbedUI
from utils.basic.services.draw import DrawService
from utils.dataclasses import CardItem
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/entertainment/cards.py")

__all__ = (
    "Card",
)


class Card:
    @classmethod
    async def draw_with_interact(
            cls,
            interaction: MessageInteraction | ApplicationCommandInteraction,
            card: CardItem,
            values: tuple,
            embed_key: str,
            other_data: dict[str, any] = None
    ) -> None:
        bot: "ChisatoBot" = interaction.bot  # type: ignore
        _l = interaction.guild_locale
        await_embed_data = {
            "embed": EmbedUI(
                title=_t.get("cards.wait.title", locale=_l)
            ),
            "view": None,
            "attachments": []
        }

        if isinstance(interaction, ApplicationCommandInteraction):
            await interaction.edit_original_response(**await_embed_data)
        else:
            await interaction.response.edit_message(**await_embed_data)

        async with DrawService(bot.session) as ir:
            file = await ir.draw_image(
                "cards_solo",
                cardImageName=card.image_key,
                cardRarity=card.rarity
            )

        data = defaultdict()
        data["embed"] = EmbedUI(
            title=_t.get(card.name_key, _l),
            description=_t.get(embed_key, _l, values=values)
        ).set_image(file=file)

        if other_data:
            data.update(other_data)

        await interaction.edit_original_response(**data)

    @classmethod
    async def draw_trade_image(
            cls,
            cards: list[CardItem],
            *,
            bot: "ChisatoBot"
    ) -> File:
        async with (DrawService(bot.session) as ir):
            file = await ir.draw_image(
                "cards_trade_frame",
                firstCardImageName=cards[0].image_key,
                secondCardImageName=cards[1].image_key,
                firstCardRarity=cards[0].rarity,
                secondCardRarity=cards[1].rarity
            )

        return file
