import ast
import asyncio
from asyncio import sleep
from datetime import datetime

from asyncpg import Record
from disnake import Member, Guild

from utils.basic.services.database import ChisatoPool
from utils.basic.services.database.handlers import Database
from utils.exceptions.errors import *
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/economy/simple.py")


class EconomyDB(Database):
    __slots__ = (
        "bot",
        "_lock"
    )

    cluster: str = "economy"

    def __init__(self, pool: ChisatoPool) -> None:
        super().__init__(pool=pool)

        self.bot = self.this_pool.client
        self.bot.loop.create_task(self._set_in_game())
        self._lock = asyncio.Lock()

    async def _set_in_game(self) -> None:
        await sleep(2)
        await self.execute(
            "UPDATE economy_main SET in_game = FALSE"
        )

    async def member_check_in_main_db(self, guild: int | Member, members: list[int | Member]) -> None:
        async with self._lock:
            await self.executemany(
                """
                INSERT INTO economy_main (guild_id, user_id) 
                SELECT $1, $2
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM economy_main 
                    WHERE guild_id = $1 AND user_id = $2
                )
                """,
                [
                    (
                        guild.id if isinstance(guild, Guild) else guild,
                        member.id if isinstance(member, Member) else member
                    )
                    for member in members
                ]
            )

    async def pay(self, member: int, guild: int, member_pay: int, amount: int) -> None:
        await self.member_check_in_main_db(guild=guild, members=[member, member_pay])

        values_member = (await self.fetchval(
            'SELECT money FROM economy_main WHERE guild_id = $1 AND user_id = $2', guild, member
        ))
        values_member_pay = (await self.fetchval(
            "SELECT money FROM economy_main WHERE guild_id = $1 AND user_id = $2", guild, member_pay
        ))

        if amount > values_member:
            raise NotEnoughMoney(f'User {member} does not have enough money')
        else:
            await self.execute(
                'UPDATE economy_main SET money = $1 WHERE guild_id = $2 AND user_id = $3',
                values_member - amount, guild, member
            )
            await self.execute(
                'UPDATE economy_main SET money = $1 WHERE guild_id = $2 AND user_id = $3',
                values_member_pay + amount, guild, member_pay
            )

    async def remove_balance(self, guild: int, member: int, amount: int) -> None:
        await self.member_check_in_main_db(guild=guild, members=[member])

        values_member = (await self.fetchrow(
            'SELECT money FROM economy_main WHERE guild_id = $1 AND user_id = $2',
            guild, member
        ))[0]

        if values_member < amount:
            raise NotEnoughMoney
        else:
            await self.remove_balance_no_limit(guild=guild, member=member, amount=amount)

    async def remove_balance_no_limit(self, guild: int, member: int, amount: int) -> None:
        await self.member_check_in_main_db(guild=guild, members=[member])

        await self.execute(
            'UPDATE economy_main SET money = money - $1 WHERE guild_id = $2 AND user_id = $3',
            amount, guild, member
        )

    async def add_balance(self, guild: int, member: int, amount: int) -> None:
        await self.member_check_in_main_db(guild=guild, members=[member])

        await self.execute(
            'UPDATE economy_main SET money = money + $1 WHERE guild_id = $2 AND user_id = $3',
            amount, guild, member
        )

    async def values(self, member: int, guild: int):
        await self.member_check_in_main_db(guild=guild, members=[member])

        return await self.fetchrow(
            'SELECT * FROM economy_main WHERE guild_id = $1 AND user_id = $2',
            guild, member
        )

    async def money_check(self, guild: int, check_member: int, check_rate: int = None, with_member: int = None) -> bool:
        await self.member_check_in_main_db(guild=guild, members=[check_member])
        check_values = await self.fetchval(
            "SELECT money FROM economy_main WHERE guild_id=$1 AND user_id=$2",
            guild, check_member
        )

        if isinstance(check_rate, int):
            return check_rate <= check_values
        else:
            await self.member_check_in_main_db(guild=guild, members=[with_member])
            with_values = await self.fetchval(
                'SELECT money FROM economy_main WHERE guild_id=$1 AND user_id=$2',
                guild, with_member
            )
            return with_values < check_values

    async def checker_in_bank(self, guild: int, members: list[int]) -> None:
        for member in members:
            values = await self.fetchrow(
                'SELECT * FROM economy_bank WHERE guild_id = $1 AND user_id = $2', guild, member
            )

            if not values:
                await self.execute('INSERT INTO economy_bank(guild_id, user_id) VALUES (?, ?)', (guild, member))

    async def bank_money_add(self, guild: int, member: int, amount: int) -> int | None:
        await self.checker_in_bank(guild=guild, members=[member])

        values = (
            await self.fetchrow(
                'SELECT * FROM economy_bank WHERE guild_id = $1 AND user_id = $2',
                guild, member
            )
        )[0]

        if values + amount <= 100000:
            await self.execute(
                'UPDATE economy_bank SET amount = $1 WHERE guild_id = $2 AND user_id = $3',
                values + amount, guild, member
            )

            return amount
        else:
            await self.execute(
                'UPDATE economy_bank SET amount = $1 WHERE guild_id = $2 AND user_id = $3',
                100000, guild, member
            )

            return values + amount - 100000

    async def bank_money_remove(self, guild: int, member: int, amount: int) -> list | None:
        await self.checker_in_bank(guild=guild, members=[member])

        values = (await self.fetchrow(
            'SELECT money FROM economy_main WHERE guild_id=? AND user_id=?',
            guild, member
        ))[0]

        if values - amount >= 0:
            await self.execute(
                'UPDATE economy_bank SET amount = $1 WHERE guild_id = $2 AND user_id = $3',
                values - amount, guild, member
            )

            return await self.fetchrow(
                'SELECT * FROM economy_bank WHERE guild_id = $1 AND user_id = $2', guild, member
            )
        else:
            raise BankLessThanZero

    async def bank_balance(self, guild: int, member: int) -> int:
        await self.checker_in_bank(guild=guild, members=[member])

        return (
            await self.fetchrow(
                'SELECT amount FROM economy_bank WHERE guild_id=? AND user_id=?', (guild, member)
            )
        )[0]

    async def get_top_position(self, guild: Guild, member: Member) -> str:
        await self.member_check_in_main_db(guild=guild.id, members=[member])

        data = await self.fetchall(
            """
            SELECT * FROM economy_main WHERE guild_id=$1 ORDER BY money DESC LIMIT 100
            """,
            guild.id
        )
        row = await self.fetchrow(
            """
            SELECT * FROM economy_main WHERE guild_id=$1 AND user_id=$2
            """,
            guild.id, member.id
        )

        try:
            return str(data.index(row) + 1)
        except ValueError:
            return "100+"

    async def in_game(self, member: int, guild: int, _set: bool | None = None) -> None | bool:
        await self.member_check_in_main_db(guild=guild, members=[member])

        if isinstance(_set, bool):
            await self.execute(
                "UPDATE economy_main SET in_game=$1 WHERE guild_id=$2 AND user_id=$3",
                _set, guild, member
            )
        else:
            return await self.fetchval(
                'SELECT in_game FROM economy_main WHERE guild_id=$1 AND user_id=$2',
                guild, member
            )

    async def get_marry_solo(self, guild: Guild, member: Member) -> Record | None:
        return await self.fetchrow(
            "SELECT * FROM economy_marry WHERE guild_id=$1 AND (user1_id=$2 OR user2_id=$2)",
            guild.id, member.id
        )

    async def get_marry(self, guild: Guild, members: set[Member]) -> Record | None:
        members = list(members)
        if not (member0 := await self.get_marry_solo(guild=guild, member=members[0])):
            return
        if not (member1 := await self.get_marry_solo(guild=guild, member=members[1])):
            return
        if member0[1] == member1[1]:
            return member0

    async def marry_registry(self, guild: Guild, members: list[Member]) -> None:
        await self.member_check_in_main_db(guild=guild.id, members=list(members))

        if len(members) != 2:
            raise TypeError("Members count need two!")

        if await self.get_marry(guild=guild, members=set(members)):
            raise AlreadyMarried

        members = list(members)
        await self.execute(
            """
            INSERT INTO economy_marry(guild_id, user1_id, user2_id, together_since) 
            VALUES ($1, $2, $3, $4)
            """,
            guild.id, members[0].id, members[1].id, int(datetime.now().timestamp())
        )

    async def marry_set_card(self, guild: Guild, member: Member, card_name: str) -> None:
        if marry_data := await self.get_marry_solo(guild=guild, member=member):
            return await self.execute(
                "UPDATE economy_marry SET card_selected=$1 WHERE marry_id=$2",
                card_name, marry_data[1]
            )

        raise NotMarried

    async def update_marry_balance(self, guild: Guild, member: Member, amount: int, deposit: bool = True) -> None:
        await self.member_check_in_main_db(guild=guild.id, members=[member.id])

        if marry_data := await self.get_marry_solo(guild=guild, member=member):
            member_data = await self.values(member=member.id, guild=guild.id)
            match deposit:
                case True:
                    if member_data[2] < amount:
                        await self.execute(
                            "UPDATE economy_main SET money=money-$1 WHERE user_id=$2 AND guild_id=$3",
                            amount, member.id, guild.id
                        )
                        await self.execute(
                            "UPDATE economy_marry SET balance=balance+$1 WHERE marry_id=$2",
                            amount, marry_data[1]
                        )
                        await self.bot.databases.transactions.add(
                            guild=guild.id, user=member.id, amount=amount, typing=False,
                            locale_key="loves.balance.incoming"
                        )
                        return

                    raise NotEnoughMoney
                case False:
                    if marry_data[4] < amount:
                        await self.execute(
                            "UPDATE economy_marry SET balance=balance-$1 WHERE marry_id=$2",
                            amount, marry_data[1]
                        )
                        await self.execute(
                            "UPDATE economy_main SET money=money+$1 WHERE user_id=$2 AND guild_id=$3",
                            amount, member.id, guild.id
                        )
                        await self.bot.databases.transactions.add(
                            guild=guild.id, user=member.id, amount=amount, typing=True,
                            locale_key="loves.balance.outgoing"
                        )
                        return

                    raise MarryNotEnoughMoney
        raise NotMarried

    async def marry_discard(self, marry_id: int) -> None:
        await self.execute("DELETE FROM economy_marry WHERE marry_id=$1", marry_id)

    async def append_banner(self, guild: Guild, member: Member, card_name: str) -> None:
        if card_name not in (
                data_list := ast.literal_eval((marry_data := await self.get_marry_solo(guild, member))[7])
        ):
            data_list.append(card_name)

            return await self.execute(
                "UPDATE economy_marry SET cards=$1 WHERE marry_id=$2",
                str(data_list), marry_data[1]
            )
        raise AlreadyHaveThisSubject

    async def get_shop_items(self, guild: Guild) -> list[Record]:
        items = await self.fetchall(
            "SELECT * FROM economy_shop WHERE guild_id=$1", guild.id
        )
        return items if items else []

    async def add_item(
            self, guild: Guild, cost: int, count: bool | int,
            description: str, role: Role
    ) -> None:
        if await self.fetchrow(
                "SELECT * FROM economy_shop WHERE guild_id=$1 AND role_id=$2",
                guild.id, role.id
        ):
            raise AlreadyInShop
        elif len(await self.fetchall(
                "SELECT * FROM economy_shop WHERE guild_id=$1",
                guild.id
        )) == 20:
            raise MaxShopItems

        if isinstance(count, bool):
            await self.execute(
                """
                INSERT INTO economy_shop(guild_id, role_id, unlimited, description, cost) 
                VALUES ($1, $2, $3, $4, $5)
                """,
                guild.id, role.id, True, description, cost
            )
        else:
            await self.execute(
                """
                INSERT INTO economy_shop(guild_id, role_id, count, unlimited, description, cost) 
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                guild.id, role.id, count, False, description, cost
            )

    async def remove_item(
            self, guild: Guild, role: int
    ) -> None:
        await self.execute(
            "DELETE FROM economy_shop WHERE guild_id=$1 AND role_id=$2",
            guild.id, role
        )

    async def remove_count(
            self, guild: Guild, role: int
    ) -> None:
        if not await self.fetchval(
                "SELECT unlimited FROM economy_shop WHERE guild_id=$1 AND role_id=$2",
                guild.id, role
        ):
            if await self.fetchval(
                    "SELECT count FROM economy_shop WHERE guild_id=$1 AND role_id=$2",
                    guild.id, role
            ) == 0:
                await self.remove_item(guild, role)
                raise SubjectEnded

            await self.execute(
                "UPDATE economy_shop SET count=count-1 WHERE guild_id=$1 AND role_id=$2",
                guild.id, role

            )

    async def add_count(
            self, guild: Guild, role: int
    ) -> None:
        if not await self.fetchval(
                "SELECT unlimited FROM economy_shop WHERE guild_id=$1 AND role_id=$2",
                guild.id, role
        ):
            await self.execute(
                "UPDATE economy_shop SET count=count+1 WHERE guild_id=$1 AND role_id=$2",
                guild.id, role
            )
