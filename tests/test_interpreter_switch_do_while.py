from io import StringIO

from thunder_js.cli import main
from thunder_js.interpreter import InterpreterError, run_source


def run_and_collect(source, step_limit=100_000):
    lines = []
    run_source(source, output=lines.append, step_limit=step_limit)
    return lines


def run_cli(source):
    stdout = StringIO()
    stderr = StringIO()
    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)
    return exit_code, stdout.getvalue(), stderr.getvalue()


def test_matching_switch_case():
    source = """
let value = 2;

switch (value) {
    case 1:
        console.log("one");
        break;
    case 2:
        console.log("two");
        break;
    default:
        console.log("other");
}
"""

    assert run_and_collect(source) == ["two"]


def test_default_case_runs_when_no_case_matches():
    source = """
switch ("x") {
    case "a":
        console.log("a");
        break;
    default:
        console.log("default");
}
"""

    assert run_and_collect(source) == ["default"]


def test_switch_fall_through_between_cases():
    source = """
let text = "";

switch (1) {
    case 1:
        text += "a";
    case 2:
        text += "b";
    default:
        text += "c";
}

console.log(text);
"""

    assert run_and_collect(source) == ["abc"]


def test_break_prevents_switch_fall_through():
    source = """
let text = "";

switch (1) {
    case 1:
        text += "a";
        break;
    case 2:
        text += "b";
    default:
        text += "c";
}

console.log(text);
"""

    assert run_and_collect(source) == ["a"]


def test_switch_uses_strict_equality():
    source = """
switch ("1") {
    case 1:
        console.log("number");
        break;
    default:
        console.log("default");
}
"""

    assert run_and_collect(source) == ["default"]


def test_switch_expression_is_evaluated_once():
    source = """
let calls = 0;

function next() {
    calls += 1;
    return calls;
}

switch (next()) {
    case 1:
        console.log("matched");
        break;
    default:
        console.log("default");
}

console.log(calls);
"""

    assert run_and_collect(source) == ["matched", "1"]


def test_default_can_be_placed_before_later_cases():
    source = """
let text = "";

switch (9) {
    default:
        text += "default";
    case 2:
        text += "-after";
        break;
}

console.log(text);
"""

    assert run_and_collect(source) == ["default-after"]


def test_nested_switch_break_exits_nearest_switch():
    source = """
let text = "";

switch (1) {
    case 1:
        text += "a";
        switch (2) {
            case 2:
                text += "b";
                break;
            default:
                text += "bad";
        }
        text += "c";
        break;
    default:
        text += "bad";
}

console.log(text);
"""

    assert run_and_collect(source) == ["abc"]


def test_switch_inside_loop_break_only_exits_switch():
    source = """
let text = "";

for (let i = 1; i <= 3; i++) {
    switch (i) {
        case 2:
            text += "two";
            break;
        default:
            text += i;
    }
}

console.log(text);
"""

    assert run_and_collect(source) == ["1two3"]


def test_loop_inside_switch_break_only_exits_loop():
    source = """
let text = "";

switch ("loop") {
    case "loop":
        for (let i = 1; i <= 4; i++) {
            if (i === 3) {
                break;
            }
            text += i;
        }
        text += "done";
        break;
    default:
        text += "bad";
}

console.log(text);
"""

    assert run_and_collect(source) == ["12done"]


def test_do_while_executes_once_when_condition_is_false():
    source = """
let count = 0;

do {
    count += 1;
} while (false);

console.log(count);
"""

    assert run_and_collect(source) == ["1"]


def test_do_while_runs_multiple_iterations():
    source = """
let i = 0;
let text = "";

do {
    i += 1;
    text += i;
} while (i < 3);

console.log(text);
"""

    assert run_and_collect(source) == ["123"]


def test_break_in_do_while():
    source = """
let i = 0;
let text = "";

do {
    i += 1;
    if (i === 3) {
        break;
    }
    text += i;
} while (i < 5);

console.log(text);
"""

    assert run_and_collect(source) == ["12"]


def test_continue_in_do_while():
    source = """
let i = 0;
let text = "";

do {
    i += 1;
    if (i === 2) {
        continue;
    }
    text += i;
} while (i < 3);

console.log(text);
"""

    assert run_and_collect(source) == ["13"]


def test_infinite_do_while_is_stopped_by_step_limit():
    source = """
do {
} while (true);
"""

    try:
        run_source(source, output=lambda line: None, step_limit=10)
    except InterpreterError as error:
        assert "Execution step limit exceeded" in str(error)
    else:
        raise AssertionError("Expected infinite do while loop to hit the step limit")


def test_break_outside_switch_or_loop_is_rejected():
    exit_code, stdout, stderr = run_cli("break;")

    assert exit_code == 1
    assert stdout == ""
    assert "break used outside of a loop" in stderr
    assert "Traceback" not in stderr
