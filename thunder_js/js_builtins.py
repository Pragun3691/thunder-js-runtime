"""JavaScript built-ins used by the interpreter."""

import math
import random
import re
from collections.abc import Callable

from thunder_js.environment import Environment
from thunder_js.values import (
    JS_UNDEFINED,
    format_value,
    is_nan,
    is_number,
    to_boolean,
    to_number,
    to_string,
)


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


class BuiltInFunction(JSCallable):
    """Wrap a Python helper so it can be called from JavaScript code."""

    def __init__(self, function: Callable[[list[object]], object]):
        self.function = function

    def call(self, arguments: list[object]) -> object:
        return self.function(arguments)


def _first_number(arguments: list[object]) -> float:
    return to_number(arguments[0] if arguments else JS_UNDEFINED)


def _math_abs(arguments: list[object]) -> float:
    return abs(_first_number(arguments))


def _math_ceil(arguments: list[object]) -> object:
    value = _first_number(arguments)
    if _is_nan_or_infinite(value):
        return value
    return math.ceil(value)


def _math_floor(arguments: list[object]) -> object:
    value = _first_number(arguments)
    if _is_nan_or_infinite(value):
        return value
    return math.floor(value)


def _math_round(arguments: list[object]) -> object:
    value = _first_number(arguments)
    if _is_nan_or_infinite(value):
        return value
    return math.floor(value + 0.5)


def _math_max(arguments: list[object]) -> float:
    if not arguments:
        return -math.inf

    numbers = [to_number(argument) for argument in arguments]
    if any(is_nan(number) for number in numbers):
        return math.nan
    return max(numbers)


def _math_min(arguments: list[object]) -> float:
    if not arguments:
        return math.inf

    numbers = [to_number(argument) for argument in arguments]
    if any(is_nan(number) for number in numbers):
        return math.nan
    return min(numbers)


def _math_pow(arguments: list[object]) -> float:
    base = to_number(arguments[0] if arguments else JS_UNDEFINED)
    exponent = to_number(arguments[1] if len(arguments) > 1 else JS_UNDEFINED)

    if is_nan(base) or is_nan(exponent):
        return math.nan
    if base < 0 and not exponent.is_integer():
        return math.nan

    try:
        return base**exponent
    except (OverflowError, ValueError):
        return math.nan


def _math_sqrt(arguments: list[object]) -> float:
    value = _first_number(arguments)
    if is_nan(value):
        return value
    if value < 0:
        return math.nan
    return math.sqrt(value)


def _math_trunc(arguments: list[object]) -> object:
    value = _first_number(arguments)
    if _is_nan_or_infinite(value):
        return value
    return math.trunc(value)


def _math_random(arguments: list[object]) -> float:
    return random.random()


def _number_function(arguments: list[object]) -> float:
    if not arguments:
        return 0.0
    return to_number(arguments[0])


def _string_function(arguments: list[object]) -> str:
    if not arguments:
        return "undefined"
    return to_string(arguments[0])


def _boolean_function(arguments: list[object]) -> bool:
    if not arguments:
        return False
    return to_boolean(arguments[0])


def _parse_int(arguments: list[object]) -> object:
    text = to_string(arguments[0] if arguments else JS_UNDEFINED).lstrip()
    match = re.match(r"([+-]?)(?:0[xX]([0-9a-fA-F]+)|([0-9]+))", text)

    if match is None:
        return math.nan

    sign_text, hex_digits, decimal_digits = match.groups()
    sign = -1 if sign_text == "-" else 1

    if hex_digits is not None:
        return sign * int(hex_digits, 16)
    return sign * int(decimal_digits, 10)


def _parse_float(arguments: list[object]) -> float:
    text = to_string(arguments[0] if arguments else JS_UNDEFINED).lstrip()
    match = re.match(
        r"[+-]?(?:Infinity|(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))(?:[eE][+-]?[0-9]+)?)",
        text,
    )

    if match is None:
        return math.nan

    try:
        return float(match.group(0))
    except ValueError:
        return math.nan


def _is_nan_or_infinite(value: object) -> bool:
    return is_nan(value) or (is_number(value) and math.isinf(value))


def _math_object() -> dict[str, JSCallable]:
    return {
        "abs": BuiltInFunction(_math_abs),
        "ceil": BuiltInFunction(_math_ceil),
        "floor": BuiltInFunction(_math_floor),
        "round": BuiltInFunction(_math_round),
        "max": BuiltInFunction(_math_max),
        "min": BuiltInFunction(_math_min),
        "pow": BuiltInFunction(_math_pow),
        "sqrt": BuiltInFunction(_math_sqrt),
        "trunc": BuiltInFunction(_math_trunc),
        "random": BuiltInFunction(_math_random),
    }


def create_global_environment(output: Callable[[str], None]) -> Environment:
    environment = Environment()
    environment.define("console", {"log": ConsoleLog(output)}, mutable=False)
    environment.define("Math", _math_object(), mutable=False)
    environment.define("Number", BuiltInFunction(_number_function), mutable=False)
    environment.define("String", BuiltInFunction(_string_function), mutable=False)
    environment.define("Boolean", BuiltInFunction(_boolean_function), mutable=False)
    environment.define("parseInt", BuiltInFunction(_parse_int), mutable=False)
    environment.define("parseFloat", BuiltInFunction(_parse_float), mutable=False)
    return environment
