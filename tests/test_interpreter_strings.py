from io import StringIO

import pytest

from thunder_js.cli import main
from thunder_js.interpreter import run_source


def run_and_collect(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def test_public_palindrome_case():
    source = """
let str = "racecar";
let reversed = str.split("").reverse().join("");

if (str === reversed) {
    console.log(str + " is a Palindrome");
} else {
    console.log(str + " is not a Palindrome");
}
"""

    assert run_and_collect(source) == ["racecar is a Palindrome"]


def test_non_palindrome_case():
    source = """
let str = "thunder";
let reversed = str.split("").reverse().join("");

if (str === reversed) {
    console.log(str + " is a Palindrome");
} else {
    console.log(str + " is not a Palindrome");
}
"""

    assert run_and_collect(source) == ["thunder is not a Palindrome"]


def test_empty_string_palindrome_case():
    source = """
let str = "";
let reversed = str.split("").reverse().join("");

if (str === reversed) {
    console.log("empty palindrome");
}
"""

    assert run_and_collect(source) == ["empty palindrome"]


def test_single_character_palindrome_case():
    source = """
let str = "x";
let reversed = str.split("").reverse().join("");

if (str === reversed) {
    console.log(str + " is a Palindrome");
}
"""

    assert run_and_collect(source) == ["x is a Palindrome"]


def test_string_length_property():
    assert run_and_collect('console.log("thunder".length);') == ["7"]


def test_split_with_empty_separator():
    source = """
let parts = "abc".split("");
console.log(parts.join("-"));
"""

    assert run_and_collect(source) == ["a-b-c"]


def test_split_with_normal_separator():
    source = """
let parts = "red,green,blue".split(",");
console.log(parts.join("|"));
"""

    assert run_and_collect(source) == ["red|green|blue"]


def test_reverse_mutates_runtime_array():
    source = """
let parts = "abc".split("");
let same = parts.reverse();
console.log(parts.join(""));
console.log(same.join(""));
"""

    assert run_and_collect(source) == ["cba", "cba"]


def test_join_with_separator():
    source = """
let parts = "one two three".split(" ");
console.log(parts.join(" / "));
"""

    assert run_and_collect(source) == ["one / two / three"]


def test_chained_method_calls():
    source = """
console.log("hello".split("").reverse().join(""));
console.log("  Thunder  ".trim().toLowerCase());
"""

    assert run_and_collect(source) == ["olleh", "thunder"]


def test_listed_string_methods():
    source = """
let text = "  Hello Thunder Hello  ";
console.log(text.trim());
console.log(text.toUpperCase());
console.log(text.toLowerCase());
console.log(text.replace("Hello", "Hi").trim());
console.log(text.replaceAll("Hello", "Hi").trim());
console.log("abcdef".substring(1, 4));
console.log("abcdef".substring(4, 1));
console.log("abcdef".slice(1, 4));
console.log("abcdef".slice(-3));
console.log("Thunder".includes("und"));
console.log("Thunder".startsWith("Thu"));
console.log("Thunder".endsWith("der"));
console.log("Thunder".indexOf("nde"));
console.log("Thunder".indexOf("missing"));
"""

    assert run_and_collect(source) == [
        "Hello Thunder Hello",
        "  HELLO THUNDER HELLO  ",
        "  hello thunder hello  ",
        "Hi Thunder Hello",
        "Hi Thunder Hi",
        "bcd",
        "bcd",
        "bcd",
        "def",
        "true",
        "true",
        "true",
        "3",
        "-1",
    ]


def test_selected_string_methods_and_boundaries():
    source = """
console.log("Thunder".charAt(0));
console.log("Thunder".charAt(99) === "");
console.log("".charAt(0) === "");
console.log("Thunder".charCodeAt(0));
console.log("Thunder".charCodeAt(99));
console.log("ha".repeat(3));
console.log("ha".repeat());
console.log("5".padStart(3, "0"));
console.log("5".padEnd(3));
console.log("abc".padStart(2, "0"));
console.log("abc".padEnd(5, ""));
console.log("[" + "  hi  ".trimStart() + "]");
console.log("[" + "  hi  ".trimEnd() + "]");
console.log("abc".at(0));
console.log("abc".at(-1));
console.log(String("abc".at(99)));
console.log(String("".at(0)));
console.log("a".concat("b", 1, true, null, undefined));
"""

    assert run_and_collect(source) == [
        "T",
        "true",
        "true",
        "84",
        "NaN",
        "hahaha",
        "",
        "005",
        "5  ",
        "abc",
        "abc",
        "[hi  ]",
        "[  hi]",
        "a",
        "c",
        "undefined",
        "undefined",
        "ab1truenullundefined",
    ]


@pytest.mark.parametrize("count", ["-1", '"bad"', "Infinity"])
def test_string_repeat_invalid_count_is_clear_cli_error(count):
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [],
        stdin=StringIO(f'console.log("x".repeat({count}));'),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "String.repeat count must be a finite non-negative number" in stderr.getvalue()
    assert "Traceback" not in stderr.getvalue()


def test_missing_string_method_error_goes_to_stderr_only():
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [],
        stdin=StringIO('console.log("abc".missing());'),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "String method missing is not defined" in stderr.getvalue()


def test_invalid_string_method_call_error_goes_to_stderr_only():
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [],
        stdin=StringIO('console.log("abc".length());'),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "Value is not callable" in stderr.getvalue()


def test_missing_array_method_error_goes_to_stderr_only():
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main(
        [],
        stdin=StringIO(
            'let parts = "abc".split(""); console.log(parts.unknownMethod());'
        ),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "Array method unknownMethod is not defined" in stderr.getvalue()
