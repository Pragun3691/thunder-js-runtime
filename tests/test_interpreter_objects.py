from io import StringIO

from thunder_js.cli import main
from thunder_js.interpreter import run_source


def run_and_collect(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def test_empty_object_and_missing_property_returns_undefined():
    source = """
let user = {};
console.log(user.name);
console.log(user["name"]);
"""

    assert run_and_collect(source) == ["undefined", "undefined"]


def test_reading_identifier_string_and_numeric_keys():
    source = """
let user = { name: "Pragun", "favorite color": "blue", 1: "one" };
console.log(user.name);
console.log(user["favorite color"]);
console.log(user[1]);
"""

    assert run_and_collect(source) == ["Pragun", "blue", "one"]


def test_nested_object_properties():
    source = """
let user = {
    name: "Pragun",
    address: {
        city: "Delhi"
    }
};
console.log(user.address.city);
console.log(user["address"]["city"]);
"""

    assert run_and_collect(source) == ["Delhi", "Delhi"]


def test_computed_property_access():
    source = """
let key = "age";
let user = { age: 20 };
console.log(user[key]);
"""

    assert run_and_collect(source) == ["20"]


def test_adding_property_with_dot_and_computed_assignment():
    source = """
let user = {};
user.name = "Pragun";
user["age"] = 20;
console.log(user.name);
console.log(user.age);
"""

    assert run_and_collect(source) == ["Pragun", "20"]


def test_updating_existing_property_with_dot_and_computed_assignment():
    source = """
let user = { name: "Old", age: 19 };
user.name = "Pragun";
user["age"] = 20;
console.log(user.name);
console.log(user.age);
"""

    assert run_and_collect(source) == ["Pragun", "20"]


def test_object_stored_in_const_can_have_properties_changed():
    source = """
const user = { name: "Old" };
user.name = "Pragun";
user.age = 20;
console.log(user.name);
console.log(user.age);
"""

    assert run_and_collect(source) == ["Pragun", "20"]


def test_const_variable_itself_still_cannot_be_reassigned():
    source = """
const user = { name: "Pragun" };
user = { name: "Other" };
"""
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "Assignment to constant variable user" in stderr.getvalue()


def test_object_literal_values_can_use_expressions():
    source = """
let age = 19;
let user = { name: "Pragun", age: age + 1 };
console.log(user.name + " is " + user.age);
"""

    assert run_and_collect(source) == ["Pragun is 20"]
