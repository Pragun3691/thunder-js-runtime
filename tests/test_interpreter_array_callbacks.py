from io import StringIO

from thunder_js.cli import main
from thunder_js.interpreter import run_source


def run_and_collect(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def test_map_with_arrow_function():
    source = """
let doubled = [1, 2, 3].map(x => x * 2);

console.log(doubled.join(","));
"""

    assert run_and_collect(source) == ["2,4,6"]


def test_map_uses_index_argument():
    source = """
let values = [10, 20, 30].map((value, index) => value + index);

console.log(values.join(","));
"""

    assert run_and_collect(source) == ["10,21,32"]


def test_filter_returns_matching_items():
    source = """
let evens = [1, 2, 3, 4].filter(x => x % 2 === 0);

console.log(evens.join(","));
"""

    assert run_and_collect(source) == ["2,4"]


def test_reduce_with_initial_value():
    source = """
let total = [1, 2, 3].reduce((sum, value) => sum + value, 10);

console.log(total);
"""

    assert run_and_collect(source) == ["16"]


def test_reduce_without_initial_value():
    source = """
let total = [1, 2, 3, 4].reduce((sum, value) => sum + value);

console.log(total);
"""

    assert run_and_collect(source) == ["10"]


def test_reduce_empty_array_without_initial_value_is_error():
    source = """
[].reduce((sum, value) => sum + value);
"""
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "Reduce of empty array with no initial value." in stderr.getvalue()
    assert "Traceback" not in stderr.getvalue()


def test_find_match_and_no_match():
    source = """
console.log([1, 2, 3].find(x => x > 1));
console.log([1, 2, 3].find(x => x > 9));
"""

    assert run_and_collect(source) == ["2", "undefined"]


def test_some_true_and_false():
    source = """
console.log([1, 2, 3].some(x => x === 2));
console.log([1, 2, 3].some(x => x === 9));
"""

    assert run_and_collect(source) == ["true", "false"]


def test_every_true_and_false():
    source = """
console.log([2, 4, 6].every(x => x % 2 === 0));
console.log([2, 3, 6].every(x => x % 2 === 0));
"""

    assert run_and_collect(source) == ["true", "false"]


def test_callback_receives_original_array():
    source = """
let arr = [5, 6, 7];

console.log(arr.every((value, index, array) => array === arr));
console.log(arr.map((value, index, array) => array[index]).join(","));
"""

    assert run_and_collect(source) == ["true", "5,6,7"]


def test_filter_and_map_can_be_chained():
    source = """
let result = [1, 2, 3, 4].filter(x => x % 2 === 0).map(x => x * 10);

console.log(result.join(","));
"""

    assert run_and_collect(source) == ["20,40"]


def test_some_short_circuits_after_first_truthy_result():
    source = """
let calls = 0;
let result = [1, 2, 3].some(x => {
    calls += 1;
    return x === 2;
});

console.log(result);
console.log(calls);
"""

    assert run_and_collect(source) == ["true", "2"]


def test_every_short_circuits_after_first_falsy_result():
    source = """
let calls = 0;
let result = [2, 4, 5, 6].every(x => {
    calls += 1;
    return x % 2 === 0;
});

console.log(result);
console.log(calls);
"""

    assert run_and_collect(source) == ["false", "3"]


def test_original_array_is_unchanged():
    source = """
let arr = [1, 2, 3, 4];
let mapped = arr.map(x => x * 10);
let filtered = arr.filter(x => x > 2);
let total = arr.reduce((sum, value) => sum + value, 0);

console.log(arr.join(","));
console.log(mapped.join(","));
console.log(filtered.join(","));
console.log(total);
"""

    assert run_and_collect(source) == ["1,2,3,4", "10,20,30,40", "3,4", "10"]


def test_invalid_callback_error():
    source = """
[1, 2, 3].map(123);
"""
    stdout = StringIO()
    stderr = StringIO()

    exit_code = main([], stdin=StringIO(source), stdout=stdout, stderr=stderr)

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "Array.map callback must be a function." in stderr.getvalue()
    assert "Traceback" not in stderr.getvalue()
