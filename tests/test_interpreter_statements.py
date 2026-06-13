from io import StringIO

from thunder_js.cli import main
from thunder_js.interpreter import InterpreterError, run_source


def run_and_collect(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def test_public_odd_even_case_outputs_odd():
    source = """
let num = 7;

if (num % 2 === 0) {
    console.log(num + " is Even");
} else {
    console.log(num + " is Odd");
}
"""

    assert run_and_collect(source) == ["7 is Odd"]


def test_public_odd_even_shape_outputs_even_for_eight():
    source = """
let num = 8;

if (num % 2 === 0) {
    console.log(num + " is Even");
} else {
    console.log(num + " is Odd");
}
"""

    assert run_and_collect(source) == ["8 is Even"]


def test_odd_even_shape_handles_zero():
    source = """
let num = 0;
if (num % 2 === 0) {
    console.log(num + " is Even");
} else {
    console.log(num + " is Odd");
}
"""

    assert run_and_collect(source) == ["0 is Even"]


def test_odd_even_shape_handles_negative_numbers():
    source = """
let num = -3;
if (num % 2 === 0) {
    console.log(num + " is Even");
} else {
    console.log(num + " is Odd");
}
"""

    assert run_and_collect(source) == ["-3 is Odd"]


def test_number_and_string_concatenation_with_variables():
    source = """
let num = 7;
console.log(num + " is Odd");
console.log("value: " + num);
"""

    assert run_and_collect(source) == ["7 is Odd", "value: 7"]


def test_variable_reassignment():
    source = """
let num = 7;
num = 8;
console.log(num);
num += 2;
console.log(num);
"""

    assert run_and_collect(source) == ["8", "10"]


def test_const_reassignment_error_goes_to_stderr_only_through_cli():
    source = """
const value = 1;
value = 2;
console.log(value);
"""
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "Assignment to constant variable value" in stderr.getvalue()


def test_variable_shadowing_inside_block():
    source = """
let value = "outer";
{
    let value = "inner";
    console.log(value);
}
console.log(value);
"""

    assert run_and_collect(source) == ["inner", "outer"]


def test_block_variables_do_not_leak_outside():
    source = """
{
    let hidden = 10;
}
console.log(hidden);
"""

    stdout = StringIO()
    stderr = StringIO()
    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "hidden is not defined" in stderr.getvalue()


def test_assignment_updates_parent_scope_from_nested_block():
    source = """
let value = 1;
{
    value = 3;
}
console.log(value);
"""

    assert run_and_collect(source) == ["3"]


def test_else_if_runs_matching_branch():
    source = """
let num = 0;
if (num > 0) {
    console.log("positive");
} else if (num < 0) {
    console.log("negative");
} else {
    console.log("zero");
}
"""

    assert run_and_collect(source) == ["zero"]


def test_truthy_and_falsy_values_in_if_conditions():
    source = """
if (0) {
    console.log("bad zero");
} else {
    console.log("zero is falsy");
}

if ("hello") {
    console.log("string is truthy");
}

if (null) {
    console.log("bad null");
} else if (undefined) {
    console.log("bad undefined");
} else {
    console.log("null and undefined are falsy");
}
"""

    assert run_and_collect(source) == [
        "zero is falsy",
        "string is truthy",
        "null and undefined are falsy",
    ]


def test_runtime_const_error_can_be_caught_directly():
    source = """
const value = 1;
value = 2;
"""

    try:
        run_source(source, output=lambda line: None)
    except InterpreterError as error:
        assert "Assignment to constant variable value" in str(error)
    else:
        raise AssertionError("Expected const reassignment to fail")
