"""AST node classes for JavaScript expressions and statements."""

from dataclasses import dataclass


class Expression:
    """Base class for expression nodes."""


class Statement:
    """Base class for statement nodes."""


@dataclass(frozen=True)
class Program:
    body: list[Statement]


@dataclass(frozen=True)
class ExpressionStatement(Statement):
    expression: Expression


@dataclass(frozen=True)
class BlockStatement(Statement):
    body: list[Statement]


@dataclass(frozen=True)
class VariableDeclaration(Statement):
    kind: str
    name: str
    initializer: Expression | None


@dataclass(frozen=True)
class IfStatement(Statement):
    test: Expression
    consequent: Statement
    alternate: Statement | None


@dataclass(frozen=True)
class WhileStatement(Statement):
    test: Expression
    body: Statement


@dataclass(frozen=True)
class DoWhileStatement(Statement):
    body: Statement
    test: Expression


@dataclass(frozen=True)
class ForStatement(Statement):
    initializer: Statement | Expression | None
    condition: Expression | None
    update: Expression | None
    body: Statement


@dataclass(frozen=True)
class ForOfStatement(Statement):
    kind: str
    name: str
    iterable: Expression
    body: Statement


@dataclass(frozen=True)
class BreakStatement(Statement):
    pass


@dataclass(frozen=True)
class ContinueStatement(Statement):
    pass


@dataclass(frozen=True)
class SwitchCase:
    test: Expression | None
    consequent: list[Statement]


@dataclass(frozen=True)
class SwitchStatement(Statement):
    discriminant: Expression
    cases: list[SwitchCase]


@dataclass(frozen=True)
class FunctionDeclaration(Statement):
    name: str
    parameters: list[str]
    body: BlockStatement
    rest_parameter: str | None = None
    parameter_defaults: list[Expression | None] | None = None


@dataclass(frozen=True)
class ReturnStatement(Statement):
    argument: Expression | None


@dataclass(frozen=True)
class FunctionExpression(Expression):
    name: str | None
    parameters: list[str]
    body: BlockStatement
    rest_parameter: str | None = None
    parameter_defaults: list[Expression | None] | None = None


@dataclass(frozen=True)
class ArrowFunctionExpression(Expression):
    parameters: list[str]
    body: Expression | BlockStatement
    rest_parameter: str | None = None
    parameter_defaults: list[Expression | None] | None = None


@dataclass(frozen=True)
class SpreadElement(Expression):
    expression: Expression


@dataclass(frozen=True)
class ArrayLiteral(Expression):
    elements: list[Expression | SpreadElement]


@dataclass(frozen=True)
class ObjectProperty:
    key: str
    value: Expression


@dataclass(frozen=True)
class ObjectLiteral(Expression):
    properties: list[ObjectProperty | SpreadElement]


@dataclass(frozen=True)
class NumericLiteral(Expression):
    value: int | float


@dataclass(frozen=True)
class StringLiteral(Expression):
    value: str


@dataclass(frozen=True)
class BooleanLiteral(Expression):
    value: bool


@dataclass(frozen=True)
class NullLiteral(Expression):
    pass


@dataclass(frozen=True)
class UndefinedLiteral(Expression):
    pass


@dataclass(frozen=True)
class Identifier(Expression):
    name: str


@dataclass(frozen=True)
class GroupingExpression(Expression):
    expression: Expression


@dataclass(frozen=True)
class UnaryExpression(Expression):
    operator: str
    argument: Expression


@dataclass(frozen=True)
class BinaryExpression(Expression):
    left: Expression
    operator: str
    right: Expression


@dataclass(frozen=True)
class LogicalExpression(Expression):
    left: Expression
    operator: str
    right: Expression


@dataclass(frozen=True)
class ConditionalExpression(Expression):
    test: Expression
    consequent: Expression
    alternate: Expression


@dataclass(frozen=True)
class AssignmentExpression(Expression):
    target: Expression
    operator: str
    value: Expression


@dataclass(frozen=True)
class PrefixUpdateExpression(Expression):
    operator: str
    argument: Expression


@dataclass(frozen=True)
class PostfixUpdateExpression(Expression):
    argument: Expression
    operator: str


@dataclass(frozen=True)
class PropertyAccessExpression(Expression):
    object: Expression
    property: Identifier


@dataclass(frozen=True)
class ComputedMemberExpression(Expression):
    object: Expression
    property: Expression


@dataclass(frozen=True)
class NewExpression(Expression):
    callee: Expression
    arguments: list[Expression | SpreadElement]


@dataclass(frozen=True)
class CallExpression(Expression):
    callee: Expression
    arguments: list[Expression | SpreadElement]
