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


def test_direct_object_method_call_binds_this():
    source = """
let user = {
    name: "Pragun",
    greet: function() {
        return "Hello " + this.name;
    }
};

console.log(user.greet());
"""

    assert run_and_collect(source) == ["Hello Pragun"]


def test_computed_object_method_call_binds_this():
    source = """
let user = {
    name: "Pragun",
    greet: function() {
        return this.name;
    }
};

console.log(user["greet"]());
"""

    assert run_and_collect(source) == ["Pragun"]


def test_nested_method_receiver_is_immediate_object():
    source = """
let outer = {
    value: 1,
    inner: {
        value: 10,
        getValue: function() {
            return this.value;
        }
    }
};

console.log(outer.inner.getValue());
"""

    assert run_and_collect(source) == ["10"]


def test_method_updates_receiver_property():
    source = """
let counter = {
    value: 0,
    increment: function() {
        this.value++;
        return this.value;
    }
};

console.log(counter.increment());
console.log(counter.increment());
console.log(counter.value);
"""

    assert run_and_collect(source) == ["1", "2", "2"]


def test_two_objects_sharing_same_function_receive_own_this():
    source = """
let getName = function() {
    return this.name;
};

let first = { name: "A", getName };
let second = { name: "B", getName };

console.log(first.getName());
console.log(second.getName());
"""

    assert run_and_collect(source) == ["A", "B"]


def test_nested_method_calls_do_not_leak_this_between_calls():
    source = """
let second = {
    name: "B",
    getName: function() {
        return this.name;
    }
};

let first = {
    name: "A",
    other: second,
    getBoth: function() {
        let before = this.name;
        let nested = this.other.getName();
        return before + ":" + nested + ":" + this.name;
    }
};

console.log(first.getBoth());
"""

    assert run_and_collect(source) == ["A:B:A"]


def test_recursive_method_calls_keep_receiver_this():
    source = """
let counter = {
    value: 3,
    countDown: function() {
        if (this.value <= 1) {
            return this.value;
        }
        this.value--;
        return this.countDown();
    }
};

console.log(counter.countDown());
console.log(counter.value);
"""

    assert run_and_collect(source) == ["1", "1"]


def test_detached_method_has_clean_undefined_this_behavior():
    source = """
let user = {
    name: "Pragun",
    greet: function() {
        return this.name;
    }
};

let fn = user.greet;
fn();
"""

    assert_cli_error(source, "Property name is not defined.")


def test_arrow_function_property_does_not_receive_dynamic_this():
    source = """
let user = {
    name: "Pragun",
    getThisType: () => typeof this
};

console.log(user.getThisType());
"""

    assert run_and_collect(source) == ["undefined"]


def test_optional_property_on_null_and_undefined():
    source = """
let missing;
let user = null;
console.log(user?.name);
console.log(missing?.name);
"""

    assert run_and_collect(source) == ["undefined", "undefined"]


def test_optional_property_on_object():
    source = """
let user = { name: "Pragun" };
console.log(user?.name);
"""

    assert run_and_collect(source) == ["Pragun"]


def test_optional_computed_property():
    source = """
let key = "name";
let user = { name: "Pragun" };
console.log(user?.[key]);
"""

    assert run_and_collect(source) == ["Pragun"]


def test_optional_computed_expression_not_evaluated_after_short_circuit():
    source = """
let calls = 0;
function key() {
    calls++;
    return "name";
}

let user = null;
console.log(user?.[key()]);
console.log(calls);
"""

    assert run_and_collect(source) == ["undefined", "0"]


def test_optional_call_on_missing_method_returns_undefined_and_skips_arguments():
    source = """
let calls = 0;
function sideEffect() {
    calls++;
    return 1;
}

let user = {};
console.log(user.missing?.(sideEffect()));
console.log(user?.alsoMissing(sideEffect()));
console.log(calls);
"""

    assert run_and_collect(source) == ["undefined", "undefined", "0"]


def test_optional_method_call_preserves_this():
    source = """
let user = {
    name: "Pragun",
    greet: function() {
        return this.name;
    }
};

console.log(user?.greet?.());
"""

    assert run_and_collect(source) == ["Pragun"]


def test_chained_optional_access_and_call():
    source = """
let user = {
    getProfile: function() {
        return { name: this.name };
    },
    name: "Pragun"
};
let missing = null;

console.log(user?.getProfile?.()?.name);
console.log(missing?.getProfile?.()?.name);
"""

    assert run_and_collect(source) == ["Pragun", "undefined"]


def test_falsy_non_null_values_do_not_short_circuit_optional_chain():
    source = """
console.log(""?.length);
"""

    assert run_and_collect(source) == ["0"]


def test_optional_invocation_of_present_non_callable_property_is_error():
    source = """
let user = { count: 1 };
user.count?.();
"""

    assert_cli_error(source, "Value is not callable.")


def test_invalid_optional_assignment_is_parser_error():
    source = """
let user = { name: "Old" };
user?.name = "New";
"""

    stderr = assert_cli_error(
        source,
        "Optional chaining cannot be used as an assignment target.",
    )
    assert "line" in stderr
    assert "column" in stderr


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("console.log(null ?? 5);", ["5"]),
        ("console.log(undefined ?? 5);", ["5"]),
        ("console.log(0 ?? 5);", ["0"]),
        ("console.log(false ?? true);", ["false"]),
        ('console.log("" ?? "fallback");', [""]),
    ],
)
def test_nullish_coalescing_basic_values(source, expected):
    assert run_and_collect(source) == expected


def test_nullish_coalescing_short_circuits_right_side():
    source = """
let calls = 0;
function fallback() {
    calls++;
    return 5;
}

console.log("value" ?? fallback());
console.log(calls);
"""

    assert run_and_collect(source) == ["value", "0"]


def test_chained_nullish_coalescing_is_left_associative():
    source = """
console.log(null ?? undefined ?? "fallback");
console.log("first" ?? missing ?? "fallback");
"""

    assert run_and_collect(source) == ["fallback", "first"]


def test_parenthesized_nullish_and_logical_combinations_work():
    source = """
console.log((null ?? false) || true);
console.log(null ?? (false || true));
"""

    assert run_and_collect(source) == ["true", "true"]


@pytest.mark.parametrize(
    "source",
    [
        "console.log(null ?? false || true);",
        "console.log(false || null ?? true);",
        "console.log(null ?? true && false);",
    ],
)
def test_direct_nullish_and_logical_mixing_is_rejected(source):
    stderr = assert_cli_error(
        source,
        "Cannot mix '??' with '&&' or '||' without parentheses.",
    )
    assert "line" in stderr
    assert "column" in stderr
