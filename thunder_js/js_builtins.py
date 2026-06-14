"""JavaScript built-ins used by the interpreter."""

import json
import math
import random
import re
from collections.abc import Callable
from datetime import datetime, timezone

from thunder_js.environment import Environment
from thunder_js.values import (
    JSArray,
    JSDate,
    JS_NULL,
    JSObject,
    JS_UNDEFINED,
    format_number,
    inspect_value,
    is_nan,
    is_number,
    to_boolean,
    to_number,
    to_string,
)


class BuiltInError(Exception):
    """Raised when a built-in function receives invalid JavaScript values."""


class JSCallable:
    """Base class for values that can be called like functions."""

    def call(self, arguments: list[object]) -> object:
        raise NotImplementedError


class ConsoleLog(JSCallable):
    """Implementation of console.log."""

    def __init__(self, output: Callable[[str], None]):
        self.output = output

    def call(self, arguments: list[object]) -> object:
        self.output(" ".join(inspect_value(argument) for argument in arguments))
        return JS_UNDEFINED


class BuiltInFunction(JSCallable):
    """Wrap a Python helper so it can be called from JavaScript code."""

    def __init__(self, function: Callable[[list[object]], object]):
        self.function = function

    def call(self, arguments: list[object]) -> object:
        try:
            return self.function(arguments)
        except ValueError as error:
            raise BuiltInError(str(error)) from error


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


def _date_now(arguments: list[object]) -> int:
    return _current_time_ms()


def construct_date(arguments: list[object]) -> JSDate:
    if not arguments:
        return JSDate(_current_time_ms())

    timestamp = to_number(arguments[0])
    if is_nan(timestamp) or math.isinf(timestamp):
        raise ValueError("Invalid Date timestamp.")

    timestamp_ms = int(timestamp)
    _date_to_datetime(JSDate(timestamp_ms))
    return JSDate(timestamp_ms)


def date_part(date: JSDate, part: str) -> int:
    moment = _date_to_datetime(date)

    if part == "year":
        return moment.year
    if part == "month":
        return moment.month - 1
    if part == "date":
        return moment.day
    if part == "day":
        return (moment.weekday() + 1) % 7
    if part == "hours":
        return moment.hour
    if part == "minutes":
        return moment.minute
    if part == "seconds":
        return moment.second

    raise ValueError(f"Unknown Date part {part}.")


def date_to_iso_string(date: JSDate) -> str:
    moment = _date_to_datetime(date)
    text = moment.isoformat(timespec="milliseconds")
    return text.replace("+00:00", "Z")


def _current_time_ms() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp() * 1000)


def _date_to_datetime(date: JSDate) -> datetime:
    try:
        return datetime.fromtimestamp(date.timestamp_ms / 1000, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as error:
        raise ValueError("Invalid Date timestamp.") from error


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


def _array_is_array(arguments: list[object]) -> bool:
    value = arguments[0] if arguments else JS_UNDEFINED
    return isinstance(value, JSArray)


def _object_argument(arguments: list[object], method_name: str) -> JSObject:
    value = arguments[0] if arguments else JS_UNDEFINED
    if not isinstance(value, JSObject):
        raise ValueError(f"Object.{method_name} argument must be an object.")
    return value


def _object_keys(arguments: list[object]) -> JSArray:
    value = _object_argument(arguments, "keys")
    return JSArray(list(value.properties.keys()))


def _object_values(arguments: list[object]) -> JSArray:
    value = _object_argument(arguments, "values")
    return JSArray(list(value.properties.values()))


def _object_entries(arguments: list[object]) -> JSArray:
    value = _object_argument(arguments, "entries")
    return JSArray(
        [
            JSArray([key, property_value])
            for key, property_value in value.properties.items()
        ]
    )


def _json_stringify(arguments: list[object]) -> object:
    value = arguments[0] if arguments else JS_UNDEFINED
    serialized = _json_serialize(value, set(), in_array=False)

    if serialized is None:
        return JS_UNDEFINED
    return serialized


def _json_serialize(
    value: object,
    seen: set[int],
    in_array: bool,
) -> str | None:
    if value is JS_UNDEFINED or isinstance(value, JSCallable):
        return "null" if in_array else None
    if value is JS_NULL:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if is_number(value):
        number = float(value)
        if is_nan(number) or math.isinf(number):
            return "null"
        return format_number(number)
    if isinstance(value, str):
        return json.dumps(value)

    if isinstance(value, JSArray):
        value_id = id(value)
        if value_id in seen:
            raise ValueError("Converting circular structure to JSON.")

        seen.add(value_id)
        try:
            items = []
            for item in value.items:
                serialized = _json_serialize(item, seen, in_array=True)
                items.append("null" if serialized is None else serialized)
            return "[" + ",".join(items) + "]"
        finally:
            seen.remove(value_id)

    if isinstance(value, JSObject):
        value_id = id(value)
        if value_id in seen:
            raise ValueError("Converting circular structure to JSON.")

        seen.add(value_id)
        try:
            properties = []
            for key, property_value in value.properties.items():
                serialized = _json_serialize(property_value, seen, in_array=False)
                if serialized is not None:
                    properties.append(json.dumps(key) + ":" + serialized)
            return "{" + ",".join(properties) + "}"
        finally:
            seen.remove(value_id)

    return "null" if in_array else None


def _is_nan_function(arguments: list[object]) -> bool:
    return is_nan(_first_number(arguments))


def _is_finite_function(arguments: list[object]) -> bool:
    value = _first_number(arguments)
    return not is_nan(value) and not math.isinf(value)


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


def _math_object() -> dict[str, object]:
    return {
        "PI": math.pi,
        "E": math.e,
        "LN2": math.log(2),
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


def _array_object() -> dict[str, object]:
    return {
        "isArray": BuiltInFunction(_array_is_array),
    }


def _object_object() -> dict[str, object]:
    return {
        "keys": BuiltInFunction(_object_keys),
        "values": BuiltInFunction(_object_values),
        "entries": BuiltInFunction(_object_entries),
    }


def _json_object() -> dict[str, object]:
    return {
        "stringify": BuiltInFunction(_json_stringify),
    }


def create_global_environment(output: Callable[[str], None]) -> Environment:
    environment = Environment()
    environment.define("console", {"log": ConsoleLog(output)}, mutable=False)
    environment.define("Math", _math_object(), mutable=False)
    environment.define("Array", _array_object(), mutable=False)
    environment.define("Object", _object_object(), mutable=False)
    environment.define("JSON", _json_object(), mutable=False)
    environment.define(
        "Date",
        {"now": BuiltInFunction(_date_now)},
        mutable=False,
    )
    environment.define("Number", BuiltInFunction(_number_function), mutable=False)
    environment.define("String", BuiltInFunction(_string_function), mutable=False)
    environment.define("Boolean", BuiltInFunction(_boolean_function), mutable=False)
    environment.define("NaN", math.nan, mutable=False)
    environment.define("Infinity", math.inf, mutable=False)
    environment.define("isNaN", BuiltInFunction(_is_nan_function), mutable=False)
    environment.define("isFinite", BuiltInFunction(_is_finite_function), mutable=False)
    environment.define("parseInt", BuiltInFunction(_parse_int), mutable=False)
    environment.define("parseFloat", BuiltInFunction(_parse_float), mutable=False)
    return environment
