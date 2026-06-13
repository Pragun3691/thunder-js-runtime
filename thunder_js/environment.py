"""A tiny environment for global names."""


class Environment:
    """Store names that the interpreter can look up."""

    def __init__(self):
        self.values: dict[str, object] = {}

    def define(self, name: str, value: object) -> None:
        self.values[name] = value

    def get(self, name: str) -> object:
        if name in self.values:
            return self.values[name]
        raise NameError(f"{name} is not defined.")
