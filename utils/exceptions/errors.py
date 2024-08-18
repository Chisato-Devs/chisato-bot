from typing import Any

from disnake import Role
from disnake.ext.commands import CheckFailure


# noinspection DuplicatedCode
class NotEnoughMoney(Exception):
    pass


class AlreadyHavePet(Exception):
    pass


class DoesntHavePet(Exception):
    pass


class PetMaxLvl(Exception):
    pass


class PetReachedMaxLvl(Exception):
    pass


class PetStatsZero(Exception):
    pass


class PetLowStat(Exception):
    pass


class BankNotEnoughMoney(Exception):
    pass


class BankLessThanZero(Exception):
    pass


class BankBalanceMax(Exception):
    pass


# noinspection DuplicatedCode
class AlreadyHaveWork(Exception):
    pass


class DoesntHaveWork(Exception):
    pass


class AlreadyMarried(Exception):
    pass


class NotMarried(Exception):
    pass


class MarryNotEnoughMoney(Exception):
    pass


class AlreadyInShop(Exception):
    pass


class MaxShopItems(Exception):
    pass


class NotFoundItem(Exception):
    pass


class SubjectEnded(Exception):
    pass


class TranslationError(Exception):
    pass


class AlreadyHaveThisSubject(Exception):
    pass


class DoesntHaveAgreedRole(CheckFailure):
    def __init__(self, message: str, required_roles: list[Role], *args: Any) -> None:
        self.required_roles = required_roles
        super().__init__(message, *args)


class MaxPrestige(Exception):
    pass


class NotIs100(Exception):
    pass


class DecodeJsonError(Exception):
    pass


class CardNotInTrade(Exception):
    pass


class MaximumPlaylist(Exception):
    pass


class NotFoundPlaylists(Exception):
    pass


class AlreadyCreatedPlaylist(Exception):
    pass


class QueueFull(Exception):
    pass


class PlaylistNotFound(Exception):
    pass
