class EditContainer:
    def __init__(self):
        self._name: str | None = None

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
