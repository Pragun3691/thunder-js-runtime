"""JavaScript built-ins used by the interpreter."""

import math
from collections.abc import Callable

from thunder_js.environment import Environment
from thunder_js.values import JS_UNDEFINED, format_value, is_nan, is_number, to_number


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


class MathFloor(JSCallable):
    """Implementation of Math.floor."""

    def call(self, arguments: list[object]) -> object:
        value = to_number(arguments[0] if arguments else JS_UNDEFINED)

        if is_nan(value):
            return value
        if is_number(value) and math.isinf(value):
            return value

        return math.floor(value)


def create_global_environment(output: Callable[[str], None]) -> Environment:
    environment = Environment()
    environment.define("console", {"log": ConsoleLog(output)}, mutable=False)
    environment.define("Math", {"floor": MathFloor()}, mutable=False)
    return environment
