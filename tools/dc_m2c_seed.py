#!/usr/bin/env python3
"""m2c-seeded C-conversion pipeline.

Drives the m2c (mips-to-c) decompiler to auto-generate a C *seed* for a hand-asm
`.s` function, normalizes it into our byte-splat substrate's conventions, and
scores it via `dc_permute.score` (compile + 4-byte word-diff vs retail). The seed
is then closable by `tools/dc_permute.py` and verifiable/bankable by
`tools/dc_bank_c.py` -- the same gate every hand-authored match passes.

Why m2c: it reads the `.s` + address arithmetic and recovers control flow AND the
exact global addresses (the two things that cost the most hand-authoring time and
the most near-misses -- sign-extended `lui/lw` addresses land correct here).

Idiom handling:
  * type prelude maps m2c's s32/u8/... to the compiler's int/char/...
  * global memory ops `*(T *)0xADDR` compile as-is (absolute lui/lw under -G0).
  * m2c renders POINTER-ARG field access as `argN->unkHEX`, which loses load
    width (a word store and a byte store look identical). Functions that use it
    are flagged `struct_access`: the seed still captures control flow but needs a
    width pass before it will byte-match, so the batch routes them to hand-finish.

  python tools/dc_m2c_seed.py <addr>                 # report: compiles/size/words
  python tools/dc_m2c_seed.py <addr> --emit          # print the normalized seed
  python tools/dc_m2c_seed.py --batch game --limit N # sweep, tally auto-yield

Env: ABL_M2C_DIR overrides the m2c checkout (default ~/abl-toolchain/m2c).
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dc_permute as P  # noqa: E402  (score/_want_for/SEG/original_exe)

M2C_DIR = os.environ.get("ABL_M2C_DIR", str(Path.home() / "abl-toolchain" / "m2c"))
ROOT = P.ROOT
SEEDS = ROOT / "analysis" / "dc_permuter_seeds"
TMP = Path(os.environ.get("CLAUDE_JOB_DIR", "/tmp")) / "tmp"
TMP.mkdir(parents=True, exist_ok=True)

PRELUDE = ("typedef int s32; typedef unsigned int u32; typedef unsigned char u8; "
           "typedef signed char s8; typedef short s16; typedef unsigned short u16; "
           "typedef long s64; typedef unsigned long u64; typedef float f32;\n"
           "#define NULL 0\n")


def _n(x):
    return int(x, 16) if isinstance(x, str) else x


def asm_path(va: int) -> str | None:
    hits = glob.glob(str(ROOT / "asm" / "hand_written" / f"{va:08x}_*.s"))
    return hits[0] if hits else None


def fn_name(va: int, path: str) -> str:
    base = os.path.basename(path)
    m = re.match(r"[0-9a-f]{8}_(.+)\.s$", base)
    return m.group(1) if m else f"func_{va:08x}"


_JAL_WORD = re.compile(r"^(\s*)\.word\s+0x[0-9a-fA-F]+\s*#\s*jal\s+0x([0-9a-fA-F]+)")


def _body_for_source(src: str) -> str:
    """Read a hand-asm .s, drop its comment header, and translate `.word
    0x.. # jal 0xADDR` back into a real `jal sub_ADDR` mnemonic so m2c can
    follow the call (our .s encode cross-fn calls as `.word` for the byte-exact
    rebuild; m2c reads `.word` as data and would truncate the function)."""
    out = []
    for ln in Path(ROOT / src).read_text().splitlines():
        if ln.lstrip().startswith("#"):
            continue
        m = _JAL_WORD.match(ln)
        out.append(f"{m.group(1)}jal sub_{m.group(2).lower()}" if m else ln)
    return "\n".join(out)


def _full_asm(va: int) -> tuple[str, str] | None:
    """Assemble a function's full body (main source + any `parts:`) in address
    order from its segments.yml entry, or fall back to the single .s file."""
    entry = next((e for e in P.SEG.get("attempted", []) if _n(e["start"]) == va), None)
    if entry and str(entry.get("source", "")).endswith(".s"):
        pieces = [(_n(entry["start"]), entry["source"])]
        for pt in entry.get("parts", []) or []:
            pieces.append((_n(pt["start"]), pt["source"]))
        pieces.sort()
        path = str(ROOT / entry["source"])
        name = fn_name(va, path)
        return name, "\n".join(_body_for_source(src) for _, src in pieces)
    path = asm_path(va)
    if not path:
        return None
    return fn_name(va, path), _body_for_source(os.path.relpath(path, ROOT))


_SIG_CTX: Path | None = None


def _signature_context() -> Path:
    """Build (once) an m2c context declaring every already-known function's
    signature under its `sub_<hex>` name, so m2c resolves callee signatures
    (arg count, pointer-vs-scalar) instead of guessing them per call. Sourced
    from our own banked src/main/*.c -- cleanroom-safe, no external SDK headers.
    Types are coarsened to void*/int (only the ABI shape matters to the caller)."""
    global _SIG_CTX
    if _SIG_CTX is not None:
        return _SIG_CTX
    sigs = []
    defn = re.compile(r"(?:^|\n)([A-Za-z_][\w\s\*]*?\s\**)([A-Za-z_]\w*)\s*\(([^;{]*?)\)\s*\{")
    for f in sorted((ROOT / "src" / "main").glob("*.c")):
        m = re.match(r"([0-9a-f]{8})_", f.name)
        if not m:
            continue
        fm = defn.search(f.read_text())
        if not fm or fm.group(1).strip() in ("return", "else", "if", "for", "while", "switch"):
            continue
        ret = "void" if fm.group(1).strip() == "void" else ("void *" if "*" in fm.group(1) else "int")
        astr = fm.group(3).strip()
        args = "void" if astr in ("", "void") else ", ".join(
            "void *" if "*" in a else "int" for a in astr.split(","))
        sigs.append(f"{ret} sub_{m.group(1)}({args});")
    # lever #1: also declare unbanked pool functions whose census name is a known
    # PsyQ SDK function, from the coarsened signature map (analysis/psyq_sdk_sigs.json).
    sig_map_file = ROOT / "analysis" / "psyq_sdk_sigs.json"
    if sig_map_file.exists():
        import json as _json
        sdk = _json.loads(sig_map_file.read_text())
        rmap = {"p": "void *", "i": "int", "v": "void"}
        queue = _json.loads((ROOT / "analysis" / "asm_to_c_queue.json").read_text())
        for it in queue:
            nm = it.get("name", "")
            if nm in sdk:
                a = _n(it["start"])
                s = sdk[nm]
                astr = "void" if not s["args"] else ", ".join(rmap[x] for x in s["args"])
                sigs.append(f"{rmap[s['ret']]} sub_{a:08x}({astr});")
    out = TMP / "m2c_sig_ctx.c"
    out.write_text("\n".join(sigs) + "\n")
    _SIG_CTX = out
    return out


def _invoke_m2c(name: str, asm: Path, context: Path | None) -> str | None:
    cmd = [sys.executable, os.path.join(M2C_DIR, "m2c.py"),
           "-t", "mips-gcc-c", str(asm), "-f", name, "--globals", "used"]
    if context is not None:
        cmd += ["--context", str(context)]
    try:
        out = subprocess.run(cmd, cwd=M2C_DIR, capture_output=True,
                             text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return None
    return out.stdout if out.stdout.strip() else None


def _struct_context(name: str, raw1: str) -> str | None:
    """From a first m2c pass, build a context that types each pointer argument as
    a struct with `unk_` (inferrable) space, so a second pass recovers the exact
    field WIDTHS m2c otherwise drops in its `argN->unkHEX` notation."""
    m = re.search(r"^([^\n;{]*?" + re.escape(name) + r"\s*\(([^)]*)\))\s*\{",
                  raw1, re.M)
    if not m:
        return None
    proto, argstr = m.group(1), m.group(2)
    ret = proto[:proto.rindex(name)].strip() or "void"
    args = [] if argstr.strip() in ("", "void") else [a.strip() for a in argstr.split(",")]
    structs, newargs = [], []
    for a in args:
        am = re.match(r"(.*?)(\w+)\s*$", a)
        aname = am.group(2) if am else None
        offs = [int(h, 16) for h in re.findall(rf"\b{aname}->unk([0-9A-Fa-f]+)", raw1)] if aname else []
        if aname and offs:
            size = max(offs) + 16
            structs.append(f"struct S_{aname} {{ char unk_0[0x{size:x}]; }};")
            newargs.append(f"struct S_{aname} *{aname}")
        else:
            newargs.append(a)
    if not structs:
        return None
    return "\n".join(structs) + f"\n{ret} {name}({', '.join(newargs)});\n"


_BANKED: set[int] | None = None


def _banked_addrs() -> set[int]:
    """Addresses already reconstructed as C (segments.yml source ends in .c) --
    their signatures come from the signature context, so we don't re-feed their
    asm for cross-function inference."""
    global _BANKED
    if _BANKED is None:
        _BANKED = {_n(e["start"]) for e in P.SEG.get("attempted", [])
                   if str(e.get("source", "")).endswith(".c")}
    return _BANKED


def run_m2c(va: int) -> tuple[str, str] | None:
    """Return (fn_name, raw m2c C) or None. Uses a 2-pass width-recovery
    round-trip when the function accesses pointer-argument fields, and appends
    each unbanked direct callee's asm so m2c infers its signature from the body
    (lever #2: cross-function inference)."""
    fa = _full_asm(va)
    if fa is None:
        return None
    name, body = fa
    # lever #2: gather unbanked (still-.s) direct callees so m2c cross-infers
    # their signatures; banked callees are covered by the signature context.
    banked = _banked_addrs()
    blocks, seen = [], {va}
    for m in re.finditer(r"\bjal\s+sub_([0-9a-fA-F]+)", body):
        ca = int(m.group(1), 16)
        if ca in seen or ca in banked or not asm_path(ca):
            continue
        seen.add(ca)
        cfa = _full_asm(ca)
        if cfa:
            blocks.append(f"glabel {cfa[0]}\n{cfa[1]}")
    m2c_asm = TMP / f"m2c_{va:08x}.s"
    m2c_asm.write_text(f"glabel {name}\n{body}\n" + "\n\n".join(blocks) + "\n")
    sig = _signature_context()          # callee signatures (arg count / pointerness)
    raw = _invoke_m2c(name, m2c_asm, sig)
    if raw is None:
        return None
    if re.search(r"->unk[0-9A-Fa-f]+", raw):
        ctx = _struct_context(name, raw)
        if ctx:
            ctx_file = TMP / f"m2c_ctx_{va:08x}.c"
            ctx_file.write_text(sig.read_text() + "\n" + ctx)   # merge sig + struct
            raw2 = _invoke_m2c(name, m2c_asm, ctx_file)
            if raw2 and raw2.strip():
                raw = raw2
    return name, raw


def normalize(raw: str) -> tuple[str, bool]:
    """Strip m2c diagnostics, prepend the prelude; return (seed, has_struct_access).

    m2c interleaves human warnings (`Warning: ...`, `?` markers) into stdout; those
    lines are not C and must be removed before compiling.
    """
    keep = [ln for ln in raw.splitlines()
            if not re.match(r"\s*(Warning:|Error:|Note:)", ln)]
    src = "\n".join(keep)
    struct = bool(re.search(r"->unk[0-9A-Fa-f]+", src))
    # m2c renders an unknown/undeclared type as `?`. Concretize every type
    # position it appears in -> `int`. A type-placeholder `?` only ever sits at a
    # statement/return start, or immediately after `(`/`,` (cast or parameter);
    # a ternary `?` always has an operand before it, so these never collide.
    src = re.sub(r"^(\s*)\?(\s)", r"\1int\2", src, flags=re.M)   # ? var;  ? foo(  (decl/return)
    src = re.sub(r"([(,]\s*)\?", r"\1int", src)                  # (?  ,?  (**)-cast / param type
    # Global function-pointer call: m2c emits `*(T (**)(SIG))0xADDR(args)`, which
    # in GCC binds the call before the deref -> "called object is not a function".
    # Wrap the deref+cast: `(*(T (**)(SIG))0xADDR)(args)`.
    src = re.sub(r"\*(\([^()]*\(\*\*\)\([^()]*\)\))(0x[0-9A-Fa-f]+)\(",
                 r"(*\1\2)(", src)
    # Global pointer whose element type m2c dropped on a later use: it prints the
    # first access as `**(T **)0xADDR` but a reuse as `**(void *)0xADDR` (illegal
    # double-deref). Backfill each address's void form from its first typed form.
    typed = {addr: ty for ty, addr in
             re.findall(r"\*\*\((s8|u8|s16|u16|s32|u32) \*\*\)(0x[0-9A-Fa-f]+)", src)}
    for addr, ty in typed.items():
        src = src.replace(f"**(void *){addr}", f"**({ty} **){addr}")
    # Anchor literal global addresses to `g_<hex>` symbols. m2c inlines the raw
    # address, so GCC CSEs the base across repeated uses (1 instr short vs retail,
    # which reloads per use through a relocated symbol). Referencing a symbol
    # restores the per-use load and matches retail codegen.
    externs: dict[str, str] = {}

    def _dbl(m):  # **(T **)0xADDR  ->  (*g_addr)   [g_addr is a T* at that address]
        ty, a = m.group(1), m.group(2).lower()
        externs[f"g_{a[2:]}"] = f"extern {ty} *g_{a[2:]};"
        return f"(*g_{a[2:]})"

    def _sgl(m):  # *(T *)0xADDR  ->  g_addr        [g_addr is a T at that address]
        ty, a = m.group(1), m.group(2).lower()
        externs[f"g_{a[2:]}"] = f"extern {ty} g_{a[2:]};"
        return f"g_{a[2:]}"

    src = re.sub(r"\*\*\((s8|u8|s16|u16|s32|u32) \*\*\)(0x[0-9A-Fa-f]+)", _dbl, src)
    src = re.sub(r"\*\((s8|u8|s16|u16|s32|u32) \*\)(0x[0-9A-Fa-f]+)", _sgl, src)
    ext = "".join(v + "\n" for _, v in sorted(externs.items()))
    return PRELUDE + ext + src, struct


def evaluate(va: int) -> dict:
    r = run_m2c(va)
    if r is None:
        return {"va": va, "status": "m2c_fail"}
    name, raw = r
    seed, struct = normalize(raw)
    want = P._want_for(va)
    if want is None:
        return {"va": va, "name": name, "status": "no_want"}
    entry = next((e for e in P.SEG.get("attempted", [])
                  if _n(e["start"]) == va), None)
    sd = bool(entry and entry.get("small_data"))
    score = P.score(seed, va, want, sd)
    if score == 0:
        st, delta = "match", 0
    elif score != 9999:
        st, delta = "near", 0
    else:
        # distinguish a clean compile with the wrong size from a compile error
        st, delta = "cc_error", None
        tmp = SEEDS / f"_perm_{va:08x}.c"
        tmp.write_text(seed)
        try:
            b = P.compile_at(tmp, va, compiler_id="gcc2.7.2-psx",
                             cc1_flags=["-O2", "-G0", "-mcpu=3000", "-fno-builtin"],
                             maspsx_args=["--dont-expand-li", "--expand-div"], include_dirs=P.INC,
                             externs={}, small_data=sd, gp=0x80081d98,
                             cpp_args=P.PROF["cpp_args"], section_layout=None)
            if isinstance(b, bytes):
                st, delta = "size", len(b) - want
        except Exception:
            pass
        finally:
            tmp.unlink(missing_ok=True)
    return {"va": va, "name": name, "status": st, "words": score, "want": want,
            "delta": delta, "struct_access": struct, "seed": seed, "small_data": sd}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("addr", nargs="?")
    ap.add_argument("--emit", action="store_true", help="print the normalized seed")
    ap.add_argument("--save", action="store_true",
                    help="write the seed to analysis/dc_permuter_seeds/<addr>_m2c.c")
    ap.add_argument("--batch", metavar="CLASS",
                    help="sweep the unattempted pool (game|sdk_psyq|all) and tally")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    if args.batch:
        import json
        import yaml
        seg = yaml.safe_load((ROOT / "config" / "segments.yml").read_text())
        c = {_n(e["start"]) for e in seg.get("attempted", [])
             if str(e["source"]).endswith(".c")}
        deferred = {_n(k) for k in json.load(open(ROOT / "analysis" / "dc_deferred.json"))
                    if k.startswith("0x")}
        queue = {_n(it["start"]): it for it in
                 json.load(open(ROOT / "analysis" / "asm_to_c_queue.json"))
                 if it.get("ready")}
        pool = [va for va, it in sorted(queue.items())
                if va not in c and va not in deferred
                and (args.batch == "all" or it.get("classification") == args.batch)]
        if args.limit:
            pool = pool[:args.limit]
        tally: dict[str, int] = {}
        rows = []
        for va in pool:
            r = evaluate(va)
            tally[r["status"]] = tally.get(r["status"], 0) + 1
            rows.append(r)
            d = r.get("delta")
            dtxt = (f"{r['words']}w" if r["status"] == "near"
                    else (f"Δ{d:+d}" if d is not None else ""))
            print(f"  0x{va:08x} {'S' if r.get('struct_access') else ' '} "
                  f"{r['status']:9} {dtxt:>7} {r.get('name', '')}")
        print(f"\n=== {len(pool)} evaluated ===")
        for k in ("match", "near", "size", "cc_error", "m2c_fail", "no_want"):
            if k in tally:
                print(f"  {k:9} {tally[k]}")
        # closeness-ranked worklist: 0w matches, then small word-diffs, then small
        # size deltas -- these are the bankable/finishable candidates.
        cands = [r for r in rows if r["status"] in ("match", "near", "size")]
        def rank(r):
            if r["status"] == "match":
                return (0, 0)
            if r["status"] == "near":
                return (1, r["words"])
            return (2, abs(r["delta"]))
        print("\nWORKLIST (closest first — bank/finish these):")
        for r in sorted(cands, key=rank)[:40]:
            d = r.get("delta")
            dtxt = (f"{r['words']}w" if r["status"] == "near"
                    else ("0w" if r["status"] == "match" else f"Δ{d:+d}"))
            print(f"  0x{r['va']:08x} {r['status']:6} {dtxt:>6} "
                  f"{'[struct] ' if r.get('struct_access') else ''}{r['name']}")
        return 0

    if not args.addr:
        ap.error("addr or --batch required")
    va = int(args.addr, 16)
    r = evaluate(va)
    if r["status"] in ("m2c_fail", "no_want"):
        print(f"0x{va:08x}: {r['status']}")
        return 1
    print(f"0x{va:08x} {r['name']}: {r['status']} "
          f"({r.get('words','?')}w / want {r['want']}B)"
          f"{'  [struct_access]' if r['struct_access'] else ''}")
    if args.emit:
        print("\n" + r["seed"])
    if args.save:
        out = SEEDS / f"{va:08x}_m2c.c"
        out.write_text(r["seed"])
        print(f"wrote {out}")
    return 0 if r["status"] == "match" else 2


if __name__ == "__main__":
    raise SystemExit(main())
