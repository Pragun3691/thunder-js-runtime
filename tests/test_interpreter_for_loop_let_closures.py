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


def test_for_loop_let_closures_capture_each_iteration_value():
    source = """
let functions = [];

for (let i = 0; i < 3; i++) {
    functions.push(() => i);
}

console.log(functions[0]());
console.log(functions[1]());
console.log(functions[2]());
"""

    assert run_and_collect(source) == ["0", "1", "2"]


def test_two_closures_in_same_iteration_share_iteration_binding():
    source = """
let functions = [];

for (let i = 0; i < 2; i++) {
    functions.push(() => i);
    functions.push(() => i);
}

console.log(functions[0]());
console.log(functions[1]());
console.log(functions[2]());
console.log(functions[3]());
"""

    assert run_and_collect(source) == ["0", "0", "1", "1"]


def test_nested_for_loop_let_closures_capture_nested_iteration_values():
    source = """
let functions = [];

for (let i = 0; i < 2; i++) {
    for (let j = 0; j < 2; j++) {
        functions.push(() => i + ":" + j);
    }
}

console.log(functions[0]());
console.log(functions[1]());
console.log(functions[2]());
console.log(functions[3]());
"""

    assert run_and_collect(source) == ["0:0", "0:1", "1:0", "1:1"]


def test_continue_still_creates_correct_next_iteration_binding():
    source = """
let functions = [];

for (let i = 0; i < 4; i++) {
    if (i === 1) {
        continue;
    }
    functions.push(() => i);
}

console.log(functions[0]());
console.log(functions[1]());
console.log(functions[2]());
"""

    assert run_and_collect(source) == ["0", "2", "3"]


def test_normal_for_loop_output_is_unchanged():
    source = """
let text = "";

for (let i = 1; i <= 3; i++) {
    text += i;
}

console.log(text);
"""

    assert run_and_collect(source) == ["123"]


def test_const_for_loop_binding_remains_immutable():
    source = """
for (const i = 0; i < 1; i++) {
    console.log(i);
}
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == "0\n"
    assert "Assignment to constant variable i." in stderr
    assert "Traceback" not in stderr
