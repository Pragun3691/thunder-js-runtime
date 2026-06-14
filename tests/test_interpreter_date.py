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


def test_date_now_returns_a_number():
    source = """
let now = Date.now();
console.log(now > 0);
console.log(Number(now) === now);
"""

    assert run_and_collect(source) == ["true", "true"]


def test_new_date_zero_get_time_returns_zero():
    assert run_and_collect("console.log(new Date(0).getTime());") == ["0"]


def test_new_date_zero_to_iso_string():
    source = """
let date = new Date(0);
console.log(date.toISOString());
"""

    assert run_and_collect(source) == ["1970-01-01T00:00:00.000Z"]


def test_known_utc_parts_for_unix_epoch():
    source = """
let date = new Date(0);
console.log(date.getFullYear());
console.log(date.getMonth());
console.log(date.getDate());
console.log(date.getDay());
console.log(date.getHours());
console.log(date.getMinutes());
console.log(date.getSeconds());
"""

    assert run_and_collect(source) == ["1970", "0", "1", "4", "0", "0", "0"]


def test_current_date_construction_uses_current_time():
    source = """
let before = Date.now();
let date = new Date();
let after = Date.now();
console.log(date.getTime() >= before && date.getTime() <= after);
"""

    assert run_and_collect(source) == ["true"]


def test_date_from_known_timestamp_parts():
    source = """
let date = new Date(946684800000);
console.log(date.getFullYear());
console.log(date.getMonth());
console.log(date.getDate());
console.log(date.getDay());
console.log(date.toISOString());
"""

    assert run_and_collect(source) == [
        "2000",
        "0",
        "1",
        "6",
        "2000-01-01T00:00:00.000Z",
    ]


def test_invalid_date_constructor_input_is_clean_runtime_error():
    source = """
let date = new Date("not a timestamp");
console.log(date.getTime());
"""
    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert "Invalid Date timestamp." in stderr
    assert "Traceback" not in stderr


def test_invalid_date_constructor_infinity_has_no_traceback():
    source = """
new Date(1 / 0);
"""
    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert "Invalid Date timestamp." in stderr
    assert "Traceback" not in stderr


def test_only_date_construction_is_supported_with_new():
    source = """
new Number(1);
"""
    exit_code, stdout, stderr = run_cli(source)

    assert exit_code == 1
    assert stdout == ""
    assert "Only Date construction is supported with new." in stderr
    assert "Traceback" not in stderr
