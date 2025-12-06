🦅 Falcon — A Lightweight Modern Programming Language (Prototype)

Falcon is a lightweight, expressive programming language designed to be fast, readable, and beginner-friendly.
This repository contains the prototype interpreter, implemented in Python, including:

Lexer (tokenizer)

Parser → AST

Interpreter with lexical scoping and closures

Built-in functions and safe file I/O

REPL (multiline input)

Example Falcon programs (.fn files)

This prototype focuses on the language fundamentals and experimentation — future work will add async, modules and (maybe) a bytecode VM.

🚀 What’s new since v0.1

This prototype contains changes and new features beyond the very first minimal build:

New declaration operators and keywords:

var / const declarations (with is_const semantics)

New declaration operator: := (preferred) — e.g. var x := 10;

Backwards compatibility: let x = 10 and x = 5 assignments still work

New loop constructs:

Falcon for loop: for var i := START to END [step STEP] { ... } (inclusive to, step defaults to 1)

Infinite loop: loop { ... }

Member access & method style:

obj.prop and obj::method(...) (double-colon method shorthand supported)

Assignment expressions and better scoping:

x = 3 (assign), var x := 3 (declare), const y := 5 (immutable)

Builtins and runtime improvements:

print(...), console::log(...)

readFile(path) and writeFile(path, content) with safe sandboxing (cwd-only)

Promise stub (sync placeholder for future async)

len, range, typeOf, assert, exit

String coercion:

'a' + 1 → "a1" (Falcon coerces with a consistent toString behavior)

Lexer / parser / interpreter updates:

DECL token for :=, METHODCOLON for ::, tokens for for, loop, to, step, var, const

Tests & examples scaffold (pytest-friendly)

REPL + runner CLI improvements (multiline input, .load command)

If it feels like Falcon is growing a personality — good. It now speaks a bit of its own dialect. 😊

🔖 Example Falcon programs

hello.fn

print("Hello, Falcon!");


factorial.fn

fn fact(n) {
    if (n == 0) { return 1; }
    return n * fact(n - 1);
}
print(fact(6));


for loop demo (examples/for_demo.fn)

for var i := 0 to 5 {
    print(i);
}
# prints 0 1 2 3 4 5


infinite loop demo (examples/loop_demo.fn)

# Be careful running this one — it loops forever unless you return or error.
loop {
    print("tick");
    # ... use return/exit to break out in examples
}


console and file I/O

console::log("Starting...");
writeFile("sample.txt", "hello from falcon");
print(readFile("sample.txt"));

🧭 Syntax notes (quick summary)

Declarations

var name := expr; — mutable variable (scoped to containing block)

const name := expr; — immutable (reassign raises error)

Backwards support: let name = expr (treated like var)

Functions

Declaration:

function add(a, b) {
  return a + b;
}


Expression (anonymous / named expression):

function(a, b) { a + b }


Member / method access

obj.prop

obj::method(args) — sugar for calling member method

For loop (Falcon unique syntax)

for var i := START to END [step STEP] { ... }

to is inclusive (END included).

step optional, default 1. Use negative step to count down.

Infinite loop

loop { ... }

Semicolons ; are optional but allowed — recommended at line ends for clarity.

🛠 Development setup

Clone and create a virtual environment:

git clone https://github.com/Gabrial-8467/falcon.git
cd falcon
python -m venv .venv
# mac/linux
source .venv/bin/activate
# windows (PowerShell)
.venv\Scripts\Activate.ps1


Install development requirements:

pip install -r requirements.txt
# or: pip install -e .  # for editable install of the package

▶ Running the REPL

Start the interactive REPL:

python -m falcon.repl


Tip: on Windows the standard readline module is not available. If you hit ModuleNotFoundError: No module named 'readline' you can either:

install a readline fallback: pip install pyreadline (older) or pip install prompt_toolkit and we can wire that up later, or

use the runner on a file: python -m falcon.main run examples/hello.fn

The REPL supports multiline input, .load <file> to run a file, and help/quit.

▶ Running a Falcon program

Use the runner entry point:

# run by module
python -m falcon.main run examples/hello.fn

# or if you installed package editable
falcon run examples/hello.fn
# or start REPL
falcon -i


(Commands depend on your entry point implementation — adjust if you added CLI flags.)

✅ Tests

Run the pytest suite:

pip install -r requirements.txt   # ensure pytest is available
pytest -q


Add tests under src/falcon/tests/ — we've scaffolded test files: test_lexer.py, test_parser.py, test_interpreter.py, test_examples.py. New tests for for/loop/var/const are recommended.

🧩 Project structure
src/falcon/
├── lexer.py
├── tokens.py
├── parser.py
├── ast_nodes.py
├── precedence.py
├── interpreter.py
├── env.py
├── builtins.py
├── repl.py
└── runner.py
examples/
tests/
docs/
tools/

⚠️ Current limitations & TODOs

No break/continue yet — loops can only be exited via return or exception.

Promise is a synchronous stub — real async runtime not implemented.

Module system / imports not implemented.

No arrays/maps in the prototype yet (roadmap item).

REPL readline support on Windows can be improved (see notes above).

🛣 Roadmap

Planned improvements:

 Arrays & maps (list/dict literals)

 Module system (import)

 break / continue in loops

 Async/await engine & proper Promise support

 Bytecode compiler & VM

 Formatter (falcon fmt) and LSP server

🤝 Contributing

Contributions welcome! Good first issues:

Add break / continue semantics + tests

Implement arrays & map literals

Improve REPL input (use prompt_toolkit fallback on Windows)

Add more builtin functions and safe sandboxing options

Document the language syntax in docs/syntax.md

If you make changes, please add tests and examples.

📜 License

This project is licensed under the Apache License 2.0. See LICENSE for details.