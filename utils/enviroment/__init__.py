from os import getenv

from dotenv import load_dotenv

from utils.dataclasses import Environment

__all__ = (
    "env",
)

load_dotenv()

env = Environment(
    GUILD_INVITE=str(getenv("GUILD_INVITE")),
    PREFIX=str(getenv("PREFIX")),
    COLOR=int(getenv("COLOR"), 16),
    MAIN_ID=int(getenv("MAIN_ID")),
    OWNER_IDS=set(int(x) for x in getenv("OWNER_IDS").split(",")),

    TOKEN1=str(getenv("TOKEN1")),
    TOKEN2=str(getenv("TOKEN2")),
    TOKEN3=str(getenv("TOKEN3")),
    DSN=str(getenv("DSN")),
    DSU=str(getenv("DSU")),

    COMMAND_ERROR_WEBHOOK=str(getenv("COMMAND_ERROR_WEBHOOK")),
    GUILD_WEBHOOK=str(getenv("GUILD_WEBHOOK")),
    DAY_STATISTIC_WEBHOOK=str(getenv("DAY_STATISTIC_WEBHOOK")),
    SHARDS_CONTROL_WEBHOOK=str(getenv("SHARDS_CONTROL_WEBHOOK")),

    SDC_TOKEN=str(getenv("SDC_TOKEN")),
    BOTICORD_TOKEN=str(getenv("BOTICORD_TOKEN")),
)
