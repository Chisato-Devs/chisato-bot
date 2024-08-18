import asyncio
import random
from typing import Union

from disnake import (
    Localized,
    Member,
    ui,
    AppCommandInteraction,
    ApplicationCommandInteraction,
    TextChannel,
    VoiceChannel,
    StageChannel,
    Thread,
    InteractionResponded
)
from disnake.ext import tasks
from disnake.ext.commands import (
    slash_command,
    cooldown,
    Param,
    BucketType
)
from loguru import logger

from utils.basic import (
    ChisatoBot,
    CogUI,
    IntFormatter,
    EmbedErrorUI,
    EmbedUI
)
from utils.consts import (
    REGULAR_CURRENCY
)
from utils.dataclasses import Pet
from utils.exceptions import (
    PetReachedMaxLvl,
    PetLowStat,
    PetStatsZero,
    DoesntHavePet
)
from utils.handlers.economy import (
    check_is_on,
    check_in_fight,
    pet_stats_info,
    check_in_game
)
from utils.handlers.economy.pets.handlers import OwnerAlertManager
from utils.handlers.economy.pets.views import PetFightView
from utils.i18n import ChisatoLocalStore

GuildMessageable = Union[TextChannel, Thread, VoiceChannel, StageChannel]
_t = ChisatoLocalStore.load(__file__)


class Pets(CogUI):
    def __init__(self, bot: "ChisatoBot") -> None:
        self.owner_alert = OwnerAlertManager(bot)
        super().__init__(bot)

    @slash_command(dm_permission=False, name="pet")
    @check_is_on()
    @check_in_game()
    @check_in_fight()
    async def _pet(self, interaction: AppCommandInteraction) -> None:
        pass

    @_pet.sub_command(
        name='play',
        description=Localized(
            "🐬 Питомцы: поиграть с питомцем! Повышение маны и стамины! (2 раза в час)",
            data=_t.get("pets.command.play.description")
        )
    )
    @cooldown(2, 3600, type=BucketType.member)
    async def p(
            self, interaction: ApplicationCommandInteraction
    ) -> None:
        try:
            old_pet_info: Pet = await self.bot.databases.pets.pet_get(
                guild=interaction.guild.id,
                member=interaction.author.id
            )
        except DoesntHavePet as e:
            self.f.reset_cooldown(interaction)
            raise e

        if random.randint(1, 3) != 3:
            try:
                await self.bot.databases.pets.pet_stats_update(
                    member=interaction.author.id,
                    guild=interaction.guild.id,
                    stamina=random.randint(5, 7),
                    mana=random.randint(1, 5),
                    up=True,
                    up_lvl=True,
                    pet_type=old_pet_info.name
                )
            except PetReachedMaxLvl:
                await self.owner_alert.pet_owner_alert_reached_max_lvl(
                    member=interaction.author, guild=interaction.guild, channel=interaction.channel  # type: ignore
                )
            except Exception as e:
                _ = e

            pet_info = await self.bot.databases.pets.pet_get(guild=interaction.guild.id, member=interaction.author.id)

            await interaction.response.send_message(
                embed=EmbedUI(
                    title=_t.get("pets.game.title", locale=interaction.guild_locale),
                    description=_t.get(
                        "pets.game.embed.description",
                        locale=interaction.guild_locale,
                        values=(
                            interaction.author.mention,
                            await pet_stats_info(
                                pet_info=pet_info, old_pet_info=old_pet_info,
                                interaction=interaction, bot=self.bot
                            ),
                        ),
                    )
                )
            )
        else:
            try:
                await self.bot.databases.pets.pet_stats_update(
                    member=interaction.author.id,
                    guild=interaction.guild.id,
                    stamina=random.randint(1, 7),
                    mana=random.randint(1, 5),
                    up=False,
                    up_lvl=False,
                    pet_type=old_pet_info.name
                )
            except PetLowStat:
                await self.owner_alert.pet_owner_alert_low_stat(
                    member=interaction.author, guild=interaction.guild, channel=interaction.channel  # type: ignore
                )
            except PetReachedMaxLvl:
                await self.owner_alert.pet_owner_alert_reached_max_lvl(
                    member=interaction.author, guild=interaction.guild, channel=interaction.channel  # type: ignore
                )
            except PetStatsZero:
                await self.owner_alert.pet_owner_alert_died(
                    member=interaction.author, guild=interaction.guild, channel=interaction.channel  # type: ignore
                )
            except Exception as e:
                _ = e

            pet_info: Pet = await self.bot.databases.pets.pet_get(
                guild=interaction.guild.id, member=interaction.author.id
            )

            await interaction.response.send_message(embed=EmbedUI(
                title=_t.get("pets.droplet.title", locale=interaction.guild_locale),
                description=_t.get(
                    "pets.droplet.embed.description",
                    locale=interaction.guild_locale,
                    values=(
                        interaction.author.display_name,
                        await pet_stats_info(
                            pet_info=pet_info, old_pet_info=old_pet_info,
                            interaction=interaction, bot=self.bot
                        ),
                    ),
                )
            ))

    @_pet.sub_command(
        name='fight', description=Localized(
            "🐬 Питомцы: вызвать на поединок другое животное!",
            data=_t.get("pets.command.fight.description")
        )
    )
    async def pets_fight(
            self,
            interaction: AppCommandInteraction,
            member: Member = Param(
                name=Localized("участник", data=_t.get("pets.command.option.member.name")),
                description=Localized(
                    "- укажи участника чье животное ты хочешь сразить",
                    data=_t.get("pets.command.duel.option.member.description")
                )
            ),
            rate: int = Param(
                name=Localized("ставка", data=_t.get("pets.command.option.rate.name")),
                description=Localized(
                    "- укажи ставку на поединок!",
                    data=_t.get("pets.command.duel.option.rate.description")
                ),
                min_value=1,
                max_value=100000
            )
    ) -> None:
        if member.bot:
            try:
                return await interaction.response.send_message(embed=EmbedErrorUI(
                    description=_t.get("pets.duel.error.not_bot", locale=interaction.guild_locale),
                    member=interaction.author
                ))
            except InteractionResponded:
                pass

        elif member.id == interaction.author.id:
            try:
                return await interaction.response.send_message(embed=EmbedErrorUI(
                    description=_t.get("pets.duel.error.not_you", locale=interaction.guild_locale),
                    member=interaction.author
                ))
            except InteractionResponded:
                pass

        async def check_money_author() -> None:
            if not await self.bot.databases.economy.money_check(
                    guild=interaction.guild.id,
                    check_member=interaction.author.id,
                    check_rate=rate
            ):
                try:
                    return await interaction.response.send_message(embed=EmbedErrorUI(
                        description=_t.get("pets.duel.error.not_enough_money", locale=interaction.guild_locale),
                        member=interaction.author
                    ))
                except InteractionResponded:
                    pass

        async def check_money_member() -> None:
            if not await self.bot.databases.economy.money_check(
                    guild=interaction.guild.id,
                    check_member=member.id,
                    check_rate=rate
            ):
                try:
                    return await interaction.response.send_message(embed=EmbedErrorUI(
                        description=_t.get("pets.duel.error.not_enough_money_member", locale=interaction.guild_locale),
                        member=interaction.author
                    ))
                except InteractionResponded:
                    pass

        async def get_member_pet_info() -> Pet | None:
            try:
                return await self.bot.databases.pets.pet_get(guild=interaction.guild.id, member=member.id)
            except DoesntHavePet:
                try:
                    await interaction.response.send_message(
                        embed=EmbedErrorUI(
                            description=_t.get(
                                "pets.duel.error.member_doesnt_have_pet",
                                locale=interaction.guild_locale
                            ),
                            member=interaction.author
                        ),
                        ephemeral=True
                    )
                except InteractionResponded:
                    pass

        async def send_battle_embed() -> None:
            pet_titles = _t.get("pets.dict.titles", locale=interaction.guild.preferred_locale)
            pet_info: Pet = await self.bot.databases.pets.pet_get(guild=interaction.guild.id,
                                                                  member=interaction.author.id)

            if pet := await get_member_pet_info():
                await self.bot.databases.pets.in_fight_switch(
                    guild=interaction.guild.id, member=interaction.author.id, switch=True
                )

                button_label = _t.get(
                    "pets.bet_amount",
                    locale=interaction.guild.preferred_locale,
                )
                await interaction.response.send_message(
                    embed=EmbedUI(
                        title=_t.get("pets.battle.title", locale=interaction.guild.preferred_locale),
                        description=_t.get(
                            "pets.duel.throw.to_member.description",
                            locale=interaction.guild.preferred_locale,
                            values=(
                                interaction.author.mention, member.mention,
                                member.mention, pet_titles[pet.name],
                                interaction.author.mention, pet_titles[pet_info.name]
                            )
                        )
                    ),
                    view=PetFightView(
                        bot=self.bot,
                        author=member,
                        original_author=interaction.author,
                        inter=interaction,
                        rate=rate
                    ).add_item(
                        ui.Button(
                            label=f"{button_label} {IntFormatter(rate).format_number()}",
                            disabled=True,
                            emoji=REGULAR_CURRENCY,
                            custom_id="stake_amount"
                        )
                    )
                )

        await asyncio.gather(
            check_money_author(),
            check_money_member(),
            get_member_pet_info(),
            send_battle_embed()
        )

    @_pet.sub_command(
        name='cattery', description=Localized(
            "🐬 Питомцы: отдать питомца в питомник (без возможности возврата)",
            data=_t.get("pets.command.cattery.description")
        )
    )
    async def k(self, interaction: ApplicationCommandInteraction) -> None:
        await self.bot.databases.pets.pet_remove(guild=interaction.guild.id, member=interaction.author.id)

        await interaction.response.send_message(embed=EmbedUI(
            title=_t.get("pets.cattery.title", locale=interaction.guild_locale),
            description=_t.get(
                "pets.cattery.embed.description", locale=interaction.guild_locale,
                values=(interaction.author.mention,)
            )
        ))

    async def _up_logic(self, interaction: ApplicationCommandInteraction, **kwargs) -> tuple[Pet, Pet]:
        old_pet_info: Pet = await self.bot.databases.pets.pet_get(
            guild=interaction.guild.id,
            member=interaction.author.id
        )

        try:
            await self.bot.databases.pets.pet_stats_update(**kwargs, pet_type=old_pet_info.name)
        except PetReachedMaxLvl:
            await PetsTasks(bot=interaction.bot).pet_owner_alert_reached_max_lvl(  # type: ignore
                member=interaction.author, guild=interaction.guild, channel=interaction.channel  # type: ignore
            )
        except Exception as e:
            logger.warning(f"{e.__class__.__name__}: {e}")

        pet_info: Pet = await self.bot.databases.pets.pet_get(guild=interaction.guild.id, member=interaction.author.id)

        return old_pet_info, pet_info

    @_pet.sub_command(
        name='walk', description=Localized(
            "🐬 Питомцы: погулять с питомцем! Повышение маны! (1 раз в час)",
            data=_t.get("pets.command.walk.description")
        )
    )
    @cooldown(1, 3600, type=BucketType.member)
    async def w(
            self,
            interaction: ApplicationCommandInteraction
    ) -> None:
        try:
            old_pet_info, pet_info = await self._up_logic(
                interaction,
                member=interaction.author.id,
                guild=interaction.guild.id,
                mana=random.randint(5, 10),
                up=True,
                up_lvl=True
            )
        except DoesntHavePet as e:
            self.w.reset_cooldown(interaction)
            raise e

        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("pets.walk.title", locale=interaction.guild_locale),
                description=_t.get(
                    "pets.walk.embed.description",
                    locale=interaction.guild_locale,
                    values=(
                        interaction.author.mention, await pet_stats_info(
                            pet_info=pet_info, old_pet_info=old_pet_info,
                            interaction=interaction, bot=self.bot
                        )
                    )
                )
            )
        )

    @_pet.sub_command(
        name='feed',
        description=Localized(
            "🐬 Питомцы: покормить питомца! Повышение выносливости! (1 раз в полчаса)",
            data=_t.get("pets.command.feed.description")
        )
    )
    @cooldown(1, 1800, type=BucketType.member)
    async def f(
            self, interaction: ApplicationCommandInteraction
    ) -> None:
        try:
            old_pet_info, pet_info = await self._up_logic(
                interaction,
                member=interaction.author.id,
                guild=interaction.guild.id,
                stamina=random.randint(5, 10),
                up=True,
                up_lvl=True
            )
        except DoesntHavePet as e:
            self.f.reset_cooldown(interaction)
            raise e

        await interaction.response.send_message(
            embed=EmbedUI(
                title=_t.get("pets.feed.title", locale=interaction.guild_locale),
                description=_t.get(
                    "pets.feed.embed.description",
                    locale=interaction.guild_locale,
                    values=(
                        interaction.author.mention, await pet_stats_info(
                            pet_info=pet_info, old_pet_info=old_pet_info,
                            interaction=interaction, bot=self.bot
                        )
                    ),
                )
            )
        )


class PetsTasks(CogUI):
    def __init__(self, bot: "ChisatoBot") -> None:
        self.owner_alert = OwnerAlertManager(bot)
        super().__init__(bot)

    async def cog_load(self) -> None:
        await self.bot.wait_until_first_connect()

        self.pet_relaxing.start()
        self.pet_mana_reduction.start()

    def cog_unload(self) -> None:
        self.pet_relaxing.cancel()
        self.pet_mana_reduction.cancel()

    async def tasks_backend(
            self,
            pets: list[Pet],
            **pet_args
    ) -> None:
        for pet in pets:
            member = None
            if guild := self.bot.get_guild(pet.guild_id):
                member = guild.get_member(pet.owner_id)

            try:
                await self.bot.databases.pets.pet_stats_update(
                    member=pet.owner_id,
                    guild=pet.guild_id,
                    pet_type=pet.name,
                    up_lvl=False,
                    **pet_args
                )

            except PetLowStat:
                if member and guild:
                    await self.owner_alert.pet_owner_alert_low_stat(
                        member=member,
                        guild=guild
                    )

            except PetReachedMaxLvl:
                if member and guild:
                    await self.owner_alert.pet_owner_alert_reached_max_lvl(
                        member=member,
                        guild=guild
                    )

            except PetStatsZero:
                if member and guild:
                    await self.owner_alert.pet_owner_alert_died(
                        member=member,
                        guild=guild
                    )

            except Exception as e:
                _ = e

    @tasks.loop(seconds=20)
    async def pet_relaxing(self) -> None:
        if not hasattr(self.bot.databases, 'pets'):
            return

        if not (pets := await self.bot.databases.pets.select_all_pets()):
            return

        asyncio.create_task(self.tasks_backend(
            pets=pets,
            stamina=random.randint(1, 5),
            up=True
        ))

    @tasks.loop(hours=3)
    async def pet_mana_reduction(self) -> None:
        if not hasattr(self.bot.databases, 'pets'):
            return

        if not (pets := await self.bot.databases.pets.select_all_pets()):
            return

        asyncio.create_task(self.tasks_backend(
            pets=pets,
            mana=random.randint(1, 3),
            up=False
        ))


def setup(bot: ChisatoBot) -> None:
    bot.add_cog(Pets(bot))
    bot.add_cog(PetsTasks(bot))
