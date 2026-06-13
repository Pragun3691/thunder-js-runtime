# Project Instructions

## Goal

Build a small JavaScript interpreter from scratch in Python for the
Thunder Hackathon.

## Strict Prohibitions

Do not use:

- Node.js
- QuickJS
- V8
- js2py
- any existing JavaScript engine or runtime
- subprocess to execute JavaScript
- Python eval()
- Python exec()
- transpiling JavaScript into Python and executing it
- hardcoded recognition of public test cases
- network APIs or LLM calls at runtime

## Architecture

Use this pipeline:

JavaScript source -> Lexer -> Parser -> AST -> Interpreter -> stdout

Keep these concerns separated:

- tokens and lexer
- AST nodes
- parser
- environment and scope
- JavaScript values and coercion helpers
- interpreter
- built-in methods
- CLI
- automated tests

## Development Rules

- Implement one milestone at a time.
- Preserve all previously passing tests.
- Add tests with every new feature.
- Run the complete test suite after changes.
- Do not print debugging information to stdout.
- Runtime and syntax errors must go to stderr.
- Keep the code understandable for a beginner.
- Avoid unnecessary packages.
- Prefer Python's standard library.
- Do not make large unrelated refactors without permission.