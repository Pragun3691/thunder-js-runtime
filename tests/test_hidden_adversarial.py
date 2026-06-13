from io import StringIO

import pytest

from thunder_js.cli import main
from thunder_js.interpreter import InterpreterError, run_source


def run_cli(source):
    stdout = StringIO()
    stderr = StringIO()
    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)
    return exit_code, stdout.getvalue(), stderr.getvalue()


def assert_cli_stdout(source, expected):
    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 0
    assert stdout == "".join(line + "\n" for line in expected)
    assert stderr == ""


def assert_cli_error(source, message):
    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert message in stderr
    assert "Traceback" not in stderr


def test_let_const_shadowing_and_nested_block_lookup():
    source = """
let value = "outer";
const fixed = "root";
{
    let value = "inner";
    {
        const fixed = value + "-fixed";
        console.log(value);
        console.log(fixed);
    }
}
console.log(value);
console.log(fixed);
"""

    assert_cli_stdout(source, ["inner", "inner-fixed", "outer", "root"])


def test_const_reassignment_error_after_previous_stdout_is_separated():
    source = """
const locked = 1;
console.log("before");
locked = 2;
"""
    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == "before\n"
    assert "Assignment to constant variable locked." in stderr
    assert "Traceback" not in stderr


def test_missing_block_variable_does_not_leak_scope():
    source = """
if (true) {
    let hidden = 9;
    console.log(hidden);
}
console.log(hidden);
"""
    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == "9\n"
    assert "hidden is not defined" in stderr
    assert "Traceback" not in stderr


def test_mixed_literals_coercion_and_output_formatting():
    source = """
console.log(Number(null) + ":" + Number(undefined));
console.log(String(true) + "/" + String(false));
console.log(Boolean("") + "/" + Boolean("false"));
console.log(null == undefined);
console.log(null === undefined);
"""

    assert_cli_stdout(source, ["0:NaN", "true/false", "false/true", "true", "false"])


def test_arithmetic_precedence_exponent_and_string_plus():
    source = """
console.log(2 + 3 * 4);
console.log((2 + 3) * 4);
console.log(2 ** 3 ** 2);
console.log("x" + 1 + 2);
console.log(1 + 2 + "x");
"""

    assert_cli_stdout(source, ["14", "20", "512", "x12", "3x"])


def test_logical_short_circuit_avoids_missing_identifier():
    source = """
console.log(false && missing);
console.log(true || missing);
console.log("" || "fallback");
console.log("value" && 42);
"""

    assert_cli_stdout(source, ["false", "true", "fallback", "42"])


def test_if_else_switch_and_strict_case_matching_combined():
    source = """
let value = "2";
let text = "";
if (value == 2) {
    text += "loose";
}
switch (value) {
    case 2:
        text += "-number";
        break;
    case "2":
        text += "-string";
        break;
    default:
        text += "-default";
}
console.log(text);
"""

    assert_cli_stdout(source, ["loose-string"])


def test_switch_default_before_case_falls_through_only_when_no_match():
    source = """
let text = "";
switch (3) {
    default:
        text += "default";
    case 3:
        text += "-three";
        break;
}
console.log(text);
"""

    assert_cli_stdout(source, ["-three"])


def test_nested_loop_switch_break_and_continue_targets():
    source = """
let text = "";
for (let i = 1; i <= 3; i++) {
    switch (i) {
        case 1:
            text += "a";
            break;
        case 2:
            continue;
        default:
            text += "c";
    }
    text += ".";
}
console.log(text);
"""

    assert_cli_stdout(source, ["a.c."])


def test_while_and_do_while_update_same_state():
    source = """
let i = 0;
let text = "";
while (i < 2) {
    i++;
    text += "w" + i;
}
do {
    i++;
    text += "d" + i;
} while (i < 4);
console.log(text);
"""

    assert_cli_stdout(source, ["w1w2d3d4"])


def test_do_while_continue_still_checks_condition():
    source = """
let i = 0;
let text = "";
do {
    i++;
    if (i < 3) {
        continue;
    }
    text += i;
} while (i < 3);
console.log(text);
"""

    assert_cli_stdout(source, ["3"])


def test_break_inside_function_inside_loop_is_parser_error():
    source = """
while (true) {
    function stop() {
        break;
    }
    stop();
}
"""

    assert_cli_error(source, "break used outside of a loop")


def test_continue_inside_switch_without_loop_is_parser_error():
    source = """
switch (1) {
    case 1:
        continue;
}
"""

    assert_cli_error(source, "continue used outside of a loop")


def test_array_mutators_and_access_edge_cases():
    source = """
let arr = [2];
arr.unshift(0, 1);
arr.push(3, 4);
console.log(arr.join(","));
console.log(arr.shift());
console.log(arr.pop());
console.log(arr[99]);
arr[6] = "x";
console.log(arr.join("|"));
console.log(arr[5]);
"""

    assert_cli_stdout(source, ["0,1,2,3,4", "0", "4", "undefined", "1|2|3||||x", "undefined"])


def test_array_slice_splice_concat_sort_and_originals():
    source = """
let base = [3, 11, 2, 4];
let sliced = base.slice(1, 3);
let removed = base.splice(1, 2, "a");
let combined = sliced.concat(base, 9);
combined.sort();
console.log(sliced.join(","));
console.log(removed.join(","));
console.log(base.join(","));
console.log(combined.join(","));
"""

    assert_cli_stdout(source, ["11,2", "11,2", "3,a,4", "11,2,3,4,9,a"])


def test_array_methods_with_negative_and_nan_start_indexes():
    source = """
let arr = ["a", "b", "c", "b"];
console.log(arr.includes("b", -2));
console.log(arr.indexOf("b", -2));
console.log(arr.includes("a", "bad"));
console.log(arr.indexOf("a", "bad"));
"""

    assert_cli_stdout(source, ["true", "3", "true", "0"])


def test_array_callbacks_receive_index_and_array_reference():
    source = """
let arr = [5, 6, 7];
let mapped = arr.map((value, index, array) => value + index + array.length);
let filtered = mapped.filter((value, index, array) => value < array[2]);
console.log(mapped.join(","));
console.log(filtered.join(","));
console.log(arr.join(","));
"""

    assert_cli_stdout(source, ["8,10,12", "8,10", "5,6,7"])


def test_reduce_find_some_every_chained_with_closure_callback():
    source = """
function threshold(limit) {
    return value => value > limit;
}
let values = [1, 2, 3, 4, 5];
let big = threshold(3);
console.log(values.find(big));
console.log(values.some(big));
console.log(values.every(big));
console.log(values.filter(big).reduce((sum, value) => sum + value, 0));
"""

    assert_cli_stdout(source, ["4", "true", "false", "9"])


def test_array_callback_short_circuit_counts_mutations():
    source = """
let calls = 0;
let someResult = [1, 2, 3, 4].some(x => {
    calls++;
    return x === 3;
});
let everyResult = [2, 4, 5, 6].every(x => {
    calls++;
    return x % 2 === 0;
});
console.log(someResult);
console.log(everyResult);
console.log(calls);
"""

    assert_cli_stdout(source, ["true", "false", "6"])


def test_string_methods_chain_and_indexes():
    source = """
let text = "  Hello Thunder  ";
console.log(text.trim().toLowerCase().replace("hello", "hi"));
console.log(text.trim().toUpperCase().includes("THUNDER"));
console.log("abcdef".substring(4, 1));
console.log("abcdef".slice(-4, -1));
console.log("banana".replaceAll("na", "NA"));
console.log("Thunder".startsWith("Thu") && "Thunder".endsWith("der"));
console.log("Thunder".indexOf("nde"));
"""

    assert_cli_stdout(source, ["hi thunder", "true", "bcd", "cde", "baNANA", "true", "3"])


def test_string_split_reverse_join_does_not_change_string():
    source = """
let word = "level";
let pieces = word.split("");
pieces.reverse();
console.log(pieces.join(""));
console.log(word);
console.log("a-b-c".split("-").join("|"));
"""

    assert_cli_stdout(source, ["level", "level", "a|b|c"])


def test_missing_string_method_is_stderr_only():
    source = """
console.log("before");
"abc".missing();
"""
    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == "before\n"
    assert "String method missing is not defined." in stderr
    assert "Traceback" not in stderr


def test_object_literals_nested_computed_and_assignment():
    source = """
const key = "score";
const user = { name: "Ada", nested: { score: 1 }, 2: "two" };
user[key] = user.nested.score + 4;
user.nested.score = user[key] * 2;
console.log(user.name);
console.log(user["score"]);
console.log(user.nested.score);
console.log(user[2]);
console.log(user.missing);
"""

    assert_cli_stdout(source, ["Ada", "5", "10", "two", "undefined"])


def test_const_object_property_mutation_but_not_reassignment():
    source = """
const user = { count: 1 };
user.count += 1;
console.log(user.count);
user = {};
"""
    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == "2\n"
    assert "Assignment to constant variable user." in stderr
    assert "Traceback" not in stderr


def test_function_declaration_hoisting_in_block_and_return_from_loop():
    source = """
{
    console.log(add(2, 3));
    function add(a, b) {
        return a + b;
    }
}
function firstEven(limit) {
    let i = 0;
    while (i < limit) {
        i++;
        if (i % 2 === 0) {
            return i;
        }
    }
    return undefined;
}
console.log(firstEven(5));
"""

    assert_cli_stdout(source, ["5", "2"])


def test_function_expression_not_hoisted_but_declaration_is():
    source = """
console.log(declared());
console.log(expr());
function declared() {
    return "ok";
}
const expr = function() {
    return "late";
};
"""
    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == "ok\n"
    assert "expr is not defined" in stderr
    assert "Traceback" not in stderr


def test_arrow_closure_updates_captured_state():
    source = """
function makeCounter(step) {
    let value = 0;
    return () => {
        value += step;
        return value;
    };
}
let byTwo = makeCounter(2);
let byThree = makeCounter(3);
console.log(byTwo());
console.log(byTwo());
console.log(byThree());
console.log(byTwo());
"""

    assert_cli_stdout(source, ["2", "4", "3", "6"])


def test_recursive_function_with_array_accumulator():
    source = """
function countdown(n, ...seen) {
    if (n <= 0) {
        return seen.join(",");
    }
    seen.push(n);
    return countdown(n - 1, ...seen);
}
console.log(countdown(4));
"""

    assert_cli_stdout(source, ["4,3,2,1"])


def test_callback_returning_function_and_calling_returned_value():
    source = """
function compose(value, makeFn) {
    return makeFn(value);
}
let addBase = base => value => base + value;
let addTen = compose(10, addBase);
console.log(addTen(7));
"""

    assert_cli_stdout(source, ["17"])


def test_rest_parameter_is_fresh_array_with_spread_input():
    source = """
function mutate(first, ...rest) {
    rest[0] = 99;
    return first + ":" + rest.join(",");
}
let values = [1, 2, 3];
console.log(mutate(...values));
console.log(values.join(","));
"""

    assert_cli_stdout(source, ["1:99,3", "1,2,3"])


def test_spread_multiple_arrays_and_values_into_callback():
    source = """
function call(fn, ...args) {
    return fn(...args);
}
const join = (...items) => items.join("-");
let middle = ["b", "c"];
console.log(call(join, "a", ...middle, "d"));
"""

    assert_cli_stdout(source, ["a-b-c-d"])


def test_math_and_conversion_helpers_in_expressions():
    source = """
console.log(Math.max(Number("5"), Math.ceil(2.1), Math.abs(-4)));
console.log(Math.min());
console.log(Math.max());
console.log(Math.sqrt(-1));
console.log(String(Boolean("0")) + ":" + parseInt("12px") + ":" + parseFloat(".5x"));
"""

    assert_cli_stdout(source, ["5", "Infinity", "-Infinity", "NaN", "true:12:0.5"])


def test_math_random_range_and_type():
    source = """
let value = Math.random();
console.log(value >= 0 && value < 1);
"""

    assert_cli_stdout(source, ["true"])


def test_invalid_array_callback_is_runtime_error_without_traceback():
    assert_cli_error("[1, 2].map(0);", "Array.map callback must be a function.")


def test_reduce_empty_array_without_initial_value_is_runtime_error():
    assert_cli_error("[].reduce((sum, value) => sum + value);", "Reduce of empty array")


def test_spread_non_array_in_call_is_runtime_error():
    source = """
function use(value) {
    return value;
}
use(...false);
"""

    assert_cli_error(source, "Spread argument must be an array.")


def test_array_literal_spread_non_array_is_runtime_error():
    assert_cli_error("let values = [...123];", "Spread value is not iterable.")


def test_duplicate_function_parameter_is_parser_error_without_traceback():
    assert_cli_error("function bad(a, a) { return a; }", "Duplicate parameter name 'a'.")


def test_return_outside_function_is_parser_error_without_traceback():
    assert_cli_error("return 1;", "return used outside of a function")


def test_invalid_unary_exponent_syntax_is_parser_error():
    assert_cli_error("console.log(-2 ** 2);", "Unary expression cannot be the left side")


def test_unterminated_string_is_lexer_error_without_traceback():
    assert_cli_error('console.log("oops);', "Unterminated string")


def test_object_property_assignment_to_non_object_is_runtime_error():
    assert_cli_error('"text".name = 1;', "Only object property assignment is supported")


def test_negative_array_assignment_is_runtime_error():
    assert_cli_error("let values = []; values[-1] = 2;", "Array index must be non-negative.")


def test_infinite_while_loop_hits_step_limit():
    with pytest.raises(InterpreterError, match="Execution step limit exceeded"):
        run_source("while (true) {}", output=lambda line: None, step_limit=10)


def test_infinite_do_while_loop_hits_step_limit():
    with pytest.raises(InterpreterError, match="Execution step limit exceeded"):
        run_source("do {} while (true);", output=lambda line: None, step_limit=10)


def test_recursion_limit_reports_stderr_only():
    source = """
function recurse() {
    return recurse();
}
recurse();
"""

    assert_cli_error(source, "Maximum call stack size exceeded.")
