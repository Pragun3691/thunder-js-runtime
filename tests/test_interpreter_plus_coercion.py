from thunder_js.interpreter import run_source


def run_and_collect(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def test_array_plus_array_uses_array_string_coercion():
    assert run_and_collect("console.log([1, 2] + [3, 4]);") == ["1,23,4"]


def test_array_plus_string_and_string_plus_array():
    source = """
console.log([1, 2] + "");
console.log("items: " + [1, 2]);
"""

    assert run_and_collect(source) == ["1,2", "items: 1,2"]


def test_empty_array_plus_combinations():
    source = """
console.log([] + []);
console.log([] + 1);
"""

    assert run_and_collect(source) == ["", "1"]


def test_object_plus_string_and_string_plus_object():
    source = """
console.log({ a: 1 } + "");
console.log("value=" + { a: 1 });
"""

    assert run_and_collect(source) == ["[object Object]", "value=[object Object]"]


def test_object_plus_number():
    assert run_and_collect("console.log({ a: 1 } + 5);") == ["[object Object]5"]


def test_numeric_addition_still_works():
    source = """
console.log(2 + 3);
console.log(true + 1);
console.log(null + 1);
"""

    assert run_and_collect(source) == ["5", "2", "1"]


def test_null_undefined_and_string_coercion_regressions():
    source = """
console.log("x" + null);
console.log(null + "x");
console.log("x" + undefined);
console.log(undefined + "x");
console.log(undefined + 1);
"""

    assert run_and_collect(source) == [
        "xnull",
        "nullx",
        "xundefined",
        "undefinedx",
        "NaN",
    ]
