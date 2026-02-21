```
███████╗ █████╗ ██╗      ██████╗ ██████╗ ███╗   ██╗
██╔════╝██╔══██╗██║     ██╔════╝██╔═══██╗████╗  ██║
█████╗  ███████║██║     ██║     ██║   ██║██╔██╗ ██║
██╔══╝  ██╔══██║██║     ██║     ██║   ██║██║╚██╗██║
██║     ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║
╚═╝     ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝
```

# 🦅 Falcon — A Modern Lightweight Programming Language  
**Expressive. Hackable. Built for experiments and real projects.**

Falcon is a **small, modern programming language** designed to be:

- 🧠 **Easy to learn** (clean syntax, predictable semantics)  
- ⚡ hybrid **VM + interpreter** execution model  
- 🧱 **Modular & extensible** (clean compiler architecture)  
- 🦾 **Capable** (closures, loops, functions, expressions, built-ins)

This repository contains the full Falcon **prototype implementation**, including:

- Lexer  
- Parser → AST  
- Hybrid Interpreter  
- Bytecode Compiler  
- Stack-based Virtual Machine  
- REPL  
- Built-in functions  
- Sample `.fn` programs  

Falcon is actively evolving toward a **production-grade scripting language** with modules, async, optimized bytecode, and an ahead-of-time compiler.

---

# ✨ Highlights (Prototype v0.3.0)

### ✔ Modern JavaScript-like Syntax  
```falcon
// Variable declarations with := and =
var x := 10;
let y := 20;  // `let` works as an alias for `var`
const z = 30;  // Constants

// Functions with clean syntax
function add(a, b) { return a + b; }
show(add(x, 20));

// Comments: // line comments and /* block comments */
```

### ✔ First-Class Closures & Lexical Scoping  
```falcon
function makeCounter(start) {
    var count := start;
    return function() {
        count = count + 1;
        return count;
    };
}

var next := makeCounter(0);
show(next());  // 1
show(next());  // 2
show(next());  // 3
```

### ✔ Rich Collection Types & Member Access
```falcon
// List (dynamic array)
var lst := [1, 2, 3];
// Tuple (immutable)
var tpl := (1, 2, 3);
// Dictionary / Object
var obj := { name: "Falcon", version: 0.3 };
// Set
var s := set{1, 2, 3};
// Array (fixed size)
var arr := array[5];

// Subscript and member access
show(lst[0]);        // 1
show(obj.name);      // "Falcon"
show(obj["version"]); // 0.3
```

### ✔ High-Performance Compiler Pipeline
- **Bytecode caching** for unchanged source files avoids repeated lex/parse/compile work
- **Peephole optimizer** removes no-op instruction sequences (e.g., `LOAD_CONST None ; POP`)
- **Integer-based opcodes** for faster VM execution
- **Ready for parallel compilation** extensions

### ✔ Advanced Control Flow
```falcon
// Traditional for-loop with step
for var i := 1 to 10 step 2 {
    show("Count:", i);
}

// Infinite loops with break/return
loop {
    show("Running...");
    if (some_condition) { break; }
}

// While loops
var x := 0;
while (x < 5) {
    show(x);
    x = x + 1;
}
```

### ✔ Hybrid Execution Model  
Falcon runs code through a sophisticated dual-path system:

1. **Compiler → Optimized Bytecode** (fast path for simple code)
2. **VM executes bytecode** (stack-based, efficient execution)
3. **Automatic interpreter fallback** for closures and dynamic features requiring runtime semantics

This gives you the **speed of compiled bytecode** with the **flexibility of interpretation**.

---

# 📦 Installation (Development Mode)

Clone:

```bash
git clone https://github.com/Gabrial-8467/falcon.git
cd falcon
```

Set up environment:

```bash
python -m venv myenv
myenv\Scripts\activate  # Windows
# or
source myenv/bin/activate
```

Install dev dependencies (optional):

```bash
pip install -r requirements.txt
```

---
# ▶ Installing Build Dependencies

```bash
pip install -e .
```

# ▶ Running the REPL

```bash
python -m falcon.repl
```

Example:

```bash
Falcon REPL — v0.3.0  
falcon> var x := 5;
falcon> x * 2
10
falcon> function greet(name) { show("Hello, " + name + "!"); }
falcon> greet("Falcon")
Hello, Falcon!
falcon> .quit
```

---

# ▶ Running a Falcon Program

```bash
python -m falcon.runner examples/hello.fn
```

VM output example:

```
Compiled module: examples/hello.fn
[VM] Running...
Hello, Falcon!
```

---

# 📂 Project Structure  
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
│   ├── hello.fn           # Simple Hello World
│   ├── variables.fn       # Variable declarations
│   ├── functions.fn       # Function types and patterns
│   ├── operators.fn      # Arithmetic, comparison, logical ops
│   ├── collections.fn     # Lists, tuples, dicts, sets, arrays
│   ├── control_flow.fn    # if/else, loops, break
│   ├── factorial.fn       # Recursion example
│   ├── closure.fn         # Closure demonstration
│   ├── loop.fn           # Loop constructs
│   └── async_stub.fn      # Async API stub
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

# 📘 Example Programs

### **hello.fn** - Simple Hello World
```falcon
// Basic "Hello, World!" program
show("Hello, Falcon!");

// Simple function
function greet(name) {
    return "Hello, " + name + "!";
}

show(greet("World"));
```

### **variables.fn** - Variable Declarations
```falcon
// Variable declarations with :=
var x := 10;
let y := 20;  // let works as an alias for var
show("x := 10 =", x);
show("y := 20 =", y);

// Constant declarations with =
const pi = 3.14159;
const name = "Falcon";
show("const pi =", pi);
show("const name =", name);

// Variable reassignment
x := x + 5;
show("x updated to:", x);
```

### **functions.fn** - Function Types & Patterns
```falcon
// Function declaration
function add(a, b) {
    return a + b;
}

// Function with multiple parameters
function greet(name, age) {
    return "Hello, " + name + "! You are " + age + " years old.";
}

// Function expression
var multiply := function(x, y) {
    return x * y;
};

// Higher-order function
function applyOperation(a, b, operation) {
    return operation(a, b);
}

show("add(5, 3) =", add(5, 3));
show("multiply(4, 7) =", multiply(4, 7));
show("applyOperation(10, 5, add) =", applyOperation(10, 5, add));
```

### **operators.fn** - Arithmetic, Comparison & Logical
```falcon
// Arithmetic operations
var a := 10;
var b := 3;

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

### **collections.fn** - Lists, Tuples, Dictionaries, Sets, Arrays
```falcon
// List (dynamic array)
var fruits := ["apple", "banana", "orange"];
show("List:", fruits);
show("First fruit:", fruits[0]);

// Tuple (immutable)
var coordinates := (10, 20, 30);
show("Tuple:", coordinates);
show("Second coordinate:", coordinates[1]);

// Dictionary / Object
var person := {
    name: "Alice",
    age: 25,
    city: "New York"
};
show("Dictionary:", person);
show("Name:", person.name);
show("Age:", person["age"]);

// Set
var numbers := set{1, 2, 3, 4, 5};
show("Set:", numbers);

// Array (fixed size)
var scores := array[5];
scores[0] := 95;
scores[1] := 87;
show("Array:", scores);
```

### **control_flow.fn** - If/Else, Loops, Break
```falcon
// If/else statements
function checkNumber(n) {
    if (n > 0) {
        return "Positive";
    } else if (n < 0) {
        return "Negative";
    } else {
        return "Zero";
    }
}

show("checkNumber(5) =", checkNumber(5));
show("checkNumber(-3) =", checkNumber(-3));

// For loops with different steps
for i := 1 to 5 step 1 {
    show("Count up:", i);
}

for j := 10 to 1 step -2 {
    show("Count down by 2:", j);
}

// While loop
var counter := 0;
while (counter < 3) {
    show("While iteration:", counter);
    counter := counter + 1;
}

// Controlled infinite loop
function limitedLoop(maxIterations) {
    var i := 0;
    loop {
        show("Loop iteration:", i);
        i := i + 1;
        if (i >= maxIterations) { break; }
    }
}
limitedLoop(3);
```

### **factorial.fn** - Recursive Functions
```falcon
// Classic recursive factorial implementation
function fact(n) {
    if (n == 0) { 
        return 1; 
    }
    return n * fact(n - 1);
}

// Test factorial function
show("5! =", fact(5));    // 120
show("6! =", fact(6));    // 720
show("10! =", fact(10));  // 3628800
```

### **closure.fn** - Lexical Scoping & Closures
```falcon
// Simple counter closure
function makeCounter() {
    var c = 0;
    function inc() {
        c = c + 1;
        return c;
    }
    return inc;
}

// Create and use counter
var counter = makeCounter();
show("First call:", counter());  // 1
show("Second call:", counter()); // 2
show("Third call:", counter());  // 3

// Advanced closure with parameters
function makeAdder(x) {
    return function(y) {
        return x + y;
    };
}

var add5 = makeAdder(5);
var add10 = makeAdder(10);
show("5 + 3 =", add5(3));    // 8
show("10 + 7 =", add10(7));  // 17
```

### **loop.fn** - Loop Constructs
```falcon
// For loop with step (Falcon style)
for i := 1 to 5 step 1 {
    show("for-loop value:", i);
}

// For loop with custom step
for j := 0 to 10 step 2 {
    show("even numbers:", j);
}

// While loop
var count = 0;
while (count < 3) {
    show("while loop:", count);
    count = count + 1;
}

// Infinite loop with break condition
function controlledLoop() {
    var k = 0;
    loop {
        show("infinite loop:", k);
        k = k + 1;
        if (k >= 3) { break; }
    }
}
controlledLoop();
```

### **async_stub.fn** - Promise API (Synchronous)
```falcon
show("Starting async stub...");

// Create and resolve a promise
var p = Promise.resolve(42);

// Chain promise operations
p.then(function(x) {
    show("Promise resolved with:");
    show(x);
    return x * 2;
}).then(function(doubled) {
    show("Doubled value:", doubled);
});

// Promise constructor
var p2 = Promise(function(resolve, reject) {
    resolve("Async operation complete!");
});

p2.then(function(msg) {
    show("Constructor promise:", msg);
});

show("Promise scheduled.");
```

---

# 🛣 Roadmap (Active Development)

### 🚀 Current Language Features  
- [x] **Core syntax** (variables, functions, control flow)
- [x] **Variable declarations** (var, let, const with := and =)
- [x] **Function types** (declarations, expressions, first-class functions)
- [x] **Collections** (lists, tuples, dictionaries, sets, arrays)
- [x] **Closures & lexical scoping** (full closure support)
- [x] **Control flow** (if/else, for, while, infinite loops)
- [x] **Member access & subscripting** (obj.property, obj[key], arr[index])
- [x] **Built-in functions** (show, console.log, Promise API)
- [x] **Comments** (// line comments and /* block comments */)
- [x] **Arithmetic operations** (+, -, *, /, %)
- [x] **Comparison operations** (==, !=, <, <=, >, >=)
- [x] **Logical operations** (&&, ||, !)
- [x] **Assignment operations** (=, :=)

### 📋 Planned Features  
- [ ] **Pattern matching**
- [ ] **Type annotations**
- [ ] **Async / await** (stub implemented)
- [ ] **Modules & imports**
- [ ] **Error handling** (try/catch)
- [ ] **Classes & objects**
- [ ] **Generators**  

### ⚙ Runtime  
- [ ] Optimizing bytecode VM  
- [ ] JIT compilation (optional)  
- [ ] Debugger + stack traces  

### 🛠 Tooling  
- [ ] `falcon fmt` — code formatter  
- [ ] LSP server for VS Code  
- [ ] Package manager  
- [ ] Installer (.exe / .msi / .deb)  

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

# 🦅 Falcon — “Small language. Big possibilities.”
Falcon is built to grow — from a prototype VM to a complete, scripting language.
  

