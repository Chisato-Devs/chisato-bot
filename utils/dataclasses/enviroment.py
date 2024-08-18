from dataclasses import dataclass


@dataclass
class Environment:
    GUILD_INVITE: str
    PREFIX: str
    COLOR: int
    MAIN_ID: int
    OWNER_IDS: set[int]

    TOKEN1: str | None
    TOKEN2: str | None
    TOKEN3: str | None

    DSN: str | None
    DSU: str | None

    COMMAND_ERROR_WEBHOOK: str
    GUILD_WEBHOOK: str
    DAY_STATISTIC_WEBHOOK: str
    SHARDS_CONTROL_WEBHOOK: str

    BOTICORD_TOKEN: str
    SDC_TOKEN: str
