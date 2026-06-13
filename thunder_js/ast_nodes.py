"""AST node classes for JavaScript expressions."""

from dataclasses import dataclass


class Expression:
    """Base class for expression nodes."""


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
class CallExpression(Expression):
    callee: Expression
    arguments: list[Expression]
