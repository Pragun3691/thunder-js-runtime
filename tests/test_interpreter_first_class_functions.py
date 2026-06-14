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


def test_anonymous_function_expression():
    source = """
const add = function(a, b) {
    return a + b;
};

console.log(add(2, 3));
"""

    assert run_and_collect(source) == ["5"]


def test_named_variable_containing_a_function():
    source = """
let double = function(value) {
    return value * 2;
};

console.log(double(4));
"""

    assert run_and_collect(source) == ["8"]


def test_assigning_function_value_to_existing_variable():
    source = """
let identity;
identity = x => x;

console.log(identity(9));
"""

    assert run_and_collect(source) == ["9"]


def test_single_parameter_arrow_function():
    source = """
const square = x => x * x;

console.log(square(5));
"""

    assert run_and_collect(source) == ["25"]


def test_zero_parameter_arrow_function():
    source = """
const greet = () => {
    return "hello";
};

console.log(greet());
"""

    assert run_and_collect(source) == ["hello"]


def test_multiple_parameter_arrow_function():
    source = """
const add = (a, b) => a + b;

console.log(add(6, 7));
"""

    assert run_and_collect(source) == ["13"]


def test_concise_expression_body_and_block_body_with_return():
    source = """
const concise = x => x + 1;
const block = x => {
    return x + 2;
};

console.log(concise(4));
console.log(block(4));
"""

    assert run_and_collect(source) == ["5", "6"]


def test_passing_callback_as_argument():
    source = """
function apply(value, callback) {
    return callback(value);
}

console.log(apply(5, x => x * 2));
"""

    assert run_and_collect(source) == ["10"]


def test_returning_a_function_and_calling_returned_function():
    source = """
function makeAdder(base) {
    return function(value) {
        return base + value;
    };
}

let addTwo = makeAdder(2);
console.log(addTwo(5));
console.log(makeAdder(10)(1));
"""

    assert run_and_collect(source) == ["7", "11"]


def test_named_function_expression_can_recurse_with_internal_name():
    source = """
const factorial = function inner(n) {
    return n <= 1 ? 1 : n * inner(n - 1);
};

console.log(factorial(5));
"""

    assert run_and_collect(source) == ["120"]


def test_named_function_expression_internal_name_does_not_leak():
    source = """
const factorial = function inner(n) {
    return n <= 1 ? 1 : n * inner(n - 1);
};

console.log(inner);
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert "inner is not defined." in stderr
    assert "Traceback" not in stderr


def test_named_function_expression_internal_name_is_immutable():
    source = """
const fn = function inner() {
    inner = 1;
};

fn();
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert "Assignment to constant variable inner." in stderr
    assert "Traceback" not in stderr


def test_named_function_expressions_have_independent_internal_names():
    source = """
const first = function same(n) {
    return n <= 0 ? "first" : same(n - 1);
};
const second = function same(n) {
    return n <= 0 ? "second" : same(n - 1);
};

console.log(first(2));
console.log(second(2));
"""

    assert run_and_collect(source) == ["first", "second"]


def test_named_function_expression_recurses_when_used_as_callback():
    source = """
const factorial = function inner(n) {
    return n <= 1 ? 1 : n * inner(n - 1);
};

console.log([3, 4].map(factorial).join(","));
"""

    assert run_and_collect(source) == ["6,24"]


def test_closure_reads_outer_variable():
    source = """
let suffix = "!";

function makeGreeter() {
    return name => name + suffix;
}

let greet = makeGreeter();
console.log(greet("hi"));
"""

    assert run_and_collect(source) == ["hi!"]


def test_closure_changes_captured_variable():
    source = """
function makeCounter() {
    let count = 0;

    return function() {
        count += 1;
        return count;
    };
}

let counter = makeCounter();
console.log(counter());
console.log(counter());
"""

    assert run_and_collect(source) == ["1", "2"]


def test_two_closure_instances_have_separate_state():
    source = """
function makeCounter() {
    let count = 0;

    return function() {
        count += 1;
        return count;
    };
}

let first = makeCounter();
let second = makeCounter();
console.log(first());
console.log(first());
console.log(second());
"""

    assert run_and_collect(source) == ["1", "2", "1"]


def test_function_expression_is_not_hoisted():
    source = """
console.log(add(2, 3));

const add = function(a, b) {
    return a + b;
};
"""
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "add is not defined" in stderr.getvalue()
    assert "Traceback" not in stderr.getvalue()


def test_function_declaration_hoisting_still_works():
    source = """
console.log(add(2, 3));

function add(a, b) {
    return a + b;
}
"""

    assert run_and_collect(source) == ["5"]


def test_callback_runtime_error_when_non_function_value_is_called():
    source = """
function apply(value, callback) {
    return callback(value);
}

apply(5, 10);
"""
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "Value is not callable." in stderr.getvalue()
    assert "Traceback" not in stderr.getvalue()


def test_missing_arguments_remain_undefined():
    source = """
const second = (a, b) => b;

console.log(second(1));
"""

    assert run_and_collect(source) == ["undefined"]
