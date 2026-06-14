from io import StringIO

import pytest

from thunder_js.cli import main
from thunder_js.interpreter import InterpreterError, run_source


def run_and_collect(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def run_cli(source):
    stdout = StringIO()
    stderr = StringIO()
    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)
    return exit_code, stdout.getvalue(), stderr.getvalue()


def test_remainder_and_exponent_assignment_on_variables():
    source = """
let x = 10;
x %= 4;
console.log(x);
x **= 3;
console.log(x);
"""

    assert run_and_collect(source) == ["2", "8"]


def test_remainder_and_exponent_assignment_on_object_properties():
    source = """
const obj = { count: 10 };
console.log(obj.count %= 4);
console.log(obj.count);
console.log(obj.count **= 3);
console.log(obj.count);
"""

    assert run_and_collect(source) == ["2", "2", "8", "8"]


def test_remainder_and_exponent_assignment_on_array_elements():
    source = """
let arr = [10, 3];
arr[0] %= 4;
arr[1] **= 2;
console.log(arr.join(","));
"""

    assert run_and_collect(source) == ["2,9"]


@pytest.mark.parametrize(
    ("operator", "initial", "expected"),
    [
        ("=", 9, "1"),
        ("+=", 10, "11"),
        ("-=", 10, "9"),
        ("*=", 10, "10"),
        ("/=", 10, "10"),
        ("%=", 10, "0"),
        ("**=", 2, "2"),
    ],
)
def test_computed_assignment_target_is_resolved_once_before_rhs(
    operator, initial, expected
):
    source = f"""
let values = [{initial}];
let i = 0;
values[i++] {operator} i;
console.log(values[0]);
console.log(i);
"""

    assert run_and_collect(source) == [expected, "1"]


def test_computed_assignment_target_reproduction_case():
    source = """
let a = [9];
let i = 0;
a[i++] = i;

console.log(a[0]);
console.log(i);
"""

    assert run_and_collect(source) == ["1", "1"]


def test_prefix_and_postfix_updates_on_object_properties_return_old_and_new_values():
    source = """
let obj = { count: 3 };
console.log(obj.count++);
console.log(++obj.count);
console.log(obj.count--);
console.log(--obj.count);
console.log(obj.count);
"""

    assert run_and_collect(source) == ["3", "5", "5", "3", "3"]


def test_prefix_and_postfix_updates_on_array_indexes_return_old_and_new_values():
    source = """
let arr = [3];
console.log(arr[0]++);
console.log(++arr[0]);
console.log(arr[0]--);
console.log(--arr[0]);
console.log(arr[0]);
"""

    assert run_and_collect(source) == ["3", "5", "5", "3", "3"]


@pytest.mark.parametrize(
    ("expression", "initial", "expected_lines"),
    [
        ("values[i++]++", "[1, 2]", ["1", "1", "[ 2, 2 ]"]),
        ("++values[i++]", "[1, 2]", ["2", "1", "[ 2, 2 ]"]),
        ("values[i++]--", "[2, 2]", ["2", "1", "[ 1, 2 ]"]),
        ("--values[i++]", "[2, 2]", ["1", "1", "[ 1, 2 ]"]),
    ],
)
def test_computed_update_target_is_resolved_once(expression, initial, expected_lines):
    source = f"""
let values = {initial};
let i = 0;
console.log({expression});
console.log(i);
console.log(values);
"""

    assert run_and_collect(source) == expected_lines


def test_update_on_out_of_range_array_index_writes_nan_without_traceback():
    source = """
let arr = [1];
console.log(arr[2]++);
console.log(arr[2]);
console.log(arr.length);
"""

    assert run_and_collect(source) == ["undefined", "NaN", "3"]


def test_invalid_property_update_target_raises_interpreter_error():
    with pytest.raises(
        InterpreterError, match="Only object property assignment is supported yet."
    ):
        run_source('"abc".length++;', output=lambda line: None)


def test_invalid_array_index_update_is_clear_cli_error_without_traceback():
    exit_code, stdout, stderr = run_cli('let arr = [1]; arr["bad"]++;')

    assert exit_code == 1
    assert stdout == ""
    assert "Array index must be a number." in stderr
    assert "Traceback" not in stderr


def test_user_functions_print_without_python_object_reprs():
    source = """
function named() {}
console.log(named);
console.log(function inner() {});
console.log(function() {});
console.log(() => 1);
"""

    lines = run_and_collect(source)
    output = "\n".join(lines)

    assert lines == [
        "[Function: named]",
        "[Function: inner]",
        "[Function]",
        "[Function]",
    ]
    assert "object at 0x" not in output
    assert "thunder_js.interpreter.JSFunction" not in output
