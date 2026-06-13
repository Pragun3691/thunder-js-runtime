from io import StringIO
from pathlib import Path

import pytest

from thunder_js.cli import main
from thunder_js.interpreter import run_source


ROOT = Path(__file__).resolve().parents[1]


def run_and_collect(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def run_cli(source):
    stdout = StringIO()
    stderr = StringIO()
    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)
    return exit_code, stdout.getvalue(), stderr.getvalue()


def test_function_call_with_spread():
    source = """
function add(a, b, c) {
    return a + b + c;
}

let numbers = [1, 2, 3];
console.log(add(...numbers));
"""

    assert run_and_collect(source) == ["6"]


def test_multiple_spread_arguments_and_values():
    source = """
function collect(a, b, c, d, e) {
    return [a, b, c, d, e].join("-");
}

let middle = [2, 3];
let tail = [4];
console.log(collect(1, ...middle, ...tail, 5));
"""

    assert run_and_collect(source) == ["1-2-3-4-5"]


def test_rest_only_function():
    source = """
function sum(...numbers) {
    return numbers.reduce((total, value) => total + value, 0);
}

console.log(sum(1, 2, 3, 4));
"""

    assert run_and_collect(source) == ["10"]


def test_normal_parameters_before_rest():
    source = """
function collect(first, ...rest) {
    return first + ":" + rest.join(",");
}

console.log(collect("a", "b", "c"));
"""

    assert run_and_collect(source) == ["a:b,c"]


def test_empty_rest_array():
    source = """
function count(...items) {
    return items.length;
}

console.log(count());
"""

    assert run_and_collect(source) == ["0"]


def test_function_expression_with_rest():
    source = """
const join = function(prefix, ...items) {
    return prefix + items.join("|");
};

console.log(join("items:", 1, 2, 3));
"""

    assert run_and_collect(source) == ["items:1|2|3"]


def test_arrow_function_with_rest():
    source = """
const sum = (...numbers) => numbers.reduce((total, value) => total + value, 0);

console.log(sum(5, 6, 7));
"""

    assert run_and_collect(source) == ["18"]


def test_modifying_rest_array_does_not_mutate_original_argument_array():
    source = """
function touch(...items) {
    items[0] = 99;
    return items.join(",");
}

let original = [1, 2, 3];
console.log(touch(...original));
console.log(original.join(","));
"""

    assert run_and_collect(source) == ["99,2,3", "1,2,3"]


def test_invalid_rest_position_is_parser_error():
    source = """
function bad(...items, last) {
    return last;
}
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert "Rest parameter must be last." in stderr
    assert "Traceback" not in stderr


def test_only_one_rest_parameter_is_allowed():
    source = """
function bad(...first, ...second) {
    return first;
}
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert "Rest parameter must be last." in stderr
    assert "Traceback" not in stderr


def test_spreading_non_array_runtime_error():
    source = """
function identity(value) {
    return value;
}

identity(...123);
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert "Spread argument must be an array." in stderr
    assert "Traceback" not in stderr


def test_existing_array_literal_spread_still_works():
    source = """
let original = [1, 2];
let copy = [0, ...original, 3];
copy[1] = 99;

console.log(copy.join(","));
console.log(original.join(","));
"""

    assert run_and_collect(source) == ["0,99,2,3", "1,2"]


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("01_odd_even.js", ["7 is Odd"]),
        ("02_triangle.js", ["*", "**", "***", "****", "*****"]),
        ("03_palindrome.js", ["racecar is a Palindrome"]),
        (
            "04_array_reverse.js",
            ["Original: 1, 2, 3, 4, 5", "Reversed: 5, 4, 3, 2, 1"],
        ),
        ("05_armstrong.js", ["true", "false"]),
    ],
)
def test_public_examples_still_pass(filename, expected):
    source = (ROOT / "examples" / filename).read_text(encoding="utf-8")

    assert run_and_collect(source) == expected
