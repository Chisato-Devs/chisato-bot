from typing import Any

from disnake import Role
from disnake.ext.commands import CheckFailure
from loguru import logger


# noinspection DuplicatedCode
class ChisatoBaseException(Exception):
    def __init__(self, message: str) -> None:
        logger.debug(f"{type(self).__name__}: {message}")
        super().__init__(message)


class NotEnoughMoney(ChisatoBaseException):
    pass


class AlreadyHavePet(ChisatoBaseException):
    pass


class DoesntHavePet(ChisatoBaseException):
    pass


class PetMaxLvl(ChisatoBaseException):
    pass


class PetReachedMaxLvl(ChisatoBaseException):
    pass


class PetStatsZero(ChisatoBaseException):
    pass


class PetLowStat(ChisatoBaseException):
    pass


class BankNotEnoughMoney(ChisatoBaseException):
    pass


class BankLessThanZero(ChisatoBaseException):
    pass


class BankBalanceMax(ChisatoBaseException):
    pass


# noinspection DuplicatedCode
class AlreadyHaveWork(ChisatoBaseException):
    pass


class DoesntHaveWork(ChisatoBaseException):
    pass


class AlreadyMarried(ChisatoBaseException):
    pass


class NotMarried(ChisatoBaseException):
    pass


class MarryNotEnoughMoney(ChisatoBaseException):
    pass


class AlreadyInShop(ChisatoBaseException):
    pass


class MaxShopItems(ChisatoBaseException):
    pass


class NotFoundItem(ChisatoBaseException):
    pass


class SubjectEnded(ChisatoBaseException):
    pass


class TranslationError(ChisatoBaseException):
    pass


class AlreadyHaveThisSubject(ChisatoBaseException):
    pass


class DoesntHaveAgreedRole(CheckFailure):
    def __init__(self, message: str, required_roles: list[Role], *args: Any) -> None:
        self.required_roles = required_roles
        super().__init__(message, *args)


# noinspection DuplicatedCode
class MaxPrestige(ChisatoBaseException):
    pass


class NotIs100(ChisatoBaseException):
    pass


class DecodeJsonError(ChisatoBaseException):
    pass


class CardNotInTrade(ChisatoBaseException):
    pass


class MaximumPlaylist(ChisatoBaseException):
    pass


class NotFoundPlaylists(ChisatoBaseException):
    pass


class AlreadyCreatedPlaylist(ChisatoBaseException):
    pass


class QueueFull(ChisatoBaseException):
    pass


class PlaylistNotFound(ChisatoBaseException):
    pass
