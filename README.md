# 🦅 Falcon — A Lightweight Modern Programming Language (Prototype)

Falcon is a **fast, expressive, and beginner-friendly programming language** inspired by the speed and precision of a falcon.
This is the **prototype implementation**, written in Python, featuring:

* A tokenizer (lexer)
* A recursive-descent parser
* An AST-based interpreter
* First-class functions & closures
* Basic built-in functions
* A REPL for interactive coding

Falcon aims to be a **simple, readable scripting language** that evolves into a powerful modern tool with async abilities, modularity, and a future bytecode VM.

---

## ✨ Features

* **Clean, modern syntax**
* **`let` bindings** and simple variable scoping
* **Functions & closures**
* **REPL with history**
* **Built-ins** like `print()`
* **Easy to extend** (written in Python)
* Ready for future features like:

  * async/await
  * modules
  * collections
  * bytecode VM

---

## 📦 Installation (Development Setup)

Clone the repo:

```bash
git clone https://github.com/yourname/falcon
cd falcon
```

Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate     # Windows: .venv\Scripts\activate
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

Example session:

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

Sample output:

```
Hello, Falcon!
```

---

## 📂 Project Structure

```
falcon/
├── README.md
├── CHARTER.md
├── LICENSE
│
├── src/
│   ├── falcon/
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
fn makeAdder(x) {
    return fn(y) { x + y }
}
let add2 = makeAdder(2)
print(add2(5))
```

---

## 🛣 Roadmap

Planned features:

* [ ] Arrays & maps
* [ ] Module system (`import`)
* [ ] Pattern matching
* [ ] Async/await
* [ ] Bytecode compiler + VM
* [ ] Formatter (`falcon fmt`)
* [ ] LSP server (editor support)

---

## 🤝 Contributing

Falcon is in early prototype stage — contributions are welcome!
You can help with:

* Improving the lexer / parser
* Adding more built-ins
* Designing the syntax
* Writing documentation
* Building the VM or formatter

---

## 📜 License

MIT License — free to use and modify.

---

