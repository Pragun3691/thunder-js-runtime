from io import StringIO

from thunder_js.cli import main
from thunder_js.interpreter import InterpreterError, run_source


def run_and_collect(source, step_limit=100_000):
    lines = []
    run_source(source, output=lines.append, step_limit=step_limit)
    return lines


def test_public_triangle_case():
    source = """
for (let i = 1; i <= 5; i++) {
    let row = "";

    for (let j = 1; j <= i; j++) {
        row += "*";
    }

    console.log(row);
}
"""

    assert run_and_collect(source) == ["*", "**", "***", "****", "*****"]


def test_zero_iteration_for_loop():
    source = """
for (let i = 5; i < 5; i++) {
    console.log("bad");
}
console.log("done");
"""

    assert run_and_collect(source) == ["done"]


def test_zero_iteration_while_loop():
    source = """
let i = 0;
while (i > 0) {
    console.log("bad");
}
console.log("done");
"""

    assert run_and_collect(source) == ["done"]


def test_nested_loops_build_rows():
    source = """
for (let i = 1; i <= 3; i++) {
    let row = "";
    for (let j = 1; j <= 2; j++) {
        row += i;
    }
    console.log(row);
}
"""

    assert run_and_collect(source) == ["11", "22", "33"]


def test_break_exits_loop():
    source = """
let text = "";
for (let i = 1; i <= 5; i++) {
    if (i === 4) {
        break;
    }
    text += i;
}
console.log(text);
"""

    assert run_and_collect(source) == ["123"]


def test_continue_skips_to_next_iteration():
    source = """
let text = "";
for (let i = 1; i <= 5; i++) {
    if (i === 3) {
        continue;
    }
    text += i;
}
console.log(text);
"""

    assert run_and_collect(source) == ["1245"]


def test_update_expressions_prefix_and_postfix():
    source = """
let i = 1;
console.log(i++);
console.log(i);
console.log(++i);
console.log(i--);
console.log(i);
console.log(--i);
"""

    assert run_and_collect(source) == ["1", "2", "3", "3", "2", "1"]


def test_compound_assignments_inside_loop():
    source = """
let value = 8;
value += 2;
value -= 3;
value *= 4;
value /= 2;
console.log(value);
"""

    assert run_and_collect(source) == ["14"]


def test_loop_variables_use_block_scope():
    source = """
for (let i = 0; i < 1; i++) {
    let inside = "visible";
    console.log(inside);
}
console.log(i);
"""
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)

    assert exit_code == 1
    assert stdout.getvalue() == "visible\n"
    assert "i is not defined" in stderr.getvalue()


def test_for_loop_initializer_can_update_outer_variable():
    source = """
let i = 0;
for (i = 1; i <= 2; i++) {
    console.log(i);
}
console.log(i);
"""

    assert run_and_collect(source) == ["1", "2", "3"]


def test_while_loop_with_break_and_continue():
    source = """
let i = 0;
let text = "";
while (i < 5) {
    i++;
    if (i === 2) {
        continue;
    }
    if (i === 5) {
        break;
    }
    text += i;
}
console.log(text);
"""

    assert run_and_collect(source) == ["134"]


def test_infinite_loop_step_limit():
    source = """
while (true) {
}
"""

    try:
        run_source(source, output=lambda line: None, step_limit=10)
    except InterpreterError as error:
        assert "Execution step limit exceeded" in str(error)
    else:
        raise AssertionError("Expected infinite loop to hit the step limit")
