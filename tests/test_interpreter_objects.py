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


def test_basic_object_spread_copies_properties():
    source = """
let a = { name: "Pragun", age: 20 };
let b = { ...a };
console.log(b.name);
console.log(b.age);
"""

    assert run_and_collect(source) == ["Pragun", "20"]


def test_property_after_object_spread_overrides_spread_property():
    source = """
let a = { name: "Pragun", age: 20 };
let b = { ...a, age: 21 };
console.log(b.name);
console.log(b.age);
"""

    assert run_and_collect(source) == ["Pragun", "21"]


def test_property_before_object_spread_is_overridden_by_spread():
    source = """
let a = { age: 20 };
let b = { age: 19, ...a };
console.log(b.age);
"""

    assert run_and_collect(source) == ["20"]


def test_multiple_object_spreads_apply_in_order():
    source = """
let a = { name: "Pragun", age: 20 };
let b = { city: "Delhi", age: 21 };
let c = { ...a, ...b, country: "India" };
console.log(c.name);
console.log(c.age);
console.log(c.city);
console.log(c.country);
"""

    assert run_and_collect(source) == ["Pragun", "21", "Delhi", "India"]


def test_spreading_empty_object_works():
    source = """
let empty = {};
let user = { ...empty, name: "Pragun" };
console.log(user.name);
"""

    assert run_and_collect(source) == ["Pragun"]


def test_object_spread_copies_nested_values_by_reference():
    source = """
let source = { nested: { count: 1 } };
let copy = { ...source };
copy.nested.count = 2;
console.log(source.nested.count);
console.log(copy.nested.count);
"""

    assert run_and_collect(source) == ["2", "2"]


def test_object_spread_does_not_mutate_source_object():
    source = """
let source = { name: "Pragun", age: 20 };
let copy = { ...source };
copy.age = 21;
console.log(source.age);
console.log(copy.age);
"""

    assert run_and_collect(source) == ["20", "21"]


def test_object_spread_non_object_is_runtime_error():
    source = """
let copy = { ...123 };
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert "Object spread value must be an object." in stderr
    assert "Traceback" not in stderr


def test_existing_array_literal_spread_still_works_with_object_spread():
    source = """
let original = [1, 2];
let copy = [0, ...original, 3];
console.log(copy.join(","));
"""

    assert run_and_collect(source) == ["0,1,2,3"]
