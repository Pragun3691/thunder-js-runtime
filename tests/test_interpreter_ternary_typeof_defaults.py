from thunder_js.interpreter import run_source


def run_and_collect(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def test_basic_ternary():
    source = """
let score = 75;
let result = score >= 50 ? "pass" : "fail";
console.log(result);
"""

    assert run_and_collect(source) == ["pass"]


def test_nested_ternary():
    source = """
let positive = 3;
let negative = -1;
let zero = 0;
console.log(positive > 0 ? "positive" : positive < 0 ? "negative" : "zero");
console.log(negative > 0 ? "positive" : negative < 0 ? "negative" : "zero");
console.log(zero > 0 ? "positive" : zero < 0 ? "negative" : "zero");
"""

    assert run_and_collect(source) == ["positive", "negative", "zero"]


def test_ternary_evaluates_only_chosen_branch():
    source = """
console.log(true ? "yes" : missingName);
console.log(false ? missingName : "no");
"""

    assert run_and_collect(source) == ["yes", "no"]


def test_ternary_inside_return_and_assignment():
    source = """
function label(value) {
    return value ? "truthy" : "falsy";
}

let result;
result = false ? "bad" : label(1);
console.log(result);
"""

    assert run_and_collect(source) == ["truthy"]


def test_typeof_supported_values():
    source = """
console.log(typeof undefined);
console.log(typeof null);
console.log(typeof true);
console.log(typeof 42);
console.log(typeof "x");
console.log(typeof function() {});
console.log(typeof []);
console.log(typeof {});
"""

    assert run_and_collect(source) == [
        "undefined",
        "object",
        "boolean",
        "number",
        "string",
        "function",
        "object",
        "object",
    ]


def test_typeof_unknown_identifier_is_undefined_without_throwing():
    assert run_and_collect("console.log(typeof missingName);") == ["undefined"]


def test_object_shorthand_properties():
    source = """
let name = "Pragun";
let age = 20;
let user = { name, age };
console.log(user.name);
console.log(user.age);
"""

    assert run_and_collect(source) == ["Pragun", "20"]


def test_object_shorthand_mixed_with_normal_properties_and_spread():
    source = """
let name = "Pragun";
let base = { city: "Delhi", age: 19 };
let user = { ...base, name, age: 21 };
console.log(user.name);
console.log(user.age);
console.log(user.city);
"""

    assert run_and_collect(source) == ["Pragun", "21", "Delhi"]


def test_function_declaration_default_parameters():
    source = """
function greet(name = "World") {
    return "Hello " + name;
}

console.log(greet());
console.log(greet("Pragun"));
"""

    assert run_and_collect(source) == ["Hello World", "Hello Pragun"]


def test_function_expression_default_parameters():
    source = """
const greet = function(name = "World") {
    return "Hello " + name;
};

console.log(greet());
console.log(greet("Pragun"));
"""

    assert run_and_collect(source) == ["Hello World", "Hello Pragun"]


def test_arrow_function_default_parameters():
    source = """
const add = (a = 1, b = 2) => a + b;
console.log(add());
console.log(add(5));
console.log(add(5, 6));
"""

    assert run_and_collect(source) == ["3", "7", "11"]


def test_default_parameters_can_reference_earlier_parameters():
    source = """
function makeLabel(name, label = name + "!") {
    return label;
}

console.log(makeLabel("Pragun"));
console.log(makeLabel("Pragun", "custom"));
"""

    assert run_and_collect(source) == ["Pragun!", "custom"]


def test_default_parameters_distinguish_missing_undefined_and_other_falsy_values():
    source = """
function show(value = "default") {
    return String(value);
}

console.log(show());
console.log(show(undefined));
console.log(show(null));
console.log(show(false));
console.log(show(0));
console.log(show(""));
"""

    assert run_and_collect(source) == [
        "default",
        "default",
        "null",
        "false",
        "0",
        "",
    ]
