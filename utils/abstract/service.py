class AbstractService:
    async def __aenter__(self) -> "AbstractService":
        return self

    async def __aexit__(self, *args):
        ...

    def __await__(self):
        return (yield from self.__aenter__())
