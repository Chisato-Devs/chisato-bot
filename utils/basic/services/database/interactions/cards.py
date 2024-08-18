import asyncio
import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Literal

import aiofiles
from asyncpg import Record
from disnake import Member, User

from utils.basic.services.database import Database, ChisatoPool
from utils.dataclasses import CardItem
from utils.exceptions import CardNotInTrade


class CardsDB(Database):
    __slots__ = (
        "bot",
        "_cards_list",
        "_cards_config",
        "_probabilities",
        "_lock"
    )

    cluster: str = "cards"

    def __init__(self, pool: ChisatoPool) -> None:
        self._cards_list = {}
        self._cards_config = {}
        self._probabilities = {}

        super().__init__(pool=pool)

        self.bot = self.this_pool.client
        self.bot.loop.create_task(self.load_cards())
        self._lock = asyncio.Lock()

    @property
    def cards_list(self) -> dict[str, dict[str, str | int]]:
        return self._cards_list.copy()

    async def load_cards(self) -> None:
        async with aiofiles.open(Path(f'./json/cards.json'), encoding='utf-8') as file:
            self._cards_list = json.loads(await file.read())

        async with aiofiles.open(Path(f'./json/cards_config.json'), encoding='utf-8') as file:
            self._cards_config = json.loads(await file.read())

        self._load_probabilities()

    def _load_probabilities(self):
        for config_data in self._cards_config.values():
            if not config_data["limited"]:
                self._probabilities[config_data["rarity"]] = config_data["probability"]

    def card_drop(self) -> int | str:
        total_probability = sum(self._probabilities.values())
        random_number = random.randint(1, total_probability)

        current_probability = 0
        for card, probability in self._probabilities.items():
            current_probability += probability
            if random_number <= current_probability:
                return card

    async def check_in_main(self, user: Member | User) -> None:
        async with self._lock:
            await self.execute(
                """
                INSERT INTO cards_main(user_id, rolls) 
                SELECT $1, $2 
                WHERE NOT EXISTS (SELECT 1 FROM cards_main WHERE user_id=$1)
                """,
                user.id, 2
            )

    async def add_rolls(self, user: Member | Literal["all"], count: int) -> None:
        if user == "all":
            await self.execute(
                """
                UPDATE cards_main SET rolls = rolls + $1
                """,
                count
            )
        elif isinstance(user, Member) or isinstance(user, User):
            await self.check_in_main(user)
            await self.execute(
                """
                UPDATE cards_main SET rolls = rolls + $1 WHERE user_id = $2
                """,
                count, user.id
            )

    async def get_rolls(self, user: Member | User) -> int:
        await self.check_in_main(user)
        return await self.fetchval("SELECT rolls FROM cards_main WHERE user_id = $1", user.id)

    async def create_card(self, card_id: int, user: Member | User, rarity: int | str) -> CardItem:
        await self.execute(
            """
            INSERT INTO cards_store(user_id, created_since, card_id, rarity) 
            VALUES ($1, $2, $3, $4)
            """,
            user.id, (time := datetime.now().timestamp()), card_id, str(rarity)
        )
        return self.create_item(
            await self.fetchrow(
                """
                SELECT * FROM cards_store 
                WHERE user_id=$1 
                    AND card_id=$2 
                    AND rarity=$3 
                    AND created_since=$4
                """,
                user.id, card_id, str(rarity), time
            )
        )

    @staticmethod
    def _try_int(_a: int | str) -> Optional[int]:
        try:
            return int(_a)
        except ValueError:
            return None

    def create_item(self, card: Record) -> CardItem:
        card_item = self._cards_list.get(str(card[3]), {}).copy()

        return CardItem(
            uid=card[0],
            card_id=card_item["id"],
            owner=card[1],
            name_key=card_item["name"],
            description_key=card_item["description"],
            male_key=card_item["male"],
            image_key=card_item["name"].split(".")[-2],
            rarity=card[4],
            stars_count=rarity if (rarity := self._try_int(card[4])) else 6,
            created_timestamp=card[2]
        )

    async def get_card_from_id(self, card_id: int) -> CardItem:
        return self.create_item(
            await self.fetchrow(
                "SELECT * FROM cards_store WHERE id=$1",
                card_id
            )
        )

    async def get_cards(self, user: Member | User) -> list[Record]:
        return await self.fetchall(
            "SELECT * FROM cards_store WHERE user_id = $1", user.id
        )

    async def generate_cards(self, count: int) -> list[CardItem]:
        to_return = []

        for _ in range(count):
            card = random.choice(list(self._cards_list.values()))

            to_return.append(
                CardItem(
                    card_id=card["id"],
                    name_key=card["name"],
                    description_key=card["description"],
                    male_key=card["male"],
                    image_key=card["name"].replace("cards.", "").replace(".name", ""),
                    rarity=(rarity := self.card_drop()),
                    stars_count=r if (r := self._try_int(rarity)) else 6,
                    uid=None,
                    created_timestamp=None,
                    owner=None
                )
            )

        return to_return

    async def can_roll(self, user: Member | User) -> bool:
        if (await self.get_rolls(user)) > 0:
            await self.execute(
                "UPDATE cards_main SET rolls=rolls-1 WHERE user_id=$1", user.id
            )

            return True
        return False

    async def get_card_owner(self, _id: int) -> Optional[int]:
        return await self.fetchval(
            "SELECT user_id FROM cards_store WHERE card_id = $1", _id
        )

    async def get_trades(self, _id: int) -> Optional[list[Record]]:
        return await self.fetchall(
            """
            SELECT *
            FROM cards_trades
            JOIN public.cards_store cs ON cards_trades.card_id = cs.id OR cards_trades.to_card_id = cs.id
            WHERE cs.user_id = $1
            """, _id
        )

    async def check_in_trade(self, _id: int) -> bool:
        if await self.fetchrow(
                """
                SELECT *
                FROM cards_trades
                JOIN public.cards_store cs ON cards_trades.card_id = $1 OR cards_trades.to_card_id = $1
                """, _id
        ):
            return True
        return False

    async def trade_send(self, card: CardItem, to_card: CardItem) -> None:
        await self.execute(
            """
            INSERT INTO cards_trades(card_id, to_card_id, created) 
            VALUES ($1, $2, $3)
            """,
            card.uid, to_card.uid, datetime.now().timestamp()
        )

    async def is_your_side(self, card: CardItem) -> tuple[bool, int]:
        if val := await self.fetchval(
                "SELECT id FROM cards_trades WHERE card_id=$1",
                card.uid
        ):
            return True, val
        elif val := await self.fetchval(
                "SELECT id FROM cards_trades WHERE to_card_id=$1",
                card.uid
        ):
            return False, val
        else:
            raise CardNotInTrade("This card not in trade")

    async def remove_trade_from_id(self, _id: int) -> None:
        await self.execute(
            "DELETE FROM cards_trades WHERE id=$1", _id
        )

    async def trade_success(self, _id: int) -> None:
        trade_data = await self.fetchrow(
            "SELECT * FROM cards_trades WHERE id=$1", _id
        )

        await self.execute(
            """
            UPDATE cards_store
            SET user_id = cs2.user_id
            FROM cards_store AS cs1
            JOIN cards_store AS cs2 ON (cs1.id = $1 AND cs2.id = $2) OR (cs1.id = $2 AND cs2.id = $1)
            JOIN cards_trades AS ct ON ct.card_id = cs1.id OR ct.to_card_id = cs1.id
            WHERE cards_store.id = cs1.id;
            """,
            trade_data[1], trade_data[2]
        )

        await self.execute(
            "DELETE FROM cards_trades WHERE id=$1",
            trade_data[0]
        )

    async def truncate_timely(self) -> None:
        await self.execute("TRUNCATE TABLE cards_timely")

    async def check_in_timely(self, member: Member | User) -> None:
        if not await self.fetchval(
                "SELECT next_get FROM cards_timely WHERE user_id=$1",
                member.id
        ):
            await self.execute(
                "INSERT INTO cards_timely(user_id, next_get) VALUES ($1, $2)",
                member.id, datetime.now().timestamp()
            )

    async def get_timely(self, member: Member | User) -> bool:
        await self.check_in_main(member)
        await self.check_in_timely(member)
        if await self.fetchval(
                "SELECT next_get FROM cards_timely WHERE user_id=$1",
                member.id
        ) < datetime.now().timestamp():
            await self.execute(
                "UPDATE cards_main SET rolls=rolls + 3 WHERE user_id=$1",
                member.id
            )
            await self.execute(
                "UPDATE cards_timely SET next_get=$2 WHERE user_id=$1",
                member.id, (datetime.now() + timedelta(hours=12)).timestamp()
            )
            return True
        return False

    async def get_time_to_timely(self, member: Member | User) -> int:
        await self.check_in_main(member)

        return await self.fetchval(
            "SELECT next_get FROM cards_timely WHERE user_id=$1",
            member.id
        )
