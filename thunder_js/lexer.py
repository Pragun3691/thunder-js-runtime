"""A small, beginner-friendly JavaScript lexer."""

from thunder_js.tokens import Token, TokenType


KEYWORDS = {
    "let": TokenType.LET,
    "const": TokenType.CONST,
    "var": TokenType.VAR,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "while": TokenType.WHILE,
    "do": TokenType.DO,
    "for": TokenType.FOR,
    "switch": TokenType.SWITCH,
    "case": TokenType.CASE,
    "default": TokenType.DEFAULT,
    "function": TokenType.FUNCTION,
    "return": TokenType.RETURN,
    "new": TokenType.NEW,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "null": TokenType.NULL,
    "undefined": TokenType.UNDEFINED,
    "typeof": TokenType.TYPEOF,
    "break": TokenType.BREAK,
    "continue": TokenType.CONTINUE,
}


class LexerError(Exception):
    """Raised when source text cannot be turned into tokens."""


class Lexer:
    """Turn JavaScript source text into a list of tokens."""

    def __init__(self, source: str):
        self.source = source
        self.tokens: list[Token] = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1
        self.start_line = 1
        self.start_column = 1

    def tokenize(self) -> list[Token]:
        """Scan the complete source and return tokens ending in one EOF."""
        self.tokens = []
        self.start = 0
        self.current = 0
        self.line = 1
        self.column = 1

        while not self._is_at_end():
            self.start = self.current
            self.start_line = self.line
            self.start_column = self.column
            self._scan_token()

        self.tokens.append(Token(TokenType.EOF, "", None, self.line, self.column))
        return self.tokens

    def _scan_token(self) -> None:
        char = self._advance()

        if char in " \t\r\n":
            return

        if char == "(":
            self._add_token(TokenType.LEFT_PAREN)
        elif char == ")":
            self._add_token(TokenType.RIGHT_PAREN)
        elif char == "{":
            self._add_token(TokenType.LEFT_BRACE)
        elif char == "}":
            self._add_token(TokenType.RIGHT_BRACE)
        elif char == "[":
            self._add_token(TokenType.LEFT_BRACKET)
        elif char == "]":
            self._add_token(TokenType.RIGHT_BRACKET)
        elif char == ",":
            self._add_token(TokenType.COMMA)
        elif char == ".":
            if self._peek() == "." and self._peek_next() == ".":
                self._advance()
                self._advance()
                self._add_token(TokenType.ELLIPSIS)
            elif self._peek().isdigit():
                self._number(started_with_dot=True)
            else:
                self._add_token(TokenType.DOT)
        elif char == ";":
            self._add_token(TokenType.SEMICOLON)
        elif char == ":":
            self._add_token(TokenType.COLON)
        elif char == "?":
            self._add_token(TokenType.QUESTION)
        elif char == "+":
            if self._match("+"):
                self._add_token(TokenType.PLUS_PLUS)
            elif self._match("="):
                self._add_token(TokenType.PLUS_EQUAL)
            else:
                self._add_token(TokenType.PLUS)
        elif char == "-":
            if self._match("-"):
                self._add_token(TokenType.MINUS_MINUS)
            elif self._match("="):
                self._add_token(TokenType.MINUS_EQUAL)
            else:
                self._add_token(TokenType.MINUS)
        elif char == "*":
            if self._match("*"):
                if self._match("="):
                    self._add_token(TokenType.STAR_STAR_EQUAL)
                else:
                    self._add_token(TokenType.STAR_STAR)
            elif self._match("="):
                self._add_token(TokenType.STAR_EQUAL)
            else:
                self._add_token(TokenType.STAR)
        elif char == "/":
            if self._match("/"):
                self._skip_line_comment()
            elif self._match("*"):
                self._skip_block_comment()
            elif self._match("="):
                self._add_token(TokenType.SLASH_EQUAL)
            else:
                self._add_token(TokenType.SLASH)
        elif char == "%":
            if self._match("="):
                self._add_token(TokenType.PERCENT_EQUAL)
            else:
                self._add_token(TokenType.PERCENT)
        elif char == "=":
            if self._match("="):
                if self._match("="):
                    self._add_token(TokenType.EQUAL_EQUAL_EQUAL)
                else:
                    self._add_token(TokenType.EQUAL_EQUAL)
            elif self._match(">"):
                self._add_token(TokenType.ARROW)
            else:
                self._add_token(TokenType.EQUAL)
        elif char == "!":
            if self._match("="):
                if self._match("="):
                    self._add_token(TokenType.BANG_EQUAL_EQUAL)
                else:
                    self._add_token(TokenType.BANG_EQUAL)
            else:
                self._add_token(TokenType.BANG)
        elif char == "<":
            if self._match("="):
                self._add_token(TokenType.LESS_EQUAL)
            else:
                self._add_token(TokenType.LESS)
        elif char == ">":
            if self._match("="):
                self._add_token(TokenType.GREATER_EQUAL)
            else:
                self._add_token(TokenType.GREATER)
        elif char == "&":
            if self._match("&"):
                self._add_token(TokenType.AND_AND)
            else:
                self._raise_unexpected(char)
        elif char == "|":
            if self._match("|"):
                self._add_token(TokenType.OR_OR)
            else:
                self._raise_unexpected(char)
        elif char in ("'", '"'):
            self._string(char)
        elif char.isdigit():
            self._number(started_with_dot=False)
        elif self._is_identifier_start(char):
            self._identifier()
        else:
            self._raise_unexpected(char)

    def _identifier(self) -> None:
        while self._is_identifier_part(self._peek()):
            self._advance()

        text = self.source[self.start : self.current]
        token_type = KEYWORDS.get(text, TokenType.IDENTIFIER)
        self._add_token(token_type)

    def _number(self, started_with_dot: bool) -> None:
        if not started_with_dot:
            while self._peek().isdigit():
                self._advance()

            if self._peek() == ".":
                self._advance()

        while self._peek().isdigit():
            self._advance()

        text = self.source[self.start : self.current]
        literal = float(text) if "." in text else int(text)
        self._add_token(TokenType.NUMBER, literal)

    def _string(self, quote: str) -> None:
        value = ""

        while not self._is_at_end():
            char = self._advance()

            if char == quote:
                self._add_token(TokenType.STRING, value)
                return

            if char == "\n":
                self._raise_unterminated_string()

            if char == "\\":
                value += self._read_escape_sequence(quote)
            else:
                value += char

        self._raise_unterminated_string()

    def _read_escape_sequence(self, quote: str) -> str:
        if self._is_at_end():
            self._raise_unterminated_string()

        char = self._advance()
        escapes = {
            "n": "\n",
            "r": "\r",
            "t": "\t",
            "\\": "\\",
            "'": "'",
            '"': '"',
        }

        if char == quote:
            return quote

        return escapes.get(char, char)

    def _skip_line_comment(self) -> None:
        while self._peek() != "\n" and not self._is_at_end():
            self._advance()

    def _skip_block_comment(self) -> None:
        while not self._is_at_end():
            if self._peek() == "*" and self._peek_next() == "/":
                self._advance()
                self._advance()
                return
            self._advance()

        raise LexerError(
            "Unterminated block comment starting at "
            f"line {self.start_line}, column {self.start_column}."
        )

    def _add_token(self, token_type: TokenType, literal: object = None) -> None:
        text = self.source[self.start : self.current]
        self.tokens.append(
            Token(token_type, text, literal, self.start_line, self.start_column)
        )

    def _advance(self) -> str:
        char = self.source[self.current]
        self.current += 1

        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

        return char

    def _match(self, expected: str) -> bool:
        if self._is_at_end() or self.source[self.current] != expected:
            return False

        self._advance()
        return True

    def _peek(self) -> str:
        if self._is_at_end():
            return "\0"
        return self.source[self.current]

    def _peek_next(self) -> str:
        next_index = self.current + 1
        if next_index >= len(self.source):
            return "\0"
        return self.source[next_index]

    def _is_at_end(self) -> bool:
        return self.current >= len(self.source)

    def _is_identifier_start(self, char: str) -> bool:
        return char.isalpha() or char in ("_", "$")

    def _is_identifier_part(self, char: str) -> bool:
        return self._is_identifier_start(char) or char.isdigit()

    def _raise_unexpected(self, char: str) -> None:
        raise LexerError(
            f"Unexpected character {char!r} at "
            f"line {self.start_line}, column {self.start_column}."
        )

    def _raise_unterminated_string(self) -> None:
        raise LexerError(
            "Unterminated string starting at "
            f"line {self.start_line}, column {self.start_column}."
        )
