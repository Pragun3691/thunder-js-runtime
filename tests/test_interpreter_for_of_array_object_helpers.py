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


def test_for_of_over_array():
    source = """
let values = [1, 2, 3];
let total = 0;

for (const value of values) {
    total += value;
}

console.log(total);
"""

    assert run_and_collect(source) == ["6"]


def test_for_of_over_string():
    source = """
let letters = [];

for (let letter of "abc") {
    letters.push(letter);
}

console.log(letters.join("-"));
"""

    assert run_and_collect(source) == ["a-b-c"]


def test_for_of_supports_break_and_continue():
    source = """
let seen = [];

for (const value of [1, 2, 3, 4, 5]) {
    if (value === 2) {
        continue;
    }
    if (value === 5) {
        break;
    }
    seen.push(value);
}

console.log(seen.join(","));
"""

    assert run_and_collect(source) == ["1,3,4"]


def test_for_of_let_and_const_loop_variables_are_scoped():
    source = """
for (let value of [1]) {
    console.log(value);
}

for (const letter of "x") {
    console.log(letter);
}

console.log(typeof value);
console.log(typeof letter);
"""

    assert run_and_collect(source) == ["1", "x", "undefined", "undefined"]


def test_array_for_each_callback_receives_value_index_and_array():
    source = """
let values = ["a", "b"];
let seen = [];

values.forEach((value, index, array) => {
    seen.push(value + ":" + index + ":" + (array === values));
});

console.log(seen.join("|"));
"""

    assert run_and_collect(source) == ["a:0:true|b:1:true"]


def test_array_for_each_returns_undefined():
    source = """
let result = [1, 2].forEach(value => value * 2);
console.log(result);
"""

    assert run_and_collect(source) == ["undefined"]


def test_array_for_each_non_function_callback_is_error():
    exit_code, stdout, stderr = run_cli("[1, 2].forEach(123);")

    assert exit_code == 1
    assert stdout == ""
    assert "Array.forEach callback must be a function." in stderr
    assert "Traceback" not in stderr


def test_array_is_array_true_and_false_cases():
    source = """
console.log(Array.isArray([]));
console.log(Array.isArray({}));
console.log(Array.isArray("x"));
"""

    assert run_and_collect(source) == ["true", "false", "false"]


def test_object_keys_values_and_entries_preserve_insertion_order():
    source = """
let user = { name: "Pragun", age: 20, city: "Delhi" };
let keys = Object.keys(user);
let values = Object.values(user);
let entries = Object.entries(user);

console.log(keys.join(","));
console.log(values.join(","));
console.log(entries[0].join(":"));
console.log(entries[1].join(":"));
console.log(entries[2].join(":"));
"""

    assert run_and_collect(source) == [
        "name,age,city",
        "Pragun,20,Delhi",
        "name:Pragun",
        "age:20",
        "city:Delhi",
    ]


def test_object_helper_invalid_arguments_are_clear_errors():
    cases = [
        ("Object.keys(123);", "Object.keys argument must be an object."),
        ("Object.values(null);", "Object.values argument must be an object."),
        ('Object.entries("x");', "Object.entries argument must be an object."),
    ]

    for source, message in cases:
        exit_code, stdout, stderr = run_cli(source)

        assert exit_code == 1
        assert stdout == ""
        assert message in stderr
        assert "Traceback" not in stderr
