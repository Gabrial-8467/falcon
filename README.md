```
███████╗ █████╗ ██╗      ██████╗ ██████╗ ███╗   ██╗
██╔════╝██╔══██╗██║     ██╔════╝██╔═══██╗████╗  ██║
█████╗  ███████║██║     ██║     ██║   ██║██╔██╗ ██║
██╔══╝  ██╔══██║██║     ██║     ██║   ██║██║╚██╗██║
██║     ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║
╚═╝     ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝
```
# 🦅 Falcon — A Lightweight Modern Programming Language (Prototype)

Falcon is a **lightweight, expressive programming language** designed to be fast, readable, and developer-friendly.
This repository contains the **prototype interpreter**, fully implemented in Python, including:

* Lexer (tokenizer)
* Parser → AST
* Interpreter with lexical scoping
* Built-in functions
* REPL shell
* Example Falcon programs (`.fn` files)

Falcon is evolving toward a modern scripting environment with async, modules, and a future bytecode VM — but this prototype focuses on core semantics and experimentation.

---

## ✨ Features (Prototype v0.2)

* Unique Falcon syntax (`var`, `const`, `:=`, `::` method calls)
* First-class functions and closures
* Assignment expressions
* Block scoping with shadowing
* Built-in functions (`print`, `len`, `range`, `console::log`, file I/O, etc.)
* REPL with multiline parsing & history
* Expression & statement execution
* Extensible design for language research

Example Falcon code:

```
var x := 10;
function add(a, b) { return a + b; }

print(add(x, 20));
```

---

## 🔁 New Loop Syntax (Falcon-style)

**For-loop:**

```
for var i := 1 to 5 step 1 {
    print(i);
}
```

**Infinite loop:**

```
loop {
    print("infinite loop running...");
}
```

---

## 🧸 Closures

```
function makeCounter() {
    var c := 0;
    return function() {
        c = c + 1;
        return c;
    };
}

var next := makeCounter();
print(next());  # 1
print(next());  # 2
```

---

## 📦 Clone the Repository

```bash
git clone https://github.com/Gabrial-8467/falcon.git
cd falcon
```

---

## 🛠 Development Setup

Create a virtual environment:

```bash
python -m venv .venv
```

Activate it:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate
```

Install optional dev tools:

```bash
pip install -r requirements.txt
```

---

## ▶ Running the REPL

```bash
python -m falcon.repl
```

Example:

```
Falcon v0.2 — REPL
falcon> var x := 5;
falcon> x * 2
10
falcon> :quit
```

---

## ▶ Running a Falcon Program

```bash
python -m falcon.main run examples/hello.fn
```

Output:

```
Hello, Falcon!
```

---

## 📂 Project Structure

```
falcon-prototype/
├── README.md
├── CHARTER.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
│
├── src/
│   ├── falcon/
│   │   ├── __init__.py
│   │   ├── main.py                  # CLI entry: runs files or repl
│   │   │
│   │   ├── lexer.py                 # tokenizer for .fn source
│   │   ├── tokens.py                # token constants / Token class
│   │   │
│   │   ├── parser.py                # recursive-descent parser -> AST
│   │   ├── ast_nodes.py             # AST node classes
│   │   ├── precedence.py            # operator precedence table
│   │   │── vm.py
│   │   ├── interpreter.py           # AST evaluator (env, execution)
│   │   ├── env.py                   # Environment / Scope system
│   │   ├── builtins.py              # builtins (print, len, range, etc.)
│   │   │── compiler.py
│   │   ├── repl.py                  # interactive REPL
│   │   ├── runner.py                # executes .fn files
│   │   │
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── errors.py
│   │       ├── file_loader.py
│   │       └── text_helpers.py
│   │
│   └── tests/                       # pytest suite
│       ├── test_lexer.py
│       ├── test_parser.py
│       ├── test_interpreter.py
│       ├── test_examples.py
│
├── examples/
│   ├── hello.fn
│   ├── factorial.fn
│   ├── closure.fn
│   └── async_stub.fn
│
├── docs/
│   ├── quickstart.md
│   ├── syntax.md
│   └── roadmap.md
│
└── tools/
    └── run_example.py
```

---

## 📘 Example Programs

**hello.fn**

```
print("Hello, Falcon!");
```

**factorial.fn**

```
function fact(n) {
    if (n == 0) { return 1; }
    return n * fact(n - 1);
}
print(fact(6));
```

**closure.fn**

```
function makeAdder(x) {
    return function(y) {
        return x + y;
    };
}
var add2 := makeAdder(2);
print(add2(5));
```

---

## 🛣 Roadmap

Planned improvements:

* [ ] Arrays & maps
* [ ] Module system (`import`)
* [ ] Pattern matching
* [ ] Async/await engine
* [ ] Bytecode compiler & VM
* [ ] Formatter (`falcon fmt`)
* [ ] LSP server for editor support

This prototype intentionally focuses on simplicity — the next milestones expand Falcon into a full scripting language.

---

## 🤝 Contributing

Contributions are welcome! You can help with:

* Improving the parser / AST
* Adding built-in functions
* Designing language features
* Writing docs & examples
* Working on the VM or transpiler

Open an issue or PR anytime.

---

## 📜 License

Licensed under the **Apache License 2.0**.
See the `LICENSE` file for details.

---


