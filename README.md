# Thunder JavaScript Runtime

A small JavaScript interpreter built from scratch in Python for Thunder Hackathon 2.

## Quick Start

### Installation

Use Python 3 and install the test dependency:

```powershell
python -m pip install -r requirements.txt
```

An optional virtual environment keeps dependencies local:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Run a JavaScript File

Run a file through the root entry point:

```powershell
python main.py examples\01_odd_even.js
```

Or with a virtual environment:

```powershell
.\.venv\Scripts\python.exe main.py examples\01_odd_even.js
```

### Run Through Stdin

PowerShell:

```powershell
Get-Content examples\01_odd_even.js | python main.py
```

Shells that support input redirection:

```sh
python main.py < examples/01_odd_even.js
```

### Run the Tests

Run the full pytest suite:

```powershell
python -m pytest -q
```

The suite includes lexer, parser, interpreter, CLI, public-example, and
adversarial hidden-test-style coverage. The latest verified run completed with 517 tests passing.

## Project Overview

Thunder JavaScript Runtime reads JavaScript source code, tokenizes it, parses it
into an AST, and interprets that AST directly in Python. It is intended as a
clear, beginner-readable runtime for hackathon programs and tests, not as a
production JavaScript engine.

Program output goes to stdout. Syntax and runtime errors are reported to stderr.

Supports an educational subset of JavaScript covering the supplied tests and related language features. It is not a complete ECMAScript implementation.

### Hackathon Context

This project was built for Thunder Hackathon 2, where the goal is to implement a
small JavaScript interpreter from scratch. The implementation focuses on the
public examples, the supplied tests, and adjacent hidden-test-style language
features while keeping each milestone scoped and understandable.

## Architecture

```text
JavaScript source -> Lexer -> Parser -> AST -> Interpreter -> stdout
```

The codebase keeps these pieces separated:

- `tokens.py` and `lexer.py`: scan source text into tokens.
- `ast_nodes.py`: defines the program, statement, and expression node classes.
- `parser.py`: turns tokens into AST nodes and reports syntax errors.
- `environment.py`: stores lexical scopes, variables, and const bindings.
- `values.py`: provides JavaScript-like values, output formatting, and coercion.
- `js_builtins.py`: defines built-in objects and functions.
- `interpreter.py`: walks the AST and executes programs.
- `cli.py` and `main.py`: provide command-line execution.

### Repository Structure

```text
thunder-js-runtime/
  main.py
  README.md
  PLAN.md
  AGENTS.md
  requirements.txt
  thunder_js/
    __init__.py
    ast_nodes.py
    cli.py
    environment.py
    interpreter.py
    js_builtins.py
    lexer.py
    parser.py
    tokens.py
    values.py
  examples/
    01_odd_even.js
    02_triangle.js
    03_palindrome.js
    04_array_reverse.js
    05_armstrong.js
    ...
  tests/
    test_lexer.py
    test_parser.py
    test_interpreter_*.py
    test_hidden_adversarial.py
```

## Supported Features

- Literals and globals: numbers including decimal, hexadecimal, binary, octal,
  and scientific notation forms, strings, template literals, booleans, `null`,
  `undefined`, `NaN`, `Infinity`, arrays, objects, and minimal `Date` values.
- Expressions: grouping, unary operators including `typeof`, arithmetic,
  exponentiation, comparisons, equality, logical operators, ternary expressions,
  nullish coalescing with `??`, optional chaining with `?.`,
  assignments, compound assignments including `%=` and `**=`, prefix/postfix
  `++` and `--` on variables, properties, and indexes, member access, computed
  access, calls, spread arguments, and `new Date(...)`.
- Statements: expression statements, `let`, `const`, `var`, blocks, `if`/`else`,
  `switch`/`case`/`default`, `for`, `for...of`, `for...in`, `while`,
  `do...while`, `break`, `continue`, function declarations, and `return`.
- Declarations: identifier bindings plus array and object destructuring
  patterns in `let`, `const`, and `var` declarations. Destructuring supports
  skipped array entries, nested patterns, defaults, and array/object rest
  patterns.
- Scoping: lexical environments, parent-scope lookup, variable shadowing,
  function-local scope, function/global-scoped `var`, closure capture,
  function-declaration hoisting, simple `var` name hoisting to `undefined`, and
  const reassignment protection, including per-iteration `let` bindings for
  closures in classic `for` loops.
- Functions: declarations, expressions, arrow functions, shorthand object
  methods, parameters, rest parameters, default parameters, destructured
  parameters, recursion, closures, callbacks, returned functions, missing
  arguments as `undefined`, and limited method-call `this` binding for normal
  functions called through object member access.
- Arrays: literals, indexing, length, indexed assignment, array spread,
  `push`, `pop`, `shift`, `unshift`, `slice`, `splice`, `concat`, `includes`,
  `indexOf`, `reverse`, `join`, default `sort`, `map`, `filter`, `reduce`,
  `find`, `some`, `every`, `forEach`, and `Array.isArray`.
- Strings: length, `split`, `replace`, `replaceAll`, `substring`, `slice`,
  `charAt`, `charCodeAt`, `repeat`, `padStart`, `padEnd`, `trim`, `trimStart`,
  `trimEnd`, `toUpperCase`, `toLowerCase`, `includes`, `startsWith`, `endsWith`,
  `indexOf`, `at`, and `concat`.
- Objects: object literals, empty objects, identifier keys, string keys,
  numeric keys converted to strings, nested objects, property reads, computed
  reads, shorthand properties, shorthand methods, property assignment, adding
  properties, shallow object spread, `Object.keys`, `Object.values`,
  `Object.entries`, and missing properties as `undefined`. Normal functions
  stored on objects receive the immediate receiver as `this` when called as
  `object.method()` or `object["method"]()`.

Object spread copies properties into a new object and is shallow:

```js
let base = { name: "Pragun", age: 20 };
let updated = { ...base, age: 21 };
```

- Built-ins: `console.log`, `isNaN`, `isFinite`, `Math.PI`, `Math.E`,
  `Math.LN2`, `Math.abs`, `Math.ceil`, `Math.floor`, `Math.round`, `Math.max`,
  `Math.min`, `Math.pow`, `Math.sqrt`, `Math.log`, `Math.log2`, `Math.log10`,
  `Math.sign`, `Math.hypot`, `Math.cbrt`, `Math.trunc`, `Math.random`,
  `Number`, `String`, `Boolean`, `parseInt`, `parseFloat`, `JSON.stringify`,
  `JSON.parse`, and `Date.now`.
- Output: direct `console.log` uses simple inspect-style formatting for arrays
  and objects while string coercion paths still use JavaScript-like conversion.
- Minimal Date support: `new Date()`, `new Date(milliseconds)`, `getTime`,
  `getFullYear`, `getMonth`, `getDate`, `getDay`, `getHours`, `getMinutes`,
  `getSeconds`, and `toISOString`.

## Examples

The first five examples correspond to the core public-test milestones:

| File | Demonstrates |
| --- | --- |
| `examples/01_odd_even.js` | variables, arithmetic, `if`/`else`, string concatenation |
| `examples/02_triangle.js` | `for` loops, nested loops, updates, compound assignment |
| `examples/03_palindrome.js` | string methods, array values from `split`, chaining |
| `examples/04_array_reverse.js` | array literals, spread cloning, `reverse`, `join` |
| `examples/05_armstrong.js` | functions, `while`, `return`, recursion-related runtime support, `Math.floor` |

Additional examples show later supported features:

- `examples/06_objects.js`
- `examples/07_first_class_functions.js`
- `examples/08_array_callbacks.js`
- `examples/09_switch_do_while.js`
- `examples/10_spread_rest.js`
- `examples/11_math_conversions.js`
- `examples/12_date.js`
- `examples/13_complex_edge_test.js`
- `examples/14_coercion_edges.js`
- `examples/15_object_spread.js`
- `examples/16_globals_math_constants.js`
- `examples/17_assignment_updates.js`
- `examples/18_ternary_typeof_defaults.js`
- `examples/19_iteration_helpers.js`
- `examples/20_template_json.js`
- `examples/21_loop_closure.js`
- `examples/22_final_audit_fixes.js`
- `examples/23_var_destructuring.js`
- `examples/24_destructuring_edges.js`
- `examples/25_this_optional_nullish.js`
- `examples/26_final_low_risk_features.js`
- `examples/27_six_correctness_fixes.js`

## Safety, Compliance, and AI Disclosure

### Runtime Safety Limits

The interpreter includes runtime guardrails for programs that do not terminate:

- Execution-step limit: the default interpreter step limit is `100_000`.
- Recursion/call limit: the default function call-depth limit is `100`.

When these limits are exceeded, the runtime raises a controlled interpreter
error instead of allowing an unbounded Python traceback.

### What Is Not Used

This project does not use any existing JavaScript engine or runtime.

Specifically, it does not use Node.js, QuickJS, V8, js2py, Python `eval()`,
Python `exec()`, subprocess execution of JavaScript, JavaScript-to-Python
transpilation, hardcoded recognition of public tests, or runtime network/API/LLM
calls.

### AI Assistance Disclosure

AI assistance was used during development for planning, implementation,
testing, review, and documentation. The project remains a from-scratch Python
interpreter and does not call an AI model at runtime.

## Limitations

This runtime intentionally supports only an educational subset of JavaScript.
Notable missing or incomplete areas include:

- No full ECMAScript compatibility, including try/catch, throw, classes,
  prototypes, modules, imports, async functions, generators, promises, bitwise
  operators, regex literals, or the full standard library.
- `this` support is intentionally limited: only normal functions called as
  object methods receive dynamic `this`. Detached method calls use `undefined`
  as `this`; `bind`, `call`, `apply`, constructor-style `this`, and complete
  lexical arrow-function `this` semantics are not implemented.
- Destructuring is supported in declarations and function or arrow parameters,
  but destructuring assignment expressions such as `[a, b] = [b, a]` are not
  supported.
- Optional chaining is read/call-only; optional assignment targets such as
  `object?.property = value` are rejected.
- `var` implements function/global scoping and simple declaration-name hoisting,
  but it does not model every ECMAScript global-object or browser Annex B
  scoping edge case.
- Date support is intentionally minimal and does not attempt full JavaScript
  date parsing or timezone behavior.
- Object output is basic; full JSON-style formatting is not a goal.
- Array and string methods are implemented only to the level needed by the
  supported subset.
- Error messages are designed to be clear, but they are not identical to browser
  or Node.js errors.