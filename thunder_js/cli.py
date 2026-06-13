"""Command-line entry point for the Thunder JavaScript runtime."""

import sys
from collections.abc import Sequence
from typing import TextIO

from thunder_js.interpreter import InterpreterError, run_source
from thunder_js.lexer import LexerError
from thunder_js.parser import ParserError


def main(
    argv: Sequence[str] | None = None,
    stdin: TextIO | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    input_stream = sys.stdin if stdin is None else stdin
    output_stream = sys.stdout if stdout is None else stdout
    error_stream = sys.stderr if stderr is None else stderr

    if len(args) > 1:
        print("Usage: python main.py [file.js]", file=error_stream)
        return 1

    try:
        source = _read_source(args, input_stream)
        run_source(source, output=lambda line: print(line, file=output_stream))
        return 0
    except (LexerError, ParserError, InterpreterError, OSError) as error:
        print(error, file=error_stream)
        return 1


def _read_source(args: list[str], stdin: TextIO) -> str:
    if args:
        with open(args[0], "r", encoding="utf-8") as source_file:
            return source_file.read()
    return stdin.read()
