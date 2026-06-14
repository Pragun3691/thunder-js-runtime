"""Lexical environments for JavaScript variables."""

from dataclasses import dataclass


@dataclass
class Binding:
    value: object
    mutable: bool


class Environment:
    """Store names and optionally look them up in a parent scope."""

    def __init__(
        self,
        parent: "Environment | None" = None,
        is_var_scope: bool = False,
    ):
        self.parent = parent
        self.is_var_scope = is_var_scope
        self.values: dict[str, Binding] = {}

    def define(self, name: str, value: object, mutable: bool = True) -> None:
        if name in self.values:
            raise NameError(f"{name} has already been declared.")
        self.values[name] = Binding(value, mutable)

    def define_var(
        self,
        name: str,
        value: object,
        assign_existing: bool = True,
    ) -> None:
        scope = self.var_scope()

        if name not in scope.values:
            scope.values[name] = Binding(value, mutable=True)
            return

        if not assign_existing:
            return

        binding = scope.values[name]
        if not binding.mutable:
            raise TypeError(f"Assignment to constant variable {name}.")
        binding.value = value

    def var_scope(self) -> "Environment":
        if self.is_var_scope or self.parent is None:
            return self
        return self.parent.var_scope()

    def has_local(self, name: str) -> bool:
        return name in self.values

    def resolve(self, name: str) -> "Environment":
        if name in self.values:
            return self
        if self.parent is not None:
            return self.parent.resolve(name)
        raise NameError(f"{name} is not defined.")

    def get(self, name: str) -> object:
        if name in self.values:
            return self.values[name].value
        if self.parent is not None:
            return self.parent.get(name)
        raise NameError(f"{name} is not defined.")

    def assign(self, name: str, value: object) -> object:
        if name in self.values:
            binding = self.values[name]
            if not binding.mutable:
                raise TypeError(f"Assignment to constant variable {name}.")
            binding.value = value
            return value
        if self.parent is not None:
            return self.parent.assign(name, value)
        raise NameError(f"{name} is not defined.")
