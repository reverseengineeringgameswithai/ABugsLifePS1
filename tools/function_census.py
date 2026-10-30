#!/usr/bin/env python3
"""Whole-image function census — canonical machine-readable function inventory.

Merges every discovery signal the project has into ONE committed artifact set
(bytes-free metadata only — addresses/sizes/edges/names, never instruction bytes):

  analysis/functions.json    canonical census (resident EXE + every overlay)
  analysis/functions.csv     flat projection for grepping/spreadsheets
  analysis/code_coverage.md  coverage/confidence report (vault-quotable)

Signals (each tagged in the per-function `discovery` list):
  symbol     symbols/re_symbols.sym (authoritative names; *_OBJ_* interior labels
             are basic-block markers inside SDK functions, NOT starts)
  entry      PS-X EXE entry point (crt0)
  r2         radare2 aflj ranges (extracted/re_baseline/functions.json + overlays/)
  psyq       PsyQ 4.0.0 signature matches (extracted/re_baseline/psyq_matches.csv)
  ghidra     extracted/re_baseline/ghidra_functions.csv (when exported)
  jal_target every direct `jal` in the image (opcode 3), decoded + filtered
  j_target   direct `j` to a known start (tail-call edge source)
  prologue   `addiu sp,sp,-N` with a `sw ra,off(sp)` in the next few words
  jumptable  targets read from KNOWN jr-dispatch tables (see JUMP_TABLES)
  reachable  BFS over the call graph from entry + jump-table roots
  dynamic    analysis/traces/function_hits.csv entry-PC hits (when present)

False-positive filters: r2 string ranges (izzj), KNOWN data anchors
(DATA_ANCHORS), word alignment, text-range bounds.

Determinism: no timestamps; stable sort; `inputs` records the sha256 of every
input actually consumed, so identical inputs => byte-identical outputs.

Overlay handling: LEVEL*.BIN carry a 4-byte header/ID word at +0 — code starts
at region base + 4 (`level_overlay_init`); r2 hits at the bare base are
remapped. Same-VA collisions across overlays are legal: the census key is
(space, overlay, start).

Usage:  python tools/re_baseline.py --all   (refresh inputs)
        python tools/function_census.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import exe_read  # noqa: E402

OUT = ROOT / "extracted" / "re_baseline"
ANALYSIS = ROOT / "analysis"
SYMBOLS = ROOT / "symbols" / "re_symbols.sym"
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
BASELINES = ROOT / "tools" / "build_baselines.json"
TRACE_HITS = ANALYSIS / "traces" / "function_hits.csv"
EXTENT_OVERRIDES = ANALYSIS / "extent_overrides.json"

TEXT_LO = exe_read.LOAD_VA                       # 0x80010000
TEXT_HI = exe_read.LOAD_VA + exe_read.TEXT_SIZE  # 0x80082800 (exclusive)
REGION_A = 0x800B39A0
REGION_B = 0x800B5788
OVERLAY_HDR = 4          # LEVEL*.BIN: [+0]=ID word, code entry at +4
RAM_HI = 0x80200000

# Known jr-dispatch tables (docs/EXECUTABLE_AND_OVERLAYS.md, src_re/*): the
# census reads consecutive words while they decode to text addresses (cap 64).
JUMP_TABLES = {
    0x8001B1C0: "berry_throw_jump_table",
    0x8001B2F4: "mover_vm_opcode_table",
    0x8001B3C4: "main_shell_substate_table",
    0x8001B828: "state_handler_table_8001b828",
}
# Known data-in-text anchors that must never sit at/around a census code START.
DATA_ANCHORS = {**JUMP_TABLES, 0x8007FD00: "psyq_copyright_string",
                0x80078D84: "resident_table_gap_golddrop_cave"}

# Resident gp-relative BSS/globals live at the tail of the text image (from the
# gp base `runtime_gp` up to TEXT_HI). r2/symbols mis-emit each named global as a
# "function START", so these get range_type:code by default — but they are DATA
# (G_* pointers, master_game_state, current_scene_id, …). Records at/above this
# boundary in the resident space are reclassified data (see RCA a5 / AUDIT-23).
RESIDENT_DATA_TAIL_LO = 0x80081D98

# r2-only resident starts that were verified to be lookup data, not functions.
# Each has no callers/callees or return; their monotonic halfword payloads merely
# decode as legal MIPS words. Keep this explicit rather than weakening the code
# detector for legitimate returnless callbacks/tail calls.
_RESIDENT_DATA_OVERRIDE = {
    0x80017DB4: "resident pseudo-random/noise byte table",
    0x8001A900: "resident pointer/string table (address words, no executable flow)",
    0x80074970: "monotonic halfword lookup table (no callers/callees/return)",
    0x800749A8: "VAB/sample metadata table; prior vab_bank_stage name retracted",
    0x8007564C: "continuation of VAB/sample metadata table",
    0x800769A8: "VAB/sample metadata table; prior vab_bank_stage_69a8 name retracted",
    0x80078B54: "monotonic fixed-point lookup table",
    0x8007D5C0: "monotonic signed-halfword lookup table; jal-like word is data",
    0x8007D8B0: "continuation word of monotonic signed-halfword lookup table",
    0x8007D8B4: "continuation of monotonic signed-halfword lookup table",
    0x8007D9E0: "continuation of monotonic signed-halfword lookup table",
    0x8007E7C4: "lookup-table words that decode as backward branches",
    0x8007E7CC: "lookup-table words that decode as backward branches",
    0x8007E7D4: "lookup-table words that decode as backward branches",
    0x8007E7DC: "monotonic opcode/ordinal table (contains impossible jalr zero,zero)",
    0x8007E810: "continuation of monotonic opcode/ordinal lookup table",
    # sc-2: single 0x00000000 alignment-padding words r2 emitted as function starts
    # (4 B each, all-zero, no callers/callees/return) between real functions.
    0x8005F758: "inter-function alignment padding (single 0x00000000 word)",
    0x8005F798: "inter-function alignment padding (single 0x00000000 word)",
    0x800653CC: "inter-function alignment padding (single 0x00000000 word)",
    0x800653D0: "inter-function alignment padding (single 0x00000000 word)",
    0x80065F38: "inter-function alignment padding (single 0x00000000 word)",
    0x800667E8: "inter-function alignment padding (single 0x00000000 word)",
    0x800667F8: "inter-function alignment padding (single 0x00000000 word)",
    0x800668A8: "inter-function alignment padding (single 0x00000000 word)",
    # sc-2 final: word-pairs r2 mis-disassembled as functions (invalid R3000 funct
    # fields; 0 callers) inside PsyQ lib / BIOS-thunk regions.
    0x800600C4: "constant data pair in libgte object (invalid opcode words)",
    0x800653B4: "constant data pair between v_wait and padding (invalid opcode words)",
    0x80065F1C: "data words inside the A0-table BIOS thunk table (not a thunk)",
}

# The resident libpad block did not match the available PsyQ 4.0 signature
# library, but its public exports, hardware accesses, and object sizes match the
# PsyQ 4.x LIBPAD modules exactly. Keep the SDK classification independent of
# whether every local callback has acquired a descriptive symbol yet.
_RESIDENT_SDK_RANGES = (
    (0x8006607C, 0x800661E8, "PsyQ LIBAPI root-counter functions"),
    (0x800718E0, 0x80074970, "PsyQ 4.x LIBPAD controller library"),
)


# Overlay code fns that legitimately have no `jr ra`/`jal` (pure tail-call via `j`)
# and would otherwise trip the data detector. Verified real code by disassembly.
_OVERLAY_CODE_OVERRIDE = {("LEVEL08_LEVEL1", 0x800B3B70)}

# Overlay spans r2 emitted as function starts that are actually DATA (a jal-looking
# word with an out-of-RAM target fools the permissive detector). Verified data by
# disassembly (pointer tables of gp-globals; never executed in any pristine trace).
_OVERLAY_DATA_OVERRIDE = {
    ("LEVEL01_LEVEL", 0x800B3F54),    # 55-word gp-global ptr table
    ("MEMORY", 0x800BD898),           # 844-word data table (incrementing-index; 0 jr-ra/jal,
}                                     # never executes across all menu screens - u3 live capture)


def _span_returns(img, s: int, e: int) -> bool:
    """True if the span contains a `jr ra` (0x03e00008) — i.e. it returns like a
    function. Metadata/VM/dispatch DATA tables named in re_symbols.sym do not."""
    for a in range(s, e, 4):
        if img.word(a) == 0x03E00008:
            return True
    return False


def _span_is_code(img, s: int, e: int, overlay: str | None = None) -> bool:
    """A real function must return (`jr ra` = 0x03e00008) or call (`jal`). Pointer
    tables (0x800xxxxx words) and embedded strings never contain either, so a
    >=32B span with neither is DATA — even if a stray data word happens to decode
    as a branch (which the weaker any-control-flow test was fooled by)."""
    if (overlay, s) in _OVERLAY_CODE_OVERRIDE:
        return True
    for a in range(s, e, 4):
        w = img.word(a)
        if w is None:
            continue
        if w == 0x03E00008:                          # jr ra (return)
            return True
        if (w >> 26) == 3:                           # jal
            return True
    return False

OP_J, OP_JAL = 2, 3


# ------------------------------------------------------------------ inputs
def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def load_symbols() -> dict[int, str]:
    out = {}
    for ln in SYMBOLS.read_text().splitlines():
        mo = re.match(r"^([0-9A-Fa-f]{8})\s+(\S+)", ln)
        if mo:
            out[int(mo.group(1), 16)] = mo.group(2)
    return out


def load_csv_map(path: Path) -> dict[int, str]:
    if not path.exists():
        return {}
    with path.open() as f:
        return {int(r["address"], 16): r["name"] for r in csv.DictReader(f)}


LEVEL_COVERAGE = ANALYSIS / "traces" / "level_coverage.json"


def load_trace_hits() -> set[int]:
    """Addresses that EXECUTED at runtime -> the `dynamic` signal (confidence=
    confirmed). Two sources: the boot-anchor CSV (tools/trace_boot_baseline.py)
    and the per-level range-coverage (tools/trace_level_coverage.py)."""
    hits: set[int] = set()
    if TRACE_HITS.exists():
        with TRACE_HITS.open() as f:
            hits |= {int(r["address"], 16) for r in csv.DictReader(f)}
    if LEVEL_COVERAGE.exists():
        cov = json.loads(LEVEL_COVERAGE.read_text())
        hits |= {int(a, 16) for a in (cov.get("function_levels") or {})}
    return hits


def load_extent_overrides() -> dict[int, int]:
    """Manual start->end extent corrections (analysis/extent_overrides.json).

    r2's `realsz` truncates a switch dispatcher at its jr-table, splitting one
    real function into a small head + a `gap_code` tail. An override pins the
    real `end` so the head absorbs its case bodies (the gap-recovery only fires
    on *uncovered* jal sites). RESIDENT space only; applied deterministically."""
    if not EXTENT_OVERRIDES.exists():
        return {}
    doc = json.loads(EXTENT_OVERRIDES.read_text())
    return {int(k, 16): int(v["end"], 16) for k, v in (doc.get("overrides") or {}).items()}


def string_ranges(lo: int, hi: int) -> list[tuple[int, int]]:
    strings = json.loads((OUT / "strings.json").read_text())
    spans = sorted((s["vaddr"], s["vaddr"] + s.get("size", 0)) for s in strings
                   if lo <= s.get("vaddr", 0) < hi)
    merged: list[list[int]] = []
    for a, b in spans:
        if merged and a <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(a, b) for a, b in merged]


def in_ranges(addr: int, ranges: list[tuple[int, int]]) -> bool:
    for a, b in ranges:
        if a <= addr < b:
            return True
    return False


# ------------------------------------------------------------- word decode
class Image:
    """One mapped code image (resident text or an overlay blob)."""

    def __init__(self, data: bytes, base: int, code_lo: int):
        self.data = data
        self.base = base          # VA of data[0]
        self.lo = code_lo         # first legal code VA
        self.hi = base + len(data)

    def word(self, va: int) -> int | None:
        off = va - self.base
        if 0 <= off <= len(self.data) - 4:
            return struct.unpack_from("<I", self.data, off)[0]
        return None

    def words(self):
        lo = self.lo + ((4 - (self.lo - self.base) % 4) % 4)
        for va in range(lo, self.hi - 3, 4):
            yield va, struct.unpack_from("<I", self.data, va - self.base)[0]


def scan_image(img: Image, call_lo: int, call_hi: int):
    """One pass: jal/j call sites, prologue candidates, jr/j end markers."""
    jal_sites: dict[int, list[int]] = {}
    j_sites: dict[int, list[int]] = {}
    prologues: set[int] = set()
    sw_ra: set[int] = set()
    ends: set[int] = set()          # VA of `jr rs` / `j` instructions
    for va, w in img.words():
        op = w >> 26
        if op in (OP_J, OP_JAL):
            tgt = 0x80000000 | ((w & 0x03FFFFFF) << 2)
            if call_lo <= tgt < call_hi:
                (jal_sites if op == OP_JAL else j_sites).setdefault(tgt, []).append(va)
            if op == OP_J:
                ends.add(va)
        elif (w & 0xFFFF8000) == 0x27BD8000:      # addiu sp,sp,-N
            prologues.add(va)
        elif (w & 0xFFFF0000) == 0xAFBF0000:      # sw ra, off(sp)
            sw_ra.add(va)
        if op == 0 and (w & 0x3F) == 0x08:        # jr rs (any register)
            ends.add(va)
    # prologue heuristic: addiu sp,-N with a sw ra within the next 8 words
    strong_prologues = {va for va in prologues
                        if any((va + 4 * i) in sw_ra for i in range(1, 9))}
    return jal_sites, j_sites, strong_prologues, ends


def jump_table_targets(img: Image) -> dict[int, str]:
    """Read the known jr-dispatch tables; stop at the first non-text word."""
    out: dict[int, str] = {}
    for table, name in JUMP_TABLES.items():
        for i in range(64):
            w = img.word(table + 4 * i)
            if w is None or not (TEXT_LO <= w < TEXT_HI) or w % 4:
                break
            out[w] = name
    return out


# ------------------------------------------------------------------ census
def build_space(img: Image, *, space: str, overlay: str | None, syms: dict[int, str],
                r2_funcs: dict[int, dict], psyq: dict[int, str], ghidra: dict[int, str],
                dyn_hits: set[int], entry: int | None, str_ranges,
                call_lo: int, call_hi: int, forced_starts: dict[int, str] | None = None,
                extent_overrides: dict[int, int] | None = None):
    jal_sites, j_sites, prologues, ends = scan_image(img, call_lo, call_hi)
    jt_targets = jump_table_targets(img) if space == "resident" else {}

    # A union entry offset (resident jal) is only kept as a start in THIS
    # overlay variant when it is structurally function-like here: it has a
    # prologue, or the previous instruction slot ends a function (jr/j at -8),
    # or it is the overlay's own entry. Everything else would fragment real
    # functions of variants that don't implement that entry.
    dropped_entry_offsets = []
    if forced_starts:
        def _function_like(a: int) -> bool:
            return a in prologues or (a - 8) in ends or a == img.lo
        kept = {}
        for a, label in forced_starts.items():
            if label != "resident_jal" or _function_like(a):
                kept[a] = label
            else:
                dropped_entry_offsets.append(a)
        forced_starts = kept

    lo, hi = img.lo, img.hi
    local = lambda d: {a: v for a, v in d.items() if lo <= a < hi}
    sym_fns = {a: n for a, n in local(syms).items()
               if "_OBJ_" not in n and not n.startswith("provisional_")}
    r2_local = local(r2_funcs)
    # *_OBJ_* PsyQ entries are interior basic-block labels of SDK functions,
    # not function starts — same exclusion as for the symbol map.
    psyq_local = {a: n for a, n in local(psyq).items() if "_OBJ_" not in n}
    ghidra_local = local(ghidra)
    jal_local = {a: s for a, s in jal_sites.items() if lo <= a < hi}
    jt_local = local(jt_targets)

    discovery: dict[int, list[str]] = {}
    def tag(addrs, label):
        for a in addrs:
            if a % 4 == 0 and lo <= a < hi:
                discovery.setdefault(a, []).append(label)

    tag(sym_fns, "symbol")
    if entry is not None:
        tag([entry], "entry")
    tag(r2_local, "r2")
    tag(psyq_local, "psyq")
    tag(ghidra_local, "ghidra")
    tag(jal_local, "jal_target")
    tag(jt_local, "jumptable")
    for addr, label in (forced_starts or {}).items():
        tag([addr], label)
    # prologue-only candidates (weak): keep only when no stronger start claims
    # the same address and the address is not inside a string range
    for a in sorted(prologues):
        if a not in discovery and not in_ranges(a, str_ranges):
            discovery[a] = ["prologue"]

    # drop weak starts inside string (data) ranges; keep multi-signal ones w/ note
    dropped_in_strings = []
    for a in list(discovery):
        if in_ranges(a, str_ranges) and discovery[a] != ["symbol"]:
            if set(discovery[a]) <= {"jal_target", "prologue", "r2", "j_target"}:
                dropped_in_strings.append(a)
                del discovery[a]

    starts = sorted(discovery)
    # extent-override: a jr-table dispatcher whose inline case bodies were split
    # into interior jumptable/gap sub-blocks. Drop every start STRICTLY inside an
    # override range so the dispatcher record can span its whole real extent (not
    # just clamp to the first interior sub-block). Safe only for self-contained
    # dispatchers (no external jal-target inside — verified before adding the
    # override); the gap-recovery re-adds any genuinely-orphan jal site.
    if extent_overrides:
        interior = {a for a in starts
                    for os, oe in extent_overrides.items()
                    if os < a < oe}
        starts = [a for a in starts if a not in interior]
    # anomaly: a jal target that is not a start (should be impossible here) or
    # that lands strictly inside another function's r2 range
    records = []
    for i, start in enumerate(starts):
        nxt = starts[i + 1] if i + 1 < len(starts) else hi
        end = nxt
        r2rec = r2_local.get(start)
        if extent_overrides and start in extent_overrides:
            # manual correction: r2 truncated a jr-table dispatcher at its table.
            # pin the real end (clamped to the next start) so it swallows its
            # case bodies; the gap-recovery then finds no orphan sites there.
            end = min(extent_overrides[start], nxt)
        elif r2rec and r2rec.get("realsz"):
            end = min(start + r2rec["realsz"], nxt)
        else:
            # refine: last jr/j instruction before nxt (+8 for the delay slot)
            last = max((e for e in ends if start <= e < nxt), default=None)
            if last is not None:
                end = min(last + 8, nxt)
        end = min(end, hi)
        # never let a code range swallow a known data anchor
        for anchor in DATA_ANCHORS:
            if start < anchor < end:
                end = anchor
        sigs = sorted(set(discovery[start]))
        name = (syms.get(start) or psyq_local.get(start) or ghidra_local.get(start)
                or (r2rec or {}).get("name", ""))
        if name.startswith("fcn."):
            name = ""
        dyn = start in dyn_hits
        if dyn:
            sigs.append("dynamic")
        conf = ("confirmed" if dyn or start in psyq_local
                or (start in sym_fns and not name.startswith("FUNC_"))
                else "high" if len(sigs) >= 2
                else "medium" if sigs != ["prologue"]
                else "low")
        records.append({
            "start": f"{start:#010x}", "end": f"{end:#010x}", "size": end - start,
            "range_type": "code", "space": space, "overlay": overlay,
            "confidence": conf, "discovery": sigs,
            "name": name, "classification": "unknown", "notes": "",
            "_start": start, "_end": end,
        })

    # gap-code recovery: a jal CALL SITE that no range covers proves code in
    # that gap (r2 realsz often truncates at jr-tables). Emit an explicit
    # low-confidence continuation range so the call graph stays closed.
    all_sites = sorted(s for sites in jal_sites.values() for s in sites)
    spans = sorted((int(r["start"], 16) if isinstance(r["start"], str) else r["_start"],
                    r["_end"]) for r in records)
    def covered(va: int) -> bool:
        import bisect
        i = bisect.bisect_right(spans, (va, RAM_HI)) - 1
        return i >= 0 and spans[i][0] <= va < spans[i][1]
    orphan_sites = [s for s in all_sites if not covered(s)]
    if orphan_sites:
        gap_records = []
        starts_arr = [s for s, _ in spans]
        import bisect
        by_gap: dict[tuple[int, int], list[int]] = {}
        for site in orphan_sites:
            i = bisect.bisect_right(starts_arr, site) - 1
            gap_lo = spans[i][1] if i >= 0 else lo
            gap_hi = spans[i + 1][0] if i + 1 < len(spans) else hi
            by_gap.setdefault((gap_lo, gap_hi), []).append(site)
        for (gap_lo, gap_hi), sites in sorted(by_gap.items()):
            last_end = max((e for e in ends if max(sites) <= e < gap_hi),
                           default=None)
            end = min(last_end + 8, gap_hi) if last_end is not None else gap_hi
            gap_records.append({
                "start": f"{gap_lo:#010x}", "end": f"{end:#010x}", "size": end - gap_lo,
                "range_type": "code", "space": space, "overlay": overlay,
                "confidence": "low", "discovery": ["gap_code"],
                "name": "", "classification": "unknown",
                "notes": f"continuation code evidenced by {len(sites)} uncovered "
                         f"outgoing jal site(s); boundary imprecise (r2 fragment)",
                "_start": gap_lo, "_end": end,
            })
        records += gap_records
        records.sort(key=lambda r: r["_start"])

    # classification + thunk detection
    for r in records:
        s = r["_start"]
        w0, w1 = img.word(s), img.word(s + 4)
        is_bios_thunk = (r["size"] <= 16 and w0 is not None and w1 is not None
                         and (w0 >> 26) in (9, 15)                # addiu/lui t-reg
                         and ((w1 & 0xFC00FFFF) == 0x00000008))   # jr rs
        if r["name"] == "entry0" or s == entry:
            r["classification"] = "crt0"
        elif is_bios_thunk:
            r["classification"] = "bios_thunk"
            r["range_type"] = "thunk"
        elif s in psyq_local or any(lo <= s < hi for lo, hi, _ in _RESIDENT_SDK_RANGES):
            r["classification"] = "sdk_psyq"
        elif r["name"] and not r["name"].startswith("FUNC_"):
            r["classification"] = "game"
        elif r["name"].startswith("FUNC_"):
            r["classification"] = "game"
        if s in jt_local:
            r["notes"] = f"jr-dispatch target of {jt_local[s]}"
        # resident gp/BSS globals mis-emitted as function starts -> reclassify data
        if space == "resident" and s >= RESIDENT_DATA_TAIL_LO:
            r["range_type"] = "data"
            r["classification"] = "data"
            r["notes"] = "gp-relative BSS/global (not code); RCA a5 reclassification"
        if space == "resident" and s in _RESIDENT_DATA_OVERRIDE:
            r["range_type"] = "data"
            r["classification"] = "data"
            r["notes"] = _RESIDENT_DATA_OVERRIDE[s]
        # symbol-only resident records that never disassemble/trace/return are DATA:
        # metadata tables / VM bytecode / dispatch pools named in re_symbols.sym but
        # not actually functions (never r2-decoded, jal-targeted, dynamic, or reachable,
        # and no `jr ra`). Same class as the RCA a5 / overlay data findings (v5 d0).
        if space == "resident" and r["range_type"] == "code" \
                and set(r["discovery"]) == {"symbol"} \
                and not _span_returns(img, r["_start"], r["_end"]):
            r["range_type"] = "data"
            r["classification"] = "data"
            r["notes"] = "symbol-only, no jr ra: metadata/VM/dispatch table, not code (v5 d0)"
        # a resident "function" of all-identical words is a fill/marker, not code
        if space == "resident" and r["range_type"] == "code" and r["size"] >= 8:
            ws = [img.word(a) for a in range(r["_start"], r["_end"], 4)]
            if ws and all(w == ws[0] for w in ws):
                r["range_type"] = "data"
                r["classification"] = "data"
                r["notes"] = f"all-identical words ({ws[0]:#010x}): data fill/marker, not code"
        if space == "overlay" and set(r["discovery"]) <= {"resident_jal"}:
            r["confidence"] = "low"
            r["notes"] = ("union entry offset (resident jal); may be interior "
                          "code in this overlay variant")
        # overlay data-in-code: a span >=32B with ZERO control-flow instructions
        # can't be a function (a real fn must contain a jr ra to return). These are
        # pointer tables / embedded filename strings / overlay headers the r2 pass
        # mis-emitted as function starts. (overlay analogue of the RCA a5 fix)
        if space == "overlay" and r["range_type"] == "code" and r["size"] >= 32 \
                and (not _span_is_code(img, r["_start"], r["_end"], overlay)
                     or (overlay, r["_start"]) in _OVERLAY_DATA_OVERRIDE):
            r["range_type"] = "data"
            r["classification"] = "data"
            r["notes"] = "no control flow in >=32B span (pointer table / string / header), not code"

    # call graph (jal + j-to-known-start)
    idx = {r["_start"]: r for r in records}
    bounds = sorted((r["_start"], r["_end"]) for r in records)
    def owner(va: int) -> int | None:
        import bisect
        i = bisect.bisect_right(bounds, (va, RAM_HI)) - 1
        if i >= 0 and bounds[i][0] <= va < bounds[i][1]:
            return bounds[i][0]
        return None

    callers: dict[int, set[int]] = {}
    callees: dict[int, set[int]] = {}
    anomalies, cross_space = [], {}
    for tgt, sites in sorted(jal_sites.items()):
        # Opcode-looking words in resident metadata tables are not call sites.
        # Classification is available now, so exclude any site owned by a data
        # record before building edges or reporting an interior-target anomaly.
        sites = [site for site in sites
                 if (owner(site) is not None
                     and idx[owner(site)]["range_type"] != "data")]
        if not sites:
            continue
        tgt_rec = idx.get(tgt)
        for site in sites:
            src = owner(site)
            if src is not None and tgt_rec is not None:
                callees.setdefault(src, set()).add(tgt)
                callers.setdefault(tgt, set()).add(src)
        if tgt_rec is None:
            if not (lo <= tgt < hi):
                # legitimate cross-space call (resident -> overlay window):
                # this is the resident->overlay ABI surface, not an anomaly
                cross_space[tgt] = {
                    "n_sites": len(sites),
                    "call_sites": [f"{s:#010x}" for s in sites[:8]],
                    "callers": sorted({f"{o:#010x}" for o in
                                       (owner(s) for s in sites) if o is not None}),
                }
                continue
            own = owner(tgt)
            anomalies.append({
                "target": f"{tgt:#010x}", "call_sites": [f"{s:#010x}" for s in sites[:8]],
                "n_sites": len(sites),
                "reason": (f"jal into interior of {own:#010x}" if own is not None
                           else "jal target in-image but not a census start"),
            })
    for tgt, sites in sorted(j_sites.items()):
        if tgt in idx:
            for site in sites:
                src = owner(site)
                if src is not None and idx[src]["range_type"] != "data" and src != tgt:
                    callees.setdefault(src, set()).add(tgt)
                    callers.setdefault(tgt, set()).add(src)
                    if "j_target" not in idx[tgt]["discovery"]:
                        idx[tgt]["discovery"].append("j_target")

    # reachability BFS from entry + jump-table targets
    roots = [a for a in ([entry] if entry is not None else []) if a in idx]
    roots += [a for a in jt_local if a in idx]
    seen = set(roots)
    work = list(roots)
    while work:
        cur = work.pop()
        for nxt in callees.get(cur, ()):
            if nxt not in seen:
                seen.add(nxt)
                work.append(nxt)
    for r in records:
        s = r["_start"]
        r["callers"] = sorted(f"{a:#010x}" for a in callers.get(s, ()))
        r["callees"] = sorted(f"{a:#010x}" for a in callees.get(s, ()))
        if s in seen and "reachable" not in r["discovery"]:
            r["discovery"].append("reachable")
        r["discovery"] = sorted(set(r["discovery"]))
        del r["_start"], r["_end"]

    code_recs = [r for r in records if r.get("range_type") != "data"]
    stats = {
        "functions": len(code_recs),
        "code_bytes": sum(r["size"] for r in code_recs),
        "data_records": len(records) - len(code_recs),
        "image_bytes": hi - lo,
        "dropped_starts_in_string_data": len(dropped_in_strings),
        "jal_anomalies": len(anomalies),
        "cross_space_targets": len(cross_space),
        "entry_offsets_not_function_like": sorted(
            f"{a:#010x}" for a in dropped_entry_offsets),
    }
    return records, anomalies, stats, cross_space


def load_overlay_symbols() -> dict[str, dict[int, str]]:
    """Per-overlay name store (analysis/overlay_symbols.json) -> {overlay: {addr: name}}.
    Overlays share load addresses, so overlay names cannot live in re_symbols.sym;
    this is the (overlay,address)-keyed authority (see tools/apply_overlay_names.py)."""
    p = ANALYSIS / "overlay_symbols.json"
    if not p.exists():
        return {}
    doc = json.loads(p.read_text())
    return {ov: {int(a, 16): e["name"] for a, e in m.items()}
            for ov, m in doc.get("overlays", {}).items()}


def staged_overlay_targets(baselines: dict) -> list[tuple[str, Path, bool, str]]:
    """Enumerate every overlay from the pinned pristine staging tree.

    Local ``OVL/`` extraction copies are deliberately not authority. LEVEL00's
    four-byte sentinel is not a code overlay, so the census covers the 19 real
    level blobs plus MEMORY.BIN.
    """
    rows = []
    pattern = re.compile(r"^(LEVEL(?:0[1-9]|10))/(LEVEL1?)\.BIN$")
    for rel, pin in sorted(baselines["staged_inputs"].items()):
        match = pattern.fullmatch(rel)
        if not match:
            continue
        path = ROOT / "REBUILD/files" / rel
        if not path.is_file() or _sha256(path) != pin["sha256"]:
            raise SystemExit(f"missing/mismatched pristine staged overlay: {rel}")
        rows.append((f"{match.group(1)}_{match.group(2)}", path, False, rel))
    rel = "BITS/MEMORY.BIN"
    pin = baselines["staged_inputs"][rel]
    path = ROOT / "REBUILD/files" / rel
    if not path.is_file() or _sha256(path) != pin["sha256"]:
        raise SystemExit(f"missing/mismatched pristine staged overlay: {rel}")
    rows.append(("MEMORY", path, True, rel))
    if len(rows) != 20:
        raise SystemExit(f"expected 20 pinned code overlays, found {len(rows)}")
    return rows


def required_external_metadata(targets: list[tuple[str, Path, bool, str]]) -> list[Path]:
    paths = [OUT / "psyq_matches.csv", OUT / "ghidra_functions.csv"]
    paths.extend(OUT / "overlays" / f"{stem}.functions.json"
                 for stem, _path, _is_mem, _rel in targets)
    return paths


def main() -> int:
    ANALYSIS.mkdir(exist_ok=True)
    syms = load_symbols()
    overlay_syms = load_overlay_symbols()
    baselines = json.loads(BASELINES.read_text())
    expected_exe = baselines["pristine_media"]["SCUS_942.88"]["sha1"]
    if hashlib.sha1(EXE.read_bytes()).hexdigest() != expected_exe:
        raise SystemExit("refusing non-pristine root SCUS_942.88")
    targets = staged_overlay_targets(baselines)
    metadata = required_external_metadata(targets)
    missing = [str(path.relative_to(ROOT)) for path in metadata if not path.is_file()]
    if missing:
        raise SystemExit(f"missing required derived census metadata: {missing}")
    r2_funcs = {f["offset"]: f for f in json.loads((OUT / "functions.json").read_text())}
    psyq = load_csv_map(OUT / "psyq_matches.csv")
    ghidra = load_csv_map(OUT / "ghidra_functions.csv")
    dyn_hits = load_trace_hits()
    extent_overrides = load_extent_overrides()

    exe = EXE.read_bytes()
    entry = struct.unpack_from("<I", exe, 0x10)[0]
    resident = Image(exe[exe_read.HDR:], TEXT_LO, TEXT_LO)
    str_ranges = string_ranges(TEXT_LO, TEXT_HI)

    all_records, all_anoms = [], {}
    res_records, res_anoms, res_stats, res_cross = build_space(
        resident, space="resident", overlay=None, syms=syms, r2_funcs=r2_funcs,
        psyq=psyq, ghidra=ghidra, dyn_hits=dyn_hits, entry=entry,
        str_ranges=str_ranges, call_lo=TEXT_LO, call_hi=RAM_HI,
        extent_overrides=extent_overrides)
    all_records += res_records
    if res_anoms:
        all_anoms["resident"] = res_anoms

    inputs = {p.name: _sha256(p) for p in
              [OUT / "functions.json", OUT / "strings.json", SYMBOLS]
              + [OUT / "psyq_matches.csv", OUT / "ghidra_functions.csv"]
              + ([TRACE_HITS] if TRACE_HITS.exists() else [])
              + ([LEVEL_COVERAGE] if LEVEL_COVERAGE.exists() else [])
              + ([EXTENT_OVERRIDES] if EXTENT_OVERRIDES.exists() else [])}
    inputs["SCUS_942.88"] = _sha256(EXE)
    inputs["tools/build_baselines.json"] = _sha256(BASELINES)
    inputs["analysis/overlay_symbols.json"] = _sha256(
        ANALYSIS / "overlay_symbols.json")
    inputs["config/segments.yml"] = _sha256(ROOT / "config/segments.yml")
    for stem, path, _is_mem, rel in targets:
        inputs[f"REBUILD/files/{rel}"] = _sha256(path)
        ovf = OUT / "overlays" / f"{stem}.functions.json"
        inputs[str(ovf.relative_to(ROOT))] = _sha256(ovf)

    overlay_stats = {}
    for stem, path, is_mem, _rel in targets:
        blob = path.read_bytes()
        if len(blob) < 16:
            continue
        base = REGION_B if is_mem else REGION_A
        code_lo = base if is_mem else base + OVERLAY_HDR
        ov_r2 = {}
        ovf = OUT / "overlays" / f"{stem}.functions.json"
        for f in json.loads(ovf.read_text()):
            off = f["offset"]
            if off == base and not is_mem:
                off = base + OVERLAY_HDR   # r2 mis-starts at the 4-byte header
                f = dict(f, realsz=max((f.get("realsz") or 4) - OVERLAY_HDR, 4))
            ov_r2[off] = f
        img = Image(blob, base, code_lo)
        forced = {code_lo: "overlay_entry"} if not is_mem else {0x800BD518: "overlay_entry"}
        # resident jal's into this overlay's window are entry points here too
        for tgt in res_cross:
            if code_lo <= tgt < img.hi:
                forced.setdefault(tgt, "resident_jal")
        # overlay names come from the per-overlay store (NOT resident syms —
        # every level overlay loads at the same base, so a resident name would
        # collide across all of them). Key: (overlay, address).
        recs, anoms, stats, ov_cross = build_space(
            img, space="overlay", overlay=stem, syms=overlay_syms.get(stem, {}),
            r2_funcs=ov_r2,
            psyq={}, ghidra={}, dyn_hits=dyn_hits, entry=None,
            str_ranges=[], call_lo=TEXT_LO, call_hi=img.hi,
            forced_starts=forced)
        all_records += recs
        if anoms:
            all_anoms[stem] = anoms
        stats["resident_callees"] = sorted(f"{t:#010x}" for t in ov_cross
                                           if TEXT_LO <= t < TEXT_HI)
        overlay_stats[stem] = stats

    # substrate match provenance: which attempted functions are reconstructed
    # from source, and in which language (config/segments.yml -> `match`).
    seg_path = ROOT / "config" / "segments.yml"
    matched = {}
    if seg_path.exists():
        import yaml
        seg = yaml.safe_load(seg_path.read_text())
        for a in seg.get("attempted") or []:
            va = a["start"] if isinstance(a["start"], int) else int(a["start"], 16)
            matched[f"{va:#010x}"] = "c" if str(a["source"]).endswith(".c") else "asm"
    for r in all_records:
        if r["space"] == "resident" and r["start"] in matched:
            r["match"] = matched[r["start"]]

    all_records.sort(key=lambda r: (r["space"], r["overlay"] or "", r["start"]))

    doc = {
        "generated_by": "tools/function_census.py",
        "inputs": inputs,
        "resident": res_stats,
        "overlays": overlay_stats,
        "data_anchors": {f"{a:#010x}": n for a, n in sorted(DATA_ANCHORS.items())},
        "resident_overlay_entry_targets": {
            f"{t:#010x}": v for t, v in sorted(res_cross.items())},
        "jal_anomalies": all_anoms,
        "functions": all_records,
    }
    (ANALYSIS / "functions.json").write_text(json.dumps(doc, indent=1) + "\n")

    with (ANALYSIS / "functions.csv").open("w", newline="") as f:
        cols = ["start", "end", "size", "space", "overlay", "name", "classification",
                "confidence", "range_type", "match", "discovery", "n_callers",
                "n_callees", "notes"]
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in all_records:
            w.writerow({**{k: r.get(k, "") for k in cols},
                        "overlay": r["overlay"] or "",
                        "discovery": "+".join(r["discovery"]),
                        "n_callers": len(r["callers"]), "n_callees": len(r["callees"])})

    _write_coverage(doc)
    _write_progress(doc)
    n_res = res_stats["functions"]
    print(f"[census] resident: {n_res} functions, {res_stats['code_bytes']}/{res_stats['image_bytes']} "
          f"bytes ({100*res_stats['code_bytes']/res_stats['image_bytes']:.1f}%), "
          f"{res_stats['jal_anomalies']} jal anomalies; "
          f"overlays: {sum(s['functions'] for s in overlay_stats.values())} functions "
          f"across {len(overlay_stats)}")
    return 0


def _write_progress(doc: dict) -> None:
    """Decompilation progress metric -> analysis/decomp_progress.json:
    functions/bytes reconstructed from source (byte-exact), split asm/C and by
    classification, as a % of resident code."""
    res = [r for r in doc["functions"] if r["space"] == "resident"]
    total_fns = len(res)
    total_bytes = doc["resident"]["code_bytes"]
    matched = [r for r in res if r.get("match")]
    def bytes_of(rows):
        return sum(int(r["end"], 16) - int(r["start"], 16) for r in rows)
    asm = [r for r in matched if r["match"] == "asm"]
    c = [r for r in matched if r["match"] == "c"]
    by_class = {}
    for r in matched:
        by_class.setdefault(r["classification"], {"asm": 0, "c": 0})[r["match"]] += 1
    prog = {
        "generated_by": "tools/function_census.py",
        "resident_functions": total_fns,
        "resident_code_bytes": total_bytes,
        "matched": {
            "functions": len(matched), "bytes": bytes_of(matched),
            "pct_functions": round(100 * len(matched) / total_fns, 2),
            "pct_bytes": round(100 * bytes_of(matched) / total_bytes, 3),
            "asm": {"functions": len(asm), "bytes": bytes_of(asm)},
            "c": {"functions": len(c), "bytes": bytes_of(c)},
            "by_classification": by_class,
        },
        "note": "matched = reconstructed byte-exact from source (config/segments.yml "
                "attempted); overlays not counted. asm = hand-written .s, c = src/main C.",
    }
    (ANALYSIS / "decomp_progress.json").write_text(json.dumps(prog, indent=1) + "\n")


def _write_coverage(doc: dict) -> None:
    recs = doc["functions"]
    res = [r for r in recs if r["space"] == "resident"]
    by = lambda key, rows: {k: sum(1 for r in rows if r[key] == k)
                            for k in sorted({r[key] for r in rows})}
    sig_counts: dict[str, int] = {}
    for r in res:
        for s in r["discovery"]:
            sig_counts[s] = sig_counts.get(s, 0) + 1
    rs = doc["resident"]
    n_asm = sum(1 for r in res if r.get("match") == "asm")
    n_c = sum(1 for r in res if r.get("match") == "c")
    lines = [
        "# Code coverage — whole-image function census",
        "",
        "Regenerate: `python tools/re_baseline.py --all && python tools/function_census.py`.",
        "Canonical data: `analysis/functions.json` / `analysis/functions.csv`.",
        "",
        "## Resident EXE (text 0x80010000–0x80082800)",
        "",
        f"- functions: **{rs['functions']}**",
        f"- classified code bytes: **{rs['code_bytes']:,} / {rs['image_bytes']:,}"
        f" ({100*rs['code_bytes']/rs['image_bytes']:.1f}%)** — the remainder of the"
        f" image is data (strings/tables/rodata) or unrecovered code",
        f"- JAL anomalies (call into a non-start): **{rs['jal_anomalies']}**",
        f"- weak starts dropped inside string data: {rs['dropped_starts_in_string_data']}",
        f"- reconstructed from source (byte-exact, substrate): **{n_asm} asm + {n_c} C**"
        f" = {n_asm + n_c} functions"
        f" ({100 * (n_asm + n_c) / rs['functions']:.1f}% of resident functions;"
        f" full metric in `analysis/decomp_progress.json`)",
        "",
        "### By confidence",
        "",
        "| confidence | functions |", "|---|---|",
        *(f"| {k} | {v} |" for k, v in by("confidence", res).items()),
        "",
        "### By classification",
        "",
        "| classification | functions |", "|---|---|",
        *(f"| {k} | {v} |" for k, v in by("classification", res).items()),
        "",
        "### By discovery signal (a function can carry several)",
        "",
        "| signal | functions |", "|---|---|",
        *(f"| {k} | {v} |" for k, v in sorted(sig_counts.items())),
        "",
        "## Overlays",
        "",
        "| overlay | functions | code bytes | image bytes | jal anomalies |",
        "|---|---|---|---|---|",
        *(f"| {name} | {s['functions']} | {s['code_bytes']} | {s['image_bytes']} | {s['jal_anomalies']} |"
          for name, s in sorted(doc["overlays"].items())),
        "",
    ]
    (ANALYSIS / "code_coverage.md").write_text("\n".join(lines))


if __name__ == "__main__":
    raise SystemExit(main())
