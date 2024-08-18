from __future__ import annotations

from typing import TYPE_CHECKING

from disnake import Guild, MessageInteraction, ApplicationCommandInteraction

from utils.dataclasses import Pet
from utils.i18n import ChisatoLocalStore

if TYPE_CHECKING:
    from utils.basic import ChisatoBot

_t = ChisatoLocalStore.load("./cogs/economy/pets.py")


async def pet_stats_info(
        bot: ChisatoBot,
        pet_info: Pet,
        guild: Guild = None,
        old_pet_info: Pet | None = None,
        interaction: MessageInteraction | ApplicationCommandInteraction = None
) -> str:
    if guild:
        loc = guild.preferred_locale
    else:
        loc = interaction.guild_locale
    max_stats_pet_info: Pet = await bot.databases.pets.pet_get_with_name(pet_info.name)

    str_stamina_remaining = _t.get("pets.info.stamina.remaining", locale=loc)
    pet_stamina = "`MAX`" if max_stats_pet_info.stamina == pet_info.stamina else \
        f"`{old_pet_info.stamina} -> {pet_info.stamina}`" if old_pet_info else f"`{pet_info.stamina}`"

    str_spiritual_energy = _t.get("pets.info.spiritual_energy.label", locale=loc)
    pet_spiritual_energy = "`MAX`" if max_stats_pet_info.mana == pet_info.mana else \
        f"`{old_pet_info.mana} -> {pet_info.mana}`" if old_pet_info else f"`{pet_info.mana}`"

    str_level = _t.get("pets.info.level.label", locale=loc)
    pet_level = pet_info.level if pet_info.level < 20 else "MAX"
    pet_level_correlation = f"({pet_info.exp_now}/{pet_info.exp_need})" if pet_info.level < 20 else ""

    return (
        f"{str_stamina_remaining} {pet_stamina}\n"
        f"{str_spiritual_energy} {pet_spiritual_energy}\n"
        f"{str_level} `{pet_level}lvl {pet_level_correlation}`\n"
    )
