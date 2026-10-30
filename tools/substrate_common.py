"""Shared helpers for the decomp substrate (docs/SUBSTRATE.md).

Loads config/segments.yml, resolves the cross toolchain, and builds one
attempted function at its original VA into raw bytes. Two front-ends share the
same assemble tail (as -> ld @VA -> objcopy):
  assemble_at  hand-written .s  (asm path)
  compile_at   src/main/*.c     (C path: era cpp/cc1 -> maspsx -> tail)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SEGMENTS = ROOT / "config" / "segments.yml"
LINKER = ROOT / "config" / "linker.ld"
LINKER_SPLIT = ROOT / "config" / "linker_split.ld"
DECLARATION_PROFILES = ROOT / "config" / "declaration_profiles.yml"
BUILD = ROOT / "build" / "substrate"
HANDWRITTEN = ROOT / "asm" / "hand_written"
NONMATCHINGS = ROOT / "asm" / "nonmatchings"
TOOLCHAIN_MANIFEST = ROOT / "tools" / "toolchain_manifest.json"

PREFIX = os.environ.get("ABL_MIPS_PREFIX", "mips64-linux-gnu-")
AS_FLAGS = ["-march=mips1", "-mabi=32", "-EL", "-no-pad-sections", "-G0"]

# C path (era compiler + maspsx). Binaries live outside the repo; override roots.
OLDGCC_DIR = Path(os.environ.get("ABL_OLDGCC_DIR",
                                 os.path.expanduser("~/abl-toolchain/old-gcc")))
MASPSX = Path(os.environ.get("ABL_MASPSX",
                             os.path.expanduser("~/abl-toolchain/maspsx/maspsx.py")))


def tool(name: str) -> str:
    exe = PREFIX + name
    if shutil.which(exe) is None:
        raise SystemExit(f"cross tool not found: {exe} (set ABL_MIPS_PREFIX)")
    return exe


def toolchain_available() -> bool:
    return all(shutil.which(PREFIX + t) for t in ("as", "ld", "objcopy"))


def load_toolchain_manifest() -> dict:
    return json.loads(TOOLCHAIN_MANIFEST.read_text())


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def external_header_evidence(path: Path) -> dict:
    """Return hash-only evidence for an external header tree."""
    if not path.is_dir():
        raise RuntimeError(f"external PsyQ include directory does not exist: {path}")
    files = sorted(p for p in path.rglob("*") if p.is_file())
    rows = [{"path": p.relative_to(path).as_posix(), "sha256": _sha256_file(p)}
            for p in files]
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode("ascii")).hexdigest()
    return {"file_count": len(rows), "tree_sha256": digest, "files": rows}


def load_declaration_profiles() -> dict:
    doc = yaml.safe_load(DECLARATION_PROFILES.read_text())
    if doc.get("schema_version") != 1 or not isinstance(doc.get("profiles"), dict):
        raise RuntimeError(f"invalid declaration profile config: {DECLARATION_PROFILES}")
    return doc


def resolve_declaration_profile(name: str | None) -> dict:
    """Resolve cpp args/include roots and hash-only evidence for one profile."""
    doc = load_declaration_profiles()
    name = name or doc["default"]
    if name not in doc["profiles"]:
        raise RuntimeError(f"unknown declaration profile {name!r}; "
                           f"known: {sorted(doc['profiles'])}")
    rec = dict(doc["profiles"][name] or {})
    include_dirs = [ROOT / "include", ROOT]
    evidence = {"profile": name, "description": rec.get("description", "")}
    env_name = rec.get("external_include_env")
    if env_name:
        value = os.environ.get(env_name)
        if not value:
            raise RuntimeError(f"declaration profile {name!r} requires ${env_name}")
        external = Path(value).expanduser().resolve()
        include_dirs.append(external)
        evidence["external_headers"] = external_header_evidence(external)
    return {"name": name, "cpp_args": list(rec.get("cpp_args") or []),
            "include_dirs": include_dirs, "evidence": evidence}


def compiler_dir(compiler_id: str) -> Path:
    """Absolute dir of the era compiler's cc1/cpp for `compiler_id`."""
    man = load_toolchain_manifest()
    rec = next((c for c in man["compilers"] if c["id"] == compiler_id), None)
    if rec is None:
        raise SystemExit(f"unknown compiler id {compiler_id!r} "
                         f"(known: {[c['id'] for c in man['compilers']]})")
    # manifest dir is "old-gcc/gcc-<ver>-psx"; OLDGCC_DIR points at the "old-gcc" level
    return OLDGCC_DIR / Path(rec["dir"]).name


def c_toolchain_available(compiler_id: str | None = None) -> bool:
    if not (MASPSX.exists() and toolchain_available()):
        return False
    if compiler_id is None:
        return OLDGCC_DIR.is_dir()
    d = compiler_dir(compiler_id)
    return (d / "cc1").exists() and (d / "cpp").exists()


def load_segments() -> dict:
    seg = yaml.safe_load(SEGMENTS.read_text())
    seg.setdefault("attempted", [])
    for a in seg["attempted"] or []:
        for k in ("start", "end"):
            if isinstance(a[k], str):
                a[k] = int(a[k], 16)
        for section in (a.get("sections") or {}).values():
            for k in ("start", "end"):
                if isinstance(section.get(k), str):
                    section[k] = int(section[k], 16)
        for part in a.get("parts") or []:
            if isinstance(part.get("start"), str):
                part["start"] = int(part["start"], 16)
    return seg


def sha1(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


_CENSUS_SYMS: dict[str, int] | None = None
# address-anchored stub names: <prefix>_<8 hex> -> that VA (e.g. sub_8002b424,
# g_80082402, D_800a7e48). Lets a C source reference an engine symbol whose
# meaning is unknown without an explicit externs entry.
_ANCHOR_RE = re.compile(r"^(?:sub|func|loc|g|D|dat)_((?:80|1f)[0-9a-fA-F]{6})$")


def _census_symbols() -> dict[str, int]:
    """Resident named functions from the census: {name: VA}. Cached."""
    global _CENSUS_SYMS
    if _CENSUS_SYMS is None:
        _CENSUS_SYMS = {}
        p = ROOT / "analysis" / "functions.json"
        if p.exists():
            for r in json.loads(p.read_text())["functions"]:
                if r["space"] == "resident" and r["name"] and not r["name"].startswith("FUNC_"):
                    _CENSUS_SYMS[r["name"]] = int(r["start"], 16)
    return _CENSUS_SYMS


def _resolve_symbol(name: str, externs: dict) -> int | None:
    """Priority: explicit externs > census function name > address-in-name."""
    if name in externs:
        a = externs[name]
        return a if isinstance(a, int) else int(a, 16)
    syms = _census_symbols()
    if name in syms:
        return syms[name]
    m = _ANCHOR_RE.match(name)
    if m:
        return int(m.group(1), 16)
    return None


def _undefined_symbols(obj: Path) -> list[str]:
    p = subprocess.run([tool("nm"), "-u", str(obj)], capture_output=True, text=True)
    if p.returncode != 0:
        return []
    out = []
    for ln in p.stdout.splitlines():
        parts = ln.split()
        if parts and parts[0] == "U" and len(parts) == 2:
            out.append(parts[1])
        elif len(parts) == 2 and parts[0] == "U":
            out.append(parts[1])
    return out


def _assemble_tail(s_source: Path, va: int, include_dirs: list[Path] | None,
                   externs: dict | None = None, *,
                   small_data: bool = False, gp: int | None = None) -> bytes:
    """Assemble+link one gnu-as .s at `va` -> raw .text bytes (objcopy -O binary).

    Undefined symbols (jal targets, absolute-addressed globals) are auto-resolved
    to their VA via _resolve_symbol (explicit `externs` > census function name >
    address-anchored name). An unresolved symbol is a clear error.

    substrate v2 (opt-in per entry):
    - small_data=True assembles with the small-data threshold -G8 (matching a
      cc1 -G8 compile) so `lw $2,sym` macros expand to gp-relative
      (%gprel/R_MIPS_GPREL16) instead of absolute lui/lw.
    - gp (=_gp) is defined at link so those R_MIPS_GPREL16 relocations resolve;
      harmless (unreferenced) for absolute/-G0 functions."""
    externs = externs or {}
    as_flags = ["-G8" if f == "-G0" else f for f in AS_FLAGS] if small_data else AS_FLAGS
    with tempfile.TemporaryDirectory(prefix="ablsub_") as td:
        obj, elf, raw = (Path(td) / n for n in ("f.o", "f.elf", "f.bin"))
        inc = sum((["-I", str(d)] for d in include_dirs or []), [])
        p = subprocess.run([tool("as"), *as_flags, *inc, "-o", str(obj), str(s_source)],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"as failed on {s_source.name}:\n{p.stderr}")
        defsyms, unresolved = [f"--defsym=__va={va:#x}"], []
        if gp is not None:
            defsyms.append(f"--defsym=_gp={gp:#x}")
        for name in _undefined_symbols(obj):
            addr = _resolve_symbol(name, externs)
            if addr is None:
                unresolved.append(name)
            else:
                defsyms.append(f"--defsym={name}={addr:#x}")
        if unresolved:
            raise RuntimeError(
                f"unresolved symbol(s) in {s_source.name}: {', '.join(unresolved)} "
                f"— add to the entry's `externs` map or use an address-anchored "
                f"name (e.g. sub_<hex>/g_<hex>).")
        for argv in (
            # --section-start pins the output `.out` at the function's true VA so
            # R_MIPS_26 relocations against a LOCAL label (internal `j`, jr-table
            # jump tables) resolve correctly. `--defsym __va` alone does NOT reach
            # the linker-script `DEFINED(__va)?__va:...` ternary, so the section
            # would otherwise land at the 0x80010000 default; harmless for
            # position-independent code (branches / absolute-external %hi-%lo /
            # jal) but wrong for any self-referential addressing (substrate v2).
            [tool("ld"), "-m", "elf32ltsmip", "-T", str(LINKER), *defsyms,
             f"--section-start=.out={va:#x}",
             "-e", f"{va:#x}", "-o", str(elf), str(obj)],
            [tool("objcopy"), "-O", "binary", str(elf), str(raw)],
        ):
            p = subprocess.run(argv, capture_output=True, text=True)
            if p.returncode != 0:
                raise RuntimeError(f"{argv[0]} failed on {s_source.name}:\n{p.stderr}")
        return raw.read_bytes()


def _assemble_split_tail(s_source: Path, section_layout: dict,
                         include_dirs: list[Path] | None,
                         externs: dict | None = None, *,
                         small_data: bool = False,
                         gp: int | None = None) -> dict[str, bytes]:
    """Assemble/link with independently placed text, rdata, and data outputs."""
    externs = externs or {}
    as_flags = ["-G8" if f == "-G0" else f for f in AS_FLAGS] if small_data else AS_FLAGS
    section_names = {"text": ".textout", "rdata": ".rdataout", "data": ".dataout"}
    with tempfile.TemporaryDirectory(prefix="ablsub_split_") as td:
        td = Path(td)
        obj, elf = td / "f.o", td / "f.elf"
        inc = sum((["-I", str(d)] for d in include_dirs or []), [])
        p = subprocess.run([tool("as"), *as_flags, *inc, "-o", str(obj), str(s_source)],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"as failed on {s_source.name}:\n{p.stderr}")
        defsyms, unresolved = [], []
        for key in section_names:
            if key in section_layout:
                defsyms.append(f"--defsym=__{key}_va={section_layout[key]['start']:#x}")
        if gp is not None:
            defsyms.append(f"--defsym=_gp={gp:#x}")
        for name in _undefined_symbols(obj):
            addr = _resolve_symbol(name, externs)
            if addr is None:
                unresolved.append(name)
            else:
                defsyms.append(f"--defsym={name}={addr:#x}")
        if unresolved:
            raise RuntimeError(f"unresolved symbol(s) in {s_source.name}: "
                               f"{', '.join(unresolved)}")
        p = subprocess.run([tool("ld"), "-m", "elf32ltsmip", "-T", str(LINKER_SPLIT),
                            *defsyms, "-o", str(elf), str(obj)],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"ld failed on {s_source.name}:\n{p.stderr}")
        outputs: dict[str, bytes] = {}
        for key, out_section in section_names.items():
            if key not in section_layout:
                continue
            raw = td / f"f_{key}.bin"
            p = subprocess.run([tool("objcopy"), "-O", "binary", "-j", out_section,
                                str(elf), str(raw)], capture_output=True, text=True)
            if p.returncode != 0:
                raise RuntimeError(f"objcopy failed on {s_source.name} {key}:\n{p.stderr}")
            outputs[key] = raw.read_bytes() if raw.exists() else b""
        return outputs


def assemble_at(source: Path, va: int, include_dirs: list[Path] | None = None,
                externs: dict | None = None, *,
                small_data: bool = False, gp: int | None = None) -> bytes:
    """Asm path: assemble+link one hand-written .s at `va` -> raw bytes."""
    return _assemble_tail(source, va, include_dirs, externs,
                          small_data=small_data, gp=gp)


def compile_at(source: Path, va: int, *, compiler_id: str, cc1_flags: list[str],
               maspsx_args: list[str] | None = None,
               include_dirs: list[Path] | None = None,
               externs: dict | None = None,
               small_data: bool = False, gp: int | None = None,
               cpp_args: list[str] | None = None,
               section_layout: dict | None = None) -> bytes | dict[str, bytes]:
    """C path: cpp -> cc1 -S -> maspsx -> the shared assemble tail -> raw bytes.

    small_data=True swaps the cc1 -G0 threshold for -G8 so small globals are
    addressed gp-relative (matched by the -G8 assemble tail + _gp defsym)."""
    if small_data:
        cc1_flags = ["-G8" if f == "-G0" else f for f in cc1_flags]
    cdir = compiler_dir(compiler_id)
    cpp, cc1 = cdir / "cpp", cdir / "cc1"
    if not cpp.exists() or not cc1.exists():
        raise SystemExit(f"era compiler {compiler_id} missing at {cdir} "
                         f"(set ABL_OLDGCC_DIR; see tools/toolchain_manifest.json)")
    inc = sum((["-I", str(d)] for d in include_dirs or []), [])
    with tempfile.TemporaryDirectory(prefix="ablc_") as td:
        i, s, gas = (Path(td) / n for n in ("f.i", "f.s", "f_gas.s"))
        # cpp: preprocess
        p = subprocess.run([str(cpp), *(cpp_args or []), *inc, str(source), str(i)],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"cpp failed on {source.name}:\n{p.stderr}")
        # cc1: compile to MIPS asm
        p = subprocess.run([str(cc1), *cc1_flags, "-quiet", str(i), "-o", str(s)],
                           capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"cc1 failed on {source.name}:\n{p.stderr}")
        # maspsx: ASPSX-semantics translation to gnu-as input
        p = subprocess.run(["python3", str(MASPSX), *(maspsx_args or [])],
                           stdin=s.open(), capture_output=True, text=True)
        if p.returncode != 0:
            raise RuntimeError(f"maspsx failed on {source.name}:\n{p.stderr}")
        gas.write_text(p.stdout)
        if section_layout:
            return _assemble_split_tail(gas, section_layout, include_dirs, externs,
                                        small_data=small_data, gp=gp)
        return _assemble_tail(gas, va, include_dirs, externs,
                              small_data=small_data, gp=gp)


def build_entry(entry: dict, seg: dict, include_dirs: list[Path] | None = None) -> bytes | dict[str, bytes]:
    """Dispatch an `attempted` entry to the asm or C path by source extension.

    Per-entry `small_data: true` opts into the gp-relative path (substrate v2):
    -G8 compile+assemble + `_gp` (from the top-level `gp:` in segments.yml)."""
    src = ROOT / entry["source"]
    if not src.exists():
        raise SystemExit(f"attempted source missing: {src}")
    externs = entry.get("externs")
    small_data = bool(entry.get("small_data"))
    gp = seg.get("gp")
    if isinstance(gp, str):
        gp = int(gp, 16)
    if src.suffix == ".c":
        ct = seg.get("c_toolchain") or {}
        if not ct:
            raise SystemExit("segments.yml has a .c entry but no c_toolchain block")
        profile = resolve_declaration_profile(entry.get("declaration_profile"))
        all_includes = [*(include_dirs or []), *profile["include_dirs"]]
        return compile_at(src, entry["start"], compiler_id=ct["compiler"],
                          cc1_flags=ct["cc1_flags"],
                          maspsx_args=ct.get("maspsx_args", []),
                          include_dirs=all_includes, externs=externs,
                          small_data=small_data, gp=gp,
                          cpp_args=profile["cpp_args"],
                          section_layout=entry.get("sections"))
    data = assemble_at(src, entry["start"], include_dirs=include_dirs, externs=externs,
                       small_data=small_data, gp=gp)
    if not entry.get("parts"):
        return data

    position = entry["start"] + len(data)
    chunks = [data]
    for part in entry["parts"]:
        part_start = part["start"]
        if part_start != position:
            raise RuntimeError(
                f"non-contiguous assembly parts for {entry['source']}: "
                f"expected {position:#x}, got {part_start:#x}")
        part_source = ROOT / part["source"]
        if not part_source.exists():
            raise SystemExit(f"attempted part source missing: {part_source}")
        chunk = assemble_at(part_source, part_start, include_dirs=include_dirs,
                            externs=externs, small_data=small_data, gp=gp)
        chunks.append(chunk)
        position += len(chunk)
    return b"".join(chunks)


def original_exe(seg: dict) -> bytes:
    exe = (ROOT / seg["image"]).read_bytes()
    got = sha1(exe)
    if got != seg["sha1"]:
        raise SystemExit(f"original {seg['image']} sha1 {got} != manifest {seg['sha1']}")
    return exe


def va_to_off(seg: dict, va: int) -> int:
    return va - seg["load_va"] + seg["header_bytes"]
