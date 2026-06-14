from io import StringIO

import pytest

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


def assert_cli_error(source, expected):
    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert expected in stderr
    assert "Traceback" not in stderr

    return stderr


def test_basic_initialized_var():
    assert run_and_collect("var value = 5; console.log(value);") == ["5"]


def test_uninitialized_var_is_undefined():
    assert run_and_collect("var value; console.log(value);") == ["undefined"]


def test_var_is_mutable():
    source = """
var value = 1;
value = 2;
console.log(value);
"""

    assert run_and_collect(source) == ["2"]


def test_duplicate_var_declaration_is_allowed():
    source = """
var value = 1;
var value = 2;
var value;
console.log(value);
"""

    assert run_and_collect(source) == ["2"]


def test_var_declared_inside_block_remains_visible():
    source = """
{
    var value = "block";
}
console.log(value);
"""

    assert run_and_collect(source) == ["block"]


def test_var_declared_inside_if_remains_visible():
    source = """
if (true) {
    var value = "if";
}
console.log(value);
"""

    assert run_and_collect(source) == ["if"]


def test_var_name_is_hoisted_from_unexecuted_block():
    source = """
if (false) {
    var value = "never";
}
console.log(value);
"""

    assert run_and_collect(source) == ["undefined"]


def test_var_declared_inside_loop_remains_visible():
    source = """
for (var i = 0; i < 2; i++) {
    var last = i;
}
console.log(i);
console.log(last);
"""

    assert run_and_collect(source) == ["2", "1"]


def test_function_local_var_does_not_leak():
    source = """
function makeValue() {
    var local = 42;
    console.log(local);
}

makeValue();
console.log(local);
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == "42\n"
    assert "local is not defined" in stderr
    assert "Traceback" not in stderr


def test_classic_for_with_var():
    source = """
var text = "";
for (var i = 0; i < 3; i++) {
    text += i;
}
console.log(text);
console.log(i);
"""

    assert run_and_collect(source) == ["012", "3"]


def test_for_in_with_var_uses_function_scope_binding():
    source = """
let keys = [];
for (var key in { a: 1, b: 2 }) {
    keys.push(key);
}
console.log(keys.join(","));
console.log(key);
"""

    assert run_and_collect(source) == ["a,b", "b"]


def test_for_of_with_var_uses_function_scope_binding():
    source = """
let values = [];
for (var value of [1, 2, 3]) {
    values.push(value);
}
console.log(values.join(","));
console.log(value);
"""

    assert run_and_collect(source) == ["1,2,3", "3"]


def test_var_loop_closures_share_final_binding():
    source = """
var functions = [];

for (var i = 0; i < 3; i++) {
    functions.push(() => i);
}

console.log(functions[0]());
console.log(functions[1]());
console.log(functions[2]());
"""

    assert run_and_collect(source) == ["3", "3", "3"]


def test_let_loop_closures_keep_per_iteration_bindings():
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


def test_const_behavior_remains_unchanged():
    source = """
const value = 1;
value = 2;
"""

    assert_cli_error(source, "Assignment to constant variable value.")


def test_var_supports_multiple_declarators():
    source = """
var a = 1, b = 2, c;
console.log(a + b);
console.log(c);
"""

    assert run_and_collect(source) == ["3", "undefined"]


def test_array_declaration_destructuring():
    source = """
let [a, b] = [1, 2];
const [first, second] = [3, 4];
console.log(a + b);
console.log(first + second);
"""

    assert run_and_collect(source) == ["3", "7"]


def test_skipped_array_entries_and_rest():
    source = """
let [, second, ...rest] = [1, 2, 3, 4];
console.log(second);
console.log(rest);
"""

    assert run_and_collect(source) == ["2", "[ 3, 4 ]"]


def test_array_defaults_apply_only_to_undefined():
    source = """
let [a = 10, b = 20, c = 30] = [undefined, 5];
console.log(a);
console.log(b);
console.log(c);
"""

    assert run_and_collect(source) == ["10", "5", "30"]


def test_nested_array_pattern():
    source = """
let [first, [second]] = [1, [2]];
console.log(first);
console.log(second);
"""

    assert run_and_collect(source) == ["1", "2"]


def test_object_shorthand_and_renamed_destructuring():
    source = """
let user = { name: "A", age: 20 };
let { name, age: years } = user;
console.log(name);
console.log(years);
"""

    assert run_and_collect(source) == ["A", "20"]


def test_object_defaults_and_renamed_defaults():
    source = """
let user = {};
let { score = 0, points: total = 5 } = user;
console.log(score);
console.log(total);
"""

    assert run_and_collect(source) == ["0", "5"]


def test_object_rest_creates_new_remaining_object():
    source = """
let user = { name: "A", age: 20, city: "Delhi" };
let { name, ...remaining } = user;
remaining.age = 21;
console.log(name);
console.log(remaining);
console.log(user.age);
"""

    assert run_and_collect(source) == ["A", "{ age: 21, city: 'Delhi' }", "20"]


def test_nested_object_pattern():
    source = """
let user = { profile: { name: "A" } };
let { profile: { name } } = user;
console.log(name);
"""

    assert run_and_collect(source) == ["A"]


def test_missing_values_become_undefined():
    source = """
let [a, b] = [1];
let { missing } = {};
console.log(a);
console.log(b);
console.log(missing);
"""

    assert run_and_collect(source) == ["1", "undefined", "undefined"]


def test_defaults_do_not_apply_to_null_false_zero_or_empty_string():
    source = """
let [a = "A", b = "B", c = "C", d = "D", e = "E"] =
    [null, false, 0, "", undefined];
console.log(String(a) + "|" + String(b) + "|" + String(c) + "|" + d + "|" + e);
"""

    assert run_and_collect(source) == ["null|false|0||E"]


def test_let_const_and_var_destructuring_binding_rules():
    source = """
let [letValue] = [1];
const { locked } = { locked: 2 };
{
    var [varValue] = [3];
}
letValue = 10;
console.log(letValue);
console.log(locked);
console.log(varValue);
"""

    assert run_and_collect(source) == ["10", "2", "3"]


def test_const_destructured_binding_cannot_be_reassigned():
    source = """
const { value } = { value: 1 };
value = 2;
"""

    assert_cli_error(source, "Assignment to constant variable value.")


def test_function_declaration_parameter_destructuring():
    source = """
function printUser({ name, age }) {
    console.log(name);
    console.log(age);
}

function total([a, b]) {
    return a + b;
}

printUser({ name: "A", age: 20 });
console.log(total([2, 3]));
"""

    assert run_and_collect(source) == ["A", "20", "5"]


def test_destructured_default_parameter():
    source = """
function greet({ name = "World" } = {}) {
    return "Hello " + name;
}

console.log(greet());
console.log(greet({ name: "A" }));
"""

    assert run_and_collect(source) == ["Hello World", "Hello A"]


def test_arrow_function_parameter_destructuring():
    source = """
const getName = ({ name }) => name;
const addPair = ([a, b]) => a + b;
console.log(getName({ name: "A" }));
console.log(addPair([2, 4]));
"""

    assert run_and_collect(source) == ["A", "6"]


def test_array_callback_with_destructured_arrow_parameter():
    source = """
let doubled = [{ x: 1 }, { x: 2 }].map(({ x }) => x * 2);
console.log(doubled);
"""

    assert run_and_collect(source) == ["[ 2, 4 ]"]


def test_initializer_expression_is_evaluated_once():
    source = """
let calls = 0;
function makeValues() {
    calls++;
    return [1, 2];
}

let [a, b] = makeValues();
console.log(a + b);
console.log(calls);
"""

    assert run_and_collect(source) == ["3", "1"]


def test_pattern_defaults_are_evaluated_only_when_needed():
    source = """
let calls = 0;
function fallback() {
    calls++;
    return 10;
}

let [a = fallback(), b = fallback()] = [null, undefined];
console.log(a);
console.log(b);
console.log(calls);
"""

    assert run_and_collect(source) == ["null", "10", "1"]


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("let [a] = 123;", "Array destructuring source must be an array."),
        ("let { a } = null;", "Object destructuring source must be an object."),
        ("let { a } = undefined;", "Object destructuring source must be an object."),
        (
            "function bad([a]) { return a; }\nbad(123);",
            "Array destructuring source must be an array.",
        ),
    ],
)
def test_invalid_destructuring_source_types_are_clear_errors(source, message):
    assert_cli_error(source, message)


@pytest.mark.parametrize(
    "source",
    [
        "let [a, a] = [1, 2];",
        "function bad([a, a]) {}",
        "const bad = ({ x: a, y: a }) => a;",
    ],
)
def test_duplicate_destructured_bindings_are_parser_errors(source):
    stderr = assert_cli_error(source, "Duplicate")

    assert "line" in stderr
    assert "column" in stderr


@pytest.mark.parametrize(
    "source",
    [
        "let [a, ...rest, last] = values;",
        "let { ...rest, age } = user;",
        "let [...a, ...b] = values;",
    ],
)
def test_invalid_rest_placement_is_parser_error(source):
    stderr = assert_cli_error(source, "Rest")

    assert "line" in stderr
    assert "column" in stderr


def test_destructuring_assignment_expression_is_not_supported():
    source = """
let a = 1;
let b = 2;
[a, b] = [b, a];
"""

    assert_cli_error(source, "Expected assignment target.")
