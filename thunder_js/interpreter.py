"""Basic expression interpreter for the Thunder JavaScript runtime."""

import math
from collections.abc import Callable
from dataclasses import dataclass

from thunder_js.ast_nodes import (
    AssignmentExpression,
    ArrayBindingPattern,
    ArrayLiteral,
    ArrowFunctionExpression,
    BinaryExpression,
    BindingIdentifier,
    BlockStatement,
    BreakStatement,
    BooleanLiteral,
    CallExpression,
    ComputedMemberExpression,
    ConditionalExpression,
    ContinueStatement,
    DoWhileStatement,
    ExpressionStatement,
    ForInStatement,
    ForOfStatement,
    ForStatement,
    FunctionDeclaration,
    FunctionExpression,
    GroupingExpression,
    Identifier,
    IfStatement,
    LogicalExpression,
    NewExpression,
    NullLiteral,
    NullishCoalescingExpression,
    NumericLiteral,
    ObjectBindingPattern,
    ObjectLiteral,
    PostfixUpdateExpression,
    PrefixUpdateExpression,
    Program,
    PropertyAccessExpression,
    ReturnStatement,
    SpreadElement,
    StringLiteral,
    SwitchStatement,
    TemplateLiteral,
    UnaryExpression,
    UndefinedLiteral,
    VariableDeclaration,
    WhileStatement,
)
from thunder_js.environment import Environment
from thunder_js.js_builtins import (
    BuiltInError,
    JSCallable,
    construct_date,
    create_global_environment,
    date_part,
    date_to_iso_string,
)
from thunder_js.lexer import Lexer
from thunder_js.parser import Parser
from thunder_js.values import (
    JSArray,
    JSDate,
    JS_NULL,
    JSObject,
    JS_UNDEFINED,
    format_value,
    is_nan,
    is_number,
    js_add,
    js_divide,
    js_power,
    js_remainder,
    loose_equal,
    strict_equal,
    to_boolean,
    to_number,
    to_string,
)


class InterpreterError(Exception):
    """Raised when a program cannot be executed."""


class BreakSignal(Exception):
    """Internal signal used to exit a loop."""


class ContinueSignal(Exception):
    """Internal signal used to continue a loop."""


class ReturnSignal(Exception):
    """Internal signal used to return from a function."""

    def __init__(self, value: object):
        self.value = value


OPTIONAL_CHAIN_SHORT_CIRCUIT = object()


@dataclass(frozen=True)
class ResolvedReference:
    read: Callable[[], object]
    write: Callable[[object], object]


class NativeMethod(JSCallable):
    """A small callable wrapper for built-in methods."""

    def __init__(self, method: Callable[[list[object]], object]):
        self.method = method

    def call(self, arguments: list[object]) -> object:
        try:
            return self.method(arguments)
        except ValueError as error:
            raise InterpreterError(str(error)) from error


class JSFunction(JSCallable):
    """A user-defined JavaScript function."""

    def __init__(
        self,
        parameters: list[object],
        rest_parameter: str | None,
        parameter_defaults: list[object | None] | None,
        body: object,
        closure: Environment,
        interpreter: "Interpreter",
        name: str | None = None,
        dynamic_this: bool = True,
    ):
        self.parameters = parameters
        self.rest_parameter = rest_parameter
        if parameter_defaults is None:
            self.parameter_defaults = [None] * len(parameters)
        else:
            self.parameter_defaults = parameter_defaults
        self.body = body
        self.closure = closure
        self.interpreter = interpreter
        self.name = name
        self.dynamic_this = dynamic_this

    def __str__(self) -> str:
        if self.name is not None:
            return f"[Function: {self.name}]"
        return "[Function]"

    __repr__ = __str__

    def call(
        self,
        arguments: list[object],
        this_value: object = JS_UNDEFINED,
    ) -> object:
        self.interpreter.call_depth += 1
        if self.interpreter.call_depth > self.interpreter.call_limit:
            self.interpreter.call_depth -= 1
            raise InterpreterError("Maximum call stack size exceeded.")

        function_environment = Environment(self.closure, is_var_scope=True)

        try:
            previous = self.interpreter.environment
            self.interpreter.environment = function_environment
            try:
                if self.dynamic_this:
                    function_environment.define(
                        "this",
                        this_value,
                        mutable=False,
                    )

                for index, parameter in enumerate(self.parameters):
                    if index < len(arguments) and arguments[index] is not JS_UNDEFINED:
                        value = arguments[index]
                    else:
                        default = self.parameter_defaults[index]
                        if default is None:
                            value = JS_UNDEFINED
                        else:
                            value = self.interpreter.evaluate(default)
                    self.interpreter._bind_pattern(
                        parameter,
                        value,
                        kind="let",
                        assign_existing_var=True,
                    )

                if self.rest_parameter is not None:
                    rest_items = list(arguments[len(self.parameters) :])
                    function_environment.define(self.rest_parameter, JSArray(rest_items))
            finally:
                self.interpreter.environment = previous

            if isinstance(self.body, BlockStatement):
                self.interpreter._execute_block(
                    self.body,
                    Environment(function_environment),
                )
            else:
                previous = self.interpreter.environment
                self.interpreter.environment = function_environment
                try:
                    return self.interpreter.evaluate(self.body)
                finally:
                    self.interpreter.environment = previous
        except ReturnSignal as signal:
            return signal.value
        finally:
            self.interpreter.call_depth -= 1

        return JS_UNDEFINED


class Interpreter:
    """Execute programs and evaluate expression AST nodes."""

    def __init__(
        self,
        output: Callable[[str], None] | None = None,
        step_limit: int = 100_000,
        call_limit: int = 100,
    ):
        self.output = output if output is not None else print
        self.environment = create_global_environment(self.output)
        self.step_limit = step_limit
        self.steps = 0
        self.call_limit = call_limit
        self.call_depth = 0

    def execute(self, statement: object) -> None:
        self._count_step()

        if isinstance(statement, Program):
            try:
                self._execute_statements(statement.body)
            except BreakSignal as error:
                raise InterpreterError("break used outside of a loop.") from error
            except ContinueSignal as error:
                raise InterpreterError("continue used outside of a loop.") from error
            except ReturnSignal as error:
                raise InterpreterError("return used outside of a function.") from error
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
        if isinstance(statement, WhileStatement):
            self._execute_while(statement)
            return
        if isinstance(statement, DoWhileStatement):
            self._execute_do_while(statement)
            return
        if isinstance(statement, ForStatement):
            self._execute_for(statement)
            return
        if isinstance(statement, ForInStatement):
            self._execute_for_in(statement)
            return
        if isinstance(statement, ForOfStatement):
            self._execute_for_of(statement)
            return
        if isinstance(statement, SwitchStatement):
            self._execute_switch(statement)
            return
        if isinstance(statement, FunctionDeclaration):
            self._execute_function_declaration(statement)
            return
        if isinstance(statement, ReturnStatement):
            self._execute_return(statement)
            return
        if isinstance(statement, BreakStatement):
            raise BreakSignal()
        if isinstance(statement, ContinueStatement):
            raise ContinueSignal()

        raise InterpreterError("Unknown statement.")

    def evaluate(self, expression: object) -> object:
        if isinstance(expression, NumericLiteral):
            return expression.value
        if isinstance(expression, StringLiteral):
            return expression.value
        if isinstance(expression, TemplateLiteral):
            return self._evaluate_template_literal(expression)
        if isinstance(expression, BooleanLiteral):
            return expression.value
        if isinstance(expression, NullLiteral):
            return JS_NULL
        if isinstance(expression, UndefinedLiteral):
            return JS_UNDEFINED
        if isinstance(expression, ArrayLiteral):
            return self._evaluate_array_literal(expression)
        if isinstance(expression, ObjectLiteral):
            return self._evaluate_object_literal(expression)
        if isinstance(expression, FunctionExpression):
            function = JSFunction(
                expression.parameters,
                expression.rest_parameter,
                expression.parameter_defaults,
                expression.body,
                self.environment,
                self,
                expression.name,
                dynamic_this=True,
            )
            if expression.name is not None:
                named_environment = Environment(self.environment)
                named_environment.define(expression.name, function, mutable=False)
                function.closure = named_environment
            return function
        if isinstance(expression, ArrowFunctionExpression):
            return JSFunction(
                expression.parameters,
                expression.rest_parameter,
                expression.parameter_defaults,
                expression.body,
                self.environment,
                self,
                dynamic_this=False,
            )
        if isinstance(expression, GroupingExpression):
            return self.evaluate(expression.expression)
        if isinstance(expression, UnaryExpression):
            return self._evaluate_unary(expression)
        if isinstance(expression, BinaryExpression):
            return self._evaluate_binary(expression)
        if isinstance(expression, LogicalExpression):
            return self._evaluate_logical(expression)
        if isinstance(expression, NullishCoalescingExpression):
            return self._evaluate_nullish_coalescing(expression)
        if isinstance(expression, ConditionalExpression):
            return self._evaluate_conditional(expression)
        if isinstance(expression, Identifier):
            return self._look_up_identifier(expression)
        if isinstance(expression, PropertyAccessExpression):
            return self._finish_optional_chain(self._evaluate_chain(expression))
        if isinstance(expression, ComputedMemberExpression):
            return self._finish_optional_chain(self._evaluate_chain(expression))
        if isinstance(expression, CallExpression):
            return self._finish_optional_chain(self._evaluate_chain(expression))
        if isinstance(expression, NewExpression):
            return self._evaluate_new(expression)
        if isinstance(expression, AssignmentExpression):
            return self._evaluate_assignment(expression)
        if isinstance(expression, PrefixUpdateExpression):
            return self._evaluate_prefix_update(expression)
        if isinstance(expression, PostfixUpdateExpression):
            return self._evaluate_postfix_update(expression)

        raise InterpreterError("Unknown expression.")

    def _evaluate_template_literal(self, expression: TemplateLiteral) -> str:
        text = ""

        for part in expression.parts:
            if isinstance(part, str):
                text += part
            else:
                text += to_string(self.evaluate(part))

        return text

    def _count_step(self) -> None:
        self.steps += 1
        if self.steps > self.step_limit:
            raise InterpreterError("Execution step limit exceeded.")

    def _execute_block(self, statement: BlockStatement, environment: Environment) -> None:
        previous = self.environment
        self.environment = environment

        try:
            self._execute_statements(statement.body)
        finally:
            self.environment = previous

    def _execute_statements(self, statements: list[object]) -> None:
        self._hoist_function_declarations(statements)
        self._hoist_var_declarations(statements)

        for child in statements:
            if isinstance(child, FunctionDeclaration):
                continue
            self.execute(child)

    def _hoist_function_declarations(self, statements: list[object]) -> None:
        for child in statements:
            if isinstance(child, FunctionDeclaration):
                self._define_function(child)

    def _hoist_var_declarations(self, statements: list[object]) -> None:
        for name in self._collect_var_names(statements):
            try:
                self.environment.define_var(
                    name,
                    JS_UNDEFINED,
                    assign_existing=False,
                )
            except TypeError as error:
                raise InterpreterError(str(error)) from error

    def _execute_variable_declaration(self, statement: VariableDeclaration) -> None:
        for declarator in statement.declarations:
            has_initializer = declarator.initializer is not None
            value = (
                self.evaluate(declarator.initializer)
                if has_initializer
                else JS_UNDEFINED
            )
            self._bind_pattern(
                declarator.pattern,
                value,
                statement.kind,
                assign_existing_var=has_initializer,
            )

    def _collect_var_names(self, statements: list[object]) -> list[str]:
        names = []
        for statement in statements:
            names.extend(self._collect_var_names_from_statement(statement))
        return names

    def _collect_var_names_from_statement(self, statement: object) -> list[str]:
        if isinstance(statement, VariableDeclaration):
            if statement.kind != "var":
                return []

            names = []
            for declarator in statement.declarations:
                names.extend(self._pattern_names(declarator.pattern))
            return names

        if isinstance(statement, FunctionDeclaration):
            return []

        if isinstance(statement, BlockStatement):
            return self._collect_var_names(statement.body)

        if isinstance(statement, IfStatement):
            names = self._collect_var_names_from_statement(statement.consequent)
            if statement.alternate is not None:
                names.extend(self._collect_var_names_from_statement(statement.alternate))
            return names

        if isinstance(statement, (WhileStatement, DoWhileStatement)):
            return self._collect_var_names_from_statement(statement.body)

        if isinstance(statement, ForStatement):
            names = []
            if isinstance(statement.initializer, VariableDeclaration):
                names.extend(self._collect_var_names_from_statement(statement.initializer))
            names.extend(self._collect_var_names_from_statement(statement.body))
            return names

        if isinstance(statement, (ForOfStatement, ForInStatement)):
            names = []
            if statement.kind == "var":
                names.extend(self._pattern_names(statement.target))
            names.extend(self._collect_var_names_from_statement(statement.body))
            return names

        if isinstance(statement, SwitchStatement):
            names = []
            for case in statement.cases:
                names.extend(self._collect_var_names(case.consequent))
            return names

        return []

    def _pattern_names(self, pattern: object) -> list[str]:
        if isinstance(pattern, BindingIdentifier):
            return [pattern.name]

        if isinstance(pattern, ArrayBindingPattern):
            names = []
            for element in pattern.elements:
                if element is not None:
                    names.extend(self._pattern_names(element.pattern))
            if pattern.rest is not None:
                names.extend(self._pattern_names(pattern.rest))
            return names

        if isinstance(pattern, ObjectBindingPattern):
            names = []
            for property_node in pattern.properties:
                names.extend(self._pattern_names(property_node.pattern))
            if pattern.rest is not None:
                names.append(pattern.rest.name)
            return names

        return []

    def _bind_pattern(
        self,
        pattern: object,
        value: object,
        kind: str,
        assign_existing_var: bool,
    ) -> None:
        if isinstance(pattern, BindingIdentifier):
            self._declare_binding(
                pattern.name,
                value,
                kind,
                assign_existing_var,
            )
            return

        if isinstance(pattern, ArrayBindingPattern):
            self._bind_array_pattern(
                pattern,
                value,
                kind,
                assign_existing_var,
            )
            return

        if isinstance(pattern, ObjectBindingPattern):
            self._bind_object_pattern(
                pattern,
                value,
                kind,
                assign_existing_var,
            )
            return

        raise InterpreterError("Unknown binding pattern.")

    def _declare_binding(
        self,
        name: str,
        value: object,
        kind: str,
        assign_existing_var: bool,
    ) -> None:
        try:
            if kind == "var":
                self.environment.define_var(
                    name,
                    value,
                    assign_existing=assign_existing_var,
                )
            else:
                self.environment.define(name, value, mutable=kind == "let")
        except (NameError, TypeError) as error:
            raise InterpreterError(str(error)) from error

    def _bind_array_pattern(
        self,
        pattern: ArrayBindingPattern,
        value: object,
        kind: str,
        assign_existing_var: bool,
    ) -> None:
        if not isinstance(value, JSArray):
            raise InterpreterError("Array destructuring source must be an array.")

        index = 0
        for element in pattern.elements:
            if element is None:
                index += 1
                continue

            item = value.items[index] if index < len(value.items) else JS_UNDEFINED
            if item is JS_UNDEFINED and element.default is not None:
                item = self.evaluate(element.default)

            self._bind_pattern(
                element.pattern,
                item,
                kind,
                assign_existing_var,
            )
            index += 1

        if pattern.rest is not None:
            rest_items = list(value.items[index:])
            self._bind_pattern(
                pattern.rest,
                JSArray(rest_items),
                kind,
                assign_existing_var,
            )

    def _bind_object_pattern(
        self,
        pattern: ObjectBindingPattern,
        value: object,
        kind: str,
        assign_existing_var: bool,
    ) -> None:
        if not isinstance(value, JSObject):
            raise InterpreterError("Object destructuring source must be an object.")

        used_keys = set()
        for property_node in pattern.properties:
            used_keys.add(property_node.key)
            item = value.properties.get(property_node.key, JS_UNDEFINED)
            if item is JS_UNDEFINED and property_node.default is not None:
                item = self.evaluate(property_node.default)

            self._bind_pattern(
                property_node.pattern,
                item,
                kind,
                assign_existing_var,
            )

        if pattern.rest is not None:
            remaining = {
                key: property_value
                for key, property_value in value.properties.items()
                if key not in used_keys
            }
            self._declare_binding(
                pattern.rest.name,
                JSObject(remaining),
                kind,
                assign_existing_var,
            )

    def _execute_if(self, statement: IfStatement) -> None:
        if to_boolean(self.evaluate(statement.test)):
            self.execute(statement.consequent)
        elif statement.alternate is not None:
            self.execute(statement.alternate)

    def _execute_function_declaration(self, statement: FunctionDeclaration) -> None:
        self._define_function(statement)

    def _define_function(self, statement: FunctionDeclaration) -> None:
        function = JSFunction(
            statement.parameters,
            statement.rest_parameter,
            statement.parameter_defaults,
            statement.body,
            self.environment,
            self,
            statement.name,
            dynamic_this=True,
        )

        try:
            if self.environment.has_local(statement.name):
                return
            self.environment.define(statement.name, function)
        except NameError as error:
            raise InterpreterError(str(error)) from error

    def _execute_return(self, statement: ReturnStatement) -> None:
        value = JS_UNDEFINED

        if statement.argument is not None:
            value = self.evaluate(statement.argument)

        raise ReturnSignal(value)

    def _execute_while(self, statement: WhileStatement) -> None:
        while to_boolean(self.evaluate(statement.test)):
            try:
                self.execute(statement.body)
            except ContinueSignal:
                continue
            except BreakSignal:
                break

    def _execute_do_while(self, statement: DoWhileStatement) -> None:
        while True:
            try:
                self.execute(statement.body)
            except ContinueSignal:
                pass
            except BreakSignal:
                break

            if not to_boolean(self.evaluate(statement.test)):
                break

    def _execute_for(self, statement: ForStatement) -> None:
        loop_environment = Environment(self.environment)
        previous = self.environment
        self.environment = loop_environment

        try:
            if isinstance(statement.initializer, VariableDeclaration):
                self._execute_variable_declaration(statement.initializer)
            elif statement.initializer is not None:
                self.evaluate(statement.initializer)

            if (
                isinstance(statement.initializer, VariableDeclaration)
                and statement.initializer.kind == "let"
            ):
                self._execute_for_with_per_iteration_let(statement, loop_environment)
                return

            while True:
                if statement.condition is not None:
                    if not to_boolean(self.evaluate(statement.condition)):
                        break

                try:
                    self.execute(statement.body)
                except ContinueSignal:
                    pass
                except BreakSignal:
                    break

                if statement.update is not None:
                    self.evaluate(statement.update)
        finally:
            self.environment = previous

    def _execute_for_with_per_iteration_let(
        self, statement: ForStatement, loop_environment: Environment
    ) -> None:
        while True:
            self.environment = loop_environment
            if statement.condition is not None:
                if not to_boolean(self.evaluate(statement.condition)):
                    break

            iteration_environment = self._copy_environment(loop_environment)
            self.environment = iteration_environment

            try:
                self.execute(statement.body)
            except ContinueSignal:
                pass
            except BreakSignal:
                break

            loop_environment = self._copy_environment(iteration_environment)

            if statement.update is not None:
                self.environment = loop_environment
                self.evaluate(statement.update)

    def _copy_environment(self, environment: Environment) -> Environment:
        copied = Environment(environment.parent, is_var_scope=environment.is_var_scope)

        for name, binding in environment.values.items():
            copied.define(name, binding.value, mutable=binding.mutable)

        return copied

    def _execute_for_of(self, statement: ForOfStatement) -> None:
        iterable = self.evaluate(statement.iterable)

        if isinstance(iterable, JSArray):
            values = list(iterable.items)
        elif isinstance(iterable, str):
            values = list(iterable)
        else:
            raise InterpreterError("for...of value must be an array or string.")

        loop_environment = Environment(self.environment)
        previous = self.environment
        self.environment = loop_environment

        try:
            for value in values:
                if statement.kind == "var":
                    self._bind_pattern(
                        statement.target,
                        value,
                        "var",
                        assign_existing_var=True,
                    )
                    try:
                        self.execute(statement.body)
                    except ContinueSignal:
                        continue
                    except BreakSignal:
                        break
                    continue

                iteration_environment = Environment(loop_environment)
                try:
                    self.environment = iteration_environment
                    self._bind_pattern(
                        statement.target,
                        value,
                        statement.kind,
                        assign_existing_var=True,
                    )
                except NameError as error:
                    raise InterpreterError(str(error)) from error

                try:
                    self.execute(statement.body)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
                finally:
                    self.environment = loop_environment
        finally:
            self.environment = previous

    def _execute_for_in(self, statement: ForInStatement) -> None:
        iterable = self.evaluate(statement.iterable)

        if isinstance(iterable, JSObject):
            keys = list(iterable.properties.keys())
        elif isinstance(iterable, JSArray):
            keys = [str(index) for index in range(len(iterable.items))]
        elif isinstance(iterable, str):
            keys = [str(index) for index in range(len(iterable))]
        else:
            raise InterpreterError(
                "for...in value must be an object, array, or string."
            )

        loop_environment = Environment(self.environment)
        previous = self.environment
        self.environment = loop_environment

        try:
            for key in keys:
                if statement.kind == "var":
                    self._bind_pattern(
                        statement.target,
                        key,
                        "var",
                        assign_existing_var=True,
                    )
                    try:
                        self.execute(statement.body)
                    except ContinueSignal:
                        continue
                    except BreakSignal:
                        break
                    continue

                iteration_environment = Environment(loop_environment)
                try:
                    self.environment = iteration_environment
                    self._bind_pattern(
                        statement.target,
                        key,
                        statement.kind,
                        assign_existing_var=True,
                    )
                except NameError as error:
                    raise InterpreterError(str(error)) from error

                try:
                    self.execute(statement.body)
                except ContinueSignal:
                    continue
                except BreakSignal:
                    break
                finally:
                    self.environment = loop_environment
        finally:
            self.environment = previous

    def _execute_switch(self, statement: SwitchStatement) -> None:
        discriminant = self.evaluate(statement.discriminant)
        previous = self.environment
        self.environment = Environment(previous)
        try:
            default_index = None
            start_index = None

            for index, case in enumerate(statement.cases):
                if case.test is None:
                    default_index = index
                    continue

                if strict_equal(discriminant, self.evaluate(case.test)):
                    start_index = index
                    break

            if start_index is None:
                start_index = default_index
            if start_index is None:
                return

            try:
                for case in statement.cases[start_index:]:
                    self._execute_statements(case.consequent)
            except BreakSignal:
                return
        finally:
            self.environment = previous

    def _evaluate_unary(self, expression: UnaryExpression) -> object:
        if expression.operator == "typeof":
            return self._evaluate_typeof(expression.argument)

        value = self.evaluate(expression.argument)

        if expression.operator == "!":
            return not to_boolean(value)
        if expression.operator == "-":
            return -to_number(value)
        if expression.operator == "+":
            return to_number(value)

        raise InterpreterError(f"Unsupported unary operator {expression.operator}.")

    def _evaluate_typeof(self, argument: object) -> str:
        if isinstance(argument, Identifier):
            try:
                value = self.environment.get(argument.name)
            except NameError:
                return "undefined"
        else:
            value = self.evaluate(argument)

        if value is JS_UNDEFINED:
            return "undefined"
        if value is JS_NULL:
            return "object"
        if isinstance(value, bool):
            return "boolean"
        if is_number(value):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, JSCallable):
            return "function"
        return "object"

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
            return self._power(left, right)
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

    def _power(self, left: object, right: object) -> object:
        return js_power(left, right)

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

    def _evaluate_nullish_coalescing(
        self,
        expression: NullishCoalescingExpression,
    ) -> object:
        left = self.evaluate(expression.left)

        if self._is_nullish(left):
            return self.evaluate(expression.right)
        return left

    def _evaluate_conditional(self, expression: ConditionalExpression) -> object:
        if to_boolean(self.evaluate(expression.test)):
            return self.evaluate(expression.consequent)
        return self.evaluate(expression.alternate)

    def _evaluate_assignment(self, expression: AssignmentExpression) -> object:
        try:
            reference = self._resolve_reference(expression.target)

            if expression.operator == "=":
                right = self.evaluate(expression.value)
                return reference.write(right)

            left = reference.read()
            right = self.evaluate(expression.value)

            if expression.operator == "+=":
                value = js_add(left, right)
            elif expression.operator == "-=":
                value = to_number(left) - to_number(right)
            elif expression.operator == "*=":
                value = to_number(left) * to_number(right)
            elif expression.operator == "/=":
                value = js_divide(left, right)
            elif expression.operator == "%=":
                value = js_remainder(left, right)
            elif expression.operator == "**=":
                value = self._power(left, right)
            else:
                raise InterpreterError(
                    f"Unsupported assignment operator {expression.operator}."
                )

            return reference.write(value)
        except (NameError, TypeError, ValueError) as error:
            raise InterpreterError(str(error)) from error

    def _resolve_reference(self, target: object) -> ResolvedReference:
        if isinstance(target, Identifier):
            environment = self.environment.resolve(target.name)

            def read() -> object:
                return environment.values[target.name].value

            def write(value: object) -> object:
                binding = environment.values[target.name]
                if not binding.mutable:
                    raise TypeError(f"Assignment to constant variable {target.name}.")
                binding.value = value
                return value

            return ResolvedReference(read, write)

        if isinstance(target, PropertyAccessExpression):
            if target.optional:
                raise InterpreterError(
                    "Optional chaining cannot be used as an assignment target."
                )
            container = self.evaluate(target.object)
            return self._property_reference(container, target.property.name)

        if isinstance(target, ComputedMemberExpression):
            if target.optional:
                raise InterpreterError(
                    "Optional chaining cannot be used as an assignment target."
                )
            container = self.evaluate(target.object)
            key = self.evaluate(target.property)
            return self._computed_reference(container, key)

        raise InterpreterError("Invalid assignment target.")

    def _property_reference(
        self, container: object, property_name: str
    ) -> ResolvedReference:
        def read() -> object:
            return self._get_property_value(container, property_name)

        def write(value: object) -> object:
            if not isinstance(container, JSObject):
                raise InterpreterError(
                    "Only object property assignment is supported yet."
                )
            container.properties[property_name] = value
            return value

        return ResolvedReference(read, write)

    def _computed_reference(self, container: object, key: object) -> ResolvedReference:
        property_name = self._property_key(key)

        if isinstance(container, JSObject):
            def read_object() -> object:
                return container.properties.get(property_name, JS_UNDEFINED)

            def write_object(value: object) -> object:
                container.properties[property_name] = value
                return value

            return ResolvedReference(read_object, write_object)

        if isinstance(container, JSArray):
            index = self._canonical_array_index(property_name)

            def read_array() -> object:
                return self._get_computed_member_value(container, key)

            def write_array(value: object) -> object:
                if self._is_negative_numeric_key(key, property_name):
                    raise InterpreterError("Array index must be non-negative.")
                if index is None:
                    raise InterpreterError("Array index must be a number.")
                while len(container.items) <= index:
                    container.items.append(JS_UNDEFINED)
                container.items[index] = value
                return value

            return ResolvedReference(read_array, write_array)

        def read_other() -> object:
            return self._get_computed_member_value(container, key)

        def write_other(value: object) -> object:
            raise InterpreterError(
                "Only array index and object property assignment are supported yet."
            )

        return ResolvedReference(read_other, write_other)

    def _read_assignment_target(self, target: object) -> object:
        if isinstance(target, Identifier):
            return self.environment.get(target.name)
        if isinstance(target, ComputedMemberExpression):
            if target.optional:
                raise InterpreterError(
                    "Optional chaining cannot be used as an assignment target."
                )
            return self._get_computed_member(target)
        if isinstance(target, PropertyAccessExpression):
            if target.optional:
                raise InterpreterError(
                    "Optional chaining cannot be used as an assignment target."
                )
            return self._get_property(target)
        raise InterpreterError("Invalid assignment target.")

    def _assign_target(self, target: object, value: object) -> object:
        if isinstance(target, Identifier):
            return self.environment.assign(target.name, value)
        if isinstance(target, ComputedMemberExpression):
            if target.optional:
                raise InterpreterError(
                    "Optional chaining cannot be used as an assignment target."
                )
            return self._assign_computed_member(target, value)
        if isinstance(target, PropertyAccessExpression):
            if target.optional:
                raise InterpreterError(
                    "Optional chaining cannot be used as an assignment target."
                )
            return self._assign_property(target, value)
        raise InterpreterError("Invalid assignment target.")

    def _evaluate_prefix_update(self, expression: PrefixUpdateExpression) -> object:
        _, new_value = self._apply_update(
            expression.argument, expression.operator
        )
        return new_value

    def _evaluate_postfix_update(self, expression: PostfixUpdateExpression) -> object:
        old_value, _ = self._apply_update(
            expression.argument, expression.operator
        )
        return old_value

    def _apply_update(self, target: object, operator: str) -> tuple[object, object]:
        if not isinstance(
            target, (Identifier, PropertyAccessExpression, ComputedMemberExpression)
        ):
            raise InterpreterError("Invalid update target.")
        if isinstance(
            target,
            (PropertyAccessExpression, ComputedMemberExpression),
        ) and target.optional:
            raise InterpreterError(
                "Optional chaining cannot be used as an assignment target."
            )

        try:
            reference = self._resolve_reference(target)
            old_value = reference.read()
            amount = 1 if operator == "++" else -1
            new_value = to_number(old_value) + amount
            assigned_value = reference.write(new_value)
            return old_value, assigned_value

        except (NameError, TypeError, ValueError) as error:
            raise InterpreterError(str(error)) from error

    def _look_up_identifier(self, expression: Identifier) -> object:
        try:
            return self.environment.get(expression.name)
        except NameError as error:
            raise InterpreterError(str(error)) from error

    def _evaluate_array_literal(self, expression: ArrayLiteral) -> JSArray:
        items = []

        for element in expression.elements:
            if isinstance(element, SpreadElement):
                value = self.evaluate(element.expression)
                if not isinstance(value, JSArray):
                    raise InterpreterError("Spread value is not iterable.")
                items.extend(value.items)
            else:
                items.append(self.evaluate(element))

        return JSArray(items)

    def _evaluate_object_literal(self, expression: ObjectLiteral) -> JSObject:
        properties = {}

        for property_node in expression.properties:
            if isinstance(property_node, SpreadElement):
                value = self.evaluate(property_node.expression)
                if not isinstance(value, JSObject):
                    raise InterpreterError("Object spread value must be an object.")
                properties.update(value.properties)
            else:
                properties[property_node.key] = self.evaluate(property_node.value)

        return JSObject(properties)

    def _get_property(self, expression: PropertyAccessExpression) -> object:
        container = self.evaluate(expression.object)

        if expression.optional and self._is_nullish(container):
            return JS_UNDEFINED

        return self._get_property_value(container, expression.property.name)

    def _get_property_value(self, container: object, property_name: str) -> object:
        if isinstance(container, str):
            return self._get_string_property(container, property_name)
        if isinstance(container, JSArray):
            return self._get_array_property(container, property_name)
        if isinstance(container, JSDate):
            return self._get_date_property(container, property_name)
        if isinstance(container, JSObject):
            return container.properties.get(property_name, JS_UNDEFINED)
        if isinstance(container, dict) and property_name in container:
            return container[property_name]

        raise InterpreterError(f"Property {property_name} is not defined.")

    def _assign_property(
        self, expression: PropertyAccessExpression, value: object
    ) -> object:
        container = self.evaluate(expression.object)

        if not isinstance(container, JSObject):
            raise InterpreterError("Only object property assignment is supported yet.")

        container.properties[expression.property.name] = value
        return value

    def _get_string_property(self, text: str, property_name: str) -> object:
        if property_name == "length":
            return len(text)

        methods = {
            "split": lambda args: self._string_split(text, args),
            "replace": lambda args: self._string_replace(text, args, replace_all=False),
            "replaceAll": lambda args: self._string_replace(
                text, args, replace_all=True
            ),
            "substring": lambda args: self._string_substring(text, args),
            "slice": lambda args: self._string_slice(text, args),
            "charAt": lambda args: self._string_char_at(text, args),
            "charCodeAt": lambda args: self._string_char_code_at(text, args),
            "repeat": lambda args: self._string_repeat(text, args),
            "padStart": lambda args: self._string_pad(text, args, at_start=True),
            "padEnd": lambda args: self._string_pad(text, args, at_start=False),
            "trim": lambda args: text.strip(),
            "trimStart": lambda args: text.lstrip(),
            "trimEnd": lambda args: text.rstrip(),
            "toUpperCase": lambda args: text.upper(),
            "toLowerCase": lambda args: text.lower(),
            "includes": lambda args: self._string_includes(text, args),
            "startsWith": lambda args: self._string_starts_with(text, args),
            "endsWith": lambda args: self._string_ends_with(text, args),
            "indexOf": lambda args: self._string_index_of(text, args),
            "at": lambda args: self._string_at(text, args),
            "concat": lambda args: self._string_concat(text, args),
        }

        if property_name in methods:
            return NativeMethod(methods[property_name])

        raise InterpreterError(f"String method {property_name} is not defined.")

    def _get_array_property(self, array: JSArray, property_name: str) -> object:
        if property_name == "length":
            return len(array.items)
        if property_name == "reverse":
            return NativeMethod(lambda args: self._array_reverse(array))
        if property_name == "join":
            return NativeMethod(lambda args: self._array_join(array, args))
        if property_name == "push":
            return NativeMethod(lambda args: self._array_push(array, args))
        if property_name == "pop":
            return NativeMethod(lambda args: self._array_pop(array))
        if property_name == "shift":
            return NativeMethod(lambda args: self._array_shift(array))
        if property_name == "unshift":
            return NativeMethod(lambda args: self._array_unshift(array, args))
        if property_name == "slice":
            return NativeMethod(lambda args: self._array_slice(array, args))
        if property_name == "splice":
            return NativeMethod(lambda args: self._array_splice(array, args))
        if property_name == "concat":
            return NativeMethod(lambda args: self._array_concat(array, args))
        if property_name == "includes":
            return NativeMethod(lambda args: self._array_includes(array, args))
        if property_name == "indexOf":
            return NativeMethod(lambda args: self._array_index_of(array, args))
        if property_name == "sort":
            return NativeMethod(lambda args: self._array_sort(array))
        if property_name == "map":
            return NativeMethod(lambda args: self._array_map(array, args))
        if property_name == "filter":
            return NativeMethod(lambda args: self._array_filter(array, args))
        if property_name == "reduce":
            return NativeMethod(lambda args: self._array_reduce(array, args))
        if property_name == "find":
            return NativeMethod(lambda args: self._array_find(array, args))
        if property_name == "some":
            return NativeMethod(lambda args: self._array_some(array, args))
        if property_name == "every":
            return NativeMethod(lambda args: self._array_every(array, args))
        if property_name == "forEach":
            return NativeMethod(lambda args: self._array_for_each(array, args))

        raise InterpreterError(f"Array method {property_name} is not defined.")

    def _array_property_names(self) -> set[str]:
        return {
            "length",
            "reverse",
            "join",
            "push",
            "pop",
            "shift",
            "unshift",
            "slice",
            "splice",
            "concat",
            "includes",
            "indexOf",
            "sort",
            "map",
            "filter",
            "reduce",
            "find",
            "some",
            "every",
            "forEach",
        }

    def _string_property_names(self) -> set[str]:
        return {
            "length",
            "split",
            "replace",
            "replaceAll",
            "substring",
            "slice",
            "charAt",
            "charCodeAt",
            "repeat",
            "padStart",
            "padEnd",
            "trim",
            "trimStart",
            "trimEnd",
            "toUpperCase",
            "toLowerCase",
            "includes",
            "startsWith",
            "endsWith",
            "indexOf",
            "at",
            "concat",
        }

    def _get_date_property(self, date: JSDate, property_name: str) -> object:
        methods = {
            "getTime": lambda args: date.timestamp_ms,
            "getFullYear": lambda args: date_part(date, "year"),
            "getMonth": lambda args: date_part(date, "month"),
            "getDate": lambda args: date_part(date, "date"),
            "getDay": lambda args: date_part(date, "day"),
            "getHours": lambda args: date_part(date, "hours"),
            "getMinutes": lambda args: date_part(date, "minutes"),
            "getSeconds": lambda args: date_part(date, "seconds"),
            "toISOString": lambda args: date_to_iso_string(date),
        }

        if property_name in methods:
            return NativeMethod(methods[property_name])

        raise InterpreterError(f"Date method {property_name} is not defined.")

    def _get_computed_member(self, expression: ComputedMemberExpression) -> object:
        container = self.evaluate(expression.object)

        if expression.optional and self._is_nullish(container):
            return JS_UNDEFINED

        key = self.evaluate(expression.property)
        return self._get_computed_member_value(container, key)

    def _get_computed_member_value(self, container: object, key: object) -> object:
        property_name = self._property_key(key)

        if isinstance(container, JSArray):
            index = self._canonical_array_index(property_name)
            if index is None:
                if property_name in self._array_property_names():
                    return self._get_array_property(container, property_name)
                return JS_UNDEFINED
            if 0 <= index < len(container.items):
                return container.items[index]
            return JS_UNDEFINED

        if isinstance(container, str):
            index = self._canonical_array_index(property_name)
            if index is None:
                if property_name in self._string_property_names():
                    return self._get_string_property(container, property_name)
                return JS_UNDEFINED
            if 0 <= index < len(container):
                return container[index]
            return JS_UNDEFINED
        if isinstance(container, JSObject):
            return container.properties.get(property_name, JS_UNDEFINED)

        raise InterpreterError("Computed member access is not supported for this value.")

    def _assign_computed_member(
        self, expression: ComputedMemberExpression, value: object
    ) -> object:
        container = self.evaluate(expression.object)
        key = self.evaluate(expression.property)

        if isinstance(container, JSObject):
            container.properties[self._property_key(key)] = value
            return value

        if not isinstance(container, JSArray):
            raise InterpreterError(
                "Only array index and object property assignment are supported yet."
            )

        index = self._array_index(key)
        if index is None:
            raise InterpreterError("Array index must be a number.")
        if index < 0:
            raise InterpreterError("Array index must be non-negative.")

        while len(container.items) <= index:
            container.items.append(JS_UNDEFINED)

        container.items[index] = value
        return value

    def _finish_optional_chain(self, value: object) -> object:
        if value is OPTIONAL_CHAIN_SHORT_CIRCUIT:
            return JS_UNDEFINED
        return value

    def _evaluate_chain(self, expression: object) -> object:
        if isinstance(expression, PropertyAccessExpression):
            container = self._evaluate_chain_operand(expression.object)
            if container is OPTIONAL_CHAIN_SHORT_CIRCUIT:
                return OPTIONAL_CHAIN_SHORT_CIRCUIT
            if expression.optional and self._is_nullish(container):
                return OPTIONAL_CHAIN_SHORT_CIRCUIT
            return self._get_property_value(container, expression.property.name)

        if isinstance(expression, ComputedMemberExpression):
            container = self._evaluate_chain_operand(expression.object)
            if container is OPTIONAL_CHAIN_SHORT_CIRCUIT:
                return OPTIONAL_CHAIN_SHORT_CIRCUIT
            if expression.optional and self._is_nullish(container):
                return OPTIONAL_CHAIN_SHORT_CIRCUIT
            key = self.evaluate(expression.property)
            return self._get_computed_member_value(container, key)

        if isinstance(expression, CallExpression):
            return self._evaluate_call_chain(expression)

        return self.evaluate(expression)

    def _evaluate_chain_operand(self, expression: object) -> object:
        if isinstance(
            expression,
            (PropertyAccessExpression, ComputedMemberExpression, CallExpression),
        ):
            return self._evaluate_chain(expression)
        return self.evaluate(expression)

    def _evaluate_call(self, expression: CallExpression) -> object:
        return self._finish_optional_chain(self._evaluate_call_chain(expression))

    def _evaluate_call_chain(self, expression: CallExpression) -> object:
        callee, receiver = self._evaluate_call_target(expression.callee)

        if callee is OPTIONAL_CHAIN_SHORT_CIRCUIT:
            return OPTIONAL_CHAIN_SHORT_CIRCUIT
        if expression.optional and self._is_nullish(callee):
            return OPTIONAL_CHAIN_SHORT_CIRCUIT

        arguments = self._evaluate_call_arguments(expression.arguments)

        return self._call_callable(callee, arguments, receiver)

    def _evaluate_call_target(
        self,
        callee: object,
    ) -> tuple[object, object]:
        if isinstance(callee, PropertyAccessExpression):
            receiver = self._evaluate_chain_operand(callee.object)
            if receiver is OPTIONAL_CHAIN_SHORT_CIRCUIT:
                return OPTIONAL_CHAIN_SHORT_CIRCUIT, JS_UNDEFINED
            if callee.optional and self._is_nullish(receiver):
                return OPTIONAL_CHAIN_SHORT_CIRCUIT, JS_UNDEFINED
            return (
                self._get_property_value(receiver, callee.property.name),
                receiver,
            )

        if isinstance(callee, ComputedMemberExpression):
            receiver = self._evaluate_chain_operand(callee.object)
            if receiver is OPTIONAL_CHAIN_SHORT_CIRCUIT:
                return OPTIONAL_CHAIN_SHORT_CIRCUIT, JS_UNDEFINED
            if callee.optional and self._is_nullish(receiver):
                return OPTIONAL_CHAIN_SHORT_CIRCUIT, JS_UNDEFINED
            key = self.evaluate(callee.property)
            return (
                self._get_computed_member_value(receiver, key),
                receiver,
            )

        value = self._evaluate_chain_operand(callee)
        if value is OPTIONAL_CHAIN_SHORT_CIRCUIT:
            return OPTIONAL_CHAIN_SHORT_CIRCUIT, JS_UNDEFINED
        return value, JS_UNDEFINED

    def _call_callable(
        self,
        callee: object,
        arguments: list[object],
        receiver: object,
    ) -> object:
        if isinstance(callee, JSFunction):
            try:
                return callee.call(arguments, this_value=receiver)
            except RecursionError as error:
                raise InterpreterError("Maximum call stack size exceeded.") from error

        if isinstance(callee, JSCallable):
            try:
                return callee.call(arguments)
            except BuiltInError as error:
                raise InterpreterError(str(error)) from error
            except RecursionError as error:
                raise InterpreterError("Maximum call stack size exceeded.") from error

        raise InterpreterError("Value is not callable.")

    def _evaluate_new(self, expression: NewExpression) -> object:
        arguments = self._evaluate_call_arguments(expression.arguments)

        if isinstance(expression.callee, Identifier) and expression.callee.name == "Date":
            try:
                return construct_date(arguments)
            except ValueError as error:
                raise InterpreterError(str(error)) from error

        raise InterpreterError("Only Date construction is supported with new.")

    def _evaluate_call_arguments(self, argument_nodes: list[object]) -> list[object]:
        arguments = []

        for argument_node in argument_nodes:
            if isinstance(argument_node, SpreadElement):
                value = self.evaluate(argument_node.expression)
                if not isinstance(value, JSArray):
                    raise InterpreterError("Spread argument must be an array.")
                arguments.extend(value.items)
            else:
                arguments.append(self.evaluate(argument_node))

        return arguments

    def _string_split(self, text: str, arguments: list[object]) -> JSArray:
        if not arguments or arguments[0] is JS_UNDEFINED:
            return JSArray([text])

        separator = to_string(arguments[0])
        if separator == "":
            return JSArray(list(text))
        return JSArray(text.split(separator))

    def _string_replace(
        self, text: str, arguments: list[object], replace_all: bool
    ) -> str:
        search = to_string(arguments[0]) if arguments else "undefined"
        replacement = to_string(arguments[1]) if len(arguments) > 1 else "undefined"

        if replace_all:
            return text.replace(search, replacement)
        return text.replace(search, replacement, 1)

    def _string_substring(self, text: str, arguments: list[object]) -> str:
        start = self._substring_index(arguments[0] if arguments else JS_UNDEFINED)
        end = (
            len(text)
            if len(arguments) < 2 or arguments[1] is JS_UNDEFINED
            else self._substring_index(arguments[1])
        )
        start = min(start, len(text))
        end = min(end, len(text))

        if start > end:
            start, end = end, start

        return text[start:end]

    def _string_slice(self, text: str, arguments: list[object]) -> str:
        start = self._slice_index(arguments[0] if arguments else JS_UNDEFINED, len(text))
        end = (
            len(text)
            if len(arguments) < 2 or arguments[1] is JS_UNDEFINED
            else self._slice_index(arguments[1], len(text))
        )
        return text[start:end]

    def _string_includes(self, text: str, arguments: list[object]) -> bool:
        search = to_string(arguments[0]) if arguments else "undefined"
        position = self._substring_index(arguments[1]) if len(arguments) > 1 else 0
        return search in text[position:]

    def _string_starts_with(self, text: str, arguments: list[object]) -> bool:
        search = to_string(arguments[0]) if arguments else "undefined"
        position = self._substring_index(arguments[1]) if len(arguments) > 1 else 0
        return text.startswith(search, position)

    def _string_ends_with(self, text: str, arguments: list[object]) -> bool:
        search = to_string(arguments[0]) if arguments else "undefined"
        end = (
            len(text)
            if len(arguments) < 2 or arguments[1] is JS_UNDEFINED
            else self._substring_index(arguments[1])
        )
        return text[:end].endswith(search)

    def _string_index_of(self, text: str, arguments: list[object]) -> int:
        search = to_string(arguments[0]) if arguments else "undefined"
        position = self._substring_index(arguments[1]) if len(arguments) > 1 else 0
        return text.find(search, position)

    def _string_char_at(self, text: str, arguments: list[object]) -> str:
        index = self._string_integer_index(arguments[0] if arguments else 0)
        if not isinstance(index, int) or index < 0 or index >= len(text):
            return ""
        return text[index]

    def _string_char_code_at(self, text: str, arguments: list[object]) -> object:
        index = self._string_integer_index(arguments[0] if arguments else 0)
        if not isinstance(index, int) or index < 0 or index >= len(text):
            return math.nan
        return ord(text[index])

    def _string_repeat(self, text: str, arguments: list[object]) -> str:
        if not arguments or arguments[0] is JS_UNDEFINED:
            return ""

        count = to_number(arguments[0])
        if is_nan(count) or math.isinf(count) or count < 0:
            raise ValueError("String.repeat count must be a finite non-negative number.")

        return text * int(count)

    def _string_pad(self, text: str, arguments: list[object], at_start: bool) -> str:
        target_length = self._string_length_argument(
            arguments[0] if arguments else JS_UNDEFINED,
            "String.padStart target length" if at_start else "String.padEnd target length",
        )
        if target_length <= len(text):
            return text

        pad_text = (
            " "
            if len(arguments) < 2 or arguments[1] is JS_UNDEFINED
            else to_string(arguments[1])
        )
        if pad_text == "":
            return text

        needed = target_length - len(text)
        repeated = (pad_text * ((needed // len(pad_text)) + 1))[:needed]
        return repeated + text if at_start else text + repeated

    def _string_at(self, text: str, arguments: list[object]) -> object:
        index = self._string_integer_index(arguments[0] if arguments else 0)
        if not isinstance(index, int):
            return JS_UNDEFINED
        if index < 0:
            index = len(text) + index
        if index < 0 or index >= len(text):
            return JS_UNDEFINED
        return text[index]

    def _string_concat(self, text: str, arguments: list[object]) -> str:
        return text + "".join(to_string(argument) for argument in arguments)

    def _array_reverse(self, array: JSArray) -> JSArray:
        array.items.reverse()
        return array

    def _array_join(self, array: JSArray, arguments: list[object]) -> str:
        if not arguments or arguments[0] is JS_UNDEFINED:
            separator = ","
        else:
            separator = to_string(arguments[0])

        return separator.join(self._join_item_to_string(item) for item in array.items)

    def _array_push(self, array: JSArray, arguments: list[object]) -> int:
        array.items.extend(arguments)
        return len(array.items)

    def _array_pop(self, array: JSArray) -> object:
        if not array.items:
            return JS_UNDEFINED
        return array.items.pop()

    def _array_shift(self, array: JSArray) -> object:
        if not array.items:
            return JS_UNDEFINED
        return array.items.pop(0)

    def _array_unshift(self, array: JSArray, arguments: list[object]) -> int:
        array.items[0:0] = arguments
        return len(array.items)

    def _array_slice(self, array: JSArray, arguments: list[object]) -> JSArray:
        start = self._slice_index(arguments[0] if arguments else JS_UNDEFINED, len(array.items))
        end = (
            len(array.items)
            if len(arguments) < 2 or arguments[1] is JS_UNDEFINED
            else self._slice_index(arguments[1], len(array.items))
        )
        return JSArray(array.items[start:end])

    def _array_splice(self, array: JSArray, arguments: list[object]) -> JSArray:
        length = len(array.items)
        start = self._slice_index(arguments[0] if arguments else JS_UNDEFINED, length)

        if len(arguments) < 2:
            delete_count = length - start
        else:
            delete_count_number = to_number(arguments[1])
            if is_nan(delete_count_number):
                delete_count = 0
            elif math.isinf(delete_count_number):
                delete_count = length - start
            else:
                delete_count = max(int(delete_count_number), 0)

        delete_count = min(delete_count, length - start)
        removed = array.items[start : start + delete_count]
        array.items[start : start + delete_count] = arguments[2:]
        return JSArray(removed)

    def _array_concat(self, array: JSArray, arguments: list[object]) -> JSArray:
        items = list(array.items)

        for argument in arguments:
            if isinstance(argument, JSArray):
                items.extend(argument.items)
            else:
                items.append(argument)

        return JSArray(items)

    def _array_includes(self, array: JSArray, arguments: list[object]) -> bool:
        if not arguments:
            search = JS_UNDEFINED
            start = 0
        else:
            search = arguments[0]
            start = (
                self._array_search_start(arguments[1], len(array.items))
                if len(arguments) > 1
                else 0
            )

        for item in array.items[start:]:
            if strict_equal(item, search):
                return True
        return False

    def _array_index_of(self, array: JSArray, arguments: list[object]) -> int:
        if not arguments:
            search = JS_UNDEFINED
            start = 0
        else:
            search = arguments[0]
            start = (
                self._array_search_start(arguments[1], len(array.items))
                if len(arguments) > 1
                else 0
            )

        for index in range(start, len(array.items)):
            if strict_equal(array.items[index], search):
                return index
        return -1

    def _array_sort(self, array: JSArray) -> JSArray:
        array.items.sort(key=to_string)
        return array

    def _array_map(self, array: JSArray, arguments: list[object]) -> JSArray:
        callback = self._array_callback(arguments, "map")
        mapped = []

        for index, item in enumerate(array.items):
            mapped.append(callback.call([item, index, array]))

        return JSArray(mapped)

    def _array_filter(self, array: JSArray, arguments: list[object]) -> JSArray:
        callback = self._array_callback(arguments, "filter")
        filtered = []

        for index, item in enumerate(array.items):
            if to_boolean(callback.call([item, index, array])):
                filtered.append(item)

        return JSArray(filtered)

    def _array_reduce(self, array: JSArray, arguments: list[object]) -> object:
        callback = self._array_callback(arguments, "reduce")

        if len(arguments) > 1:
            accumulator = arguments[1]
            start_index = 0
        elif array.items:
            accumulator = array.items[0]
            start_index = 1
        else:
            raise InterpreterError("Reduce of empty array with no initial value.")

        for index in range(start_index, len(array.items)):
            accumulator = callback.call(
                [accumulator, array.items[index], index, array]
            )

        return accumulator

    def _array_find(self, array: JSArray, arguments: list[object]) -> object:
        callback = self._array_callback(arguments, "find")

        for index, item in enumerate(array.items):
            if to_boolean(callback.call([item, index, array])):
                return item

        return JS_UNDEFINED

    def _array_some(self, array: JSArray, arguments: list[object]) -> bool:
        callback = self._array_callback(arguments, "some")

        for index, item in enumerate(array.items):
            if to_boolean(callback.call([item, index, array])):
                return True

        return False

    def _array_every(self, array: JSArray, arguments: list[object]) -> bool:
        callback = self._array_callback(arguments, "every")

        for index, item in enumerate(array.items):
            if not to_boolean(callback.call([item, index, array])):
                return False

        return True

    def _array_for_each(self, array: JSArray, arguments: list[object]) -> object:
        callback = self._array_callback(arguments, "forEach")

        for index, item in enumerate(list(array.items)):
            callback.call([item, index, array])

        return JS_UNDEFINED

    def _array_callback(self, arguments: list[object], method_name: str) -> JSCallable:
        if not arguments or not isinstance(arguments[0], JSCallable):
            raise InterpreterError(f"Array.{method_name} callback must be a function.")
        return arguments[0]

    def _join_item_to_string(self, item: object) -> str:
        if item is JS_NULL or item is JS_UNDEFINED:
            return ""
        return to_string(item)

    def _substring_index(self, value: object) -> int:
        number = to_number(value)
        if number != number or number < 0:
            return 0
        if math.isinf(number):
            return 0 if number < 0 else 2**31
        return int(number)

    def _string_integer_index(self, value: object) -> int | float:
        number = to_number(value)
        if is_nan(number):
            return 0
        if math.isinf(number):
            return number
        return int(number)

    def _string_length_argument(self, value: object, name: str) -> int:
        number = to_number(value)
        if is_nan(number) or number <= 0:
            return 0
        if math.isinf(number):
            raise ValueError(f"{name} must be finite.")
        return int(number)

    def _slice_index(self, value: object, length: int) -> int:
        number = to_number(value)
        if number != number:
            return 0
        if math.isinf(number):
            return 0 if number < 0 else length

        index = int(number)
        if index < 0:
            return max(length + index, 0)
        return min(index, length)

    def _array_index(self, value: object) -> int | None:
        number = to_number(value)
        if is_nan(number) or math.isinf(number):
            return None
        return int(number)

    def _canonical_array_index(self, property_name: str) -> int | None:
        if property_name == "":
            return None
        if not all(character.isdigit() for character in property_name):
            return None
        if len(property_name) > 1 and property_name.startswith("0"):
            return None
        return int(property_name)

    def _is_negative_numeric_key(self, key: object, property_name: str) -> bool:
        if is_number(key):
            number = to_number(key)
            return not is_nan(number) and not math.isinf(number) and number < 0
        return property_name.startswith("-") and property_name[1:].isdigit()

    def _array_search_start(self, value: object, length: int) -> int:
        number = to_number(value)
        if is_nan(number):
            return 0
        if math.isinf(number):
            return 0 if number < 0 else length

        index = int(number)
        if index < 0:
            return max(length + index, 0)
        return min(index, length)

    def _property_key(self, value: object) -> str:
        return to_string(value)

    def _is_nullish(self, value: object) -> bool:
        return value is JS_NULL or value is JS_UNDEFINED


def evaluate_expression(source: str) -> object:
    tokens = Lexer(source).tokenize()
    expression = Parser(tokens).parse()
    return Interpreter().evaluate(expression)


def run_source(
    source: str,
    output: Callable[[str], None] | None = None,
    step_limit: int = 100_000,
) -> None:
    interpreter = Interpreter(output, step_limit=step_limit)
    tokens = Lexer(source).tokenize()
    program = Parser(tokens).parse_program()
    interpreter.execute(program)


def value_to_output(value: object) -> str:
    return format_value(value)
