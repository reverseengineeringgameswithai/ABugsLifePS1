#!/usr/bin/env python3
"""Decomp permuter: hill-climb semantics-preserving C rewrites to close the last few
words of a byte-exact near-miss.

The residual on a near-matching function is GCC-2.7.2 instruction scheduling /
register allocation, which C *semantics* can't steer directly but source *shape*
can. This tool takes a close `.c` (a few words off) and the target address, then
repeatedly applies random semantics-preserving transforms, compiling each variant
through the real toolchain (`compile_at`) and scoring the byte-diff, keeping variants
via simulated-annealing acceptance and stopping at 0 (MATCH).

Transforms are applied on the pycparser AST when the seed parses (robust), falling
back to text edits otherwise. Because every candidate is re-compiled and byte-scored,
a *wrong* transform simply fails to compile / mismatches and is discarded -- the
compiler + scorer enforce correctness, so the transform set can be liberal.

  python tools/dc_permute.py <addr> <src.c> [--small-data] [--iters N] [--seed K]

On MATCH it writes the winning source back to <src.c> and prints it. Standard
decomp-community fix for scheduling walls (cf. simonlindholm/decomp-permuter).
"""
from __future__ import annotations

import argparse
import copy
import random
import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from substrate_common import (  # noqa: E402
    compile_at, ROOT, BUILD, HANDWRITTEN, original_exe, va_to_off,
    resolve_declaration_profile,
)

try:
    from pycparser import c_parser, c_generator, c_ast
    _CP = c_parser.CParser()
    _CG = c_generator.CGenerator()
    HAVE_PYCPARSER = True
except Exception:  # pragma: no cover
    HAVE_PYCPARSER = False

SEG = yaml.safe_load((ROOT / "config" / "segments.yml").read_text())
PROF = resolve_declaration_profile("cleanroom_unprototyped")
INC = [BUILD, HANDWRITTEN, *PROF["include_dirs"]]
COMMUTATIVE = ("+", "|", "&", "^", "*")


def score(src_text: str, va: int, want: int, small_data: bool) -> int:
    """Compile src_text; return #differing 4-byte words vs retail (9999 on any build
    failure / size mismatch). 0 == byte-exact."""
    exe = original_exe(SEG)
    orig = exe[va_to_off(SEG, va):va_to_off(SEG, va) + want]
    tmp = ROOT / "analysis" / "dc_permuter_seeds" / f"_perm_{va:08x}.c"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(src_text)
    try:
        new = compile_at(tmp, va, compiler_id="gcc2.7.2-psx",
                         cc1_flags=["-O2", "-G0", "-mcpu=3000", "-fno-builtin"],
                         maspsx_args=["--dont-expand-li", "--expand-div"], include_dirs=INC,
                         externs={}, small_data=small_data, gp=0x80081d98,
                         cpp_args=PROF["cpp_args"], section_layout=None)
    except Exception:
        return 9999
    finally:
        tmp.unlink(missing_ok=True)
    if not isinstance(new, bytes) or len(new) != want:
        return 9999
    return sum(orig[i:i + 4] != new[i:i + 4] for i in range(0, want, 4))


# ---------------------------------------------------------------- AST transforms
def _funcdef(ast):
    for e in ast.ext:
        if isinstance(e, c_ast.FuncDef):
            return e
    return None


def _iter(node, parent=None, attr=None):
    """Yield (child, parent, attr) where attr is 'left' or 'block_items[2]' etc."""
    for cname, child in node.children():
        yield child, node, cname
        yield from _iter(child, node, cname)


def _set_child(parent, attr, new):
    m = re.match(r"(\w+)\[(\d+)\]$", attr)
    if m:
        getattr(parent, m.group(1))[int(m.group(2))] = new
    else:
        setattr(parent, attr, new)


def _all(ast, pred):
    return [(n, p, a) for (n, p, a) in _iter(ast) if pred(n)]


def _compounds(ast):
    return [n for (n, _, _) in _iter(ast) if isinstance(n, c_ast.Compound) and n.block_items]


def _make_decl(typ: str, name: str, init):
    tu = _CP.parse(f"void _f(void){{ {typ} {name} = 0; }}")
    d = tu.ext[0].body.block_items[0]
    d.init = init
    return d


def t_commute(ast, rng):
    s = _all(ast, lambda n: isinstance(n, c_ast.BinaryOp) and n.op in COMMUTATIVE)
    if not s:
        return False
    n = rng.choice(s)[0]
    n.left, n.right = n.right, n.left
    return True


def t_reassoc(ast, rng):
    def pred(n):
        return (isinstance(n, c_ast.BinaryOp) and n.op in ("+", "*", "|", "&", "^")
                and isinstance(n.left, c_ast.BinaryOp) and n.left.op == n.op)
    s = _all(ast, pred)
    if not s:
        return False
    n = rng.choice(s)[0]
    a, b, c = n.left.left, n.left.right, n.right
    n.left = a
    n.right = c_ast.BinaryOp(n.op, b, c)
    return True


def t_addrform(ast, rng):
    """&X[Y] <-> X+Y (pointer arithmetic identity)."""
    amp = _all(ast, lambda n: isinstance(n, c_ast.UnaryOp) and n.op == "&"
               and isinstance(n.expr, c_ast.ArrayRef))
    add = _all(ast, lambda n: isinstance(n, c_ast.BinaryOp) and n.op == "+"
               and isinstance(n.left, (c_ast.ID, c_ast.Cast)))
    choices = [("amp", x) for x in amp] + [("add", x) for x in add]
    if not choices:
        return False
    kind, (n, p, a) = rng.choice(choices)
    if kind == "amp":
        ar = n.expr
        _set_child(p, a, c_ast.BinaryOp("+", ar.name, ar.subscript))
    else:
        _set_child(p, a, c_ast.UnaryOp("&", c_ast.ArrayRef(n.left, n.right)))
    return True


def t_invert_if(ast, rng):
    s = _all(ast, lambda n: isinstance(n, c_ast.If) and n.iftrue is not None)
    if not s:
        return False
    n = rng.choice(s)[0]
    cond = n.cond
    if isinstance(cond, c_ast.UnaryOp) and cond.op == "!":
        n.cond = cond.expr
    else:
        n.cond = c_ast.UnaryOp("!", cond)
    n.iftrue, n.iffalse = n.iffalse or c_ast.Compound(block_items=[]), n.iftrue
    return True


def t_reorder(ast, rng):
    comps = [c for c in _compounds(ast) if len(c.block_items) >= 2]
    if not comps:
        return False
    c = rng.choice(comps)
    i = rng.randrange(len(c.block_items) - 1)
    c.block_items[i], c.block_items[i + 1] = c.block_items[i + 1], c.block_items[i]
    return True


def _hoistable_exprs(stmt):
    out = []
    for n, p, a in _iter(stmt):
        if isinstance(n, (c_ast.BinaryOp, c_ast.Cast, c_ast.ArrayRef, c_ast.UnaryOp)) \
                and not (isinstance(n, c_ast.UnaryOp) and n.op in ("p++", "p--", "++", "--")):
            out.append((n, p, a))
    return out


def t_hoist_subexpr(ast, rng):
    """Wrap a statement in a fresh block that hoists one subexpression to a temp:
    `S(... E ...)` -> `{ T _t = E; S(... _t ...) }`. Fresh scope keeps the decl legal
    (C89) and hands the scheduler an independent materialization point."""
    comps = _compounds(ast)
    if not comps:
        return False
    c = rng.choice(comps)
    i = rng.randrange(len(c.block_items))
    stmt = c.block_items[i]
    if isinstance(stmt, (c_ast.Decl, c_ast.Return, c_ast.If, c_ast.For, c_ast.While,
                         c_ast.Compound)):
        return False
    exprs = _hoistable_exprs(stmt)
    if not exprs:
        return False
    typ = rng.choice(["int", "int", "void *"])
    node, p, a = rng.choice(exprs)
    tname = f"_h{i}"
    saved = node
    _set_child(p, a, c_ast.ID(tname))
    decl = _make_decl(typ, tname, saved)
    c.block_items[i] = c_ast.Compound(block_items=[decl, stmt])
    return True


def t_blockhoist_prev(ast, rng):
    """`PREV; f(A,B);` -> `{ int _a=A,_b=B; PREV; f(_a,_b); }` -- hoist call args into
    a block that also absorbs the preceding statement (the arg-load-between-stores
    scheduling near-miss)."""
    comps = [c for c in _compounds(ast) if len(c.block_items) >= 2]
    rng.shuffle(comps)
    for c in comps:
        idxs = list(range(1, len(c.block_items)))
        rng.shuffle(idxs)
        for i in idxs:
            call = c.block_items[i]
            if not (isinstance(call, c_ast.FuncCall) and call.args
                    and 2 <= len(call.args.exprs) <= 4):
                continue
            prev = c.block_items[i - 1]
            if isinstance(prev, (c_ast.Decl, c_ast.Compound, c_ast.If, c_ast.For)):
                continue
            names = [f"_a{j}" for j in range(len(call.args.exprs))]
            decls = [_make_decl("int", nm, ex)
                     for nm, ex in zip(names, call.args.exprs)]
            call.args.exprs = [c_ast.ID(nm) for nm in names]
            block = c_ast.Compound(block_items=decls + [prev, call])
            c.block_items[i - 1:i + 1] = [block]
            return True
    return False


def t_temp_blocktop(ast, rng):
    """Hoist a subexpression to a temp declared at the top of its enclosing block
    (C89-legal). Unlike the scoped block-hoist, this changes the live range across
    the whole block -> shifts register allocation (the residual on regalloc-naming
    near-misses). Early evaluation is fine for pure param/global reads; the scorer
    discards anything that changes behaviour."""
    comps = _compounds(ast)
    rng.shuffle(comps)
    for c in comps:
        n_decl = 0
        while n_decl < len(c.block_items) and isinstance(c.block_items[n_decl], c_ast.Decl):
            n_decl += 1
        # candidate subexprs from the non-decl statements
        cand = []
        for st in c.block_items[n_decl:]:
            cand += [(x, p, a) for (x, p, a) in _hoistable_exprs(st)]
        if not cand:
            continue
        node, p, a = rng.choice(cand)
        typ = rng.choice(["int", "int", "void *"])
        tname = f"_t{rng.randrange(1000)}"
        _set_child(p, a, c_ast.ID(tname))
        c.block_items.insert(n_decl, _make_decl(typ, tname, node))
        return True
    return False


def t_inline_temp(ast, rng):
    """Inline a temp used exactly once (reverse of hoisting) -> merges live ranges."""
    comps = _compounds(ast)
    rng.shuffle(comps)
    for c in comps:
        decls = [(k, d) for k, d in enumerate(c.block_items)
                 if isinstance(d, c_ast.Decl) and d.init is not None
                 and isinstance(d.name, str)]
        rng.shuffle(decls)
        for k, d in decls:
            uses = _all(ast, lambda n: isinstance(n, c_ast.ID) and n.name == d.name)
            if len(uses) != 1:
                continue
            un, up, ua = uses[0]
            _set_child(up, ua, copy.deepcopy(d.init))
            del c.block_items[k]
            return True
    return False


def t_decl_reorder(ast, rng):
    """Swap two adjacent top-of-block declarations -> changes the allocator's variable
    ordering (a lever on register-naming residuals)."""
    comps = _compounds(ast)
    rng.shuffle(comps)
    for c in comps:
        decls = [k for k in range(len(c.block_items) - 1)
                 if isinstance(c.block_items[k], c_ast.Decl)
                 and isinstance(c.block_items[k + 1], c_ast.Decl)]
        if decls:
            k = rng.choice(decls)
            c.block_items[k], c.block_items[k + 1] = c.block_items[k + 1], c.block_items[k]
            return True
    return False


def t_vary_temp_type(ast, rng):
    """Flip a local scalar decl's type among int/unsigned/short/char -> changes
    sign/size handling (lh<->lhu, etc.) and thus register/instruction selection."""
    decls = _all(ast, lambda n: isinstance(n, c_ast.Decl)
                 and isinstance(n.type, c_ast.TypeDecl)
                 and isinstance(getattr(n.type, "type", None), c_ast.IdentifierType))
    scal = [(n, p, a) for (n, p, a) in decls
            if set(n.type.type.names) <= {"int", "unsigned", "short", "char", "long"}]
    if not scal:
        return False
    n = rng.choice(scal)[0]
    n.type.type.names = rng.choice([["int"], ["unsigned", "int"], ["short"],
                                    ["unsigned", "char"], ["char"]])
    return True


AST_TRANSFORMS = [t_commute, t_reassoc, t_addrform, t_invert_if, t_reorder,
                  t_hoist_subexpr, t_blockhoist_prev, t_temp_blocktop, t_inline_temp,
                  t_decl_reorder, t_vary_temp_type]


def ast_neighbor(src_text, rng, nmoves=1):
    try:
        ast = _CP.parse(src_text)
    except Exception:
        return None
    fn = _funcdef(ast)
    if fn is None:
        return None
    work = copy.deepcopy(ast)
    applied = 0
    for _ in range(nmoves):
        for t in rng.sample(AST_TRANSFORMS, len(AST_TRANSFORMS)):
            try:
                if t(work, rng):
                    applied += 1
                    break
            except Exception:
                continue
    if not applied:
        return None
    try:
        return _CG.visit(work)
    except Exception:
        return None


# ---------------------------------------------------------------- text fallback
def split_body(src):
    m = re.search(r"\)\s*\{", src)
    if not m:
        return None
    open_i = m.end() - 1
    depth, i = 0, open_i
    while i < len(src):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = src[open_i + 1:i]
    head, tail = src[:open_i + 1], src[i:]
    units, depth, cur = [], 0, ""
    for ch in body:
        cur += ch
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                units.append(cur.strip()); cur = ""
        elif ch == ";" and depth == 0:
            units.append(cur.strip()); cur = ""
    if cur.strip():
        units.append(cur.strip())
    return head, [u for u in units if u], tail


def text_neighbor(src_text, rng):
    parsed = split_body(src_text)
    if not parsed:
        return None
    head, units, tail = parsed
    if len(units) < 2:
        return None
    body_idx = list(range(len(units)))
    a, b = rng.choice(body_idx), rng.choice(body_idx)
    if a == b:
        return None
    u = list(units)
    u.insert(b, u.pop(a))
    return head + "\n    " + "\n    ".join(u) + "\n" + tail


def neighbor(src_text, rng):
    if HAVE_PYCPARSER and rng.random() < 0.9:
        nmoves = 1 if rng.random() < 0.7 else 2
        cand = ast_neighbor(src_text, rng, nmoves)
        if cand is not None:
            return cand
    return text_neighbor(src_text, rng)


def _want_for(va):
    for e in SEG.get("attempted", []):
        s = int(e["start"], 16) if isinstance(e["start"], str) else e["start"]
        if s == va and isinstance(e.get("end"), int):
            return e["end"] - s
    import json
    for r in json.loads((ROOT / "analysis" / "functions.json").read_text())["functions"]:
        if int(r["start"], 16) == va:
            return int(r["end"], 16) - int(r["start"], 16)
    return None


def main() -> int:
    import math
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("addr")
    ap.add_argument("src")
    ap.add_argument("--small-data", action="store_true")
    ap.add_argument("--iters", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    va = int(args.addr, 16)
    want = _want_for(va)
    entry = next((e for e in SEG.get("attempted", [])
                  if (int(e["start"], 16) if isinstance(e["start"], str) else e["start"]) == va), None)
    sd = args.small_data or bool(entry and entry.get("small_data"))
    src_path = ROOT / args.src
    base = src_path.read_text()
    best_sc = score(base, va, want, sd)
    print(f"[permute] seed={best_sc}w want={want}B small_data={sd} "
          f"pycparser={'yes' if HAVE_PYCPARSER else 'no'}")
    if best_sc == 0:
        print("[permute] already MATCH"); return 0
    rng = random.Random(args.seed)
    best_text = cur_text = base
    cur = best_sc
    for it in range(args.iters):
        cand = neighbor(cur_text, rng)
        if cand is None:
            continue
        sc = score(cand, va, want, sd)
        T = max(0.05, 2.0 * (1 - it / args.iters))
        if sc <= cur or rng.random() < math.exp(-(sc - cur) / T):
            cur_text, cur = cand, sc
            if sc < best_sc:
                print(f"[permute] iter {it}: {best_sc} -> {sc}w")
                best_text, best_sc = cand, sc
        if best_sc == 0:
            src_path.write_text(best_text)
            print(f"[permute] MATCH at iter {it}; wrote {args.src}\n{best_text}")
            return 0
        if it % 60 == 59:
            cur_text, cur = best_text, best_sc
    # persist best-so-far so runs can be chained / inspected (never overwrites the seed)
    if best_sc < score(base, va, want, sd):
        Path(str(src_path) + ".best").write_text(best_text)
        print(f"[permute] wrote improved {best_sc}w seed -> {args.src}.best")
    print(f"[permute] best={best_sc}w after {args.iters} iters (no exact match)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
