from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .ast_nodes import (
    Assign,
    Binary,
    BlockStmt,
    Call,
    Expr,
    ExprStmt,
    ForStmt,
    FunctionExpr,
    FunctionStmt,
    Grouping,
    IfStmt,
    LetStmt,
    ListLiteral,
    Literal,
    LoopStmt,
    MatchExpr,
    MatchStmt,
    Member,
    ReturnStmt,
    SetLiteral,
    Stmt,
    Subscript,
    TupleLiteral,
    Unary,
    Variable,
    WhileStmt,
    DictLiteral,
)


class TypeCheckError(Exception):
    pass


@dataclass
class FunctionSig:
    params: List[str]
    param_types: Dict[str, str]
    return_type: Optional[str]


class TypeChecker:
    def __init__(self) -> None:
        self.scopes: List[Dict[str, str]] = [{}]
        self.functions: Dict[str, FunctionSig] = {}
        self.current_return_type: Optional[str] = None

    def check(self, stmts: List[Stmt]) -> None:
        for stmt in stmts:
            self._check_stmt(stmt)

    def _push(self) -> None:
        self.scopes.append({})

    def _pop(self) -> None:
        self.scopes.pop()

    def _define(self, name: str, type_name: str) -> None:
        self.scopes[-1][name] = type_name

    def _lookup(self, name: str) -> Optional[str]:
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def _compatible(self, actual: str, expected: str) -> bool:
        actual = actual.strip()
        expected = expected.strip()
        expected_parts = [p.strip() for p in expected.split("|")]
        if actual in expected_parts:
            return True
        if "any" in expected_parts or "object" in expected_parts:
            return True
        actual_parts = [p.strip() for p in actual.split("|")]
        if len(actual_parts) > 1:
            return all(self._compatible(a, expected) for a in actual_parts)
        if actual == "int" and "number" in expected_parts:
            return True
        if actual == "float" and "number" in expected_parts:
            return True
        if actual.startswith("list[") and any(e.startswith("list[") for e in expected_parts):
            a_inner = actual[5:-1]
            return any(self._compatible(a_inner, e[5:-1]) for e in expected_parts if e.startswith("list["))
        if actual.startswith("set[") and any(e.startswith("set[") for e in expected_parts):
            a_inner = actual[4:-1]
            return any(self._compatible(a_inner, e[4:-1]) for e in expected_parts if e.startswith("set["))
        if actual.startswith("tuple[") and any(e.startswith("tuple[") for e in expected_parts):
            a_inners = self._split_top_level(actual[6:-1])
            for e in expected_parts:
                if not e.startswith("tuple["):
                    continue
                e_inners = self._split_top_level(e[6:-1])
                if len(a_inners) == len(e_inners) and all(
                    self._compatible(a, b) for a, b in zip(a_inners, e_inners)
                ):
                    return True
        if actual.startswith("dict[") and any(e.startswith("dict[") for e in expected_parts):
            a_pair = self._split_top_level(actual[5:-1])
            if len(a_pair) == 2:
                for e in expected_parts:
                    if not e.startswith("dict["):
                        continue
                    e_pair = self._split_top_level(e[5:-1])
                    if len(e_pair) == 2 and self._compatible(a_pair[0], e_pair[0]) and self._compatible(a_pair[1], e_pair[1]):
                        return True
            return "dict" in expected_parts
        if actual.startswith("fn(") and "function" in expected_parts:
            return True
        return False

    def _split_top_level(self, text: str) -> List[str]:
        parts: List[str] = []
        depth = 0
        cur: List[str] = []
        for ch in text:
            if ch == "[":
                depth += 1
            elif ch == "]" and depth > 0:
                depth -= 1
            if ch == "," and depth == 0:
                parts.append("".join(cur).strip())
                cur = []
                continue
            cur.append(ch)
        tail = "".join(cur).strip()
        if tail:
            parts.append(tail)
        return parts

    def _check_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, LetStmt):
            inferred = "null"
            if stmt.initializer is not None:
                inferred = self._infer_expr(stmt.initializer)
            declared = stmt.type_ann.name if stmt.type_ann else inferred
            if stmt.type_ann and not self._compatible(inferred, declared):
                raise TypeCheckError(
                    f"Type mismatch for '{stmt.name}': expected {declared}, got {inferred}"
                )
            self._define(stmt.name, declared)
            return

        if isinstance(stmt, ExprStmt):
            self._infer_expr(stmt.expr)
            return

        if isinstance(stmt, BlockStmt):
            self._push()
            for s in stmt.body:
                self._check_stmt(s)
            self._pop()
            return

        if isinstance(stmt, IfStmt):
            self._infer_expr(stmt.condition)
            self._check_stmt(stmt.then_branch)
            if stmt.else_branch is not None:
                self._check_stmt(stmt.else_branch)
            return

        if isinstance(stmt, WhileStmt):
            self._infer_expr(stmt.condition)
            self._check_stmt(stmt.body)
            return

        if isinstance(stmt, ForStmt):
            self._infer_expr(stmt.start)
            self._infer_expr(stmt.end)
            if stmt.step is not None:
                self._infer_expr(stmt.step)
            self._push()
            self._define(stmt.name, "number")
            self._check_stmt(stmt.body)
            self._pop()
            return

        if isinstance(stmt, LoopStmt):
            self._check_stmt(stmt.body)
            return

        if isinstance(stmt, FunctionStmt):
            sig = FunctionSig(
                params=stmt.params,
                param_types={k: v.name for k, v in stmt.param_types.items()},
                return_type=stmt.return_type.name if stmt.return_type else None,
            )
            self.functions[stmt.name] = sig
            self._define(stmt.name, f"fn({len(stmt.params)})")

            prev_ret = self.current_return_type
            self.current_return_type = sig.return_type
            self._push()
            for p in stmt.params:
                self._define(p, sig.param_types.get(p, "any"))
            for s in stmt.body.body:
                self._check_stmt(s)
            self._pop()
            self.current_return_type = prev_ret
            return

        if isinstance(stmt, ReturnStmt):
            if self.current_return_type is None:
                return
            actual = "null" if stmt.value is None else self._infer_expr(stmt.value)
            if not self._compatible(actual, self.current_return_type):
                raise TypeCheckError(
                    f"Type mismatch for return: expected {self.current_return_type}, got {actual}"
                )
            return

        if isinstance(stmt, MatchStmt):
            self._infer_expr(stmt.value)
            for arm in stmt.arms:
                if arm.guard is not None:
                    self._infer_expr(arm.guard)
                self._check_stmt(arm.body)
            return

    def _infer_expr(self, expr: Expr) -> str:
        if isinstance(expr, Literal):
            if expr.value is None:
                return "null"
            if isinstance(expr.value, bool):
                return "bool"
            if isinstance(expr.value, int):
                return "int"
            if isinstance(expr.value, float):
                return "float"
            if isinstance(expr.value, str):
                return "string"
            if isinstance(expr.value, list):
                if not expr.value:
                    return "list[any]"
                inner = self._literal_collection_type(expr.value)
                return f"list[{inner}]"
            if isinstance(expr.value, tuple):
                if not expr.value:
                    return "tuple[any]"
                inner = ", ".join(self._infer_literal(v) for v in expr.value)
                return f"tuple[{inner}]"
            if isinstance(expr.value, set):
                if not expr.value:
                    return "set[any]"
                inner = self._literal_collection_type(list(expr.value))
                return f"set[{inner}]"
            if isinstance(expr.value, dict):
                if not expr.value:
                    return "dict[any, any]"
                k_t = self._literal_collection_type(list(expr.value.keys()))
                v_t = self._literal_collection_type(list(expr.value.values()))
                return f"dict[{k_t}, {v_t}]"
            return "object"

        if isinstance(expr, Variable):
            return self._lookup(expr.name) or "any"

        if isinstance(expr, ListLiteral):
            if not expr.elements:
                return "list[any]"
            inner = [self._infer_expr(e) for e in expr.elements]
            if all(t == inner[0] for t in inner):
                return f"list[{inner[0]}]"
            return f"list[{' | '.join(sorted(set(inner)))}]"

        if isinstance(expr, TupleLiteral):
            if not expr.elements:
                return "tuple[any]"
            return f"tuple[{', '.join(self._infer_expr(e) for e in expr.elements)}]"

        if isinstance(expr, SetLiteral):
            if not expr.elements:
                return "set[any]"
            inner = [self._infer_expr(e) for e in expr.elements]
            if all(t == inner[0] for t in inner):
                return f"set[{inner[0]}]"
            return f"set[{' | '.join(sorted(set(inner)))}]"

        if isinstance(expr, DictLiteral):
            if not expr.entries:
                return "dict[any, any]"
            ktypes = [self._infer_expr(k) for k, _ in expr.entries]
            vtypes = [self._infer_expr(v) for _, v in expr.entries]
            kt = ktypes[0] if all(t == ktypes[0] for t in ktypes) else " | ".join(sorted(set(ktypes)))
            vt = vtypes[0] if all(t == vtypes[0] for t in vtypes) else " | ".join(sorted(set(vtypes)))
            return f"dict[{kt}, {vt}]"

        if isinstance(expr, Grouping):
            return self._infer_expr(expr.expression)

        if isinstance(expr, Unary):
            t = self._infer_expr(expr.operand)
            if expr.op == "!":
                return "bool"
            if expr.op == "-" and t not in ("int", "float", "number", "any"):
                raise TypeCheckError(f"Unary '-' requires number, got {t}")
            return t

        if isinstance(expr, Binary):
            lt = self._infer_expr(expr.left)
            rt = self._infer_expr(expr.right)
            if expr.op in ("==", "!=", "<", "<=", ">", ">=", "&&", "||"):
                return "bool"
            if expr.op == "+":
                if lt == "string" or rt == "string":
                    return "string"
                if lt == "int" and rt == "int":
                    return "int"
                if lt in ("int", "float", "number", "any") and rt in (
                    "int",
                    "float",
                    "number",
                    "any",
                ):
                    if lt == "float" or rt == "float":
                        return "float"
                    return "number"
            if expr.op in ("-", "*", "/", "%"):
                if lt in ("int", "float", "number", "any") and rt in (
                    "int",
                    "float",
                    "number",
                    "any",
                ):
                    if expr.op == "/" and lt == "int" and rt == "int":
                        return "float"
                    if lt == "int" and rt == "int":
                        return "int"
                    return "number"
                raise TypeCheckError(
                    f"Operator '{expr.op}' requires numbers, got {lt} and {rt}"
                )
            return "any"

        if isinstance(expr, Assign):
            value_t = self._infer_expr(expr.value)
            if isinstance(expr.target, Variable):
                target_t = self._lookup(expr.target.name)
                if target_t is not None and not self._compatible(value_t, target_t):
                    raise TypeCheckError(
                        f"Type mismatch for '{expr.target.name}': expected {target_t}, got {value_t}"
                    )
                return target_t or value_t
            return value_t

        if isinstance(expr, Call):
            if isinstance(expr.callee, Variable):
                fn_name = expr.callee.name
                sig = self.functions.get(fn_name)
                if sig is not None:
                    if len(expr.arguments) != len(sig.params):
                        raise TypeCheckError(
                            f"Function '{fn_name}' expects {len(sig.params)} args, got {len(expr.arguments)}"
                        )
                    for arg, param in zip(expr.arguments, sig.params):
                        actual = self._infer_expr(arg)
                        expected = sig.param_types.get(param, "any")
                        if not self._compatible(actual, expected):
                            raise TypeCheckError(
                                f"Argument type mismatch for '{fn_name}.{param}': expected {expected}, got {actual}"
                            )
                    return sig.return_type or "any"
            for arg in expr.arguments:
                self._infer_expr(arg)
            return "any"

        if isinstance(expr, FunctionExpr):
            return f"fn({len(expr.params)})"

        if isinstance(expr, Member):
            self._infer_expr(expr.base)
            return "any"

        if isinstance(expr, Subscript):
            base_t = self._infer_expr(expr.base)
            self._infer_expr(expr.index)
            if base_t.startswith("list[") and base_t.endswith("]"):
                return base_t[5:-1].strip()
            if base_t.startswith("set[") and base_t.endswith("]"):
                return base_t[4:-1].strip()
            if base_t.startswith("dict[") and base_t.endswith("]"):
                pair = self._split_top_level(base_t[5:-1].strip())
                if len(pair) == 2:
                    return pair[1]
            if base_t.startswith("tuple[") and base_t.endswith("]"):
                inners = self._split_top_level(base_t[6:-1].strip())
                if len(inners) == 1:
                    return inners[0]
                return " | ".join(sorted(set(inners)))
            return "any"

        if isinstance(expr, MatchExpr):
            self._infer_expr(expr.value)
            arm_types: List[str] = []
            for arm in expr.arms:
                if arm.guard is not None:
                    self._infer_expr(arm.guard)
                t = "null"
                for s in arm.body.body:
                    if isinstance(s, ExprStmt):
                        t = self._infer_expr(s.expr)
                arm_types.append(t)
            if not arm_types:
                return "null"
            first = arm_types[0]
            if all(a == first for a in arm_types):
                return first
            return " | ".join(sorted(set(arm_types)))

        return "any"

    def _infer_literal(self, value: object) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "bool"
        if isinstance(value, int):
            return "int"
        if isinstance(value, float):
            return "float"
        if isinstance(value, str):
            return "string"
        return "object"

    def _literal_collection_type(self, values: List[object]) -> str:
        inferred = [self._infer_literal(v) for v in values]
        first = inferred[0]
        if all(t == first for t in inferred):
            return first
        return " | ".join(sorted(set(inferred)))
