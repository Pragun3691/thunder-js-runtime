from io import StringIO

from thunder_js.cli import main
from thunder_js.interpreter import run_source


def run_and_collect(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def run_cli(source):
    stdout = StringIO()
    stderr = StringIO()
    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)
    return exit_code, stdout.getvalue(), stderr.getvalue()


def test_math_abs_with_positive_negative_and_decimal_values():
    source = """
console.log(Math.abs(5));
console.log(Math.abs(-5));
console.log(Math.abs(-2.5));
"""

    assert run_and_collect(source) == ["5", "5", "2.5"]


def test_math_ceil_floor_round_and_trunc():
    source = """
console.log(Math.ceil(2.1));
console.log(Math.ceil(-2.9));
console.log(Math.floor(2.9));
console.log(Math.floor(-2.1));
console.log(Math.round(2.5));
console.log(Math.round(-2.5));
console.log(Math.trunc(2.9));
console.log(Math.trunc(-2.9));
"""

    assert run_and_collect(source) == ["3", "-2", "2", "-3", "3", "-2", "2", "-2"]


def test_math_max_and_min():
    source = """
console.log(Math.max(1, 5, -2, "7"));
console.log(Math.min(1, 5, -2, "7"));
console.log(Math.max());
console.log(Math.min());
console.log(Math.max(1, "bad"));
console.log(Math.min(1, "bad"));
"""

    assert run_and_collect(source) == [
        "7",
        "-2",
        "-Infinity",
        "Infinity",
        "NaN",
        "NaN",
    ]


def test_math_pow_and_sqrt():
    source = """
console.log(Math.pow(2, 3));
console.log(Math.pow(4, 0.5));
console.log(Math.pow(-1, 0.5));
console.log(Math.sqrt(9));
console.log(Math.sqrt(2.25));
console.log(Math.sqrt(-1));
"""

    assert run_and_collect(source) == ["8", "2", "NaN", "3", "1.5", "NaN"]


def test_math_helpers_coerce_strings_booleans_null_and_undefined():
    source = """
console.log(Math.abs("-4"));
console.log(Math.ceil("2.1"));
console.log(Math.floor(true));
console.log(Math.round(false));
console.log(Math.trunc(null));
console.log(Math.sqrt(undefined));
"""

    assert run_and_collect(source) == ["4", "3", "1", "0", "0", "NaN"]


def test_math_random_returns_number_in_range():
    source = """
let value = Math.random();
console.log(value >= 0 && value < 1);
"""

    assert run_and_collect(source) == ["true"]


def test_number_conversion():
    source = """
console.log(Number("42"));
console.log(Number("-2.5"));
console.log(Number(""));
console.log(Number("bad"));
console.log(Number(true));
console.log(Number(false));
console.log(Number(null));
console.log(Number(undefined));
console.log(Number());
"""

    assert run_and_collect(source) == [
        "42",
        "-2.5",
        "0",
        "NaN",
        "1",
        "0",
        "0",
        "NaN",
        "0",
    ]


def test_string_conversion():
    source = """
console.log(String(42));
console.log(String(-2.5));
console.log(String(true));
console.log(String(false));
console.log(String(null));
console.log(String(undefined));
console.log(String());
"""

    assert run_and_collect(source) == [
        "42",
        "-2.5",
        "true",
        "false",
        "null",
        "undefined",
        "undefined",
    ]


def test_boolean_conversion():
    source = """
console.log(Boolean(1));
console.log(Boolean(0));
console.log(Boolean(""));
console.log(Boolean("0"));
console.log(Boolean(null));
console.log(Boolean(undefined));
console.log(Boolean());
"""

    assert run_and_collect(source) == [
        "true",
        "false",
        "false",
        "true",
        "false",
        "false",
        "false",
    ]


def test_parse_int_conversion():
    source = """
console.log(parseInt("42"));
console.log(parseInt("-42.9"));
console.log(parseInt("  12px"));
console.log(parseInt("0x10"));
console.log(parseInt(""));
console.log(parseInt("bad"));
console.log(parseInt(true));
console.log(parseInt(null));
console.log(parseInt(undefined));
"""

    assert run_and_collect(source) == [
        "42",
        "-42",
        "12",
        "16",
        "NaN",
        "NaN",
        "NaN",
        "NaN",
        "NaN",
    ]


def test_parse_float_conversion():
    source = """
console.log(parseFloat("42.5"));
console.log(parseFloat("-42.5px"));
console.log(parseFloat("  .25"));
console.log(parseFloat("1e3"));
console.log(parseFloat(""));
console.log(parseFloat("bad"));
console.log(parseFloat(true));
console.log(parseFloat(null));
console.log(parseFloat(undefined));
"""

    assert run_and_collect(source) == [
        "42.5",
        "-42.5",
        "0.25",
        "1000",
        "NaN",
        "NaN",
        "NaN",
        "NaN",
        "NaN",
    ]


def test_builtins_are_callable_values():
    source = """
let convert = Number;
let stringify = String;
let truthy = Boolean;

console.log(convert("5"));
console.log(stringify(false));
console.log(truthy("hello"));
"""

    assert run_and_collect(source) == ["5", "false", "true"]


def test_edge_cases_do_not_leak_python_tracebacks():
    source = """
console.log(Math.ceil(1 / 0));
console.log(Math.floor(-1 / 0));
console.log(Math.trunc(1 / 0));
console.log(Math.sqrt(-1));
console.log(Math.pow(-1, 0.5));
console.log(parseFloat("Infinity"));
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 0
    assert stdout == "Infinity\n-Infinity\nInfinity\nNaN\nNaN\nInfinity\n"
    assert stderr == ""
    assert "Traceback" not in stderr
