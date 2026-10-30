#!/usr/bin/env python3
"""Shrink a permuter MATCH back to readable C that still byte-matches.

The permuter (`dc_permute_upstream.py`) finds a *matching structure* but emits it
buried in junk transforms (dead vars, `;`, `x^0`, `(0,y)`, `do{}while(0)`, gotos).
This tool greedily applies semantics-reducing rewrites -- inline single-use temps,
drop unused decls / empty & dead statements, fold no-op arithmetic -- re-scoring each
via `compile_at` and keeping only reductions that preserve the exact byte-match (0w).
Converges to a small, readable source that still assembles byte-identical.

  python tools/dc_shrink.py <addr> <match.c> [--small-data] [--passes N]
"""
from __future__ import annotations

import argparse
import copy
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dc_permute as P  # noqa: E402
from pycparser import c_parser, c_generator, c_ast  # noqa: E402

_CP = c_parser.CParser()
_CG = c_generator.CGenerator()


def _iter(node, parent=None, attr=None):
    for cname, child in node.children():
        yield child, node, cname
        yield from _iter(child, node, cname)


def _set(parent, attr, new):
    m = re.match(r"(\w+)\[(\d+)\]$", attr)
    if m:
        getattr(parent, m.group(1))[int(m.group(2))] = new
    else:
        setattr(parent, attr, new)


def _compounds(ast):
    return [n for (n, _, _) in _iter(ast) if isinstance(n, c_ast.Compound) and n.block_items is not None]


def _fold(ast) -> bool:
    """Fold a single no-op: x^0/0^x -> x, x|0 -> x, x-0 -> x, x*0 -> 0, (0,y) -> y,
    x&ALLONES -> x, --x/~~ -> x, (T)(T)x cast idempotent-ish left to the compiler."""
    def is_zero(n):
        return isinstance(n, c_ast.Constant) and n.value.rstrip("uUlL") in ("0", "0x0")
    def is_allones(n):
        return isinstance(n, c_ast.Constant) and set(n.value.lower().lstrip("0x").rstrip("ul")) <= {"f"} \
            and n.value.lower().lstrip("0x").rstrip("ul") != ""
    for n, p, a in _iter(ast):
        if isinstance(n, c_ast.BinaryOp):
            if n.op in ("^", "|", "-", "+") and is_zero(n.right):
                _set(p, a, n.left); return True
            if n.op in ("^", "|", "+") and is_zero(n.left):
                _set(p, a, n.right); return True
            if n.op == "*" and (is_zero(n.left) or is_zero(n.right)):
                _set(p, a, c_ast.Constant("int", "0")); return True
            if n.op == "&" and is_allones(n.right):
                _set(p, a, n.left); return True
            if n.op == "&" and is_allones(n.left):
                _set(p, a, n.right); return True
        if isinstance(n, c_ast.ExprList) and len(n.exprs) == 2 and is_zero(n.exprs[0]):
            _set(p, a, n.exprs[1]); return True
        if isinstance(n, c_ast.UnaryOp) and n.op == "-" and is_zero(n.expr):
            _set(p, a, c_ast.Constant("int", "0")); return True
    return False


def _drop_empty(ast) -> bool:
    """Remove `;`, empty blocks, do{}while(0), if with empty/const bodies, dead labels."""
    for c in _compounds(ast):
        for i, st in enumerate(c.block_items):
            if isinstance(st, c_ast.EmptyStatement):
                del c.block_items[i]; return True
            if isinstance(st, c_ast.Compound) and not st.block_items:
                del c.block_items[i]; return True
            if isinstance(st, c_ast.DoWhile) and isinstance(st.stmt, c_ast.Compound) \
                    and not st.stmt.block_items:
                del c.block_items[i]; return True
            if isinstance(st, c_ast.If):
                empt = lambda b: b is None or (isinstance(b, c_ast.Compound) and not b.block_items) \
                    or isinstance(b, c_ast.EmptyStatement)
                if empt(st.iftrue) and empt(st.iffalse):
                    del c.block_items[i]; return True
            if isinstance(st, c_ast.Label) and isinstance(st.stmt, c_ast.EmptyStatement):
                # keep only if a goto targets it
                if not any(isinstance(g, c_ast.Goto) and g.name == st.name for g, _, _ in _iter(ast)):
                    del c.block_items[i]; return True
            if isinstance(st, c_ast.Goto):
                # goto L; ... L:  where nothing between -> drop goto if next real stmt is its label
                nxt = c.block_items[i + 1] if i + 1 < len(c.block_items) else None
                if isinstance(nxt, c_ast.Label) and nxt.name == st.name:
                    del c.block_items[i]; return True
    return False


def _inline_single_use(ast) -> bool:
    """`T v = E;` with v read exactly once -> inline E at the use, drop the decl.
    Also collapse `v = E` assignment-expressions whose result is used once."""
    for c in _compounds(ast):
        for i, st in enumerate(c.block_items):
            if isinstance(st, c_ast.Decl) and st.init is not None and isinstance(st.name, str):
                uses = [(n, p, a) for n, p, a in _iter(ast)
                        if isinstance(n, c_ast.ID) and n.name == st.name]
                assigns = [n for n, _, _ in _iter(ast)
                           if isinstance(n, c_ast.Assignment) and isinstance(n.lvalue, c_ast.ID)
                           and n.lvalue.name == st.name]
                if len(uses) == 1 and not assigns:
                    un, up, ua = uses[0]
                    _set(up, ua, copy.deepcopy(st.init))
                    del c.block_items[i]
                    return True
    return False


def _drop_unused_decl(ast) -> bool:
    for c in _compounds(ast):
        for i, st in enumerate(c.block_items):
            if isinstance(st, c_ast.Decl) and isinstance(st.name, str):
                used = any(isinstance(n, c_ast.ID) and n.name == st.name
                           for n, _, _ in _iter(ast))
                assigned_only = st.init is None
                if not used and assigned_only:
                    del c.block_items[i]; return True
    return False


REDUCERS = [_inline_single_use, _fold, _drop_empty, _drop_unused_decl]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("addr")
    ap.add_argument("src")
    ap.add_argument("--small-data", action="store_true")
    ap.add_argument("--passes", type=int, default=40)
    args = ap.parse_args()
    va = int(args.addr, 16)
    want = P._want_for(va)
    entry = next((e for e in P.SEG.get("attempted", [])
                  if (int(e["start"], 16) if isinstance(e["start"], str) else e["start"]) == va), None)
    sd = args.small_data or bool(entry and entry.get("small_data"))
    src_path = P.ROOT / args.src
    text = src_path.read_text()
    if P.score(text, va, want, sd) != 0:
        print("[shrink] seed does not MATCH (0w) -- refusing"); return 1
    n0 = len(text)

    def batch_drop_empties(t):
        ast = _CP.parse(t)

        class Rem(c_ast.NodeVisitor):
            def visit_Compound(self, node):
                if node.block_items:
                    node.block_items = [b for b in node.block_items
                                        if not isinstance(b, c_ast.EmptyStatement)]
                self.generic_visit(node)
        Rem().visit(ast)
        cand = _CG.visit(ast)
        return cand if P.score(cand, va, want, sd) == 0 else t

    text = batch_drop_empties(text)
    for it in range(args.passes):
        progressed = False
        for red in REDUCERS:
            while True:
                ast = _CP.parse(text)
                if not red(ast):
                    break
                cand = _CG.visit(ast)
                if P.score(cand, va, want, sd) == 0:
                    text = batch_drop_empties(cand)
                    progressed = True
                else:
                    break
        print(f"[shrink] pass {it}: {len(text)} chars"
              + ("" if progressed else " (fixpoint)"))
        if not progressed:
            break
    src_path.write_text(text)
    print(f"[shrink] done: {n0} -> {len(text)} chars, still MATCH; wrote {args.src}\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
