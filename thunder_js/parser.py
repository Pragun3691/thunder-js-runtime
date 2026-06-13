"""Expression parser for the Thunder JavaScript runtime."""

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
    Expression,
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
    ObjectProperty,
    PostfixUpdateExpression,
    PrefixUpdateExpression,
    Program,
    PropertyAccessExpression,
    ReturnStatement,
    Statement,
    SpreadElement,
    StringLiteral,
    SwitchCase,
    SwitchStatement,
    UnaryExpression,
    UndefinedLiteral,
    VariableDeclaration,
    WhileStatement,
)
from thunder_js.tokens import Token, TokenType


ASSIGNMENT_OPERATORS = {
    TokenType.EQUAL,
    TokenType.PLUS_EQUAL,
    TokenType.MINUS_EQUAL,
    TokenType.STAR_EQUAL,
    TokenType.SLASH_EQUAL,
}

UPDATE_OPERATORS = {TokenType.PLUS_PLUS, TokenType.MINUS_MINUS}
ASSIGNMENT_TARGET_TYPES = (
    Identifier,
    PropertyAccessExpression,
    ComputedMemberExpression,
)


class ParserError(Exception):
    """Raised when tokens do not form valid JavaScript syntax."""


class Parser:
    """Parse JavaScript expressions and complete programs."""

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.current = 0
        self.loop_depth = 0
        self.switch_depth = 0
        self.function_depth = 0

    def parse(self) -> Expression:
        expression = self.parse_expression()
        self._consume(TokenType.EOF, "Expected end of expression.")
        return expression

    def parse_program(self) -> Program:
        body = []

        while not self._is_at_end():
            if self._match(TokenType.SEMICOLON):
                continue
            body.append(self._statement())

        return Program(body)

    def parse_expression(self) -> Expression:
        return self._arrow_function()

    def _statement(self) -> Statement:
        if self._match(TokenType.LEFT_BRACE):
            return self._block_statement()
        if self._match(TokenType.LET):
            return self._variable_declaration("let")
        if self._match(TokenType.CONST):
            return self._variable_declaration("const")
        if self._match(TokenType.IF):
            return self._if_statement()
        if self._match(TokenType.WHILE):
            return self._while_statement()
        if self._match(TokenType.DO):
            return self._do_while_statement()
        if self._match(TokenType.FOR):
            return self._for_statement()
        if self._match(TokenType.SWITCH):
            return self._switch_statement()
        if self._match(TokenType.BREAK):
            if self.loop_depth == 0 and self.switch_depth == 0:
                raise self._error(
                    self._previous(),
                    "break used outside of a loop or switch.",
                )
            self._optional_semicolon()
            return BreakStatement()
        if self._match(TokenType.CONTINUE):
            if self.loop_depth == 0:
                raise self._error(self._previous(), "continue used outside of a loop.")
            self._optional_semicolon()
            return ContinueStatement()
        if self._match(TokenType.FUNCTION):
            return self._function_declaration()
        if self._match(TokenType.RETURN):
            if self.function_depth == 0:
                raise self._error(
                    self._previous(), "return used outside of a function."
                )
            return self._return_statement()

        return self._expression_statement()

    def _block_statement(self) -> BlockStatement:
        body = []

        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            if self._match(TokenType.SEMICOLON):
                continue
            body.append(self._statement())

        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after block.")
        return BlockStatement(body)

    def _variable_declaration(self, kind: str) -> VariableDeclaration:
        name = self._consume(TokenType.IDENTIFIER, f"Expected {kind} variable name.")
        initializer = None

        if self._match(TokenType.EQUAL):
            initializer = self.parse_expression()
        elif kind == "const":
            raise self._error(name, "Expected initializer for const declaration.")

        self._optional_semicolon()
        return VariableDeclaration(kind, name.lexeme, initializer)

    def _if_statement(self) -> IfStatement:
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after if.")
        test = self.parse_expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after if condition.")

        consequent = self._statement()
        alternate = None

        if self._match(TokenType.ELSE):
            alternate = self._statement()

        return IfStatement(test, consequent, alternate)

    def _while_statement(self) -> WhileStatement:
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after while.")
        test = self.parse_expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after while condition.")
        self.loop_depth += 1
        try:
            body = self._statement()
        finally:
            self.loop_depth -= 1
        return WhileStatement(test, body)

    def _do_while_statement(self) -> DoWhileStatement:
        self.loop_depth += 1
        try:
            body = self._statement()
        finally:
            self.loop_depth -= 1

        self._consume(TokenType.WHILE, "Expected 'while' after do body.")
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after while.")
        test = self.parse_expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after do while condition.")
        self._optional_semicolon()
        return DoWhileStatement(body, test)

    def _for_statement(self) -> ForStatement:
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after for.")

        if self._match(TokenType.SEMICOLON):
            initializer = None
        elif self._match(TokenType.LET):
            initializer = self._variable_declaration_without_semicolon("let")
            self._consume(TokenType.SEMICOLON, "Expected ';' after for initializer.")
        elif self._match(TokenType.CONST):
            initializer = self._variable_declaration_without_semicolon("const")
            self._consume(TokenType.SEMICOLON, "Expected ';' after for initializer.")
        else:
            initializer = self.parse_expression()
            self._consume(TokenType.SEMICOLON, "Expected ';' after for initializer.")

        condition = None
        if not self._check(TokenType.SEMICOLON):
            condition = self.parse_expression()
        self._consume(TokenType.SEMICOLON, "Expected ';' after for condition.")

        update = None
        if not self._check(TokenType.RIGHT_PAREN):
            update = self.parse_expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after for clauses.")

        self.loop_depth += 1
        try:
            body = self._statement()
        finally:
            self.loop_depth -= 1
        return ForStatement(initializer, condition, update, body)

    def _switch_statement(self) -> SwitchStatement:
        self._consume(TokenType.LEFT_PAREN, "Expected '(' after switch.")
        discriminant = self.parse_expression()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after switch expression.")
        self._consume(TokenType.LEFT_BRACE, "Expected '{' before switch body.")

        cases = []
        has_default = False
        self.switch_depth += 1

        try:
            while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
                if self._match(TokenType.CASE):
                    test = self.parse_expression()
                    self._consume(TokenType.COLON, "Expected ':' after case value.")
                elif self._match(TokenType.DEFAULT):
                    if has_default:
                        raise self._error(
                            self._previous(),
                            "switch can only have one default case.",
                        )
                    has_default = True
                    test = None
                    self._consume(TokenType.COLON, "Expected ':' after default.")
                else:
                    raise self._error(
                        self._peek(),
                        "Expected 'case' or 'default' in switch body.",
                    )

                consequent = []
                while (
                    not self._check(TokenType.CASE)
                    and not self._check(TokenType.DEFAULT)
                    and not self._check(TokenType.RIGHT_BRACE)
                    and not self._is_at_end()
                ):
                    if self._match(TokenType.SEMICOLON):
                        continue
                    consequent.append(self._statement())

                cases.append(SwitchCase(test, consequent))
        finally:
            self.switch_depth -= 1

        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after switch body.")
        return SwitchStatement(discriminant, cases)

    def _function_declaration(self) -> FunctionDeclaration:
        name = self._consume(TokenType.IDENTIFIER, "Expected function name.")
        parameters, rest_parameter = self._function_parameters("function name")
        body = self._function_body()
        return FunctionDeclaration(name.lexeme, parameters, body, rest_parameter)

    def _function_expression(self) -> FunctionExpression:
        name = None

        if self._match(TokenType.IDENTIFIER):
            name = self._previous().lexeme

        parameters, rest_parameter = self._function_parameters("function")
        body = self._function_body()
        return FunctionExpression(name, parameters, body, rest_parameter)

    def _function_parameters(self, owner: str) -> tuple[list[str], str | None]:
        self._consume(TokenType.LEFT_PAREN, f"Expected '(' after {owner}.")
        parameters, rest_parameter = self._parameter_list()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after parameters.")
        return parameters, rest_parameter

    def _parameter_list(self) -> tuple[list[str], str | None]:
        parameters = []
        seen_names = set()
        rest_parameter = None

        if self._check(TokenType.RIGHT_PAREN):
            return parameters, rest_parameter

        while True:
            if self._match(TokenType.ELLIPSIS):
                if rest_parameter is not None:
                    raise self._error(
                        self._previous(),
                        "Only one rest parameter is allowed.",
                    )
                rest_parameter_token = self._consume(
                    TokenType.IDENTIFIER,
                    "Expected rest parameter name.",
                )
                if rest_parameter_token.lexeme in seen_names:
                    raise self._error(
                        rest_parameter_token,
                        f"Duplicate parameter name {rest_parameter_token.lexeme!r}.",
                    )
                rest_parameter = rest_parameter_token.lexeme

                if self._match(TokenType.COMMA):
                    raise self._error(
                        self._previous(),
                        "Rest parameter must be last.",
                    )
                break

            parameter = self._consume(
                TokenType.IDENTIFIER,
                "Expected parameter name.",
            )
            if parameter.lexeme in seen_names:
                raise self._error(
                    parameter,
                    f"Duplicate parameter name {parameter.lexeme!r}.",
                )
            parameters.append(parameter.lexeme)
            seen_names.add(parameter.lexeme)

            if not self._match(TokenType.COMMA):
                break

            if self._check(TokenType.RIGHT_PAREN):
                break

        return parameters, rest_parameter

    def _function_body(self) -> BlockStatement:
        self._consume(TokenType.LEFT_BRACE, "Expected '{' before function body.")
        previous_loop_depth = self.loop_depth
        previous_switch_depth = self.switch_depth
        self.loop_depth = 0
        self.switch_depth = 0
        self.function_depth += 1
        try:
            body = self._block_statement()
        finally:
            self.function_depth -= 1
            self.loop_depth = previous_loop_depth
            self.switch_depth = previous_switch_depth
        return body

    def _return_statement(self) -> ReturnStatement:
        if self._check(TokenType.SEMICOLON) or self._check(TokenType.RIGHT_BRACE):
            argument = None
        else:
            argument = self.parse_expression()

        self._optional_semicolon()
        return ReturnStatement(argument)

    def _expression_statement(self) -> ExpressionStatement:
        expression = self.parse_expression()
        self._optional_semicolon()
        return ExpressionStatement(expression)

    def _variable_declaration_without_semicolon(
        self, kind: str
    ) -> VariableDeclaration:
        name = self._consume(TokenType.IDENTIFIER, f"Expected {kind} variable name.")
        initializer = None

        if self._match(TokenType.EQUAL):
            initializer = self.parse_expression()
        elif kind == "const":
            raise self._error(name, "Expected initializer for const declaration.")

        return VariableDeclaration(kind, name.lexeme, initializer)

    def _arrow_function(self) -> Expression:
        if self._check(TokenType.IDENTIFIER) and self._check_next(TokenType.ARROW):
            parameter = self._advance()
            self._advance()
            body = self._arrow_body()
            return ArrowFunctionExpression([parameter.lexeme], body)

        if self._is_parenthesized_arrow_parameters():
            parameters, rest_parameter = self._arrow_parameters()
            self._consume(TokenType.ARROW, "Expected '=>' after arrow parameters.")
            body = self._arrow_body()
            return ArrowFunctionExpression(parameters, body, rest_parameter)

        return self._assignment()

    def _arrow_parameters(self) -> tuple[list[str], str | None]:
        self._consume(TokenType.LEFT_PAREN, "Expected '(' before arrow parameters.")
        parameters, rest_parameter = self._parameter_list()
        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after arrow parameters.")
        return parameters, rest_parameter

    def _arrow_body(self) -> Expression | BlockStatement:
        if self._check(TokenType.LEFT_BRACE):
            return self._function_body()

        return self.parse_expression()

    def _is_parenthesized_arrow_parameters(self) -> bool:
        if not self._check(TokenType.LEFT_PAREN):
            return False

        index = self.current + 1

        if self._token_type_at(index) == TokenType.RIGHT_PAREN:
            return self._token_type_at(index + 1) == TokenType.ARROW

        while True:
            if self._token_type_at(index) == TokenType.ELLIPSIS:
                index += 1
                if self._token_type_at(index) != TokenType.IDENTIFIER:
                    return False
                index += 1
                if self._token_type_at(index) != TokenType.RIGHT_PAREN:
                    return False
                return self._token_type_at(index + 1) == TokenType.ARROW

            if self._token_type_at(index) != TokenType.IDENTIFIER:
                return False

            index += 1

            if self._token_type_at(index) == TokenType.COMMA:
                index += 1
                continue

            if self._token_type_at(index) == TokenType.RIGHT_PAREN:
                return self._token_type_at(index + 1) == TokenType.ARROW

            return False

    def _assignment(self) -> Expression:
        target = self._logical_or()

        if self._match(*ASSIGNMENT_OPERATORS):
            operator = self._previous().lexeme
            self._require_assignment_target(target)
            value = self._arrow_function()
            return AssignmentExpression(target, operator, value)

        return target

    def _logical_or(self) -> Expression:
        expression = self._logical_and()

        while self._match(TokenType.OR_OR):
            operator = self._previous().lexeme
            right = self._logical_and()
            expression = LogicalExpression(expression, operator, right)

        return expression

    def _logical_and(self) -> Expression:
        expression = self._equality()

        while self._match(TokenType.AND_AND):
            operator = self._previous().lexeme
            right = self._equality()
            expression = LogicalExpression(expression, operator, right)

        return expression

    def _equality(self) -> Expression:
        expression = self._comparison()

        while self._match(
            TokenType.EQUAL_EQUAL,
            TokenType.BANG_EQUAL,
            TokenType.EQUAL_EQUAL_EQUAL,
            TokenType.BANG_EQUAL_EQUAL,
        ):
            operator = self._previous().lexeme
            right = self._comparison()
            expression = BinaryExpression(expression, operator, right)

        return expression

    def _comparison(self) -> Expression:
        expression = self._term()

        while self._match(
            TokenType.LESS,
            TokenType.LESS_EQUAL,
            TokenType.GREATER,
            TokenType.GREATER_EQUAL,
        ):
            operator = self._previous().lexeme
            right = self._term()
            expression = BinaryExpression(expression, operator, right)

        return expression

    def _term(self) -> Expression:
        expression = self._factor()

        while self._match(TokenType.PLUS, TokenType.MINUS):
            operator = self._previous().lexeme
            right = self._factor()
            expression = BinaryExpression(expression, operator, right)

        return expression

    def _factor(self) -> Expression:
        expression = self._unary()

        while self._match(TokenType.STAR, TokenType.SLASH, TokenType.PERCENT):
            operator = self._previous().lexeme
            right = self._unary()
            expression = BinaryExpression(expression, operator, right)

        return expression

    def _exponent(self) -> Expression:
        expression = self._postfix()

        if self._match(TokenType.STAR_STAR):
            operator = self._previous().lexeme
            right = self._unary()
            return BinaryExpression(expression, operator, right)

        return expression

    def _unary(self) -> Expression:
        if self._match(TokenType.BANG, TokenType.MINUS, TokenType.PLUS):
            operator_token = self._previous()
            operator = self._previous().lexeme
            argument = self._unary()

            if isinstance(argument, BinaryExpression) and argument.operator == "**":
                raise self._error(
                    operator_token,
                    "Unary expression cannot be the left side of '**'.",
                )

            return UnaryExpression(operator, argument)

        if self._match(*UPDATE_OPERATORS):
            operator = self._previous().lexeme
            argument = self._unary()
            self._require_assignment_target(argument)
            return PrefixUpdateExpression(operator, argument)

        return self._exponent()

    def _postfix(self) -> Expression:
        expression = self._call_or_member()

        while self._match(*UPDATE_OPERATORS):
            operator = self._previous().lexeme
            self._require_assignment_target(expression)
            expression = PostfixUpdateExpression(expression, operator)

        return expression

    def _call_or_member(self) -> Expression:
        expression = self._primary()

        while True:
            if self._match(TokenType.LEFT_PAREN):
                expression = self._finish_call(expression)
            elif self._match(TokenType.DOT):
                name = self._consume(
                    TokenType.IDENTIFIER, "Expected property name after '.'."
                )
                expression = PropertyAccessExpression(expression, Identifier(name.lexeme))
            elif self._match(TokenType.LEFT_BRACKET):
                property_expression = self.parse_expression()
                self._consume(TokenType.RIGHT_BRACKET, "Expected ']' after property.")
                expression = ComputedMemberExpression(expression, property_expression)
            else:
                return expression

    def _finish_call(self, callee: Expression) -> CallExpression:
        arguments = []

        if not self._check(TokenType.RIGHT_PAREN):
            while True:
                if self._match(TokenType.ELLIPSIS):
                    arguments.append(SpreadElement(self.parse_expression()))
                else:
                    arguments.append(self.parse_expression())
                if not self._match(TokenType.COMMA):
                    break

        self._consume(TokenType.RIGHT_PAREN, "Expected ')' after arguments.")
        return CallExpression(callee, arguments)

    def _primary(self) -> Expression:
        if self._match(TokenType.NUMBER):
            return NumericLiteral(self._previous().literal)
        if self._match(TokenType.STRING):
            return StringLiteral(self._previous().literal)
        if self._match(TokenType.TRUE):
            return BooleanLiteral(True)
        if self._match(TokenType.FALSE):
            return BooleanLiteral(False)
        if self._match(TokenType.NULL):
            return NullLiteral()
        if self._match(TokenType.UNDEFINED):
            return UndefinedLiteral()
        if self._match(TokenType.FUNCTION):
            return self._function_expression()
        if self._match(TokenType.IDENTIFIER):
            return Identifier(self._previous().lexeme)

        if self._match(TokenType.LEFT_PAREN):
            expression = self.parse_expression()
            self._consume(TokenType.RIGHT_PAREN, "Expected ')' after expression.")
            return GroupingExpression(expression)
        if self._match(TokenType.LEFT_BRACKET):
            return self._array_literal()
        if self._match(TokenType.LEFT_BRACE):
            return self._object_literal()

        raise self._error(self._peek(), "Expected expression.")

    def _array_literal(self) -> ArrayLiteral:
        elements = []

        if not self._check(TokenType.RIGHT_BRACKET):
            while True:
                if self._match(TokenType.ELLIPSIS):
                    elements.append(SpreadElement(self.parse_expression()))
                else:
                    elements.append(self.parse_expression())

                if not self._match(TokenType.COMMA):
                    break
                if self._check(TokenType.RIGHT_BRACKET):
                    break

        self._consume(TokenType.RIGHT_BRACKET, "Expected ']' after array literal.")
        return ArrayLiteral(elements)

    def _object_literal(self) -> ObjectLiteral:
        properties = []

        if not self._check(TokenType.RIGHT_BRACE):
            while True:
                key = self._object_property_key()
                self._consume(TokenType.COLON, "Expected ':' after object key.")
                value = self.parse_expression()
                properties.append(ObjectProperty(key, value))

                if not self._match(TokenType.COMMA):
                    break
                if self._check(TokenType.RIGHT_BRACE):
                    break

        self._consume(TokenType.RIGHT_BRACE, "Expected '}' after object literal.")
        return ObjectLiteral(properties)

    def _object_property_key(self) -> str:
        if self._match(TokenType.IDENTIFIER):
            return self._previous().lexeme
        if self._match(TokenType.STRING):
            return self._previous().literal
        if self._match(TokenType.NUMBER):
            value = self._previous().literal
            if isinstance(value, float) and value.is_integer():
                return str(int(value))
            return str(value)

        raise self._error(self._peek(), "Expected object property key.")

    def _require_assignment_target(self, expression: Expression) -> None:
        if isinstance(expression, ASSIGNMENT_TARGET_TYPES):
            return

        raise self._error(self._previous(), "Expected assignment target.")

    def _match(self, *token_types: TokenType) -> bool:
        for token_type in token_types:
            if self._check(token_type):
                self._advance()
                return True
        return False

    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._check(token_type):
            return self._advance()

        raise self._error(self._peek(), message)

    def _optional_semicolon(self) -> None:
        self._match(TokenType.SEMICOLON)

    def _check(self, token_type: TokenType) -> bool:
        if self._is_at_end() and token_type != TokenType.EOF:
            return False
        return self._peek().type == token_type

    def _check_next(self, token_type: TokenType) -> bool:
        return self._token_type_at(self.current + 1) == token_type

    def _token_type_at(self, index: int) -> TokenType:
        if index >= len(self.tokens):
            return TokenType.EOF
        return self.tokens[index].type

    def _advance(self) -> Token:
        if not self._is_at_end():
            self.current += 1
        return self._previous()

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _error(self, token: Token, message: str) -> ParserError:
        return ParserError(f"{message} at line {token.line}, column {token.column}.")
