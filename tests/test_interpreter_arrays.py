from thunder_js.interpreter import run_source


def run_and_collect(source):
    lines = []
    run_source(source, output=lines.append)
    return lines


def test_public_array_reverse_case():
    source = """
let arr = [1, 2, 3, 4, 5];
let reversed = [...arr].reverse();

console.log("Original: " + arr.join(", "));
console.log("Reversed: " + reversed.join(", "));
"""

    assert run_and_collect(source) == [
        "Original: 1, 2, 3, 4, 5",
        "Reversed: 5, 4, 3, 2, 1",
    ]


def test_empty_arrays_length_and_join():
    source = """
let arr = [];
console.log(arr.length);
console.log(arr.join(","));
"""

    assert run_and_collect(source) == ["0", ""]


def test_array_indexing_and_out_of_range_access():
    source = """
let arr = [10, 20, 30];
console.log(arr[0]);
console.log(arr[2]);
console.log(arr[99]);
"""

    assert run_and_collect(source) == ["10", "30", "undefined"]


def test_computed_array_named_properties_and_methods():
    source = """
let values = [1, 2];

console.log(values["length"]);
console.log(values["join"](","));
"""

    assert run_and_collect(source) == ["2", "1,2"]


def test_computed_array_keys_use_canonical_indexes_only():
    source = """
let values = [10, 20];

console.log(values[1]);
console.log(values["1"]);
console.log(values[1.9]);
console.log(values["01"]);
console.log(values[-1]);
console.log(values[999999]);
"""

    assert run_and_collect(source) == [
        "20",
        "20",
        "undefined",
        "undefined",
        "undefined",
        "undefined",
    ]


def test_array_length_property():
    assert run_and_collect("console.log([1, 2, 3].length);") == ["3"]


def test_spread_clone_is_separate_array():
    source = """
let arr = [1, 2, 3];
let clone = [...arr];
clone[0] = 99;
console.log(arr.join(","));
console.log(clone.join(","));
"""

    assert run_and_collect(source) == ["1,2,3", "99,2,3"]


def test_original_array_unchanged_after_reversing_clone():
    source = """
let arr = [1, 2, 3];
let reversed = [...arr].reverse();
console.log(arr.join(","));
console.log(reversed.join(","));
"""

    assert run_and_collect(source) == ["1,2,3", "3,2,1"]


def test_push_and_pop():
    source = """
let arr = [1];
console.log(arr.push(2, 3));
console.log(arr.join(","));
console.log(arr.pop());
console.log(arr.join(","));
"""

    assert run_and_collect(source) == ["3", "1,2,3", "3", "1,2"]


def test_shift_and_unshift():
    source = """
let arr = [2, 3];
console.log(arr.unshift(0, 1));
console.log(arr.join(","));
console.log(arr.shift());
console.log(arr.join(","));
"""

    assert run_and_collect(source) == ["4", "0,1,2,3", "0", "1,2,3"]


def test_slice_does_not_mutate_original():
    source = """
let arr = [1, 2, 3, 4];
let part = arr.slice(1, 3);
console.log(part.join("-"));
console.log(arr.join("-"));
console.log(arr.slice(-2).join("-"));
"""

    assert run_and_collect(source) == ["2-3", "1-2-3-4", "3-4"]


def test_splice_mutates_and_returns_removed_items():
    source = """
let arr = [1, 2, 3, 4];
let removed = arr.splice(1, 2, "x", "y");
console.log(removed.join(","));
console.log(arr.join(","));
"""

    assert run_and_collect(source) == ["2,3", "1,x,y,4"]


def test_concat_returns_new_array():
    source = """
let first = [1, 2];
let combined = first.concat([3, 4], 5);
console.log(first.join(","));
console.log(combined.join(","));
"""

    assert run_and_collect(source) == ["1,2", "1,2,3,4,5"]


def test_includes_and_index_of():
    source = """
let arr = ["a", "b", "c"];
console.log(arr.includes("b"));
console.log(arr.includes("z"));
console.log(arr.indexOf("c"));
console.log(arr.indexOf("z"));
"""

    assert run_and_collect(source) == ["true", "false", "2", "-1"]


def test_reverse_mutates_and_returns_same_array():
    source = """
let arr = [1, 2, 3];
let result = arr.reverse();
result[0] = 9;
console.log(arr.join(","));
console.log(result.join(","));
"""

    assert run_and_collect(source) == ["9,2,1", "9,2,1"]


def test_join_with_separator_and_default_separator():
    source = """
let arr = [1, 2, 3];
console.log(arr.join(" | "));
console.log(arr.join());
"""

    assert run_and_collect(source) == ["1 | 2 | 3", "1,2,3"]


def test_default_sort_mutates_array_lexicographically():
    source = """
let arr = [3, 11, 2];
let result = arr.sort();
console.log(arr.join(","));
console.log(result.join(","));
"""

    assert run_and_collect(source) == ["11,2,3", "11,2,3"]


def test_array_element_assignment_can_extend_array():
    source = """
let arr = [1, 2];
arr[1] = 20;
arr[3] = 40;
console.log(arr.join(","));
console.log(arr[2]);
console.log(arr[3]);
"""

    assert run_and_collect(source) == ["1,20,,40", "undefined", "40"]
