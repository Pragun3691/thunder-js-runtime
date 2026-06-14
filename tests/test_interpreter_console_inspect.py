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


def test_console_log_inspects_arrays_and_objects():
    source = """
console.log([1, 2, 3]);
console.log([[1, 2], [3, 4]]);
console.log({ name: "Pragun", age: 20 });
"""

    assert run_and_collect(source) == [
        "[ 1, 2, 3 ]",
        "[ [ 1, 2 ], [ 3, 4 ] ]",
        "{ name: 'Pragun', age: 20 }",
    ]


def test_console_log_keeps_top_level_strings_unquoted_and_separates_arguments():
    assert run_and_collect('console.log("hello", [1, 2]);') == [
        "hello [ 1, 2 ]"
    ]


def test_console_log_quotes_and_escapes_nested_strings():
    source = r"""
console.log(["hello", "Prag'un", "line\nend"]);
console.log({ label: "a\tb" });
"""

    assert run_and_collect(source) == [
        "[ 'hello', 'Prag\\'un', 'line\\nend' ]",
        "{ label: 'a\\tb' }",
    ]


def test_console_log_inspection_does_not_change_string_coercion_paths():
    source = """
console.log([null, undefined].join(", "));
console.log(String([1, 2, 3]));
console.log(`${[1, 2, 3]}`);
console.log([1, 2, 3] + "");
"""

    assert run_and_collect(source) == [", ", "1,2,3", "1,2,3", "1,2,3"]


def test_console_log_circular_arrays_and_objects_use_placeholder():
    source = """
let values = [];
values.push(values);
console.log(values);

let object = {};
object.self = object;
console.log(object);
"""

    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 0
    assert stdout == "[ [Circular] ]\n{ self: [Circular] }\n"
    assert stderr == ""
    assert "Traceback" not in stderr


def test_console_log_does_not_print_python_function_reprs():
    lines = run_and_collect(
        """
console.log(console.log);
console.log({ fn: console.log });
"""
    )

    output = "\n".join(lines)
    assert lines == ["[Function]", "{ fn: [Function] }"]
    assert "object at 0x" not in output
    assert "thunder_js." not in output
