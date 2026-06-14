"""Token definitions for the Thunder JavaScript lexer."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TokenType(str, Enum):
    # Literals and names
    NUMBER = "NUMBER"
    STRING = "STRING"
    TEMPLATE = "TEMPLATE"
    IDENTIFIER = "IDENTIFIER"

    # Keywords
    LET = "LET"
    CONST = "CONST"
    VAR = "VAR"
    IF = "IF"
    ELSE = "ELSE"
    WHILE = "WHILE"
    DO = "DO"
    FOR = "FOR"
    SWITCH = "SWITCH"
    CASE = "CASE"
    DEFAULT = "DEFAULT"
    FUNCTION = "FUNCTION"
    RETURN = "RETURN"
    NEW = "NEW"
    TRUE = "TRUE"
    FALSE = "FALSE"
    NULL = "NULL"
    UNDEFINED = "UNDEFINED"
    TYPEOF = "TYPEOF"
    BREAK = "BREAK"
    CONTINUE = "CONTINUE"

    # Punctuation and brackets
    LEFT_PAREN = "LEFT_PAREN"
    RIGHT_PAREN = "RIGHT_PAREN"
    LEFT_BRACE = "LEFT_BRACE"
    RIGHT_BRACE = "RIGHT_BRACE"
    LEFT_BRACKET = "LEFT_BRACKET"
    RIGHT_BRACKET = "RIGHT_BRACKET"
    COMMA = "COMMA"
    DOT = "DOT"
    OPTIONAL_CHAIN = "OPTIONAL_CHAIN"
    ELLIPSIS = "ELLIPSIS"
    SEMICOLON = "SEMICOLON"
    COLON = "COLON"
    QUESTION = "QUESTION"

    # Operators
    PLUS = "PLUS"
    MINUS = "MINUS"
    STAR = "STAR"
    SLASH = "SLASH"
    PERCENT = "PERCENT"
    STAR_STAR = "STAR_STAR"
    STAR_STAR_EQUAL = "STAR_STAR_EQUAL"
    EQUAL = "EQUAL"
    EQUAL_EQUAL = "EQUAL_EQUAL"
    EQUAL_EQUAL_EQUAL = "EQUAL_EQUAL_EQUAL"
    BANG = "BANG"
    BANG_EQUAL = "BANG_EQUAL"
    BANG_EQUAL_EQUAL = "BANG_EQUAL_EQUAL"
    LESS = "LESS"
    LESS_EQUAL = "LESS_EQUAL"
    GREATER = "GREATER"
    GREATER_EQUAL = "GREATER_EQUAL"
    AND_AND = "AND_AND"
    OR_OR = "OR_OR"
    QUESTION_QUESTION = "QUESTION_QUESTION"
    PLUS_PLUS = "PLUS_PLUS"
    MINUS_MINUS = "MINUS_MINUS"
    PLUS_EQUAL = "PLUS_EQUAL"
    MINUS_EQUAL = "MINUS_EQUAL"
    STAR_EQUAL = "STAR_EQUAL"
    SLASH_EQUAL = "SLASH_EQUAL"
    PERCENT_EQUAL = "PERCENT_EQUAL"
    ARROW = "ARROW"

    EOF = "EOF"


@dataclass(frozen=True)
class Token:
    """One meaningful piece of JavaScript source code."""

    type: TokenType
    lexeme: str
    literal: Any
    line: int
    column: int
