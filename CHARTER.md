# 🦅 vyom Language Charter

vyom is a lightweight, expressive programming language designed for clarity, speed, and ease of implementation.
This charter defines the **core goals**, **design principles**, and **scope** of the vyom language.

vyom begins as a **simple interpreter implemented in Python**, with the goal of being a modern scripting language with async capabilities and a bytecode VM.

---

## 🎯 Mission Statement

vyom aims to be a **clean, readable, lightweight scripting language** that is easy to learn, fast to write, and simple to implement.
It focuses on:

* Clear syntax
* Lightweight semantics
* First-class functions
* Optional advanced features as the language grows

vyom should feel intuitive to beginners yet flexible enough for advanced developers.

---

## 🧭 Core Goals

1. **Readable syntax** inspired by modern scripting languages.
2. **Small, understandable implementation** suitable for learning and experimentation.
3. **First-class functions & closures** as core building blocks.
4. **Minimal but useful standard library**, starting with `print`, basic I/O stubs, and booleans.
5. **Interactive REPL** for fast feedback and prototyping.
6. **Deterministic, easy-to-extend interpreter** written in Python.

The language's purpose is **clarity** and **correctness**.

---

## Design Principles

vyom’s design is guided by these principles:

### ✔ Simplicity

Avoid syntax noise, hidden behavior, or unnecessary complexity.

### ✔ Consistency

Language constructs behave predictably across contexts.

### ✔ Explicitness

Developers should understand what code does at a glance.

### ✔ Composability

Functions, expressions, and blocks should compose naturally.

### ✔ Learnability

New programmers should be able to read and write vyom comfortably.

---

## 📦 Feature Scope

### Syntax & Semantics

* `let` variable declarations
* Function definitions (`fn`)
* Closures
* Return statements
* If expressions
* Binary and unary operators
* Basic literals: numbers, strings, booleans, `null`

### Interpreter

* AST-based evaluator
* Lexical scoping
* First-class functions
* Built-in functions (`print`)

### Tools

* REPL with multiline support
* Script runner (`vyom run file.vyom`)
* Example programs

---

## 🚫 Out-of-Scope

These features are **planned but not included yet**:

* Async/await
* Type system
* Modules & imports
* Collections (arrays, maps)
* Pattern matching
* Classes / objects
* Bytecode compiler & VM
* Optimizations / JIT

These will be added incrementally as the language evolves.

---

## 🧪 Example vyom Programs

### Hello World

```
print("Hello, vyom!")
```

### Functions & Closures

```
fn makeAdder(x) {
    fn(y) { x + y }
}

let add2 = makeAdder(2)
print(add2(5))
```

### Factorial

```
fn fact(n) {
    if n == 0 { return 1 }
    n * fact(n - 1)
}

print(fact(6))
```

---

## 📍 Long-Term Vision

vyom aims to mature into a full-featured scripting language with:

* Rich standard library
* Async/await & concurrency primitives
* Pattern matching
* Modules & package system
* Bytecode VM with optimizations
* Developer tools: formatter, LSP server, REPL debugger

The implementation lays the foundation—every feature will grow from this base.

---