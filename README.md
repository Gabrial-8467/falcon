🦅 Falcon — A Lightweight Modern Programming Language (Prototype)

Falcon is a beginner-friendly, expressive programming language with a syntax that aims to be unique, clean, and easy to learn — without copying Python or JavaScript.

This repository contains the prototype interpreter, fully implemented in Python, featuring:

A custom lexer and parser

AST generation

An interpreter with lexical scoping

Built-in functions and I/O

REPL shell

Example .fn programs

Extensible architecture for future VM & bytecode backend

Falcon is evolving toward a modern scripting environment with async, modules, and a future bytecode VM — but this prototype focuses on core semantics and experimentation.

✨ Features (Prototype v0.2)

✔ Unique Falcon syntax (var, const, :=, :: method calls)
✔ First-class functions and closures
✔ Assignment expressions
✔ Block scoping with shadowing
✔ Built-in functions (print, len, range, console::log, file I/O, etc.)
✔ REPL with multiline parsing & history
✔ Expression & statement execution
✔ Extensible design for language research

⚡ Example Falcon code
var x := 10;
function add(a, b) {
    return a + b;
}

print(add(x, 20));

🔁 New Loop Syntax (Falcon-style)
for var i := 1 to 5 step 1 {
    print(i);
}

loop {
    print("infinite loop running...");
}

🧸 Closures
function makeCounter() {
    var c := 0;
    return function() {
        c = c + 1;
        return c;
    };
}

var next := makeCounter();
print(next()); # 1
print(next()); # 2

📦 Clone the Repository
git clone https://github.com/Gabrial-8467/falcon.git
cd falcon

🛠 Development Setup

Create a virtual environment:

python -m venv .venv


Activate it:

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate


Install development tools:

pip install -r requirements.txt

▶ Running the REPL
python -m falcon.repl


Example:

Falcon REPL — v0.2
falcon> var x := 5;
falcon> x * 2;
10
falcon> exit;

▶ Running a Falcon Program
python -m falcon.main run examples/hello.fn


Output:

Hello, Falcon!

📂 Project Structure
falcon/
├── README.md
├── CHARTER.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
│
├── src/
│   ├── falcon/                       
│   │   ├── __init__.py
│   │   ├── main.py             # CLI entry
│   │   │
│   │   ├── lexer.py            # Falcon tokenizer
│   │   ├── tokens.py           # token types
│   │   │
│   │   ├── parser.py           # recursive-descent parser
│   │   ├── ast_nodes.py        # AST node classes
│   │   ├── precedence.py        # operator precedence
│   │   │
│   │   ├── interpreter.py       # runtime evaluator
│   │   ├── env.py               # lexical environment model
│   │   ├── builtins.py          # built-ins (print, range, Promise, etc.)
│   │   │
│   │   ├── repl.py              # interactive REPL
│   │   ├── runner.py            # run .fn scripts
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── errors.py
│   │       ├── file_loader.py
│   │       └── text_helpers.py
│   │
│   └── tests/
│       ├── test_lexer.py
│       ├── test_parser.py
│       ├── test_interpreter.py
│       └── test_examples.py
│
├── examples/
│   ├── hello.fn
│   ├── factorial.fn
│   ├── closure.fn
│   └── loops.fn
│
└── tools/
    └── run_example.py

📘 Example Programs
hello.fn
print("Hello, Falcon!");

factorial.fn
function fact(n) {
    if (n == 0) { return 1; }
    return n * fact(n - 1);
}
print(fact(6));

closure.fn
function makeAdder(x) {
    return function(y) { x + y };
}
var add2 := makeAdder(2);
print(add2(5));

🛣 Roadmap

Upcoming features:

 Arrays & maps

 Module system (import)

 Pattern matching

 Async/await engine

 Bytecode compiler & VM backend

 Formatter (falcon fmt)

 Official LSP server

 Native method syntax using ::

 Better error messages & diagnostics

Falcon is intentionally small right now — the goal is to evolve it into a modern, expressive scripting language.

🤝 Contributing

You can help improve Falcon by:

Enhancing the parser / interpreter

Extending built-ins

Designing syntax improvements

Writing documentation & examples

Prototyping the future VM

Pull requests and issues are welcome!

📜 License

Licensed under the Apache License 2.0.
See the LICENSE file for full details.