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


def test_function_declaration_is_hoisted_in_program_scope():
    source = """
console.log(add(2, 3));
function add(a, b) {
    return a + b;
}
"""

    assert run_and_collect(source) == ["5"]


def test_function_declaration_is_hoisted_in_block_scope():
    source = """
{
    console.log(add(2, 3));
    function add(a, b) {
        return a + b;
    }
}
"""

    assert run_and_collect(source) == ["5"]


def test_invalid_break_continue_and_return_contexts_are_parser_errors():
    cases = [
        ("break;", "break used outside of a loop"),
        ("continue;", "continue used outside of a loop"),
        ("return 1;", "return used outside of a function"),
    ]

    for source, message in cases:
        exit_code, stdout, stderr = run_cli(source)

        assert exit_code == 1
        assert stdout == ""
        assert message in stderr
        assert "Traceback" not in stderr


def test_break_inside_function_cannot_affect_caller_loop():
    break_source = """
while (true) {
    function stop() {
        break;
    }
    stop();
}
"""
    continue_source = """
while (true) {
    function skip() {
        continue;
    }
    skip();
}
"""
    exit_code, stdout, stderr = run_cli(break_source)

    assert exit_code == 1
    assert stdout == ""
    assert "break used outside of a loop" in stderr
    assert "Traceback" not in stderr

    exit_code, stdout, stderr = run_cli(continue_source)

    assert exit_code == 1
    assert stdout == ""
    assert "continue used outside of a loop" in stderr
    assert "Traceback" not in stderr


def test_array_bad_indexes_and_nan_method_indexes_do_not_leak_python_errors():
    source = """
let arr = [1, 2, 3];
console.log(arr["abc"]);
console.log(arr[undefined]);
console.log(arr.slice("abc").join(","));
console.log(arr.includes(2, "abc"));
console.log(arr.indexOf(2, "abc"));
console.log(arr.splice("abc", 1).join(","));
console.log(arr.join(","));
"""

    assert run_and_collect(source) == [
        "undefined",
        "undefined",
        "1,2,3",
        "true",
        "1",
        "1",
        "2,3",
    ]


def test_math_floor_infinity_does_not_leak_python_errors():
    exit_code, stdout, stderr = run_cli(
        """
console.log(Math.floor(1 / 0));
console.log(Math.floor(-1 / 0));
"""
    )

    assert exit_code == 0
    assert stdout == "Infinity\n-Infinity\n"
    assert stderr == ""


def test_excessive_recursion_is_interpreter_error_without_traceback():
    source = """
function recurse() {
    return recurse();
}

recurse();
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert "Maximum call stack size exceeded" in stderr
    assert "Traceback" not in stderr


def test_exponentiation_edge_cases_and_invalid_unary_left_side():
    assert run_and_collect("console.log(2 ** 3 ** 2);") == ["512"]
    assert run_and_collect("console.log(2 ** -2);") == ["0.25"]
    assert run_and_collect("console.log((-1) ** 0.5);") == ["NaN"]
    assert run_and_collect("console.log((-2) ** 2);") == ["4"]

    exit_code, stdout, stderr = run_cli("console.log(-2 ** 2);")

    assert exit_code == 1
    assert stdout == ""
    assert "Unary expression cannot be the left side of '**'" in stderr
    assert "Traceback" not in stderr
