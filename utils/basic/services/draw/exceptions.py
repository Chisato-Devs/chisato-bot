__all__ = (
    "DrawBadRequest",
)


class DrawBaseException(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class DrawBadRequest(DrawBaseException):
    pass
