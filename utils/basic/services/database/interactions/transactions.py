from asyncpg import Record

from utils.basic.services.database import ChisatoPool
from utils.basic.services.database.handlers import Database
from utils.i18n import ChisatoLocalStore

_t = ChisatoLocalStore.load("./cogs/economy/simple.py")


class TransactionsDB(Database):
    __slots__ = (
        "bot"
    )

    def __init__(self, pool: ChisatoPool) -> None:
        super().__init__(pool=pool)
        self.bot = self.this_pool.client

    async def add(
            self, guild: int, user: int, amount: int,
            locale_key: str, typing: bool
    ) -> None:
        if amount != 0:
            await self.execute(
                """
                INSERT INTO economy_transactions(
                    guild_id, user_id, amount, 
                    type, description
                ) 
                VALUES ($1, $2, $3, $4, $5)
                """,
                guild, user, amount,
                f"eco.transaction.{str(typing).lower()}",
                locale_key
            )

    async def get_all(self, guild: int, user: int) -> list[Record] | None:
        return await self.fetchall(
            'SELECT * FROM economy_transactions WHERE guild_id =$1 AND user_id =$2', guild, user
        )
