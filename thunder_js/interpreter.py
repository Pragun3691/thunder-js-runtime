"""Basic expression interpreter for the Thunder JavaScript runtime."""

from collections.abc import Callable

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
from thunder_js.environment import Environment
from thunder_js.js_builtins import JSCallable, create_global_environment
from thunder_js.lexer import Lexer
from thunder_js.parser import Parser
from thunder_js.tokens import Token, TokenType
from thunder_js.values import (
    JS_NULL,
    JS_UNDEFINED,
    format_value,
    js_add,
    js_divide,
    js_remainder,
    loose_equal,
    strict_equal,
    to_boolean,
    to_number,
)


class InterpreterError(Exception):
    """Raised when an expression cannot be evaluated."""


class Interpreter:
    """Evaluate expression AST nodes."""

    def __init__(self, output: Callable[[str], None] | None = None):
        self.output = output if output is not None else print
        self.environment = create_global_environment(self.output)

    def evaluate(self, expression: object) -> object:
        if isinstance(expression, NumericLiteral):
            return expression.value
        if isinstance(expression, StringLiteral):
            return expression.value
        if isinstance(expression, BooleanLiteral):
            return expression.value
        if isinstance(expression, NullLiteral):
            return JS_NULL
        if isinstance(expression, UndefinedLiteral):
            return JS_UNDEFINED
        if isinstance(expression, GroupingExpression):
            return self.evaluate(expression.expression)
        if isinstance(expression, UnaryExpression):
            return self._evaluate_unary(expression)
        if isinstance(expression, BinaryExpression):
            return self._evaluate_binary(expression)
        if isinstance(expression, LogicalExpression):
            return self._evaluate_logical(expression)
        if isinstance(expression, Identifier):
            return self._look_up_identifier(expression)
        if isinstance(expression, PropertyAccessExpression):
            return self._get_property(expression)
        if isinstance(expression, ComputedMemberExpression):
            raise InterpreterError("Computed member access is not supported yet.")
        if isinstance(expression, CallExpression):
            return self._evaluate_call(expression)
        if isinstance(expression, AssignmentExpression):
            raise InterpreterError("Assignment is not supported yet.")
        if isinstance(expression, PrefixUpdateExpression):
            raise InterpreterError("Update expressions are not supported yet.")
        if isinstance(expression, PostfixUpdateExpression):
            raise InterpreterError("Update expressions are not supported yet.")

        raise InterpreterError("Unknown expression.")

    def _evaluate_unary(self, expression: UnaryExpression) -> object:
        value = self.evaluate(expression.argument)

        if expression.operator == "!":
            return not to_boolean(value)
        if expression.operator == "-":
            return -to_number(value)
        if expression.operator == "+":
            return to_number(value)

        raise InterpreterError(f"Unsupported unary operator {expression.operator}.")

    def _evaluate_binary(self, expression: BinaryExpression) -> object:
        left = self.evaluate(expression.left)
        right = self.evaluate(expression.right)
        operator = expression.operator

        if operator == "+":
            return js_add(left, right)
        if operator == "-":
            return to_number(left) - to_number(right)
        if operator == "*":
            return to_number(left) * to_number(right)
        if operator == "/":
            return js_divide(left, right)
        if operator == "%":
            return js_remainder(left, right)
        if operator == "**":
            return to_number(left) ** to_number(right)
        if operator == "<":
            return self._compare(left, right, "<")
        if operator == "<=":
            return self._compare(left, right, "<=")
        if operator == ">":
            return self._compare(left, right, ">")
        if operator == ">=":
            return self._compare(left, right, ">=")
        if operator == "==":
            return loose_equal(left, right)
        if operator == "!=":
            return not loose_equal(left, right)
        if operator == "===":
            return strict_equal(left, right)
        if operator == "!==":
            return not strict_equal(left, right)

        raise InterpreterError(f"Unsupported binary operator {operator}.")

    def _compare(self, left: object, right: object, operator: str) -> bool:
        if isinstance(left, str) and isinstance(right, str):
            left_value = left
            right_value = right
        else:
            left_value = to_number(left)
            right_value = to_number(right)

        if operator == "<":
            return left_value < right_value
        if operator == "<=":
            return left_value <= right_value
        if operator == ">":
            return left_value > right_value
        if operator == ">=":
            return left_value >= right_value

        raise InterpreterError(f"Unsupported comparison operator {operator}.")

    def _evaluate_logical(self, expression: LogicalExpression) -> object:
        left = self.evaluate(expression.left)

        if expression.operator == "&&":
            if not to_boolean(left):
                return left
            return self.evaluate(expression.right)
        if expression.operator == "||":
            if to_boolean(left):
                return left
            return self.evaluate(expression.right)

        raise InterpreterError(f"Unsupported logical operator {expression.operator}.")

    def _look_up_identifier(self, expression: Identifier) -> object:
        try:
            return self.environment.get(expression.name)
        except NameError as error:
            raise InterpreterError(str(error)) from error

    def _get_property(self, expression: PropertyAccessExpression) -> object:
        container = self.evaluate(expression.object)

        if isinstance(container, dict) and expression.property.name in container:
            return container[expression.property.name]

        raise InterpreterError(f"Property {expression.property.name} is not defined.")

    def _evaluate_call(self, expression: CallExpression) -> object:
        callee = self.evaluate(expression.callee)
        arguments = [self.evaluate(argument) for argument in expression.arguments]

        if isinstance(callee, JSCallable):
            return callee.call(arguments)

        raise InterpreterError("Value is not callable.")


def evaluate_expression(source: str) -> object:
    tokens = Lexer(source).tokenize()
    expression = Parser(tokens).parse()
    return Interpreter().evaluate(expression)


def run_source(source: str, output: Callable[[str], None] | None = None) -> None:
    interpreter = Interpreter(output)
    for expression in parse_expression_chunks(source):
        interpreter.evaluate(expression)


def parse_expression_chunks(source: str) -> list[object]:
    tokens = Lexer(source).tokenize()
    expressions = []
    current_tokens: list[Token] = []

    for token in tokens:
        if token.type == TokenType.SEMICOLON:
            if current_tokens:
                expressions.append(_parse_chunk(current_tokens, token))
                current_tokens = []
        elif token.type == TokenType.EOF:
            if current_tokens:
                expressions.append(_parse_chunk(current_tokens, token))
        else:
            current_tokens.append(token)

    return expressions


def _parse_chunk(tokens: list[Token], end_token: Token) -> object:
    chunk = tokens + [Token(TokenType.EOF, "", None, end_token.line, end_token.column)]
    return Parser(chunk).parse()


def value_to_output(value: object) -> str:
    return format_value(value)
