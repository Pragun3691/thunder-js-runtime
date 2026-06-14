import pytest

from thunder_js.lexer import Lexer, LexerError
from thunder_js.tokens import TokenType


def token_types(source):
    return [token.type for token in Lexer(source).tokenize()]


def tokens_without_eof(source):
    return Lexer(source).tokenize()[:-1]


def test_empty_source_produces_one_eof_token():
    tokens = Lexer("").tokenize()

    assert len(tokens) == 1
    assert tokens[0].type == TokenType.EOF
    assert tokens[0].line == 1
    assert tokens[0].column == 1


def test_numbers_include_integers_decimals_and_leading_dot_decimals():
    tokens = tokens_without_eof("5 5.25 .25 5.")

    assert [token.type for token in tokens] == [
        TokenType.NUMBER,
        TokenType.NUMBER,
        TokenType.NUMBER,
        TokenType.NUMBER,
    ]
    assert [token.lexeme for token in tokens] == ["5", "5.25", ".25", "5."]
    assert [token.literal for token in tokens] == [5, 5.25, 0.25, 5.0]


def test_single_and_double_quoted_strings_keep_literal_values():
    tokens = tokens_without_eof("'hello' \"line\\nnext\" 'it\\'s fine'")

    assert [token.type for token in tokens] == [
        TokenType.STRING,
        TokenType.STRING,
        TokenType.STRING,
    ]
    assert [token.literal for token in tokens] == [
        "hello",
        "line\nnext",
        "it's fine",
    ]


def test_identifiers_and_keywords_are_distinguished():
    source = (
        "let const var if else while do for switch case default function "
        "return new true false null undefined typeof break continue console _name "
        "$value name123"
    )

    assert token_types(source) == [
        TokenType.LET,
        TokenType.CONST,
        TokenType.VAR,
        TokenType.IF,
        TokenType.ELSE,
        TokenType.WHILE,
        TokenType.DO,
        TokenType.FOR,
        TokenType.SWITCH,
        TokenType.CASE,
        TokenType.DEFAULT,
        TokenType.FUNCTION,
        TokenType.RETURN,
        TokenType.NEW,
        TokenType.TRUE,
        TokenType.FALSE,
        TokenType.NULL,
        TokenType.UNDEFINED,
        TokenType.TYPEOF,
        TokenType.BREAK,
        TokenType.CONTINUE,
        TokenType.IDENTIFIER,
        TokenType.IDENTIFIER,
        TokenType.IDENTIFIER,
        TokenType.IDENTIFIER,
        TokenType.EOF,
    ]


def test_punctuation_and_brackets_are_tokenized():
    assert token_types("(){ }[] ,.;:? ... ?.") == [
        TokenType.LEFT_PAREN,
        TokenType.RIGHT_PAREN,
        TokenType.LEFT_BRACE,
        TokenType.RIGHT_BRACE,
        TokenType.LEFT_BRACKET,
        TokenType.RIGHT_BRACKET,
        TokenType.COMMA,
        TokenType.DOT,
        TokenType.SEMICOLON,
        TokenType.COLON,
        TokenType.QUESTION,
        TokenType.ELLIPSIS,
        TokenType.OPTIONAL_CHAIN,
        TokenType.EOF,
    ]


def test_all_required_operators_are_tokenized_longest_match_first():
    source = "+ - * / % ** = == === != !== < <= > >= && || ?? ! ++ -- += -= *= /= %= **= =>"

    assert token_types(source) == [
        TokenType.PLUS,
        TokenType.MINUS,
        TokenType.STAR,
        TokenType.SLASH,
        TokenType.PERCENT,
        TokenType.STAR_STAR,
        TokenType.EQUAL,
        TokenType.EQUAL_EQUAL,
        TokenType.EQUAL_EQUAL_EQUAL,
        TokenType.BANG_EQUAL,
        TokenType.BANG_EQUAL_EQUAL,
        TokenType.LESS,
        TokenType.LESS_EQUAL,
        TokenType.GREATER,
        TokenType.GREATER_EQUAL,
        TokenType.AND_AND,
        TokenType.OR_OR,
        TokenType.QUESTION_QUESTION,
        TokenType.BANG,
        TokenType.PLUS_PLUS,
        TokenType.MINUS_MINUS,
        TokenType.PLUS_EQUAL,
        TokenType.MINUS_EQUAL,
        TokenType.STAR_EQUAL,
        TokenType.SLASH_EQUAL,
        TokenType.PERCENT_EQUAL,
        TokenType.STAR_STAR_EQUAL,
        TokenType.ARROW,
        TokenType.EOF,
    ]


def test_decrement_operator_after_identifier_is_tokenized():
    assert token_types("i--") == [
        TokenType.IDENTIFIER,
        TokenType.MINUS_MINUS,
        TokenType.EOF,
    ]


def test_comments_and_whitespace_are_ignored():
    source = """
    let x = 1; // ignore this
    /*
      ignore this too
    */
    x += 2;
    """

    assert token_types(source) == [
        TokenType.LET,
        TokenType.IDENTIFIER,
        TokenType.EQUAL,
        TokenType.NUMBER,
        TokenType.SEMICOLON,
        TokenType.IDENTIFIER,
        TokenType.PLUS_EQUAL,
        TokenType.NUMBER,
        TokenType.SEMICOLON,
        TokenType.EOF,
    ]


def test_tokens_track_line_and_column():
    tokens = tokens_without_eof("let x = 1;\n  console.log(x);")

    positions = [(token.lexeme, token.line, token.column) for token in tokens]

    assert positions == [
        ("let", 1, 1),
        ("x", 1, 5),
        ("=", 1, 7),
        ("1", 1, 9),
        (";", 1, 10),
        ("console", 2, 3),
        (".", 2, 10),
        ("log", 2, 11),
        ("(", 2, 14),
        ("x", 2, 15),
        (")", 2, 16),
        (";", 2, 17),
    ]


def test_eof_position_tracks_end_of_source():
    eof = Lexer("let x;\n").tokenize()[-1]

    assert eof.type == TokenType.EOF
    assert eof.line == 2
    assert eof.column == 1


def test_unexpected_character_raises_clear_error():
    with pytest.raises(LexerError, match=r"Unexpected character '@'.*line 1, column 5"):
        Lexer("let @").tokenize()


def test_single_ampersand_and_pipe_are_unexpected():
    with pytest.raises(LexerError, match=r"Unexpected character '&'.*line 1, column 1"):
        Lexer("&").tokenize()

    with pytest.raises(LexerError, match=r"Unexpected character '\|'.*line 1, column 1"):
        Lexer("|").tokenize()


def test_unterminated_single_quoted_string_raises_clear_error():
    with pytest.raises(
        LexerError, match=r"Unterminated string starting at line 1, column 1"
    ):
        Lexer("'missing end").tokenize()


def test_unterminated_double_quoted_string_raises_clear_error():
    with pytest.raises(
        LexerError, match=r"Unterminated string starting at line 1, column 1"
    ):
        Lexer('"missing end').tokenize()


def test_newline_inside_string_is_reported_as_unterminated():
    with pytest.raises(
        LexerError, match=r"Unterminated string starting at line 1, column 1"
    ):
        Lexer("'line one\nline two'").tokenize()


def test_unterminated_block_comment_raises_clear_error():
    with pytest.raises(
        LexerError, match=r"Unterminated block comment starting at line 1, column 5"
    ):
        Lexer("let /* nope").tokenize()

def test_increment_operator_after_identifier_is_tokenized():
    assert token_types("i++") == [
        TokenType.IDENTIFIER,
        TokenType.PLUS_PLUS,
        TokenType.EOF,
    ]

def test_string_escape_sequences():
    tokens = tokens_without_eof(r'"a\tb" "quote: \"" "slash: \\"')

    assert [token.literal for token in tokens] == [
        "a\tb",
        'quote: "',
        "slash: \\",
    ]    


def test_tokenize_can_be_called_twice_without_adding_extra_eof_tokens():
    lexer = Lexer("let x = 1;")

    first = lexer.tokenize()
    second = lexer.tokenize()

    assert [token.type for token in first].count(TokenType.EOF) == 1
    assert [token.type for token in second].count(TokenType.EOF) == 1
    assert [token.type for token in first] == [token.type for token in second]
