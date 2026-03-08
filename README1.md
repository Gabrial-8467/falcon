<p align="center">
<img src="assets\vyomm.png" alt="vyom Logo" width="500" height="300">
</p>

---

# Vyom — A Modern Lightweight Programming Language  
**Expressive. Hackable. Built for experiments and real projects.**

Vyom is a **modern, production-ready programming language** designed to be:

- 🧠 **Easy to learn** (clean syntax, predictable semantics)  
- ⚡ **hybrid Compiler + VM + Interpreter** execution model  
- 🧱 **Modular & extensible** (clean compiler architecture)  
- 🦾 **Capable** (closures, loops, functions, expressions, built-ins)

This repository contains the complete Vyom implementation, including:

- **Lexer** - Tokenizes Vyom source code
- **Parser → AST** - Builds abstract syntax tree from tokens  
- **Bytecode Compiler** - Compiles AST to optimized bytecode
- **Stack-based Virtual Machine** - Executes bytecode efficiently
- **Hybrid Interpreter** - Handles dynamic features and closures
- **REPL** - Interactive development environment
- **Built-in functions** - Core runtime library (including `show`, `console.log`, regex functions)
- **Sample `.vyom` programs** - Comprehensive examples  

Vyom is actively developed as a **production-grade scripting language** with async, optimized bytecode, and an ahead-of-time compiler.

## Easy syntax

Vyom supports an easy custom style used across current examples:

```vyom
set count = 0

fn add(a: int, b: int) => int {
    give a + b
}

when count == 0 {
    say "start"
}

loop count < 3 {
    say add(count, 2)
    count = count + 1
}
```

Keyword aliases:
- `fn`/`def` = `function`
- `give` = `return`
- `when` = `if`
- `say expr` = `show(expr)`
- `set name = value` = easy variable declaration
- `loop condition { ... }` = while-style loop

---

# ✨ Highlights (v1.0.0)

### ✔ Modern JavaScript-like Syntax  
```vyom
// Variable declarations with =
set x = 10;
set y = 20;  // set works as an alias for set
const z = 30;  // Constants

// Functions with clean syntax
fn add(a, b) { give a + b; }
show(add(x, 20));

// Comments: // line comments and /* block comments */
```

### ✔ First-Class Closures & Lexical Scoping  
```vyom
fn makeCounter(start) {
    set count = start;
    give fn() {
        count = count + 1;
        give count;
    };
}

set next = makeCounter(0);
show(next());  // 1
show(next());  // 2
show(next());  // 3
```

### ✔ Rich Collection Types & Member Access
```vyom
// List (dynamic array)
set lst = [1, 2, 3];
// Tuple (immutable)
set tpl = (1, 2, 3);
// Dictionary / Object
set obj = { name: "Vyom", version: 0.3 };
// Set
set s = set{1, 2, 3};
// Array (fixed size)
set arr = array[5];

// Subscript and member access
show(lst[0]);        // 1
show(obj.name);      // "Vyom"
show(obj["version"]); // 0.3
```

### ✔ Comparison Operations
```vyom
// Equality operators
set a = 10;
set b = 20;

show(a == b);   // false (equal to)
show(a != b);   // true  (not equal to)

// Relational operators
show(a < b);    // true  (less than)
show(a <= b);   // true  (less than or equal to)
show(a > b);    // false (greater than)
show(a >= b);   // false (greater than or equal to)

// In conditional statements
when (a < b) {
    show("a is less than b");
} else when (a > b) {
    show("a is greater than b");
} else {
    show("a equals b");
}

// In pattern matching guards
fn classify_number(n) {
    give match n {
        case x if x < 0: "negative";
        case x if x == 0: "zero";
        case x if x > 0: "positive";
    };
}
```

### ✔ High-Performance Compiler Pipeline
- **Bytecode caching** for unchanged source files avoids repeated lex/parse/compile work
- **Peephole optimizer** removes no-op instruction sequences (e.g., `LOAD_CONST None ; POP`)
- **Integer-based opcodes** for faster VM execution
- **Ready for parallel compilation** extensions

### ✔ Advanced Control Flow
```vyom
// Traditional for-loop with step
for set i = 1 to 10 step 2 {
    show("Count:", i);
}

// Infinite loops with break/return
loop {
    show("Running...");
    when (some_condition) { break; }
}

// While loops
set x = 0;
while (x < 5) {
    show(x);
    x = x + 1;
}
```

### ✔ Hybrid Execution Model  
Vyom runs code through a sophisticated dual-path system:

1. **Compiler → Optimized Bytecode** (fast path for simple code)
2. **VM executes bytecode** (stack-based, efficient execution)
3. **Automatic interpreter fallback** for closures and dynamic features requiring runtime semantics

This gives you the **speed of compiled bytecode** with the **flexibility of interpretation**.

---

# 📦 Installation

Clone:

```bash
git clone https://github.com/Gabrial-8467/vyom.git
cd vyom
```

Set up environment:

```bash
python -m venv myenv
myenv\Scripts\activate  # Windows
# or
source myenv/bin/activate
```

Install dependencies (optional):

```bash
pip install -r requirements.txt
```

---
# ▶ Install Vyom

```bash
pip install -e .
```

# ▶ Running the REPL

```bash
python -m vyom.repl
```

Example:

```bash
Vyom REPL — v1.0.0  
vyom> set x = 5;
vyom> x * 2
10
vyom> fn greet(name) { show("Hello, " + name + "!"); }
vyom> greet("Vyom")
Hello, Vyom!
vyom> .quit
```

---

# ▶ Running a Vyom Program

```bash
python -m vyom.runner examples/hello.vyom
```

Or using the package entry point:

```bash
vyom examples/hello.vyom
```

VM output example:

```
Compiled module: examples/hello.vyom
[VM] Running...
Hello, Vyom!
```

---

# 🎨 Passive Built-in Formatter

Vyom includes a **passive AST-based formatter** that automatically normalizes code structure during execution. No manual commands required.

## How It Works

The formatter runs automatically in the execution pipeline:
```
source code → lexer → parser → AST → formatter normalization → interpreter/compiler
```

## Features

- **Automatic**: Runs on every execution without user intervention
- **Memory-only**: Never modifies source files on disk
- **Deterministic**: Same AST always produces the same normalized structure
- **Graceful**: Formatting failures don't break execution

## Formatting Rules

- **4-space indentation** (configurable)
- **K&R brace style** - opening braces on same line
- **Operator spacing** - proper spacing around `+`, `-`, `*`, `/`, etc.
- **Function formatting** - consistent parameter and body formatting
- **Collection formatting** - proper list, tuple, dictionary formatting

## Example Transformation

Input code with inconsistent formatting:
```vyom
fn add(a,b){give a+b}
set x=5
set y=10
show(add(x,y))
```

Gets automatically normalized during execution:
```vyom
fn add(a, b) {
    give a + b
}

set x = 5
set y = 10
show(add(x, y))
```

## Integration

- **Runner**: Automatically formats when running `.vyom` files
- **REPL**: Formats each input before interpretation
- **Zero configuration**: Works out of the box

The formatter ensures consistent code structure across all Vyom programs while maintaining full backward compatibility.

---

# 📂 Project Architecture  

```
vyom/
├── README.md                 # Main documentation and getting started guide
├── CHARTER.md               # Language design principles and goals
├── LICENSE                  # Apache License 2.0
├── pyproject.toml           # Python package configuration
├── requirements.txt          # Development dependencies
│
├── src/                     # Source code directory
│   ├── vyom/               # Main language package
│   │   ├── __init__.py      # Package initialization and entry points
│   │   ├── main.py          # CLI interface
│   │   ├── lexer.py         # Tokenizer: converts source text to tokens
│   │   ├── tokens.py        # Token types and Token class definitions
│   │   ├── parser.py        # Parser: builds AST from token stream
│   │   ├── ast_nodes.py     # AST node classes for language constructs
│   │   ├── precedence.py    # Operator precedence table for parsing
│   │   ├── vm.py            # Virtual Machine: executes bytecode
│   │   ├── interpreter.py   # AST interpreter: handles dynamic features
│   │   ├── env.py          # Environment: variable scopes and bindings
│   │   ├── builtins.py      # Built-in functions and runtime utilities
│   │   ├── compiler.py      # Compiler: converts AST to bytecode
│   │   ├── formatter/        # Passive built-in formatter
│   │   │   ├── __init__.py  # Package exports
│   │   │   ├── formatter.py  # AST visitor for normalization
│   │   │   ├── printer.py    # Structured output generation
│   │   │   └── rules.py     # Formatting rules configuration
│   │   ├── repl.py          # REPL: interactive development environment
│   │   ├── runner.py        # File runner: executes .vyom programs
│   │   ├── type_checker.py # Type system and runtime type checking
│   │   └── utils/          # Utility modules
│   │       ├── __init__.py
│   │       ├── errors.py      # Custom exception classes
│   │       ├── file_loader.py # File I/O utilities
│   │       └── text_helpers.py # Text processing helpers
│   └── tests/               # Test suite
│       ├── test_lexer.py      # Lexer unit tests
│       ├── test_parser.py     # Parser unit tests
│       ├── test_interpreter.py # Interpreter unit tests
│       └── test_examples.py   # Integration tests for examples
│
├── examples/                # Example programs demonstrating language features
│   ├── hello.vyom           # Simple Hello World program
│   ├── easy_custom.vyom     # Super easy custom syntax demo
│   ├── variables.vyom       # Variable declarations and types
│   ├── type_annotations.vyom # Language-level type annotations
│   ├── functions.vyom       # Function types and patterns
│   ├── operators.vyom      # Arithmetic, comparison, logical operations
│   ├── collections.vyom     # Lists, tuples, dictionaries, sets, arrays
│   ├── control_flow.vyom    # if/else, loops, break statements
│   ├── factorial.vyom       # Recursion example
│   ├── closure.vyom         # Closure demonstration
│   ├── loop.vyom           # Loop constructs
│   ├── pattern_matching.vyom # Advanced pattern matching examples
│   ├── match_guards.vyom    # Pattern matching with guards and dict destructuring
│   ├── error_handling.vyom  # Custom try/catch/throw error handling
│   └── async_stub.vyom      # Promise API (synchronous stub)
│
├── assets/                 # Project assets (logos, images)
├── tools/                  # Development and utility tools
│   └── run_example.py   # Script to run example programs
└── myenv/                  # Virtual environment (gitignored)
```

---

# 📘 Example Programs

### **hello.vyom** - Simple Hello World
```vyom
// Basic "Hello, World!" program
show("Hello, Vyom!");

// Simple function
fn greet(name) {
    give "Hello, " + name + "!";
}

show(greet("World"));
```

### **easy_custom.vyom** - Super Easy Custom Syntax
```vyom
set count = 0

fn add(a: int, b: int) => int {
    give a + b
}

when count == 0 {
    say "start"
}

loop count < 3 {
    say add(count, 2)
    count = count + 1
}
```

### **variables.vyom** - Variable Declarations
```vyom
// Easy declarations
set x = 10
set y = 20
show("x =", x)
show("y =", y)

// Constant declarations with =
const pi = 3.14159;
const name = "Vyom";
show("const pi =", pi);
show("const name =", name);

// Variable reassignment
x = x + 5;
show("x updated to:", x);
```

### **type_annotations.vyom** - Language-level Type Annotations
```vyom
set count: int = 3;
set title: string = "Vyom";
const enabled: bool = true;

fn add(a: int, b: int): int {
    give a + b;
}

fn banner(name: string): string {
    give "Hello, " + name;
}

show(add(count, 9));
show(banner(title));
show(enabled);
```

### **functions.vyom** - Function Types & Patterns
```vyom
// Function declaration
fn add(a, b) {
    give a + b
}

// Function with multiple parameters
fn greet(name, age) {
    give "Hello, " + name + "! You are " + age + " years old."
}

// Function expression
set multiply = fn(x, y) {
    give x * y
}

// Higher-order function
fn applyOperation(a, b, operation) {
    give operation(a, b)
}

show("add(5, 3) =", add(5, 3));
show("multiply(4, 7) =", multiply(4, 7));
show("applyOperation(10, 5, add) =", applyOperation(10, 5, add));
```

### **operators.vyom** - Arithmetic, Comparison & Logical
```vyom
// Arithmetic operations
set a = 10
set b = 3

show("10 + 3 =", a + b);      // 13
show("10 - 3 =", a - b);      // 7
show("10 * 3 =", a * b);      // 30
show("10 / 3 =", a / b);      // 3.333...
show("10 % 3 =", a % b);      // 1

// Comparison operations
show("10 > 3 =", a > b);       // true
show("10 == 3 =", a == b);     // false
show("10 != 3 =", a != b);     // true

// Logical operations
show("true && false =", true && false);  // false
show("true || false =", true || false);  // true
show("!true =", !true);                 // false
```

### **collections.vyom** - Lists, Tuples, Dictionaries, Sets, Arrays
```vyom
// List (dynamic array)
set fruits = ["apple", "banana", "orange"];
show("List:", fruits);
show("First fruit:", fruits[0]);

// Tuple (immutable)
set coordinates = (10, 20, 30);
show("Tuple:", coordinates);
show("Second coordinate:", coordinates[1]);

// Dictionary / Object
set person = {
    name: "Vyom",
    age: 25,
    city: "New York"
};
show("Dictionary:", person);
show("Name:", person.name);
show("Age:", person["age"]);

// Set
set numbers = set{1, 2, 3, 4, 5};
show("Set:", numbers);

// Array (fixed size)
set scores = array[5];
scores[0] = 95;
scores[1] = 87;
show("Array:", scores);
```

### **control_flow.vyom** - If/Else, Loops, Break
```vyom
// If/else statements
fn checkNumber(n) {
    when (n > 0) {
        give "Positive";
    } else when (n < 0) {
        give "Negative";
    } else {
        give "Zero";
    }
}

show("checkNumber(5) =", checkNumber(5));
show("checkNumber(-3) =", checkNumber(-3));

// For loops with different steps
for set i = 1 to 5 step 1 {
    show("Count up:", i);
}

for set j = 10 to 1 step -2 {
    show("Count down by 2:", j);
}

// While loop
set counter = 0;
while (counter < 3) {
    show("While iteration:", counter);
    counter = counter + 1;
}

// Controlled infinite loop
fn limitedLoop(maxIterations) {
    set i = 0;
    loop {
        show("Loop iteration:", i);
        i = i + 1;
        when (i >= maxIterations) { break; }
    }
}
limitedLoop(3);
```

### **factorial.vyom** - Recursive Functions
```vyom
// Classic recursive factorial implementation
fn fact(n) {
    when (n == 0) { 
        give 1; 
    }
    give n * fact(n - 1);
}

// Test factorial function
show("5! =", fact(5));    // 120
show("6! =", fact(6));    // 720
show("10! =", fact(10));  // 3628800
```

### **closure.vyom** - Lexical Scoping & Closures
```vyom
// Simple counter closure
fn makeCounter() {
    set c = 0;
    fn inc() {
        c = c + 1;
        give c;
    }
    give inc;
}

// Create and use counter
set counter = makeCounter();
show("First call:", counter());  // 1
show("Second call:", counter()); // 2
show("Third call:", counter());  // 3

// Advanced closure with parameters
fn makeAdder(x) {
    give fn(y) {
        give x + y;
    };
}

set add5 = makeAdder(5);
set add10 = makeAdder(10);
show("5 + 3 =", add5(3));    // 8
show("10 + 7 =", add10(7));  // 17
```

### **loop.vyom** - Loop Constructs
```vyom
// For loop with step (Vyom style)
for set i = 1 to 5 step 1 {
    show("for-loop value:", i);
}

// For loop with custom step
for set j = 0 to 10 step 2 {
    show("even numbers:", j);
}

// While loop
set count = 0;
while (count < 3) {
    show("while loop:", count);
    count = count + 1;
}

// Infinite loop with break condition
fn controlledLoop() {
    set k = 0;
    loop {
        show("infinite loop:", k);
        k = k + 1;
        when (k >= 3) { break; }
    }
}
controlledLoop();
```

### **match_guards.vyom** - Pattern Matching with Guards
```vyom
fn classifyUser(user) {
    give match user {
        case { role: "admin", active: true, name: n }: "admin:" + n;
        case { role: "member", score: s } if s >= 90: "top-member";
        case { role: "member", score: s } if s >= 50: "member";
        case { role: "guest" }: "guest";
        case _: "unknown";
    };
}

show(classifyUser({ role: "admin", active: true, name: "Ava" }));
show(classifyUser({ role: "member", score: 95 }));
show(classifyUser({ role: "member", score: 64 }));
show(classifyUser({ role: "guest" }));
show(classifyUser({ foo: "bar" }));
```

### **error_handling.vyom** - Custom try/catch/throw
```vyom
fn safeDivide(a, b) {
    when (b == 0) {
        throw "division by zero";
    }
    give a / b;
}

try {
    show("10 / 2 =", safeDivide(10, 2));
    show("10 / 0 =", safeDivide(10, 0));
} catch (err) {
    show("Caught error:", err);
}
```

### **async_stub.vyom** - Promise API (Synchronous)
```vyom
show("Starting async stub...");

// Create and resolve a promise
set p = Promise.resolve(42);

// Chain promise operations
p.then(fn(x) {
    show("Promise resolved with:");
    show(x);
    give x * 2;
}).then(fn(doubled) {
    show("Doubled value:", doubled);
});

// Promise constructor
set p2 = Promise(fn(resolve, reject) {
    resolve("Async operation complete!");
});

p2.then(fn(msg) {
    show("Constructor promise:", msg);
});

show("Promise scheduled.");
```

---

# 🛣 Development Roadmap

### 🚀 Implemented Features  
- [x] **Core syntax** (variables, functions, control flow)
- [x] **Variable declarations** (set, const with =)
- [x] **Function types** (declarations, expressions, first-class functions)
- [x] **Collections** (lists, tuples, dictionaries, sets, arrays)
- [x] **Closures & lexical scoping** (full closure support)
- [x] **Control flow** (when/else, for, while, infinite loops)
- [x] **Member access & subscripting** (obj.property, obj[key], arr[index])
- [x] **Built-in functions** (show, console.log, Promise API)
- [x] **Comments** (// line comments and /* block comments */)
- [x] **Arithmetic operations** (+, -, *, /, %)
- [x] **Comparison operations** (==, !=, <, <=, >, >=)
- [x] **Logical operations** (&&, ||, !)
- [x] **Assignment operations** (=)
- [x] **Pattern matching** (native syntax with variable binding, guards, OR patterns)
- [x] **Language-level type annotations** (runtime-checked declarations, params, returns)
- [x] **Error handling** (try/catch/throw)

### 📋 Future Enhancements  
- [ ] **Async / await** (stub implemented)
- [ ] **Modules & imports**
- [ ] **Classes & objects**
- [ ] **Generators**  

### ⚙ Runtime Optimizations  
- [ ] Optimizing bytecode VM  
- [ ] JIT compilation (optional)  
- [ ] Debugger + stack traces  

### 🛠 Development Tooling  
- [x] **Passive built-in formatter** — AST-based code normalization (automatic, no CLI command needed)
- [ ] **Package manager** —  package management system
- [ ] LSP server for VS Code  
- [x] **Installer** — Windows .exe and installer implemented (.deb not yet implemented)  

---

# 🤝 Contributing

You can help by:

- Improving the parser / VM  
- Adding built-in functions  
- Expanding the compiler  
- Writing documentation  
- Testing examples  

PRs and issues are always welcome!

---

# 📜 License  
Released under **Apache License 2.0**.  
See `LICENSE` for details.

---

# Vyom — “Small language. Big possibilities.”
Vyom is built to grow — from a lightweight VM to a complete, scripting language.
