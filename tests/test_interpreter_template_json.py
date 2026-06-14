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


def test_plain_template_literal():
    assert run_and_collect("console.log(`Hello World`);") == ["Hello World"]


def test_template_literal_one_interpolation():
    source = """
let name = "Pragun";
console.log(`Hello ${name}`);
"""

    assert run_and_collect(source) == ["Hello Pragun"]


def test_template_literal_multiple_interpolations():
    source = """
let a = 2;
let b = 3;
console.log(`${a} + ${b} = ${a + b}`);
"""

    assert run_and_collect(source) == ["2 + 3 = 5"]


def test_template_literal_expression_interpolation():
    source = """
let x = 4;
console.log(`next ${x + 1}`);
"""

    assert run_and_collect(source) == ["next 5"]


def test_template_literal_object_property_interpolation():
    source = """
let user = { name: "Pragun" };
console.log(`user=${user.name}`);
"""

    assert run_and_collect(source) == ["user=Pragun"]


def test_template_literal_method_call_interpolation():
    source = """
let arr = ["a", "b", "c"];
console.log(`items=${arr.join(", ")}`);
"""

    assert run_and_collect(source) == ["items=a, b, c"]


def test_template_literal_ternary_interpolation():
    source = """
let x = -1;
console.log(`${x > 0 ? "positive" : "not positive"}`);
"""

    assert run_and_collect(source) == ["not positive"]


def test_multiline_template_literal():
    source = """let message = `line one
line two`;
console.log(message);
"""

    assert run_and_collect(source) == ["line one\nline two"]


def test_template_literal_escaped_backtick():
    source = r"console.log(`hello \`there`);"

    assert run_and_collect(source) == ["hello `there"]


def test_template_literal_escaped_backslash():
    source = r"console.log(`a\\b`);"

    assert run_and_collect(source) == ["a\\b"]


def test_template_literal_escaped_newline_and_tab():
    source = r"console.log(`line\n\tend`);"

    assert run_and_collect(source) == ["line\n\tend"]


def test_template_literal_escaped_interpolation_start_is_literal():
    source = r"""
let name = "Pragun";
console.log(`Hello \${name}`);
"""

    assert run_and_collect(source) == ["Hello ${name}"]


def test_unterminated_template_literal_is_clear_cli_error():
    exit_code, stdout, stderr = run_cli("console.log(`hello);")

    assert exit_code == 1
    assert stdout == ""
    assert "Unterminated template literal" in stderr
    assert "line 1, column" in stderr
    assert "Traceback" not in stderr


def test_unterminated_template_interpolation_is_clear_cli_error():
    exit_code, stdout, stderr = run_cli("console.log(`hello ${name`);")

    assert exit_code == 1
    assert stdout == ""
    assert "Unterminated template interpolation" in stderr
    assert "line 1, column" in stderr
    assert "Traceback" not in stderr


def test_json_stringify_primitives():
    source = """
console.log(JSON.stringify("Pragun"));
console.log(JSON.stringify(12.5));
console.log(JSON.stringify(true));
console.log(JSON.stringify(null));
"""

    assert run_and_collect(source) == ['"Pragun"', "12.5", "true", "null"]


def test_json_stringify_array_and_object():
    source = """
console.log(JSON.stringify([1, "x", false, null]));
console.log(JSON.stringify({ name: "Pragun", age: 20 }));
"""

    assert run_and_collect(source) == [
        '[1,"x",false,null]',
        '{"name":"Pragun","age":20}',
    ]


def test_json_stringify_nested_arrays_and_objects():
    source = """
let value = { items: [1, { ok: true }], name: "nested" };
console.log(JSON.stringify(value));
"""

    assert run_and_collect(source) == [
        '{"items":[1,{"ok":true}],"name":"nested"}'
    ]


def test_json_stringify_escapes_strings():
    source = r"""
console.log(JSON.stringify("quote: \" slash: \\ newline: \n tab: \t"));
"""

    assert run_and_collect(source) == [
        '"quote: \\" slash: \\\\ newline: \\n tab: \\t"'
    ]


def test_json_stringify_nan_and_infinity_as_null():
    source = """
console.log(JSON.stringify(NaN));
console.log(JSON.stringify(Infinity));
console.log(JSON.stringify([1, undefined, NaN, Infinity, -Infinity]));
"""

    assert run_and_collect(source) == ["null", "null", "[1,null,null,null,null]"]


def test_json_stringify_undefined_top_level_returns_undefined():
    source = """
console.log(JSON.stringify(undefined));
"""

    assert run_and_collect(source) == ["undefined"]


def test_json_stringify_omits_undefined_and_function_object_properties():
    source = """
let obj = {
    name: "Pragun",
    missing: undefined,
    fn: function() {}
};

console.log(JSON.stringify(obj));
"""

    assert run_and_collect(source) == ['{"name":"Pragun"}']


def test_json_stringify_undefined_and_function_array_elements_become_null():
    source = """
let values = [undefined, function() {}, 3];
console.log(JSON.stringify(values));
"""

    assert run_and_collect(source) == ["[null,null,3]"]


def test_json_stringify_preserves_object_insertion_order():
    source = """
let obj = {};
obj.first = 1;
obj.second = 2;
obj.third = 3;
console.log(JSON.stringify(obj));
"""

    assert run_and_collect(source) == ['{"first":1,"second":2,"third":3}']


def test_json_stringify_circular_array_is_clear_cli_error():
    source = """
let arr = [];
arr.push(arr);
JSON.stringify(arr);
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert "Converting circular structure to JSON." in stderr
    assert "Traceback" not in stderr


def test_json_stringify_circular_object_is_clear_cli_error():
    source = """
let obj = {};
obj.self = obj;
JSON.stringify(obj);
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert "Converting circular structure to JSON." in stderr
    assert "Traceback" not in stderr


def test_template_literal_containing_json_stringify_result():
    source = """
let user = { name: "Pragun" };
console.log(`json=${JSON.stringify(user)}`);
"""

    assert run_and_collect(source) == ['json={"name":"Pragun"}']


def test_json_stringify_object_created_with_spread():
    source = """
let base = { name: "Pragun", age: 20 };
let updated = { ...base, age: 21 };
console.log(JSON.stringify(updated));
"""

    assert run_and_collect(source) == ['{"name":"Pragun","age":21}']


def test_json_parse_primitives():
    source = """
console.log(JSON.parse("null"));
console.log(JSON.parse("true"));
console.log(JSON.parse("12.5"));
console.log(JSON.parse('"Pragun"'));
"""

    assert run_and_collect(source) == ["null", "true", "12.5", "Pragun"]


def test_json_parse_arrays_objects_and_nested_values():
    source = """
let array = JSON.parse('[1, true, null, "x"]');
let object = JSON.parse('{"name":"Pragun","age":20}');
let nested = JSON.parse('{"items":[1,{"ok":true}],"name":"nested"}');

console.log(JSON.stringify(array));
console.log(object.name + ":" + object.age);
console.log(nested.items[1].ok);
console.log(nested.name);
"""

    assert run_and_collect(source) == [
        '[1,true,null,"x"]',
        "Pragun:20",
        "true",
        "nested",
    ]


def test_json_parse_escaped_characters_and_whitespace():
    source = r"""
let text = JSON.parse('"line\\nquote: \\\"ok\\\""');
let object = JSON.parse('  { "ok": true, "value": 3 }  ');

console.log(text);
console.log(object.ok);
console.log(object.value);
"""

    assert run_and_collect(source) == ["line\nquote: \"ok\"", "true", "3"]


def test_json_parse_round_trip_with_json_stringify():
    source = """
let value = { name: "Pragun", items: [1, true, null] };
let copy = JSON.parse(JSON.stringify(value));

console.log(copy.name);
console.log(copy.items[0]);
console.log(copy.items[1]);
console.log(copy.items[2]);
"""

    assert run_and_collect(source) == ["Pragun", "1", "true", "null"]


def test_json_parse_invalid_json_is_clear_cli_error():
    exit_code, stdout, stderr = run_cli("JSON.parse('{bad json}');")

    assert exit_code == 1
    assert stdout == ""
    assert "Invalid JSON." in stderr
    assert "Traceback" not in stderr


def test_json_parse_non_string_argument_is_clear_cli_error():
    exit_code, stdout, stderr = run_cli("JSON.parse(123);")

    assert exit_code == 1
    assert stdout == ""
    assert "JSON.parse argument must be a string." in stderr
    assert "Traceback" not in stderr


def test_json_parse_requires_exactly_one_argument():
    exit_code, stdout, stderr = run_cli("JSON.parse();")

    assert exit_code == 1
    assert stdout == ""
    assert "JSON.parse expects exactly one argument." in stderr
    assert "Traceback" not in stderr
