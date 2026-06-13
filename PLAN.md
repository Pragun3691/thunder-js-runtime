# Thunder JavaScript Runtime Plan

## Goal

Build a small JavaScript interpreter from scratch in Python for Thunder
Hackathon 2.

The required execution pipeline is:

```text
JavaScript source -> Lexer -> Parser -> AST -> Interpreter -> stdout
```

The project must not use Node.js, QuickJS, V8, js2py, any existing
JavaScript engine or runtime, subprocess to execute JavaScript, Python
`eval()`, Python `exec()`, JavaScript-to-Python transpilation, hardcoded
recognition of public tests, or network/LLM calls at runtime.

## Smallest Clean Architecture

Keep each concern in its own small module:

```text
main.py

thunder_js/
  __init__.py
  cli.py
  tokens.py
  lexer.py
  ast_nodes.py
  parser.py
  values.py
  environment.py
  js_builtins.py
  interpreter.py

examples/

tests/
  test_lexer.py
  test_parser.py
  test_interpreter_public.py
```

### Module Responsibilities

`tokens.py`

- Defines token types.
- Defines a simple `Token` data structure.
- Examples: numbers, strings, identifiers, keywords, operators, braces,
  parentheses, commas, semicolons, and end-of-file.

`lexer.py`

- Turns raw JavaScript source text into tokens.
- Handles whitespace, comments, literals, identifiers, keywords, punctuation,
  and operators.
- Reports syntax/lexing errors without printing debug output.

`ast_nodes.py`

- Defines beginner-friendly AST node classes, likely as dataclasses.
- Keeps syntax structure separate from parsing and execution.
- Examples: program, expression statement, literal, binary expression,
  variable declaration, identifier, call expression, member expression, block,
  if statement.

`parser.py`

- Turns tokens into AST nodes.
- Owns grammar rules and operator precedence.
- Reports syntax errors clearly.

`values.py`

- Defines JavaScript-like runtime values and coercion helpers.
- Includes helpers for truthiness, string conversion, number conversion,
  equality, and display formatting.
- Defines special values such as `undefined` and maybe `null`.

`environment.py`

- Stores variables.
- Supports nested scopes.
- Handles lookup, declaration, and assignment.

`js_builtins.py`

- Defines built-in methods and objects.
- Initial priority: `console.log`.
- Uses a `js_` prefix to avoid confusion with Python's own built-in module.

`interpreter.py`

- Walks the AST and executes it.
- Evaluates expressions.
- Runs statements.
- Uses environments, values, coercion helpers, and JavaScript built-ins.

`cli.py`

- Reads JavaScript source from a file.
- Runs the full pipeline.
- Writes program output to stdout.
- Writes syntax/runtime errors to stderr.

`main.py`

- Root-level entry point for the hackathon-friendly command:

```text
python main.py program.js
```

- Delegates to `thunder_js.cli` instead of holding interpreter logic itself.

`examples/`

- Holds small `.js` sample programs once implementation begins.
- Useful for manual checks and README examples.
- Should not contain implementation code.

`tests/`

- Contains pytest tests for each milestone.
- Covers lexer behavior, parser behavior, interpreter behavior, CLI behavior,
  public cases, and hidden-test-style edge cases.

## Public-Test Feature Mapping

The repository currently does not include the five public test cases. The
mapping below is the working point-targeting map from the approved plan. Once
the exact public cases are available, this table should be replaced with a
case-by-case mapping using the actual source snippets and expected output.

| Public case | Likely language features required | Runtime behavior required |
| --- | --- | --- |
| 1. Basic `console.log(...)` | identifiers, dot/member access, call expressions, parentheses, string or number literals, semicolons | built-in `console.log`, stdout formatting |
| 2. Arithmetic expressions | numeric literals, `+`, `-`, `*`, `/`, `%`, parentheses, precedence | numeric evaluation, number output formatting |
| 3. Variables | `let`, identifiers, initializers, expression statements, variable lookup | environment storage, reads from current/outer scope |
| 4. Conditionals and comparisons | `if`, `else`, blocks, comparison operators such as `===`, `!==`, `<`, `>`, `<=`, `>=` | truthiness, branch selection, block scope |
| 5. Loops or functions | likely `while`/`for` loops or function declarations/calls, blocks, returns if functions appear | repeated execution or user-defined calls, nested scope handling |

## Milestone Order

Implement one milestone at a time. Add tests with every milestone and run the
complete test suite after each change.

1. Project skeleton and importable package only.
2. CLI shape and error-routing tests, without interpreter behavior yet.
3. Tokens and lexer for literals, identifiers, keywords, punctuation, comments,
   and basic operators.
4. Parser for programs, expression statements, literals, member access, and
   call expressions.
5. Interpreter support for literals and `console.log`.
6. Arithmetic expressions with operator precedence.
7. Variables with `let` declarations and identifier lookup.
8. Comparisons, equality, booleans, and truthiness.
9. `if`/`else` and block scopes.
10. Loops if required by public tests.
11. Functions, returns, and closures only after simpler control flow is solid.

This order earns likely public-test points early by making `console.log`,
expressions, and variables work before attempting broader JavaScript behavior.

## Testing Strategy

Use pytest only.

Every feature should have tests at three levels where useful:

- Lexer tests: source text becomes the expected sequence of token types and
  literal values.
- Parser tests: token streams become the expected AST shape.
- Interpreter tests: JavaScript source produces expected stdout or expected
  stderr.

Recommended test groups:

- Public tests copied exactly once available.
- Small milestone tests, one behavior per test.
- Edge tests for whitespace, comments, missing semicolons, nested parentheses,
  nested blocks, bad syntax, and runtime errors.
- CLI tests that confirm stdout and stderr stay separate.

Do not print debugging information to stdout from the runtime or tests.

## Highest-Risk Areas

- JavaScript `+`: it can mean numeric addition or string concatenation.
- JavaScript truthiness: `0`, empty strings, booleans, `null`, and `undefined`
  need careful handling.
- `undefined` versus `null`.
- Exact `console.log` output formatting.
- Operator precedence and associativity.
- Block scope, especially with `let`.
- Runtime errors versus syntax errors.
- Keeping all errors on stderr.
- Avoiding accidental use of Python `eval()` or `exec()`.
- Hidden tests around whitespace, comments, semicolons, nested blocks, bad
  syntax, and variable lookup.
- Hidden tests that combine simple features, such as variables plus arithmetic
  inside `console.log`.

## Beginner-Friendly Explanations

### Lexer

A lexer reads the raw source code one character at a time and groups characters
into useful pieces. For example, it turns this:

```js
let x = 3;
```

into pieces like `let`, `x`, `=`, `3`, and `;`.

### Token

A token is one labeled piece of source code. It says what kind of thing was
found. For example, `3` might become a `NUMBER` token, while `x` might become
an `IDENTIFIER` token.

### Parser

A parser reads tokens and figures out the structure of the program. It knows
that `1 + 2 * 3` means `1 + (2 * 3)` because multiplication has higher
precedence than addition.

### AST

AST means abstract syntax tree. It is a tree-shaped version of the program.
The interpreter can walk this tree more easily than it can understand raw text.

### Environment

An environment is the place where variables are stored. If the program says:

```js
let score = 10;
```

the environment remembers that `score` currently means `10`.

### Scope

A scope is a layer of variables. A block or function can have its own scope.
When the interpreter needs a variable, it checks the current scope first, then
looks outward if needed.

### Interpreter

An interpreter walks the AST and performs the program's actions. It calculates
expressions, stores variables, chooses `if` branches, runs loops, calls
built-ins like `console.log`, and produces output.

## Initial File and Folder Structure

No implementation files should be created until implementation is explicitly
approved.

When implementation begins, create this structure:

```text
thunder-js-runtime/
  AGENTS.md
  README.md
  PLAN.md
  requirements.txt
  .gitignore
  main.py
  thunder_js/
    __init__.py
    cli.py
    tokens.py
    lexer.py
    ast_nodes.py
    parser.py
    values.py
    environment.py
    js_builtins.py
    interpreter.py
  examples/
  tests/
    test_lexer.py
    test_parser.py
    test_interpreter_public.py
```

Until then, `PLAN.md` is the only new file.
