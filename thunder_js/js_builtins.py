"""JavaScript built-ins used by the interpreter."""

from collections.abc import Callable

from thunder_js.environment import Environment
from thunder_js.values import JS_UNDEFINED, format_value


class JSCallable:
    """Base class for values that can be called like functions."""

    def call(self, arguments: list[object]) -> object:
        raise NotImplementedError


class ConsoleLog(JSCallable):
    """Implementation of console.log."""

    def __init__(self, output: Callable[[str], None]):
        self.output = output

    def call(self, arguments: list[object]) -> object:
        self.output(" ".join(format_value(argument) for argument in arguments))
        return JS_UNDEFINED


def create_global_environment(output: Callable[[str], None]) -> Environment:
    environment = Environment()
    environment.define("console", {"log": ConsoleLog(output)})
    return environment
