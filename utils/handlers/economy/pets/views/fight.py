import asyncio
import random
from typing import Union

from disnake import (
    Member,
    HTTPException,
    MessageInteraction,
    ui,
    Embed,
    Guild,
    ApplicationCommandInteraction,
    TextChannel,
    VoiceChannel,
    StageChannel,
    Thread
)
from loguru import logger

from utils.basic import (
    ChisatoBot,
    View,
    IntFormatter,
    EmbedErrorUI,
    EmbedUI
)
from utils.consts import (
    REGULAR_CURRENCY, ERROR_EMOJI, SUCCESS_EMOJI
)
from utils.dataclasses import Pet
from utils.exceptions import (
    PetReachedMaxLvl,
    PetLowStat,
    PetStatsZero
)
from utils.handlers.economy import check_in_fight_button, check_in_game_button
from utils.handlers.economy.pets.handlers import OwnerAlertManager
from utils.i18n import ChisatoLocalStore

GuildMessageable = Union[TextChannel, Thread, VoiceChannel, StageChannel]
_t = ChisatoLocalStore.load("./cogs/economy/pets.py")

_LEVELING_BALANCE_LIST = [x for x in range(0, 200, 10)]
LEVELING_BALANCE = {i: _LEVELING_BALANCE_LIST[i] for i in range(0, 20)}
ATTACK_EMOJIS = ["🪓", "🔪", "🪃", "🥊"]


class PetFights(View):
    FIGHT_BALANCE_DICT: dict[int, int] = {
        2: 10,
        3: 12,
        4: 13,
        5: 15,
        6: 17,
        7: 19,
        8: 25,
        9: 30,
        10: 40,
        11: 45,
        12: 50,
        13: 55,
        14: 60,
        15: 65
    }

    def __init__(
            self,
            bot: ChisatoBot,
            first: Member,
            first_pet: Pet,
            second: Member,
            second_pet: Pet,
            first_attack: Member,
            inter: MessageInteraction, rate: int
    ) -> None:
        self.attacker: Member = first_attack
        self.first_player_hp: int = 100 + LEVELING_BALANCE[first_pet.level]
        self.second_player_hp: int = 100 + LEVELING_BALANCE[second_pet.level]
        self.first_hard_hit: bool = False
        self.second_hard_hit: bool = False

        self.rate: int = rate

        self.bot = bot
        self.tasks_manager = OwnerAlertManager(self.bot)
        self.interaction = inter
        self.win: bool = False

        self.first_player: Member = first
        self.first_pet: Pet = first_pet

        self.second_player: Member = second
        self.second_pet: Pet = second_pet

        super().__init__(timeout=120, store=_t, guild=inter.guild)

        button_label = _t.get(
            "pets.bet_amount",
            locale=inter.guild.preferred_locale,
        )
        self.add_item(
            ui.Button(
                label=f"{button_label} {IntFormatter(rate).format_number()}",
                disabled=True, row=1, emoji=REGULAR_CURRENCY,
                custom_id="pet_money_fight_rate"
            )
        )

    async def on_timeout(self) -> None:
        if not self.win:
            for player in [self.first_player, self.second_player]:
                await self.bot.databases.pets.in_fight_switch(guild=player.guild.id, member=player.id)

            for child in self.children:
                child.disabled = True
            try:
                await self.interaction.edit_original_response(view=self)
            except HTTPException:
                pass

    async def interaction_check(self, interaction: MessageInteraction) -> bool | None:
        if interaction.author not in [self.first_player, self.second_player]:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get("pets.error.its_not_your", locale=interaction.guild_locale),
                    member=interaction.author
                ),
                ephemeral=True
            )

        if self.attacker.id != interaction.author.id:
            return await interaction.response.send_message(
                embed=EmbedErrorUI(
                    description=_t.get("pets.error.its_not_your_turn", locale=interaction.guild_locale),
                    member=interaction.author
                ),
                ephemeral=True
            )

        return True

    def super_attack_logic(self) -> None:
        choice = random.randint(1, 5)

        if self.first_hard_hit and self.attacker.id == self.first_player.id:
            self.first_hard_hit = False
            self.button_disables(custom_ids=['pet_super_attack_button'], disabled=False)

        elif self.second_hard_hit and self.attacker.id == self.second_player.id:
            self.second_hard_hit = False
            self.button_disables(custom_ids=['pet_super_attack_button'], disabled=False)

        else:
            if choice == 3:
                if self.attacker.id == self.first_player.id:
                    self.first_hard_hit = False
                else:
                    self.second_hard_hit = False

                self.button_disables(custom_ids=['pet_super_attack_button'], disabled=False)
            else:
                self.button_disables(custom_ids=['pet_super_attack_button'], disabled=True)

    def _get_current_pet(self, player: Member) -> Pet:
        return self.first_pet if player.id == self.first_player.id else self.second_pet

    async def win_logic(self, interaction: MessageInteraction | ApplicationCommandInteraction) -> bool:
        if self.first_player_hp <= 0:
            winner = self.second_player
        elif self.second_player_hp <= 0:
            winner = self.first_player
        else:
            return False

        self.win = True
        await interaction.response.defer()

        self.clear_items()
        self.add_item(
            ui.Button(
                label=_t.get(
                    "pets.button.win_amount.label",
                    locale=interaction.guild.preferred_locale,
                    values=(IntFormatter(self.rate).format_number(),)
                ),
                disabled=True, row=1,
                emoji=REGULAR_CURRENCY
            )
        )
        self.add_item(
            ui.Button(
                label=_t.get(
                    "pets.button.winner.label", locale=interaction.guild.preferred_locale,
                    values=(winner.name,)
                ),
                emoji='<:karona:1114243322031132733>',
                row=2, disabled=True
            )
        )
        self.add_item(
            ui.Button(
                label=_t.get(
                    "pets.button.loser.label", locale=interaction.guild.preferred_locale,
                    values=(self.attacker.name,)
                ),
                emoji='<:swords:1131522485309943938>',
                row=2, disabled=True
            )
        )

        await interaction.edit_original_response(
            embed=EmbedUI(
                title=_t.get("pets.battle.title", locale=interaction.guild_locale),
                description=_t.get(
                    "pets.win.duel_result",
                    locale=interaction.guild_locale,
                    values=(
                        winner.mention, self.attacker.mention,

                        self.second_player.mention, self.second_player_hp,
                        self.first_player.mention, self.first_player_hp
                    )
                )
            ),
            view=self
        )

        async def update_pet_stats(player: Member) -> None:
            try:
                await self.bot.databases.pets.pet_stats_update(
                    member=player.id,
                    guild=interaction.guild.id,
                    stamina=random.randint(1, 5),
                    mana=random.randint(1, 5),
                    up=False,
                    up_lvl=True,
                    pet_type=self._get_current_pet(player).name
                )
            except PetLowStat:
                await self.tasks_manager.pet_owner_alert_low_stat(
                    member=player, guild=interaction.guild, channel=interaction.channel  # type: ignore
                )
            except PetReachedMaxLvl:
                await self.tasks_manager.pet_owner_alert_reached_max_lvl(
                    member=player, guild=interaction.guild, channel=interaction.channel  # type: ignore
                )
            except PetStatsZero:
                await self.tasks_manager.pet_owner_alert_died(
                    member=player, guild=interaction.guild, channel=interaction.channel  # type: ignore
                )
            except Exception as e:
                _ = e

        await asyncio.gather(
            *(
                update_pet_stats(player)
                for player in [self.first_player, self.second_player]
            )
        )

        await asyncio.gather(
            *(
                self.bot.databases.pets.in_fight_switch(
                    guild=interaction.guild.id, member=player.id
                )
                for player in [self.first_player, self.second_player]
            )
        )

        await asyncio.gather(
            self.bot.databases.economy.remove_balance_no_limit(
                guild=interaction.guild.id,
                member=self.attacker.id,
                amount=self.rate
            ),
            self.bot.databases.economy.add_balance(
                guild=interaction.guild.id,
                member=winner.id,
                amount=self.rate
            ),
            self.bot.databases.transactions.add(
                guild=interaction.guild.id, user=self.attacker.id, amount=self.rate,
                typing=False, locale_key="pets.duel.lose.transaction"
            ),
            self.bot.databases.transactions.add(
                guild=interaction.guild.id, user=winner.id, amount=self.rate,
                typing=True, locale_key="pets.duel.win.transaction"
            )
        )
        return True

    async def generate_embed(self, guild: Guild, embed_key: str) -> Embed:
        pet_titles = _t.get("pets.dict.titles", locale=guild.preferred_locale)
        pet_info: Pet = await self.bot.databases.pets.pet_get(guild=guild.id, member=self.attacker.id)

        if embed_key == "pets.duel.retreat":
            values = (
                self.first_player.mention if self.attacker.id == self.second_player.id
                else self.second_player.mention,

                self.attacker.mention, pet_titles[pet_info.name],

                self.second_player.mention, self.second_player_hp,
                self.first_player.mention, self.first_player_hp
            )
        else:
            values = (
                self.first_player.mention if self.attacker.id == self.second_player.id
                else self.second_player.mention, self.attacker.mention,

                pet_titles[pet_info.name], self.attacker.mention,

                self.second_player.mention, self.second_player_hp,
                self.first_player.mention, self.first_player_hp
            )

        return EmbedUI(
            title=_t.get(
                "pets.battle.title",
                locale=guild.preferred_locale
            ),
            description=_t.get(
                embed_key, values=values,
                locale=guild.preferred_locale
            )
        ).set_footer(
            text=_t.get(
                "pets.battle.footer",
                locale=guild.preferred_locale
            )
        )

    @ui.button(
        label="pets.attack",
        emoji=random.choice(ATTACK_EMOJIS),
        custom_id='pet_attack_button'
    )
    async def attack(self, button: ui.Button, interaction: MessageInteraction) -> None:
        power = self._get_current_pet(self.attacker).power

        if self.attacker.id == self.first_player.id:
            self.attacker = self.second_player
            self.second_player_hp -= random.randint(
                4, int(self.FIGHT_BALANCE_DICT[power])
            )
        else:
            self.attacker = self.first_player
            self.first_player_hp -= random.randint(
                4, int(self.FIGHT_BALANCE_DICT[power])
            )

        if await self.win_logic(interaction):
            return

        self.super_attack_logic()
        button.emoji = random.choice(ATTACK_EMOJIS)

        await interaction.response.edit_message(
            embed=await self.generate_embed(
                guild=interaction.guild,
                embed_key="pets.duel.default_attack"
            ),
            view=self
        )

    @ui.button(
        label="pets.super_attack", disabled=True,
        emoji=random.choice(ATTACK_EMOJIS),
        custom_id='pet_super_attack_button'
    )
    async def super_attack(self, button: ui.Button, interaction: MessageInteraction) -> None:
        power = self._get_current_pet(self.attacker).power
        if self.attacker.id == self.first_player.id:
            self.first_hard_hit = False
            self.attacker = self.second_player
            self.second_player_hp -= random.randint(
                10, int(self.FIGHT_BALANCE_DICT[power] + 15)
            )
        else:
            self.second_hard_hit = False
            self.attacker = self.first_player
            self.first_player_hp -= random.randint(
                10, int(self.FIGHT_BALANCE_DICT[power] + 15)
            )

        if await self.win_logic(interaction):
            return

        self.super_attack_logic()
        button.emoji = random.choice(ATTACK_EMOJIS)

        await interaction.response.edit_message(
            embed=await self.generate_embed(
                guild=interaction.guild,
                embed_key="pets.duel.super_attack"
            ),
            view=self
        )

    @ui.button(
        label="pets.retreat",
        emoji="🪤", disabled=False,
        custom_id='pet_back_button'
    )
    async def back_button(self, _, interaction: MessageInteraction) -> None:
        if self.attacker.id == self.first_player.id:
            self.first_hard_hit = True
            self.attacker = self.second_player
        else:
            self.second_hard_hit = True
            self.attacker = self.first_player

        if await self.win_logic(interaction):
            return

        self.super_attack_logic()

        await interaction.response.edit_message(
            embed=await self.generate_embed(
                guild=interaction.guild,
                embed_key="pets.duel.retreat"
            ),
            view=self
        )


class PetFightView(View):
    def __init__(
            self,
            bot: ChisatoBot,
            author: Member,
            original_author: Member,
            inter: ApplicationCommandInteraction,
            rate: int
    ) -> None:
        self.attacker: Member | None = None

        self.bot = bot
        self.interaction = inter
        self.rate = rate

        self.author = author
        self.original_author = original_author

        self.end: bool = False

        super().__init__(timeout=30, author=author, store=_t, guild=author.guild)

    async def on_timeout(self) -> None:
        if not self.end:
            for child in self.children:
                child.disabled = True

            try:
                await self.interaction.edit_original_response(view=self)
            except HTTPException:
                pass

            await self.bot.databases.pets.in_fight_switch(
                guild=self.interaction.guild.id,
                member=self.original_author.id
            )

    async def interaction_check(self, interaction: MessageInteraction) -> bool | None:
        if (
                interaction.component.custom_id == "fight_discard"
                and interaction.author in [self.author, self.original_author]
        ):
            return True
        return await super().interaction_check(interaction)

    @ui.button(
        label="pets.button.accept_fight.label",
        emoji=SUCCESS_EMOJI,
        custom_id='pet_fight_accept'
    )
    @check_in_fight_button
    @check_in_game_button
    async def accept_fight(self, _, interaction: MessageInteraction) -> None:
        print("TRUE")
        self.end = True
        self.attacker = random.choice([self.author, self.original_author])

        for player in [self.author, self.original_author]:
            await self.bot.databases.pets.in_fight_switch(guild=interaction.guild.id, member=player.id, switch=True)

        pet_titles = _t.get("pets.dict.titles", locale=interaction.guild.preferred_locale)
        pet_info: Pet = await self.bot.databases.pets.pet_get(guild=interaction.guild.id, member=self.attacker.id)

        view = PetFights(
            first=self.original_author,
            first_pet=await self.bot.databases.pets.pet_get(
                guild=interaction.guild.id, member=self.original_author.id
            ),

            second=self.author,
            second_pet=await self.bot.databases.pets.pet_get(
                guild=interaction.guild.id, member=self.author.id
            ),

            first_attack=self.attacker,

            inter=interaction, bot=self.bot, rate=self.rate
        )

        print("TRUE")
        await interaction.response.edit_message(
            embed=EmbedUI(
                title=_t.get("pets.battle.title", locale=interaction.guild.preferred_locale),
                description=_t.get(
                    "pets.battle.start.description",
                    locale=interaction.guild.preferred_locale,
                    values=(
                        self.attacker.mention,

                        pet_titles[pet_info.name], self.attacker.mention,

                        view.first_player.mention, view.first_player_hp,
                        view.second_player.mention, view.second_player_hp
                    )
                )
            ).set_footer(
                text=_t.get("pets.battle.footer", locale=interaction.guild.preferred_locale)
            ),
            view=view
        )

    @ui.button(
        label="pets.button.discard_fight.label",
        emoji=ERROR_EMOJI,
        custom_id="fight_discard"
    )
    async def discard_fight(self, _, interaction: MessageInteraction) -> None:
        try:
            await self.bot.databases.pets.in_fight_switch(
                guild=self.interaction.guild.id,
                member=self.original_author.id
            )
        except Exception as e:
            logger.warning(f"{e.__class__.__name__}: {e}")
        await self.custom_defer(interaction)
        self.end = True
