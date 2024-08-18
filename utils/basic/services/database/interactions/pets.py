import json
from asyncio import sleep
from datetime import datetime, timedelta
from pathlib import Path
from random import randint

import aiofiles
from asyncpg import Record

from utils.dataclasses import Pet
from utils.exceptions.errors import *
from .. import ChisatoPool
from ..handlers import Database


class PetsDB(Database):
    __slots__ = (
        "bot",
        "pet_list",
        "pets",
        "_serialized_pets"
    )

    def __init__(self, pool: ChisatoPool) -> None:
        self._serialized_pets: dict[str, Pet] = {}
        super().__init__(pool=pool)

        self.bot = self.this_pool.client
        self.bot.loop.create_task(self._set_in_game())
        self.bot.loop.create_task(self._load_pets())

    @property
    def pets_list(self) -> list[Pet]:
        return list(self._serialized_pets.copy().values())

    async def _set_in_game(self) -> None:
        await sleep(2)
        await self.execute(
            "UPDATE economy_pets SET in_fight = False"
        )

    async def _load_pets(self) -> None:
        async with aiofiles.open(Path(f'./json/pets.json'), encoding='utf-8') as f:
            json_data = json.loads(await f.read())
            for pet in json_data:
                self._serialized_pets[pet["name"]] = Pet(
                    name=pet["name"],
                    emoji=pet["emoji"],
                    power=pet["power"],
                    stamina=pet["stamina"],
                    mana=pet["mana"],
                    cost=pet["cost"],
                    image_link=pet["link"],
                    level=0
                )

    async def in_fight_switch(self, guild: int, member: int, switch: bool = False) -> None:
        if await self.fetchall(
                'SELECT * FROM economy_pets WHERE guild_id=$1 AND user_id=$2', guild, member
        ):
            await self.execute(
                'UPDATE economy_pets SET in_fight=$1 WHERE guild_id=$2 AND user_id=$3',
                switch, guild, member
            )

    async def in_fight_check(self, guild: int, member: int) -> bool:
        values = await self.fetchrow(
            'SELECT * FROM economy_pets WHERE guild_id=$1 AND user_id=$2',
            guild, member
        )
        return values[9] if values and values[9] else False

    async def owner_alert(self, guild: int, member: int) -> bool | None:
        values = await self.fetchrow(
            'SELECT * FROM economy_pets WHERE guild_id=$1 AND user_id=$2',
            guild, member
        )

        if values and values[8] <= datetime.now().timestamp():
            await self.execute(
                'UPDATE economy_pets SET alert=$1 WHERE guild_id=$2 AND user_id=$3',
                (datetime.now() + timedelta(hours=12)).timestamp(), guild, member
            )
            return True
        return False

    async def pet_get_with_name(self, pet_name: str) -> Pet:
        return self._get_default_object(pet_name)

    async def select_all_pets(self) -> list[Pet]:
        if not (
                data := await self.fetchall("SELECT * FROM economy_pets")
        ):
            return []
        return [
            self._serialize_from_record(i)
            for i in data
        ]

    async def select_all_pets_where_mana_0(self) -> list[Pet]:
        if not (
                data := await self.fetchall(
                    "SELECT * FROM economy_pets WHERE mana_residue <= 0"
                )
        ):
            return []
        return [
            self._serialize_from_record(i) for i in data
        ]

    def _get_default_object(self, pet_type: str) -> Pet:
        try:
            pet = self._serialized_pets.copy()[pet_type]
        except KeyError:
            raise ValueError('Invalid pet type!')

        return pet

    def _serialize_from_record(self, record: Record) -> Pet:
        pet: Pet = self._get_default_object(record[2])

        return Pet(
            name=record[2],
            emoji=pet.emoji,
            power=pet.power,
            stamina=record[3],
            mana=record[4],
            cost=pet.cost,
            level=record[5],
            image_link=pet.image_link,
            exp_now=record[6],
            exp_need=record[7],
            owner_id=record[1],
            guild_id=record[0]
        )

    async def pet_get(self, guild: int, member: int) -> Pet:
        pets_info = await self.fetchrow(
            'SELECT * FROM economy_pets WHERE guild_id=$1 AND user_id=$2', guild, member
        )

        if not pets_info:
            raise DoesntHavePet('Doesnt Have Any Pet')
        else:
            return self._serialize_from_record(pets_info)

    async def pet_remove(self, guild: int, member: int) -> None:
        pets_info = await self.fetchrow(
            'SELECT * FROM economy_pets WHERE guild_id=$1 AND user_id=$2', guild, member
        )

        if not pets_info:
            raise DoesntHavePet('Doesnt Have Any Pet')
        else:
            await self.execute('DELETE FROM economy_pets WHERE guild_id=$1 AND user_id=$2', guild, member)

    async def pet_add(self, guild: int, member: int, pet_type: str) -> None:
        await self.bot.databases.economy.member_check_in_main_db(guild=guild, members=[member])

        if await self.fetchrow(
                'SELECT * FROM economy_pets WHERE guild_id=$1 AND user_id=$2',
                guild, member
        ):
            raise AlreadyHavePet

        else:
            try:
                pet = self._serialized_pets[pet_type]
            except KeyError:
                raise ValueError("Invalid pet type!")

            await self.execute(
                """
                INSERT INTO economy_pets(guild_id, user_id, pet, stamina_residue, mana_residue) 
                VALUES ($1, $2, $3, $4, $5)
                """,
                guild, member, pet.name, pet.stamina, pet.mana
            )

    async def pet_stats_update(
            self, member: int, guild: int, pet_type: str, stamina: int = None, mana: int = None,
            up: bool = False, up_lvl: bool = False
    ) -> None:
        if not (pet_info := await self.pet_get_with_name(pet_type)):
            raise ValueError('Error pet type!')

        if not (
                values := await self.fetchrow(
                    'SELECT * FROM economy_pets WHERE guild_id=$1 AND user_id=$2',
                    guild, member
                )
        ):
            raise DoesntHavePet('Doesnt Have Any Pet')

        if up is True:
            if stamina:
                stamina_to_set = pet_info.stamina if (
                        (values[3] + stamina) >= pet_info.stamina
                ) else (values[3] + stamina)

                await self.execute(
                    'UPDATE economy_pets SET stamina_residue=$1 WHERE guild_id=$2 AND user_id=$3',
                    stamina_to_set, guild, member
                )
            if mana:
                mana_to_set = pet_info.mana if (values[4] + mana) >= pet_info.mana else (values[4] + mana)

                await self.execute(
                    'UPDATE economy_pets SET mana_residue=$1 WHERE guild_id=$2 AND user_id=$3',
                    mana_to_set, guild, member
                )

        if up is False:
            if values[3] - stamina <= 0:
                await self.execute(
                    'UPDATE economy_pets SET stamina_residue=$1 WHERE guild_id=$2 AND user_id=$3',
                    0, guild, member
                )

                raise PetStatsZero
            else:
                await self.execute(
                    'UPDATE economy_pets SET stamina_residue=stamina_residue-$1 WHERE guild_id=$2 AND user_id=$3',
                    stamina, guild, member
                )

            if mana:
                if values[4] - mana <= 0:
                    await self.execute(
                        'UPDATE economy_pets SET mana_residue=$1 WHERE guild_id=$2 AND user_id=$3',
                        0, guild, member
                    )

                    raise PetStatsZero
                else:
                    await self.execute(
                        """
                        UPDATE economy_pets SET mana_residue=mana_residue-$1 
                        WHERE guild_id=$2 AND user_id=$3
                        """,
                        mana, guild, member
                    )

            if (stamina and values[3] - stamina <= 5) or (mana and values[4] - mana <= 5):
                raise PetLowStat

        if up_lvl is True:
            exp_plus = randint(1, 4)
            await self.execute(
                'UPDATE economy_pets SET exp_now=exp_now+$1 WHERE guild_id=$2 AND user_id=$3',
                exp_plus, guild, member
            )

            if values[6] + exp_plus >= values[7]:
                if values[5] >= 20:
                    raise PetMaxLvl

                exp = round(
                    values[6] + (values[6] / 100 * 30)
                ) if (values[5] + 1 <= 10) else round(
                    values[6] + (values[6] / 100 * 10)
                )

                await self.execute(
                    'UPDATE economy_pets SET lvl=lvl+1, exp_need=$1, exp_now=0 WHERE guild_id=$2 AND user_id=$3',
                    exp, guild, member
                )

                if values[5] + 1 == 20:
                    raise PetReachedMaxLvl
