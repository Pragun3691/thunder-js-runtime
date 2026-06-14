"""JavaScript-like values and coercion helpers."""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class JSNull:
    """The JavaScript null value."""


@dataclass(frozen=True)
class JSUndefined:
    """The JavaScript undefined value."""


@dataclass
class JSArray:
    """Small runtime array value used by string split()."""

    items: list[object]


@dataclass
class JSObject:
    """Small runtime object value."""

    properties: dict[str, object]


@dataclass(frozen=True)
class JSDate:
    """Small runtime Date value storing milliseconds since Unix epoch."""

    timestamp_ms: int


JS_NULL = JSNull()
JS_UNDEFINED = JSUndefined()


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_nan(value: object) -> bool:
    return isinstance(value, float) and math.isnan(value)


def to_boolean(value: object) -> bool:
    if value is JS_NULL or value is JS_UNDEFINED:
        return False
    if isinstance(value, bool):
        return value
    if is_number(value):
        return value != 0 and not is_nan(value)
    if isinstance(value, str):
        return value != ""
    return True


def to_number(value: object) -> float:
    if value is JS_UNDEFINED:
        return math.nan
    if value is JS_NULL:
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if is_number(value):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if text == "":
            return 0.0
        try:
            return float(text)
        except ValueError:
            return math.nan
    return math.nan


def to_string(value: object) -> str:
    if value is JS_UNDEFINED:
        return "undefined"
    if value is JS_NULL:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if is_number(value):
        return format_number(float(value))
    if isinstance(value, str):
        return value
    if isinstance(value, JSArray):
        return ",".join(to_string(item) for item in value.items)
    if isinstance(value, JSObject):
        return "[object Object]"
    if isinstance(value, JSDate):
        return "[object Date]"
    return str(value)


def format_number(value: float) -> str:
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Infinity" if value > 0 else "-Infinity"
    if value == 0:
        return "0"
    if value.is_integer():
        return str(int(value))
    return str(value)


def format_value(value: object) -> str:
    return to_string(value)


def inspect_value(value: object) -> str:
    return _inspect_value(value, set(), is_top_level=True)


def _inspect_value(value: object, seen: set[int], is_top_level: bool) -> str:
    if value is JS_UNDEFINED:
        return "undefined"
    if value is JS_NULL:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if is_number(value):
        return format_number(float(value))
    if isinstance(value, str):
        if is_top_level:
            return value
        return "'" + _escape_inspect_string(value) + "'"
    if isinstance(value, JSArray):
        return _inspect_array(value, seen)
    if isinstance(value, JSObject):
        return _inspect_object(value, seen)
    if isinstance(value, dict):
        return _inspect_dict(value, seen)
    if isinstance(value, JSDate):
        return to_string(value)
    if hasattr(value, "call"):
        text = str(value)
        if " object at 0x" in text:
            return "[Function]"
        return text
    return to_string(value)


def _inspect_array(array: JSArray, seen: set[int]) -> str:
    array_id = id(array)
    if array_id in seen:
        return "[Circular]"

    seen.add(array_id)
    try:
        if not array.items:
            return "[]"

        items = [
            _inspect_value(item, seen, is_top_level=False)
            for item in array.items
        ]
        return "[ " + ", ".join(items) + " ]"
    finally:
        seen.remove(array_id)


def _inspect_object(js_object: JSObject, seen: set[int]) -> str:
    object_id = id(js_object)
    if object_id in seen:
        return "[Circular]"

    seen.add(object_id)
    try:
        if not js_object.properties:
            return "{}"

        properties = []
        for key, value in js_object.properties.items():
            properties.append(
                _inspect_key(key)
                + ": "
                + _inspect_value(value, seen, is_top_level=False)
            )
        return "{ " + ", ".join(properties) + " }"
    finally:
        seen.remove(object_id)


def _inspect_dict(value: dict[str, object], seen: set[int]) -> str:
    object_id = id(value)
    if object_id in seen:
        return "[Circular]"

    seen.add(object_id)
    try:
        if not value:
            return "{}"

        properties = []
        for key, property_value in value.items():
            properties.append(
                _inspect_key(key)
                + ": "
                + _inspect_value(property_value, seen, is_top_level=False)
            )
        return "{ " + ", ".join(properties) + " }"
    finally:
        seen.remove(object_id)


def _inspect_key(key: str) -> str:
    if key and (key[0].isalpha() or key[0] in ("_", "$")):
        if all(character.isalnum() or character in ("_", "$") for character in key):
            return key
    return "'" + _escape_inspect_string(key) + "'"


def _escape_inspect_string(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("'", "\\'")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )


def strict_equal(left: object, right: object) -> bool:
    if left is JS_NULL or right is JS_NULL:
        return left is JS_NULL and right is JS_NULL
    if left is JS_UNDEFINED or right is JS_UNDEFINED:
        return left is JS_UNDEFINED and right is JS_UNDEFINED
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if is_number(left) and is_number(right):
        if is_nan(left) or is_nan(right):
            return False
        return float(left) == float(right)
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    return left is right


def loose_equal(left: object, right: object) -> bool:
    if strict_equal(left, right):
        return True
    if (left is JS_NULL and right is JS_UNDEFINED) or (
        left is JS_UNDEFINED and right is JS_NULL
    ):
        return True
    if isinstance(left, bool):
        return loose_equal(to_number(left), right)
    if isinstance(right, bool):
        return loose_equal(left, to_number(right))
    if is_number(left) and isinstance(right, str):
        return strict_equal(left, to_number(right))
    if isinstance(left, str) and is_number(right):
        return strict_equal(to_number(left), right)
    return False


def js_add(left: object, right: object) -> object:
    left_primitive = _to_primitive_for_add(left)
    right_primitive = _to_primitive_for_add(right)

    if isinstance(left_primitive, str) or isinstance(right_primitive, str):
        return to_string(left_primitive) + to_string(right_primitive)
    return to_number(left_primitive) + to_number(right_primitive)


def _to_primitive_for_add(value: object) -> object:
    if isinstance(value, (JSArray, JSObject, JSDate)):
        return to_string(value)
    return value


def js_divide(left: object, right: object) -> float:
    left_number = to_number(left)
    right_number = to_number(right)

    if is_nan(left_number) or is_nan(right_number):
        return math.nan
    if right_number == 0:
        if left_number == 0:
            return math.nan
        sign = 1 if left_number > 0 else -1
        return math.inf * sign
    return left_number / right_number


def js_remainder(left: object, right: object) -> float:
    left_number = to_number(left)
    right_number = to_number(right)

    if is_nan(left_number) or is_nan(right_number) or right_number == 0:
        return math.nan
    return math.fmod(left_number, right_number)
