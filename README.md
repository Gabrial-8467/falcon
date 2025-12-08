```
███████╗ █████╗ ██╗      ██████╗ ██████╗ ███╗   ██╗
██╔════╝██╔══██╗██║     ██╔════╝██╔═══██╗████╗  ██║
█████╗  ███████║██║     ██║     ██║   ██║██╔██╗ ██║
██╔══╝  ██╔══██║██║     ██║     ██║   ██║██║╚██╗██║
██║     ██║  ██║███████╗╚██████╗╚██████╔╝██║ ╚████║
╚═╝     ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝
```

# 🦅 Falcon — A Modern Lightweight Programming Language  
**Fast. Expressive. Hackable. Built for experiments and real projects.**

Falcon is a **small, modern programming language** designed to be:

- 🧠 **Easy to learn** (clean syntax, predictable semantics)  
- ⚡ **Fast** (hybrid **VM + interpreter** execution model)  
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

# ✨ Highlights (Prototype v0.3)

### ✔ Falcon Syntax  
```
var x := 10;
function add(a, b) { return a + b; }
show(add(x, 20));
```

### ✔ Closures  
```
function makeCounter() {
    var c := 0;
    return function() {
        c = c + 1;
        return c;
    };
}

var next := makeCounter();
show(next());  # 1
show(next());  # 2
```

### ✔ Falcon Loop System  
```
for var i := 1 to 5 step 1 {
    show(i);
}

loop {
    show("Running...");
}
```

### ✔ Hybrid Execution Model  
Falcon runs code through:

1. **Compiler → Bytecode**  
2. **VM executes bytecode**  
3. Automatically **falls back to interpreter** when closures or complex features require dynamic semantics.

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

# ▶ Running the REPL

```bash
python -m falcon.repl
```

Example:

```
Falcon REPL — v0.3  
falcon> var x := 5;
falcon> x * 2
10
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

# 📘 Example Programs

### **hello.fn**
```
show("Hello from Falcon!");
```

### **factorial.fn**
```
function fact(n) {
    if (n == 0) { return 1; }
    return n * fact(n - 1);
}
show(fact(6));
```

### **closure.fn**
```
function makeAdder(x) {
    return function(y) {
        return x + y;
    };
}
var add2 := makeAdder(2);
show(add2(10));
```

---

# 🛣 Roadmap (Active Development)

### 🚀 Language  
- [ ] Arrays & Maps  
- [ ] Pattern Matching  
- [ ] Type annotations  
- [ ] Async / await  
- [ ] Modules (`import`)  

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
Falcon is built to grow — from a prototype VM to a complete, fast scripting language.

If you'd like, I can also generate:

✅ A logo  
✅ Website for documentation  
✅ Syntax highlighter for VS Code  
✅ Installer generator (PyInstaller / NSIS)  
✅ Nice CLI scaffolding (`falcon new project`)  

