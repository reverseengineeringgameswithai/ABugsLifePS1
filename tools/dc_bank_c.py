#!/usr/bin/env python3
"""dc bank helper: given a candidate C source for a function, run compiler_proof;
on a byte-exact MATCH, install it (src/main/<addr>_<name>.c), flip the segments.yml
entry .s -> .c (preserving start/end + adding externs/small_data), rebuild, and
validate SHA-1. Reverts on any failure. Usage:
  bank_c.py <addr_hex> <name> <c_src_path> [--extern n=va ...] [--small-data] [--profile P]
"""
import argparse, json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEG = ROOT / "config" / "segments.yml"


def sh(*cmd):
    return subprocess.run([str(c) for c in cmd], cwd=ROOT, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("addr"); ap.add_argument("name"); ap.add_argument("csrc")
    ap.add_argument("--extern", action="append", default=[])
    ap.add_argument("--small-data", action="store_true")
    ap.add_argument("--profile")
    a = ap.parse_args()
    addr = a.addr.lower().replace("0x", "")

    # 1. compiler_proof
    cmd = ["python3", "tools/compiler_proof.py", "--function", addr, "--source", a.csrc]
    for e in a.extern: cmd += ["--extern", e]
    if a.small_data: cmd.append("--small-data")
    if a.profile: cmd += ["--profiles", a.profile]
    r = sh(*cmd)
    if "-> MATCH" not in r.stdout:
        print(f"  NO MATCH {addr} {a.name}"); return 1

    # 2. install into src/main (author may already have written it there)
    dst = ROOT / "src" / "main" / f"{addr}_{a.name}.c"
    copied = Path(a.csrc).resolve() != dst.resolve()
    if copied:
        shutil.copy(a.csrc, dst)

    # 3. flip segments.yml .s -> .c (preserve start/end; add opts)
    txt = SEG.read_text(); lines = txt.splitlines()
    opts = ""
    if a.extern:
        opts += ", externs: {%s}" % ", ".join(
            f"{e.split('=')[0]}: {e.split('=')[1]}" for e in a.extern)
    if a.small_data:
        opts += ", small_data: true"
    if a.profile:
        opts += f", declaration_profile: {a.profile}"
    new, hit = [], False
    for ln in lines:
        m = re.search(rf"start: 0x0*{addr}\b.*end: (0x[0-9a-fA-F]+).*source: asm/hand_written/\S+\.s", ln)
        if m and not hit:
            end = m.group(1)
            new.append(f"  - {{start: 0x{addr}, end: {end}, source: src/main/{addr}_{a.name}.c{opts}}}")
            hit = True
        else:
            new.append(ln)
    if not hit:
        print(f"  ERR: no .s segments line for {addr}");
        (dst.unlink() if copied else None); return 1
    SEG.write_text("\n".join(new) + "\n")

    # 4. build + validate
    sh("python3", "tools/build_psx_exe.py")
    v = sh("python3", "tools/validate_build.py")
    if "PASS" in v.stdout:
        print(f"  BANKED {addr} {a.name}")
        return 0
    # revert
    SEG.write_text(txt)
    if copied:
        dst.unlink()
    print(f"  VALIDATE FAIL {addr} {a.name} -> reverted:\n{v.stdout[-200:]}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
