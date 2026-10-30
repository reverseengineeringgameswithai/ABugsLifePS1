#!/usr/bin/env python3
"""Generate analysis/psyq_sdk_sigs.json -- a COARSENED PsyQ SDK signature map for
the m2c seed pipeline (lever #1).

For each well-known PsyQ library function we record only the *ABI shape* the caller
needs: whether the return and each argument is a pointer or a scalar. `dc_m2c_seed`
emits `<ret> sub_<hex>(<args>);` for any pool function whose census name matches a
key here, so m2c uses the right arg count / pointer-ness instead of guessing.

Cleanroom: these are interface FACTS (arg counts, pointer-vs-scalar) for the public
PsyQ API, cross-checked against the open-licensed PSn00bSDK / PsyCross headers.
NO struct layouts, macros, or code are copied -- struct field WIDTHS come from our
own binary-derived round-trip. Only functions whose signature is standard and
unambiguous are listed; internal `_`-prefixed and RE-named functions are left to
cross-function inference (lever #2).

  python tools/dc_m2c_sdk_sigs.py         # (re)write analysis/psyq_sdk_sigs.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# name -> (ret, [arg, ...])   where each is "p" (pointer) or "i" (scalar/void).
# Return "v" == void. Verified against PSn00bSDK psxgpu/psxgte/psxcd/psxspu headers.
_SIGS: dict[str, tuple[str, list[str]]] = {
    # libgpu
    "DrawSync":       ("i", ["i"]),
    "DrawOTag":       ("i", ["p"]),
    "DrawOTagEnv":    ("p", ["p", "p"]),
    "ResetGraph":     ("i", ["i"]),
    "SetDefDrawEnv":  ("p", ["p", "i", "i", "i", "i"]),
    "SetDefDispEnv":  ("p", ["p", "i", "i", "i", "i"]),
    "ClearOTagR":     ("p", ["p", "i"]),
    "ClearOTag":      ("p", ["p", "i"]),
    "FntLoad":        ("i", ["i", "i"]),
    "FntOpen":        ("i", ["i", "i", "i", "i", "i", "i"]),
    "FntFlush":       ("p", ["i"]),
    # libgte
    "RotMatrix":      ("p", ["p", "p"]),
    # libcd
    "CdInit":         ("i", []),
    "CdReadSync":     ("i", ["i", "p"]),
    "CdControl":      ("i", ["i", "p", "p"]),
    "CdControlB":     ("i", ["i", "p", "p"]),
    "CdControlF":     ("i", ["i", "p"]),
    "CdRead":         ("i", ["i", "p", "i"]),
    "CdReadBreak":    ("i", []),
    "CdGetToc2":      ("i", ["p"]),
    "CdIntToPos":     ("p", ["i", "p"]),
    "CdDataSync":     ("i", ["i"]),
}

_MAP = {"p": "void *", "i": "int", "v": "void"}


def coarse(name: str) -> tuple[str, str] | None:
    """Return (ret_type, args_str) for a known name, or None."""
    if name not in _SIGS:
        return None
    ret, args = _SIGS[name]
    astr = "void" if not args else ", ".join(_MAP[a] for a in args)
    return _MAP[ret], astr


def main() -> int:
    out = {k: {"ret": v[0], "args": v[1]} for k, v in _SIGS.items()}
    (ROOT / "analysis" / "psyq_sdk_sigs.json").write_text(
        json.dumps(out, indent=1) + "\n")
    print(f"wrote {len(out)} coarsened PsyQ signatures -> analysis/psyq_sdk_sigs.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
