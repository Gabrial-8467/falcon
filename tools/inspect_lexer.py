# tools/inspect_lexer.py
import inspect
import importlib
import pkgutil
import sys
from pprint import pprint

# adjust this import path if your project layout differs
modname = "src.falcon.lexer"

# Try several import styles to be robust
spec = None
mod = None
try:
    # primary attempt
    mod = importlib.import_module("src.falcon.lexer")
except Exception as e:
    print("Importing src.falcon.lexer failed:", e)
    print("Trying to import falcon.lexer (alternate layout)...")
    try:
        mod = importlib.import_module("falcon.lexer")
    except Exception as e2:
        print("Importing falcon.lexer failed too:", e2)
        print("Give me the path to lexer.py if these both fail.")
        raise

print("Module:", mod.__name__)
print("Location:", getattr(mod, "__file__", "??"))

# Find Lexer class
Lexer = None
for name, obj in vars(mod).items():
    if name.lower() == "lexer" and inspect.isclass(obj):
        Lexer = obj
        break
# fallback: first class named Lexer
if Lexer is None:
    for name, obj in vars(mod).items():
        if inspect.isclass(obj) and name == "Lexer":
            Lexer = obj
            break

if Lexer is None:
    print("No class named 'Lexer' was found in the module. Here are module globals:")
    pprint([k for k in vars(mod).keys() if not k.startswith("_")][:200])
    sys.exit(1)

print("\nFound Lexer class:", Lexer)
print("\n--- Lexer source ---\n")
try:
    src = inspect.getsource(Lexer)
    print(src)
except Exception as e:
    print("Could not get source for Lexer class:", e)

print("\n--- Lexer members (callables & attributes) ---")
members = inspect.getmembers(Lexer)
for name, val in members:
    if name.startswith("__"):
        continue
    print(name, "->", "callable" if callable(val) else type(val))

print("\n--- Module-level variables (looking for KEYWORDS, keywords, RESERVED) ---")
for k in ("KEYWORDS", "keywords", "RESERVED", "reserved_words"):
    if k in vars(mod):
        print(f"{k} found in module; value:")
        pprint(vars(mod)[k])
    else:
        print(f"{k} NOT found")

# Also print top-level functions that look like tokenizers
candidates = [n for n, o in vars(Lexer).items() if inspect.isfunction(o)]
print("\nPotential Lexer methods:")
pprint(candidates)

# If Lexer can be constructed quickly, list instance attrs
print("\nAttempting to construct a Lexer instance for introspection (may require source arg).")
inst = None
try:
    inst = Lexer("")  # many lexers accept source string
    print("Constructed Lexer('',...) successfully.")
    print("Instance dir():")
    pprint([a for a in dir(inst) if not a.startswith("__")])
except Exception as e:
    print("Could not construct Lexer(''): ", e)

print("\nDone inspection — paste this output here.")
