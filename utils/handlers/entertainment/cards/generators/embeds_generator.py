from collections import defaultdict

from asyncpg import Record
from disnake import MessageInteraction, ApplicationCommandInteraction

from utils.basic import EmbedUI
from utils.handlers.entertainment.cards.consts import STAR
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/entertainment/cards.py")

__all__ = (
    "Embeds",
)


class Embeds:
    @classmethod
    async def generate_with_interact(
            cls,
            interaction: MessageInteraction | ApplicationCommandInteraction,
            cards: list[Record],
            example_embed: EmbedUI
    ) -> tuple[list[EmbedUI], defaultdict[any, defaultdict]]:
        bot: "ChisatoBot" = interaction.bot  # type: ignore
        embeds = []
        text = ""
        _l = interaction.guild_locale
        from_page = defaultdict(defaultdict)

        dict_rares = _t.get("cards.rares", locale=_l)

        for i, card in enumerate(cards, 1):
            card = bot.databases.cards.create_item(card)

            text += (
                f"{i}. **{_t.get(card.name_key, _l)}** "
                f"| **{dict_rares[str(card.rarity)]}** "
                f"| {STAR * card.stars_count} (`{card.uid}`)\n"
            )

            from_page[i // 15 if i % 15 == 0 else i // 15 + 1][i] = card

            if i % 15 == 0 or i == len(cards):
                embed = example_embed.copy()
                embed.description = text

                embeds.append(embed)
                text = ""

        return embeds, from_page
