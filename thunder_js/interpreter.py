"""Basic expression interpreter for the Thunder JavaScript runtime."""

import math
from collections.abc import Callable

from thunder_js.ast_nodes import (
    AssignmentExpression,
    ArrayLiteral,
    ArrowFunctionExpression,
    BinaryExpression,
    BlockStatement,
    BreakStatement,
    BooleanLiteral,
    CallExpression,
    ComputedMemberExpression,
    ContinueStatement,
    DoWhileStatement,
    ExpressionStatement,
    ForStatement,
    FunctionDeclaration,
    FunctionExpression,
    GroupingExpression,
    Identifier,
    IfStatement,
    LogicalExpression,
    NullLiteral,
    NumericLiteral,
    ObjectLiteral,
    PostfixUpdateExpression,
    PrefixUpdateExpression,
    Program,
    PropertyAccessExpression,
    ReturnStatement,
    SpreadElement,
    StringLiteral,
    SwitchStatement,
    UnaryExpression,
    UndefinedLiteral,
    VariableDeclaration,
    WhileStatement,
)
from thunder_js.environment import Environment
from thunder_js.js_builtins import JSCallable, create_global_environment
from thunder_js.lexer import Lexer
from thunder_js.parser import Parser
from thunder_js.values import (
    JSArray,
    JS_NULL,
    JSObject,
    JS_UNDEFINED,
    format_value,
    is_nan,
    js_add,
    js_divide,
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


class NativeMethod(JSCallable):
    """A small callable wrapper for built-in methods."""

    def __init__(self, method: Callable[[list[object]], object]):
        self.method = method

    def call(self, arguments: list[object]) -> object:
        return self.method(arguments)


class JSFunction(JSCallable):
    """A user-defined JavaScript function."""

    def __init__(
        self,
        parameters: list[str],
        body: object,
        closure: Environment,
        interpreter: "Interpreter",
    ):
        self.parameters = parameters
        self.body = body
        self.closure = closure
        self.interpreter = interpreter

    def call(self, arguments: list[object]) -> object:
        self.interpreter.call_depth += 1
        if self.interpreter.call_depth > self.interpreter.call_limit:
            self.interpreter.call_depth -= 1
            raise InterpreterError("Maximum call stack size exceeded.")

        function_environment = Environment(self.closure)

        try:
            for index, parameter in enumerate(self.parameters):
                if index < len(arguments):
                    value = arguments[index]
                else:
                    value = JS_UNDEFINED
                function_environment.define(parameter, value)

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
            return JSFunction(
                expression.parameters,
                expression.body,
                self.environment,
                self,
            )
        if isinstance(expression, ArrowFunctionExpression):
            return JSFunction(
                expression.parameters,
                expression.body,
                self.environment,
                self,
            )
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
            return self._get_computed_member(expression)
        if isinstance(expression, CallExpression):
            return self._evaluate_call(expression)
        if isinstance(expression, AssignmentExpression):
            return self._evaluate_assignment(expression)
        if isinstance(expression, PrefixUpdateExpression):
            return self._evaluate_prefix_update(expression)
        if isinstance(expression, PostfixUpdateExpression):
            return self._evaluate_postfix_update(expression)

        raise InterpreterError("Unknown expression.")

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

        for child in statements:
            if isinstance(child, FunctionDeclaration):
                continue
            self.execute(child)

    def _hoist_function_declarations(self, statements: list[object]) -> None:
        for child in statements:
            if isinstance(child, FunctionDeclaration):
                self._define_function(child)

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

    def _execute_function_declaration(self, statement: FunctionDeclaration) -> None:
        self._define_function(statement)

    def _define_function(self, statement: FunctionDeclaration) -> None:
        function = JSFunction(
            statement.parameters,
            statement.body,
            self.environment,
            self,
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

    def _execute_switch(self, statement: SwitchStatement) -> None:
        discriminant = self.evaluate(statement.discriminant)
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
        left_number = to_number(left)
        right_number = to_number(right)

        if is_nan(left_number) or is_nan(right_number):
            return math.nan
        if left_number < 0 and not right_number.is_integer():
            return math.nan

        try:
            return left_number**right_number
        except (OverflowError, ValueError):
            return math.nan

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
        right = self.evaluate(expression.value)

        try:
            if expression.operator == "=":
                return self._assign_target(expression.target, right)

            left = self._read_assignment_target(expression.target)

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

            return self._assign_target(expression.target, value)
        except (NameError, TypeError) as error:
            raise InterpreterError(str(error)) from error

    def _read_assignment_target(self, target: object) -> object:
        if isinstance(target, Identifier):
            return self.environment.get(target.name)
        if isinstance(target, ComputedMemberExpression):
            return self._get_computed_member(target)
        if isinstance(target, PropertyAccessExpression):
            return self._get_property(target)
        raise InterpreterError("Invalid assignment target.")

    def _assign_target(self, target: object, value: object) -> object:
        if isinstance(target, Identifier):
            return self.environment.assign(target.name, value)
        if isinstance(target, ComputedMemberExpression):
            return self._assign_computed_member(target, value)
        if isinstance(target, PropertyAccessExpression):
            return self._assign_property(target, value)
        raise InterpreterError("Invalid assignment target.")

    def _evaluate_prefix_update(self, expression: PrefixUpdateExpression) -> object:
        new_value = self._apply_update(expression.argument, expression.operator)
        return new_value

    def _evaluate_postfix_update(self, expression: PostfixUpdateExpression) -> object:
        if not isinstance(expression.argument, Identifier):
            raise InterpreterError("Only variable updates are supported yet.")

        old_value = self._look_up_identifier(expression.argument)
        self._apply_update(expression.argument, expression.operator)
        return old_value

    def _apply_update(self, target: object, operator: str) -> object:
        if not isinstance(target, Identifier):
            raise InterpreterError("Only variable updates are supported yet.")

        old_value = self._look_up_identifier(target)
        amount = 1 if operator == "++" else -1
        new_value = to_number(old_value) + amount

        try:
            return self.environment.assign(target.name, new_value)
        except (NameError, TypeError) as error:
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
            properties[property_node.key] = self.evaluate(property_node.value)

        return JSObject(properties)

    def _get_property(self, expression: PropertyAccessExpression) -> object:
        container = self.evaluate(expression.object)
        property_name = expression.property.name

        if isinstance(container, str):
            return self._get_string_property(container, property_name)
        if isinstance(container, JSArray):
            return self._get_array_property(container, property_name)
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
            "trim": lambda args: text.strip(),
            "toUpperCase": lambda args: text.upper(),
            "toLowerCase": lambda args: text.lower(),
            "includes": lambda args: self._string_includes(text, args),
            "startsWith": lambda args: self._string_starts_with(text, args),
            "endsWith": lambda args: self._string_ends_with(text, args),
            "indexOf": lambda args: self._string_index_of(text, args),
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

        raise InterpreterError(f"Array method {property_name} is not defined.")

    def _get_computed_member(self, expression: ComputedMemberExpression) -> object:
        container = self.evaluate(expression.object)
        key = self.evaluate(expression.property)

        if isinstance(container, JSArray):
            index = self._array_index(key)
            if index is None:
                return JS_UNDEFINED
            if 0 <= index < len(container.items):
                return container.items[index]
            return JS_UNDEFINED

        if isinstance(container, str):
            index = self._array_index(key)
            if index is None:
                return JS_UNDEFINED
            if 0 <= index < len(container):
                return container[index]
            return JS_UNDEFINED
        if isinstance(container, JSObject):
            return container.properties.get(self._property_key(key), JS_UNDEFINED)

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

    def _evaluate_call(self, expression: CallExpression) -> object:
        callee = self.evaluate(expression.callee)
        arguments = [self.evaluate(argument) for argument in expression.arguments]

        if isinstance(callee, JSCallable):
            try:
                return callee.call(arguments)
            except RecursionError as error:
                raise InterpreterError("Maximum call stack size exceeded.") from error

        raise InterpreterError("Value is not callable.")

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
