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


def test_for_in_object_keys_preserve_insertion_order():
    source = """
let user = { name: "Pragun", age: 20, city: "Delhi" };
let keys = [];

for (const key in user) {
    keys.push(key);
}

console.log(keys.join(","));
"""

    assert run_and_collect(source) == ["name,age,city"]


def test_for_in_array_indexes_are_strings():
    source = """
let indexes = [];

for (const index in ["a", "b", "c"]) {
    indexes.push(index + ":" + (index === String(Number(index))));
}

console.log(indexes.join("|"));
"""

    assert run_and_collect(source) == ["0:true|1:true|2:true"]


def test_for_in_string_indexes_are_strings():
    source = """
let indexes = [];

for (let index in "abc") {
    indexes.push(index);
}

console.log(indexes.join(","));
"""

    assert run_and_collect(source) == ["0,1,2"]


def test_for_in_let_and_const_loop_variables_are_scoped():
    source = """
for (let key in { a: 1 }) {
    console.log(key);
}

for (const index in ["x"]) {
    console.log(index);
}

console.log(typeof key);
console.log(typeof index);
"""

    assert run_and_collect(source) == ["a", "0", "undefined", "undefined"]


def test_for_in_supports_break_and_continue():
    source = """
let seen = [];

for (const key in { a: 1, b: 2, c: 3, d: 4 }) {
    if (key === "b") {
        continue;
    }
    if (key === "d") {
        break;
    }
    seen.push(key);
}

console.log(seen.join(","));
"""

    assert run_and_collect(source) == ["a,c"]


def test_nested_for_in_loops_work():
    source = """
let seen = [];

for (const outer in { a: 1, b: 2 }) {
    for (const inner in ["x", "y"]) {
        seen.push(outer + inner);
    }
}

console.log(seen.join(","));
"""

    assert run_and_collect(source) == ["a0,a1,b0,b1"]


def test_for_in_closures_capture_separate_keys():
    source = """
let functions = [];

for (let key in { name: "Pragun", age: 20 }) {
    functions.push(() => key);
}

console.log(functions[0]());
console.log(functions[1]());
"""

    assert run_and_collect(source) == ["name", "age"]


def test_for_in_iterable_expression_is_evaluated_once():
    source = """
let calls = 0;

function makeUser() {
    calls++;
    return { name: "Pragun", age: 20 };
}

let keys = [];

for (const key in makeUser()) {
    keys.push(key);
}

console.log(keys.join(","));
console.log(calls);
"""

    assert run_and_collect(source) == ["name,age", "1"]


def test_for_in_invalid_primitive_target_is_clear_error():
    exit_code, stdout, stderr = run_cli(
        """
for (let key in 123) {
    console.log(key);
}
"""
    )

    assert exit_code == 1
    assert stdout == ""
    assert "for...in value must be an object, array, or string." in stderr
    assert "Traceback" not in stderr
