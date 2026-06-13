"""Basic expression interpreter for the Thunder JavaScript runtime."""

from collections.abc import Callable

from thunder_js.ast_nodes import (
    AssignmentExpression,
    BinaryExpression,
    BlockStatement,
    BooleanLiteral,
    CallExpression,
    ComputedMemberExpression,
    ExpressionStatement,
    GroupingExpression,
    Identifier,
    IfStatement,
    LogicalExpression,
    NullLiteral,
    NumericLiteral,
    PostfixUpdateExpression,
    PrefixUpdateExpression,
    Program,
    PropertyAccessExpression,
    StringLiteral,
    UnaryExpression,
    UndefinedLiteral,
    VariableDeclaration,
)
from thunder_js.environment import Environment
from thunder_js.js_builtins import JSCallable, create_global_environment
from thunder_js.lexer import Lexer
from thunder_js.parser import Parser
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
    """Raised when a program cannot be executed."""


class Interpreter:
    """Execute programs and evaluate expression AST nodes."""

    def __init__(self, output: Callable[[str], None] | None = None):
        self.output = output if output is not None else print
        self.environment = create_global_environment(self.output)

    def execute(self, statement: object) -> None:
        if isinstance(statement, Program):
            for child in statement.body:
                self.execute(child)
            return
        if isinstance(statement, ExpressionStatement):
            self.evaluate(statement.expression)
            return
        if isinstance(statement, BlockStatement):
            self._execute_block(statement, Environment(self.environment))
            return
        if isinstance(statement, VariableDeclaration):
            self._execute_variable_declaration(statement)
            return
        if isinstance(statement, IfStatement):
            self._execute_if(statement)
            return

        raise InterpreterError("Unknown statement.")

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
            return self._evaluate_assignment(expression)
        if isinstance(expression, PrefixUpdateExpression):
            raise InterpreterError("Update expressions are not supported yet.")
        if isinstance(expression, PostfixUpdateExpression):
            raise InterpreterError("Update expressions are not supported yet.")

        raise InterpreterError("Unknown expression.")

    def _execute_block(self, statement: BlockStatement, environment: Environment) -> None:
        previous = self.environment
        self.environment = environment

        try:
            for child in statement.body:
                self.execute(child)
        finally:
            self.environment = previous

    def _execute_variable_declaration(self, statement: VariableDeclaration) -> None:
        value = JS_UNDEFINED

        if statement.initializer is not None:
            value = self.evaluate(statement.initializer)

        try:
            self.environment.define(
                statement.name,
                value,
                mutable=statement.kind == "let",
            )
        except NameError as error:
            raise InterpreterError(str(error)) from error

    def _execute_if(self, statement: IfStatement) -> None:
        if to_boolean(self.evaluate(statement.test)):
            self.execute(statement.consequent)
        elif statement.alternate is not None:
            self.execute(statement.alternate)

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

    def _evaluate_assignment(self, expression: AssignmentExpression) -> object:
        if not isinstance(expression.target, Identifier):
            raise InterpreterError("Only variable assignment is supported yet.")

        right = self.evaluate(expression.value)
        name = expression.target.name

        try:
            if expression.operator == "=":
                return self.environment.assign(name, right)

            left = self.environment.get(name)

            if expression.operator == "+=":
                value = js_add(left, right)
            elif expression.operator == "-=":
                value = to_number(left) - to_number(right)
            elif expression.operator == "*=":
                value = to_number(left) * to_number(right)
            elif expression.operator == "/=":
                value = js_divide(left, right)
            else:
                raise InterpreterError(
                    f"Unsupported assignment operator {expression.operator}."
                )

            return self.environment.assign(name, value)
        except (NameError, TypeError) as error:
            raise InterpreterError(str(error)) from error

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
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse_program()
    interpreter.execute(program)


def value_to_output(value: object) -> str:
    return format_value(value)
