from io import StringIO

import pytest

from thunder_js.cli import main
from thunder_js.interpreter import Interpreter, InterpreterError, run_source
from thunder_js.lexer import Lexer
from thunder_js.parser import Parser
from thunder_js.values import JS_NULL, JS_UNDEFINED, format_value


def evaluate(source):
    tokens = Lexer(source).tokenize()
    expression = Parser(tokens).parse()
    return Interpreter(output=lambda line: None).evaluate(expression)


def run_and_collect(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def test_evaluates_basic_literals():
    assert evaluate("12") == 12
    assert evaluate("'hello'") == "hello"
    assert evaluate("true") is True
    assert evaluate("false") is False
    assert evaluate("null") is JS_NULL
    assert evaluate("undefined") is JS_UNDEFINED


def test_javascript_output_formatting_for_special_values():
    assert format_value(True) == "true"
    assert format_value(False) == "false"
    assert format_value(JS_NULL) == "null"
    assert format_value(JS_UNDEFINED) == "undefined"


def test_grouping_unary_and_arithmetic():
    assert evaluate("(2 + 3) * 4") == 20
    assert evaluate("2 + 3 * 4") == 14
    assert evaluate("2 ** 3 ** 2") == 512
    assert evaluate("7 % 2") == 1
    assert evaluate("-5 % 2") == -1
    assert evaluate("-5 + +2") == -3
    assert evaluate("!false") is True


def test_plus_uses_javascript_string_and_number_behavior():
    assert evaluate("1 + 2") == 3
    assert evaluate('"a" + 2') == "a2"
    assert evaluate('1 + "2"') == "12"
    assert evaluate('"value: " + true') == "value: true"
    assert evaluate('"x" + null') == "xnull"


def test_comparison_and_equality_operators():
    assert evaluate("3 < 4") is True
    assert evaluate("4 <= 4") is True
    assert evaluate("5 > 6") is False
    assert evaluate('"a" < "b"') is True
    assert evaluate('"5" == 5') is True
    assert evaluate('"5" === 5') is False
    assert evaluate("null == undefined") is True
    assert evaluate("null === undefined") is False
    assert evaluate("1 != 2") is True
    assert evaluate("1 !== '1'") is True


def test_logical_operators_return_javascript_values_and_short_circuit():
    assert evaluate("true && 'yes'") == "yes"
    assert evaluate("false && missing") is False
    assert evaluate("true || missing") is True
    assert evaluate("'' || 'fallback'") == "fallback"


def test_console_log_outputs_formatted_values():
    lines = run_and_collect(
        'console.log("answer", 42, true, false, null, undefined);'
    )

    assert lines == ["answer 42 true false null undefined"]


def test_run_source_supports_multiple_expression_chunks():
    lines = run_and_collect("console.log(1); console.log(2)")

    assert lines == ["1", "2"]


def test_unknown_identifier_is_runtime_error():
    with pytest.raises(InterpreterError, match="missing is not defined"):
        evaluate("missing")


def test_cli_reads_from_stdin_and_separates_stdout_and_stderr():
    stdin = StringIO('console.log("stdin", 3 + 4);')
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([], stdin=stdin, stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert stdout.getvalue() == "stdin 7\n"
    assert stderr.getvalue() == ""


def test_cli_reads_from_file(tmp_path):
    source_file = tmp_path / "program.js"
    source_file.write_text('console.log("file");', encoding="utf-8")
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([str(source_file)], stdout=stdout, stderr=stderr)

    assert exit_code == 0
    assert stdout.getvalue() == "file\n"
    assert stderr.getvalue() == ""


def test_cli_writes_errors_to_stderr_only():
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([], stdin=StringIO("missing;"), stdout=stdout, stderr=stderr)

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "missing is not defined" in stderr.getvalue()
