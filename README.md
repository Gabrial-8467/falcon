# 🦅 Falcon — A Lightweight Modern Programming Language (Prototype)

Falcon is a **lightweight, expressive programming language** designed to be fast, readable, and developer-friendly.
This repository contains the **prototype interpreter**, fully implemented in Python, including:

* Lexer (tokenizer)
* Parser → AST
* Interpreter with lexical scoping
* Built-in functions
* REPL shell
* Example Falcon programs (`.fn` files)

Falcon aims to grow into a modern scripting language featuring async, modules, and a future bytecode VM — but this prototype focuses on the fundamentals.

---

## ✨ Features (Prototype v0.1)

* Clean, simple syntax inspired by modern languages
* First-class functions and closures
* `let` variable bindings
* Basic expression evaluation
* REPL with multiline support
* Built-in `print()`
* Easy to extend (designed for experimentation)

Example Falcon code:

```
let x = 10
fn add(a, b) { a + b }
print(add(x, 20))
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
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

Install optional dev tools (pytest, etc.):

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
Falcon v0.1 — REPL
falcon> let x = 5
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
falcon/
├── README.md
├── LICENSE (Apache-2.0)
├── CHARTER.md
│
├── src/
│   ├── falcon/
│   │   ├── __init__.py
│   │   ├── lexer.py
│   │   ├── tokens.py
│   │   ├── parser.py
│   │   ├── ast_nodes.py
│   │   ├── interpreter.py
│   │   ├── env.py
│   │   ├── builtins.py
│   │   ├── repl.py
│   │   └── runner.py
│   │
│   └── tests/
│       ├── test_lexer.py
│       ├── test_parser.py
│       └── test_interpreter.py
│
└── examples/
    ├── hello.fn
    ├── factorial.fn
    └── closure.fn
```

---

## 📘 Example Programs

**hello.fn**

```
print("Hello, Falcon!")
```

**factorial.fn**

```
fn fact(n) {
    if n == 0 { return 1 }
    return n * fact(n - 1)
}
print(fact(6))
```

**closure.fn**

```
fn makeAdder(x) { fn(y) { x + y } }
let add2 = makeAdder(2)
print(add2(5))
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
* [ ] LSP server for editor integration

This prototype is intentionally small — the next milestones will expand the language’s capabilities.

---

## 🤝 Contributing

Contributions are welcome! Areas you can help with:

* Improving the parser / AST
* Adding built-in functions
* Designing syntax extensions
* Writing docs & examples
* Building the VM or transpiler

Feel free to open issues or PRs in the repo.

---

## 📜 License

This project is licensed under the **Apache License 2.0**.
See the `LICENSE` file for details.

---

