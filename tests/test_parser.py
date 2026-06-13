import pytest

from thunder_js.ast_nodes import (
    AssignmentExpression,
    BinaryExpression,
    BooleanLiteral,
    CallExpression,
    ComputedMemberExpression,
    GroupingExpression,
    Identifier,
    LogicalExpression,
    NullLiteral,
    NumericLiteral,
    PostfixUpdateExpression,
    PrefixUpdateExpression,
    PropertyAccessExpression,
    StringLiteral,
    UnaryExpression,
    UndefinedLiteral,
)
from thunder_js.lexer import Lexer
from thunder_js.parser import Parser, ParserError


def parse_expression(source):
    return Parser(Lexer(source).tokenize()).parse()


def test_literal_expression_nodes():
    assert parse_expression("42") == NumericLiteral(42)
    assert parse_expression('"hello"') == StringLiteral("hello")
    assert parse_expression("true") == BooleanLiteral(True)
    assert parse_expression("false") == BooleanLiteral(False)
    assert parse_expression("null") == NullLiteral()
    assert parse_expression("undefined") == UndefinedLiteral()


def test_multiplication_has_higher_precedence_than_addition():
    expression = parse_expression("2 + 3 * 4")

    assert isinstance(expression, BinaryExpression)
    assert expression.operator == "+"
    assert expression.left == NumericLiteral(2)
    assert isinstance(expression.right, BinaryExpression)
    assert expression.right.operator == "*"
    assert expression.right.left == NumericLiteral(3)
    assert expression.right.right == NumericLiteral(4)


def test_grouping_can_override_arithmetic_precedence():
    expression = parse_expression("(2 + 3) * 4")

    assert isinstance(expression, BinaryExpression)
    assert expression.operator == "*"
    assert isinstance(expression.left, GroupingExpression)
    assert expression.left.expression == BinaryExpression(
        NumericLiteral(2), "+", NumericLiteral(3)
    )
    assert expression.right == NumericLiteral(4)


def test_exponentiation_is_right_associative():
    expression = parse_expression("2 ** 3 ** 2")

    assert expression == BinaryExpression(
        NumericLiteral(2),
        "**",
        BinaryExpression(NumericLiteral(3), "**", NumericLiteral(2)),
    )


def test_remainder_binds_before_strict_equality():
    expression = parse_expression("7 % 2 === 1")

    assert expression == BinaryExpression(
        BinaryExpression(NumericLiteral(7), "%", NumericLiteral(2)),
        "===",
        NumericLiteral(1),
    )


def test_logical_and_with_unary_expression():
    expression = parse_expression("true && !false")

    assert isinstance(expression, LogicalExpression)
    assert expression.operator == "&&"
    assert expression.left == BooleanLiteral(True)
    assert expression.right == UnaryExpression("!", BooleanLiteral(False))


def test_chained_property_and_computed_member_access():
    expression = parse_expression("object.items[0].name")

    assert isinstance(expression, PropertyAccessExpression)
    assert expression.property == Identifier("name")
    computed = expression.object
    assert isinstance(computed, ComputedMemberExpression)
    assert computed.property == NumericLiteral(0)
    items = computed.object
    assert isinstance(items, PropertyAccessExpression)
    assert items.object == Identifier("object")
    assert items.property == Identifier("items")


def test_method_call_parses_callee_and_arguments():
    expression = parse_expression("console.log(x + 2)")

    assert isinstance(expression, CallExpression)
    assert isinstance(expression.callee, PropertyAccessExpression)
    assert expression.callee.object == Identifier("console")
    assert expression.callee.property == Identifier("log")
    assert expression.arguments == [
        BinaryExpression(Identifier("x"), "+", NumericLiteral(2))
    ]


def test_assignment_is_right_associative():
    expression = parse_expression("a = b = 5")

    assert expression == AssignmentExpression(
        Identifier("a"),
        "=",
        AssignmentExpression(Identifier("b"), "=", NumericLiteral(5)),
    )


def test_postfix_update_expression():
    expression = parse_expression("i++")

    assert expression == PostfixUpdateExpression(Identifier("i"), "++")


def test_prefix_update_expression():
    expression = parse_expression("--i")

    assert expression == PrefixUpdateExpression("--", Identifier("i"))


def test_nested_function_calls():
    expression = parse_expression("add(1, multiply(2, 3))")

    assert isinstance(expression, CallExpression)
    assert expression.callee == Identifier("add")
    assert expression.arguments[0] == NumericLiteral(1)
    nested_call = expression.arguments[1]
    assert isinstance(nested_call, CallExpression)
    assert nested_call.callee == Identifier("multiply")
    assert nested_call.arguments == [NumericLiteral(2), NumericLiteral(3)]


def test_assignment_operators_are_supported():
    expression = parse_expression("object.count += 1")

    assert expression == AssignmentExpression(
        PropertyAccessExpression(Identifier("object"), Identifier("count")),
        "+=",
        NumericLiteral(1),
    )


def test_parser_error_includes_line_and_column():
    with pytest.raises(ParserError, match=r"line 1, column 4"):
        parse_expression("1 +")
