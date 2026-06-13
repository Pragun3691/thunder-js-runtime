from io import StringIO

from thunder_js.cli import main
from thunder_js.interpreter import run_source


def run_and_collect(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def test_public_armstrong_case():
    source = """
function isArmstrong(num) {
    let temp = num;
    let sum = 0;

    while (temp > 0) {
        let digit = temp % 10;
        sum += digit ** 3;
        temp = Math.floor(temp / 10);
    }

    return sum === num;
}

console.log(isArmstrong(153));
console.log(isArmstrong(123));
"""

    assert run_and_collect(source) == ["true", "false"]


def test_simple_add_function():
    source = """
function add(a, b) {
    return a + b;
}

console.log(add(2, 3));
"""

    assert run_and_collect(source) == ["5"]


def test_multiple_parameters():
    source = """
function mix(a, b, c) {
    return a + "-" + b + "-" + c;
}

console.log(mix("x", "y", "z"));
"""

    assert run_and_collect(source) == ["x-y-z"]


def test_function_local_variables_do_not_leak():
    source = """
function makeValue() {
    let local = 42;
    return local;
}

console.log(makeValue());
console.log(local);
"""
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)

    assert exit_code == 1
    assert stdout.getvalue() == "42\n"
    assert "local is not defined" in stderr.getvalue()


def test_function_can_access_global_variables():
    source = """
let base = 10;

function addBase(value) {
    return base + value;
}

console.log(addBase(5));
"""

    assert run_and_collect(source) == ["15"]


def test_nested_function_calls():
    source = """
function add(a, b) {
    return a + b;
}

function double(value) {
    return value * 2;
}

console.log(double(add(2, 3)));
"""

    assert run_and_collect(source) == ["10"]


def test_recursion():
    source = """
function factorial(n) {
    if (n <= 1) {
        return 1;
    }

    return n * factorial(n - 1);
}

console.log(factorial(5));
"""

    assert run_and_collect(source) == ["120"]


def test_return_from_inside_if():
    source = """
function sign(value) {
    if (value < 0) {
        return "negative";
    }

    return "non-negative";
}

console.log(sign(-1));
console.log(sign(0));
"""

    assert run_and_collect(source) == ["negative", "non-negative"]


def test_return_from_inside_while():
    source = """
function firstPositive(limit) {
    let i = 0;

    while (i < limit) {
        i++;

        if (i > 0) {
            return i;
        }
    }

    return -1;
}

console.log(firstPositive(3));
"""

    assert run_and_collect(source) == ["1"]


def test_code_after_return_does_not_execute():
    source = """
function stopEarly() {
    console.log("before");
    return 7;
    console.log("after");
}

console.log(stopEarly());
"""

    assert run_and_collect(source) == ["before", "7"]


def test_missing_arguments_become_undefined():
    source = """
function show(a, b) {
    console.log(a);
    console.log(b);
}

show(1);
"""

    assert run_and_collect(source) == ["1", "undefined"]


def test_math_floor_with_positive_and_negative_numbers():
    source = """
console.log(Math.floor(3.9));
console.log(Math.floor(-3.1));
"""

    assert run_and_collect(source) == ["3", "-4"]


def test_return_without_value_is_undefined():
    source = """
function nothing() {
    return;
}

console.log(nothing());
"""

    assert run_and_collect(source) == ["undefined"]
