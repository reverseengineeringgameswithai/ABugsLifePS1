#!/usr/bin/env python3
"""Typed-state / access-join compiler — Phase-4 DoD dimension 3.

Dimension 3 asks for fields, widths, signedness, owners, domains and
initialisation/reset. This compiler joins a declared state schema against the
frontier's ACTUAL access set and refuses to let either side certify itself.

It does two jobs.

1. SCHEMA JOIN. Every access the frontier resolved into a watched window must map
   to a declared field, at the right width. A declared field with no access is
   reported; an access with no field is reported. Neither is silently dropped.

2. BOUNDING. An access whose base the frontier could not resolve is a potential
   writer of the watched state. If the base is known to point into a declared
   REGION, the access lies in `[region.start + disp, region.end + disp)`, and
   when that range is disjoint from every window the site is bounded — it cannot
   reach the state, whatever its exact value.

   That is the whole point: most unresolved stores are actor-pointer based, and a
   region bound turns "unknown base" into "cannot alias a $gp global".

WHAT THIS TOOL WILL NOT DO
--------------------------
A declaration is not evidence. `region_bindings` may not simply assert that a
register holds an actor pointer; each binding carries a provenance kind and is
checked:

  caller_argument      VERIFIED HERE by reading the CALLERS (the ABI accelerator,
                       DoD dimension 5). The bound register must either BE the
                       incoming argument at every site being bounded or be a pure
                       copy of one; then every direct caller must materialise a
                       constant for that argument at its call site -- recovered
                       across basic blocks and across the DELAY SLOT, which is
                       where the argument is usually set -- and all callers must
                       agree on a value that lies inside the declared region.
                       Wider than counting callers (many callers are fine if they
                       agree) and stricter (one caller is not enough if the value
                       cannot be recovered or lands outside the region).
  typed_pointer_load   VERIFIED HERE by reading instructions. This compiler
                       rebuilds the ASM verifier from source and runs it, rather
                       than reading an attestation the schema points at, and
                       requires all four of:
                         - every definition reaching the sites being bounded
                           loads from ONE address,
                         - that address is the declared pointer table,
                         - no site is reachable from the function entry without
                           passing a definition,
                         - the corrected KNOWN writer lower bound is exact-set
                           pinned and cross-checked against addresses the static
                           index resolves independently,
                         - every writer's value domain is proved, and
                         - the table-writer universe is proved exhaustive.
                       The positive recogniser and corpus alias residuals are
                       retained, never called zero or complete. A 2026-08-07
                       fresh verifier rejected grandfathering this bucket while
                       either of the last two gates is open.
                       The sites tested come from the LEDGER, not the schema, so
                       a binding cannot pick the cases it is judged on.
  proved_jr_cluster_argument
                       VERIFIED HERE, for target-root ISLAND records only. The
                       island's sole established entry is one gate-proved jr
                       edge, so no within-extent analysis can see a definition
                       of its base. The chain re-derived per run: the pinned jr
                       map proves the edge; the declared cluster tiles onto
                       contiguous index records with NO direct edge, proved jr
                       target, or recursive call entering its interior; the C
                       verifier proves a straight-line prologue argument copy,
                       that every other write is a terminal-epilogue restore,
                       and that each call site copies a caller register into
                       the argument in its delay slot; that caller register is
                       then typed at the call exactly as typed_pointer_load
                       types a base (one load address == the declared table,
                       no undefined path, writers corroborated). Deliberately
                       NOT a general jr-state propagator: one island, one edge.
  external_owner       an explicitly named owner accepts it. Recorded as an
                       ASSERTION, never counted as proof, and the bound sites it
                       produces are reported separately.

Bindings whose provenance cannot be established leave their sites UNRESOLVED.

It consumes the FULL blocker ledger, not a chosen subset, so a shrinking
acceptance fixture cannot make the universe look smaller. And it never clears an
indirect-control-flow blocker: those stay exactly as the frontier left them.

Usage
  tools/phase4_typed_state.py SCHEMA.yaml --output analysis/OUT.json [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "analysis/phase4_static_frontier_index.json"
VERIFIER_SRC = "tools/phase4_typed_state_provenance.c"
REGION_PROVENANCE_SRC = "tools/region_provenance.c"
RESIDENT_EXE = "REBUILD/files/SCUS_942.88"
RESIDENT_FUNCS = "analysis/functions_resident.txt"
RESIDENT_IMAGE = "SCUS_942_88"
PS1_RAM_SIZE = 0x00200000
PS1_RAM_MIRROR_SPAN = 0x00800000
PS1_RAM_SEGMENT_BASES = (0x00000000, 0x80000000, 0xA0000000)
SCHEMA_ID = "abl-phase4-typed-state-schema/1"
RESULT_ID = "abl-phase4-typed-state-result/1"
INDEX_INTERVAL_BASELINE_COMMIT = "b6cb61d35f9da0c890f9318d1b4a0122f2e6e084"
INDEX_INTERVAL_BASELINE_ARTIFACT = "analysis/phase4_f01_typed_state.json"
INDEXDOM_RA_RATCHET_COMMIT = "05bc6b8a251b613cf6c25b6c6bdf351fdf32b7e4"
PROVENANCE_KINDS = ("caller_argument", "typed_pointer_load",
                    "proved_jr_cluster_argument", "external_owner")
# Provenance kinds whose binding must declare the pointer table it rests on.
TABLE_BACKED_KINDS = ("typed_pointer_load", "proved_jr_cluster_argument")
ACTOR_POINTER_TABLE = 0x80090748
PREVIOUS_ACTOR_TABLE_WRITERS = {
    0x8003A49C, 0x8004A4B4, 0x8004D378, 0x8004D43C,
}
PINNED_KNOWN_ACTOR_TABLE_WRITERS = PREVIOUS_ACTOR_TABLE_WRITERS | {
    0x80049C10, 0x80049C14,
}
SIGNEDNESS = ("signed", "unsigned", "not_applicable")
AUTHORITY = {
    "promotes_dimension": False,
    "declaration_is_not_evidence": True,
    "clears_indirect_control_flow_blockers": False,
    "fresh_verifier_required": True,
}
TABLE_BASE_PROOF = "all_reaching_definitions_same_constant"


class TypedStateError(RuntimeError):
    """Failed closed."""


def _int(value: Any) -> int:
    if isinstance(value, int):
        return value
    text = str(value)
    return int(text, 16 if text.lower().startswith("0x") else 10)


def _proved_table_address_definition(row: dict) -> bool:
    """Require the C classifier's independent, path-complete base proof.

    An unsigned interval for INDEX proves nothing if TABLE came from a lexical
    LUI that a branch can bypass.  Keeping this as an explicit consumer
    predicate means an older or partial C answer cannot be mistaken for the
    strengthened table-address contract.
    """
    return (row.get("class") == "table_address"
            and not (row.get("hops") or 0)
            and bool(row.get("table"))
            and bool(row.get("index"))
            and bool(row.get("table_base_register"))
            and row.get("table_base_proof") == TABLE_BASE_PROOF)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _exact(value: Any, keys: set[str], where: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise TypedStateError(
            f"{where} fields differ: expected {sorted(keys)}, got "
            f"{sorted(value) if isinstance(value, dict) else type(value).__name__}")
    return value


def load_schema(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    doc = yaml.safe_load(raw.decode("utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA_ID:
        raise TypedStateError(f"schema must use {SCHEMA_ID}")
    _exact(doc, {"schema", "row_id", "ledger", "acceptance_fixture", "windows",
                 "regions", "fields", "region_bindings", "authority"}, "schema")
    _exact(doc["acceptance_fixture"], {"path", "collection", "predicate", "detail"},
           "acceptance_fixture")
    if doc["authority"] != AUTHORITY:
        raise TypedStateError("schema authority differs from the non-promotion contract")

    for region in doc["regions"]:
        _exact(region, {"id", "start", "end", "owner", "evidence"}, "region")
        if _int(region["end"]) <= _int(region["start"]):
            raise TypedStateError(f"region {region['id']} has an empty extent")
        for key in ("owner", "evidence"):
            if not str(region.get(key) or "").strip():
                raise TypedStateError(f"region {region['id']} lacks {key}")

    seen: set[tuple[str, int]] = set()
    for field in doc["fields"]:
        _exact(field, {"id", "region", "offset", "width", "signedness", "owner",
                       "domain", "init", "reset", "points_to", "evidence"}, "field")
        if field["signedness"] not in SIGNEDNESS:
            raise TypedStateError(f"field {field['id']} has invalid signedness")
        if _int(field["width"]) not in (1, 2, 4):
            raise TypedStateError(f"field {field['id']} has invalid width")
        for key in ("owner", "domain", "init", "reset", "evidence"):
            if not str(field.get(key) or "").strip():
                raise TypedStateError(f"field {field['id']} lacks {key}")
        key = (field["region"], _int(field["offset"]))
        if key in seen:
            raise TypedStateError(f"field {field['id']} duplicates an offset")
        seen.add(key)

    for binding in doc["region_bindings"]:
        base_keys = {"image", "function", "register", "region", "provenance",
                     "detail", "pointer_table"}
        if binding.get("provenance") == "proved_jr_cluster_argument":
            _exact(binding, base_keys | {"cluster"}, "region_binding")
            _exact(binding["cluster"], {"start", "end"}, "region_binding.cluster")
        else:
            _exact(binding, base_keys, "region_binding")
        if (binding["provenance"] in TABLE_BACKED_KINDS) != (binding["pointer_table"] is not None):
            raise TypedStateError(
                "pointer_table belongs to table-backed bindings "
                f"({', '.join(TABLE_BACKED_KINDS)}) and only those")
        if binding["provenance"] not in PROVENANCE_KINDS:
            raise TypedStateError(
                f"binding {binding['function']}.{binding['register']} has invalid provenance")
        if not str(binding.get("detail") or "").strip():
            raise TypedStateError("every region binding must carry a detail citation")
    return doc, _sha(raw)


def _names_function(qualified: str, image: str, entry: int) -> bool:
    """`IMAGE:name@0xENTRY`, compared as an INTEGER.

    The ledger writes the entry lowercase while neighbouring fields are
    uppercase, so a string compare silently matches nothing instead of failing.
    """
    if not qualified.startswith(f"{image}:") or "@" not in qualified:
        return False
    try:
        return _int(qualified.rsplit("@", 1)[1]) == entry
    except ValueError:
        return False


def _extent(index: dict, image: str, entry: int) -> tuple[int, str]:
    for record in index["records"]:
        if (record.get("entry") and _int(record["entry"]) == entry
                and record["image_id"] == image):
            return _int(record["end"]), str(record.get("name") or "")
    raise TypedStateError(f"no static-index record for {image}@0x{entry:08x}")


def verify_caller_argument(binding: dict, index: dict, ledger: dict,
                           verifier: Verifier,
                           regions: dict) -> tuple[bool, str, dict | None]:
    """Type an argument from what the CALLERS actually pass. (DoD dimension 5.)

    The previous version of this check counted callers: one caller meant the
    argument was single-valued, and the VALUE was taken from the schema's prose.
    That is not a check -- a binding could name any region and pass, because
    nothing ever compared the claim to an instruction.

    This reads the callers. Three things must hold:

      1. The bound register either IS the incoming argument at every site being
         bounded, or is a pure copy of one (the verifier chases the copy).
      2. EVERY direct caller materialises a constant for that argument at its
         call site -- recovered across basic blocks, and across the delay slot,
         since that is where the argument is usually set.
      3. All callers agree on the value, and the value lies inside the declared
         region.

    Note this ACCEPTS many callers where the old check accepted only one, and
    REJECTS a single caller whose value cannot be recovered or lands outside the
    region. It is both wider and stricter.
    """
    entry = _int(binding["function"])
    image = binding["image"]
    reg = binding["register"]
    end, _name = _extent(index, image, entry)

    targets = sorted({_int(s["pc"]) for s in ledger.get("unresolved_accesses") or []
                      if _names_function(str(s.get("function", "")), image, entry)
                      and str(s.get("base_register")) == reg})
    if not targets:
        return False, "rejected: the ledger has no unresolved site for this binding", None

    pcs = ",".join(f"0x{p:08x}" for p in targets)
    callee = verifier.ask(f"{image}:0x{entry:08x}:0x{end:08x}:{reg}:{pcs}")[0]

    # (1) which argument does this binding actually rest on?
    if callee["targets_all_hold_incoming"]:
        arg = reg
        how = f"{reg} holds the caller's value at all {callee['targeted_sites']} sites"
    else:
        observed = [d for d in callee["definitions"] if d["observable"]]
        incoming = {d.get("incoming") for d in observed}
        if len(incoming) != 1 or None in incoming:
            return False, (f"rejected: {reg} is neither the incoming argument at every "
                           f"site nor a pure copy of one (it has "
                           f"{len(observed)} observable definitions)"), None
        arg = incoming.pop()
        if callee["entry_reachable_uses"]:
            return False, (f"rejected: {callee['entry_reachable_uses']} site(s) reachable "
                           "from entry without passing the copy"), None
        how = f"{reg} is a pure copy of the incoming argument {arg}"

    # (2) every direct caller, read from the instructions
    callers = []
    for record in index["records"]:
        if not record.get("entry"):
            continue
        for edge in record.get("direct_calls") or []:
            try:
                if _int(edge["target"]) == entry:
                    callers.append((record["image_id"], _int(record["entry"]),
                                    _int(record["end"]), _int(edge["pc"]),
                                    str(record.get("name") or "")))
            except (TypeError, ValueError):
                continue
    if not callers:
        return False, "rejected: the static index shows no direct caller", None

    passed, values = [], set()
    for cimage, cstart, cend, cpc, cname in callers:
        q = verifier.ask(f"defsat@{cimage}:0x{cstart:08x}:0x{cend:08x}:{arg}:0x{cpc:08x}")[0]
        observed = [d for d in q["definitions"] if d["observable"]]
        kinds = {d["class"] for d in observed}
        if not observed or kinds != {"materialised_constant"}:
            return False, (f"rejected: caller {cimage}:{cname} at 0x{cpc:08x} does not "
                           f"materialise a constant for {arg} "
                           f"({', '.join(sorted(kinds)) or 'no observable definition'})"), None
        vals = {_int(d["value"]) for d in observed}
        if len(vals) != 1:
            return False, (f"rejected: caller {cimage}:{cname} at 0x{cpc:08x} passes "
                           f"{len(vals)} different values for {arg}"), None
        value = vals.pop()
        values.add(value)
        passed.append({"image": cimage, "function": cname, "call_pc": f"0x{cpc:08x}",
                       "argument": arg, "value": f"0x{value:08x}"})

    if len(values) != 1:
        return False, (f"rejected: {len(callers)} callers pass {len(values)} different "
                       f"values for {arg}, so it is not single-valued"), None
    value = values.pop()
    low, high = regions[binding["region"]]
    if not (low <= value < high):
        return False, (f"rejected: callers pass 0x{value:08x}, which is outside "
                       f"{binding['region']} [0x{low:08x},0x{high:08x})"), None

    return True, (f"verified: {how}; all {len(callers)} direct caller(s) materialise "
                  f"{arg} = 0x{value:08x}, inside {binding['region']}"), {
        "argument": arg,
        "how_the_register_relates_to_the_argument": how,
        "callers": passed,
        "agreed_value": f"0x{value:08x}",
        "read_from_instructions": True,
    }


class Verifier:
    """The ASM verifier, COMPILED FROM SOURCE HERE and invoked by this compiler.

    The alternative -- letting the schema cite an attestation file -- would let
    the document under review supply its own evidence. Rebuilding the verifier
    from the checked-in source and running it means the answer is regenerated,
    never quoted, and the reported binary hash is of the thing that actually ran.
    """

    def __init__(self, index: dict) -> None:
        src = ROOT / VERIFIER_SRC
        self.source_sha = _sha(src.read_bytes())
        self._dir = tempfile.mkdtemp(prefix="phase4-typed-state-")
        self.binary = Path(self._dir) / "provenance"
        proc = subprocess.run(
            ["gcc", "-O2", "-std=c11", "-Wall", "-Wextra", "-Werror",
             "-o", str(self.binary), str(src)],
            capture_output=True, text=True)
        if proc.returncode != 0:
            raise TypedStateError(f"verifier failed to build:\n{proc.stderr}")
        self.binary_sha = _sha(self.binary.read_bytes())
        # The image map is generated from the static index, so the verifier and
        # the frontier can never disagree about where an overlay loads or which
        # overlays exist at all.
        rows = []
        for image in index["images"]:
            if not (ROOT / image["path"]).is_file():
                raise TypedStateError(f"image missing: {image['path']}")
            # REPO-RELATIVE. An absolute path makes the map's sha256 depend on
            # where the checkout lives, so the artifact stops reproducing from a
            # clean checkout elsewhere -- which is precisely what an independent
            # verifier is asked to do. The tool is run with cwd=ROOT so the
            # relative path resolves.
            rows.append(f"{image['image_id']} {image['path']} {image['file_va_base']}")
        self.image_map = Path(self._dir) / "images.txt"
        self.image_map.write_text("\n".join(rows) + "\n")
        self.image_map_sha = _sha(self.image_map.read_bytes())
        self.image_count = len(rows)
        self._rp_binary = None
        self._rp_binary_sha = None
        self._rp_source_sha = None
        self._rp_cache: dict[tuple[str, int, int], dict] = {}
        self._fnlists: dict[str, Path] = {}
        self._index = index
        self._image_meta = {i["image_id"]: i for i in index["images"]}

    def _function_list(self, image_id: str) -> Path:
        """Per-image function extents for the region analyser, from the STATIC INDEX.

        The resident image keeps its pinned `analysis/functions_resident.txt`,
        because that file is what the analyser's own census-parity baseline is
        stated against and regenerating it would silently move that baseline.
        Overlay lists have no such baseline, so they are generated -- which also
        means they cannot drift from the index the rest of this pipeline uses.
        """
        if image_id == RESIDENT_IMAGE:
            return ROOT / RESIDENT_FUNCS
        cached = self._fnlists.get(image_id)
        if cached is not None:
            return cached
        rows = sorted(
            ((_int(r["entry"]), _int(r["end"]), str(r.get("name") or ""))
             for r in self._index["records"]
             if r["image_id"] == image_id and r.get("entry") and r.get("end")),
            key=lambda t: t[0])
        if not rows:
            raise TypedStateError(f"no analysed functions for image {image_id}")
        path = Path(self._dir) / f"functions_{image_id}.txt"
        lines = [f"# {image_id} count {len(rows)} (generated from the static index)"]
        lines += [f"0x{a:08x} {e - a} {n or f'sub_{a:08x}'}" for a, e, n in rows]
        path.write_text("\n".join(lines) + "\n")
        self._fnlists[image_id] = path
        return path

    def region_provenance(self, image_id: str, target: int, width: int) -> dict:
        """Run the OTHER region analyser on a watched window.

        `tools/region_provenance.c` predates this compiler, answers the same
        question by a different route (abstract interpretation with three tiers of
        index-bound recovery), and has its own soundness history. Running it here
        is a second opinion on the same sites -- the kind of independent check
        that caught a 2x count inflation once already.

        Its verdicts are NOT merged into this tool's proofs. Tiers 2 and 3 rest on
        the non-negative, loop-bound-checked array-index convention, which is a
        convention about how the code was written rather than something the
        instructions state. They get their own bucket.
        """
        key = (image_id, target, width)
        if key in self._rp_cache:
            return self._rp_cache[key]
        if self._rp_binary is None:
            src = ROOT / REGION_PROVENANCE_SRC
            self._rp_source_sha = _sha(src.read_bytes())
            binary = Path(self._dir) / "region_provenance"
            proc = subprocess.run(["cc", "-O2", "-o", str(binary), str(src)],
                                  capture_output=True, text=True)
            if proc.returncode != 0:
                raise TypedStateError(f"region_provenance failed to build:\n{proc.stderr}")
            self._rp_binary = binary
            self._rp_binary_sha = _sha(binary.read_bytes())
        meta = self._image_meta.get(image_id)
        if meta is None:
            raise TypedStateError(f"image {image_id} is not in the static index")
        argv = [str(self._rp_binary), meta["path"],
                str(self._function_list(image_id)), f"0x{target:08X}", str(width),
                "--json", ""]
        out = Path(self._dir) / f"rp_{image_id}_{target:08x}_{width}.json"
        argv[-1] = str(out)
        if image_id != RESIDENT_IMAGE:
            # Overlays are raw images with no PS-X EXE header; the load address
            # comes from the index, never from a second hardcoded table.
            argv += ["--raw", str(meta["file_va_base"])]
        proc = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT)
        if proc.returncode != 0:
            raise TypedStateError(
                f"region_provenance rejected {image_id} 0x{target:08x}: {proc.stderr.strip()}")
        self._rp_cache[key] = json.loads(out.read_bytes())
        return self._rp_cache[key]

    def ask(self, *queries: str) -> list[dict]:
        proc = subprocess.run([str(self.binary), str(self.image_map), *queries],
                              capture_output=True, text=True, cwd=ROOT)
        if proc.returncode != 0:
            raise TypedStateError(f"verifier rejected {queries}: {proc.stderr.strip()}")
        return json.loads(proc.stdout)["queries"]


def _corroborate_table_writers(index: dict, image: str, table_addr: int,
                               writers: dict) -> list[dict]:
    """Stores the INDEX resolved into the table that the C scan did not find.

    The C scan matches a store's offset and walks back for a lui carrying the
    right upper half; it can MISS a writer whose base was materialised far away
    or arrived as an argument -- the direction that makes an incomplete writer
    set look complete. The static index resolves addresses by full constant
    propagation, so any store it sees that the scan does not is a hole in the
    scan, and the binding must fail on it.
    """
    scanned = {_int(w["pc"]) for w in writers["writers"]}
    index_only = []
    for record in index["records"]:
        if record["image_id"] != image:
            continue
        for acc in record.get("memory_accesses") or []:
            addr = acc.get("address")
            if addr is None or _int(addr) != table_addr:
                continue
            if str(acc.get("mnemonic", "")).lower() not in ("sb", "sh", "sw"):
                continue
            if _int(acc["pc"]) not in scanned:
                index_only.append({"pc": acc["pc"], "function": record.get("name")})
    return index_only


def _attest_known_writer_identity(table_addr: int, writers: dict) -> dict:
    """Exact-set pin for the corrected known 0x80090748 writer lower bound.

    This is deliberately NOT an exhaustiveness claim. It prevents a regression
    back to the four-writer spelling while the independent undecided-store gate
    continues to measure everything the positive recogniser cannot classify.
    """
    discovered = {_int(row["pc"]) for row in writers["writers"]}
    expected = (PINNED_KNOWN_ACTOR_TABLE_WRITERS
                if table_addr == ACTOR_POINTER_TABLE else discovered)
    return {
        "table": f"0x{table_addr:08x}",
        "comparison": "exact PC set in both directions",
        "expected_known_lower_bound": sorted(f"0x{pc:08x}" for pc in expected),
        "discovered_known_lower_bound": sorted(f"0x{pc:08x}" for pc in discovered),
        "expected_only": sorted(f"0x{pc:08x}" for pc in expected - discovered),
        "discovered_only": sorted(f"0x{pc:08x}" for pc in discovered - expected),
        "exact_match": discovered == expected,
        "previously_enumerated": sorted(
            f"0x{pc:08x}" for pc in PREVIOUS_ACTOR_TABLE_WRITERS
            if table_addr == ACTOR_POINTER_TABLE),
        "gained_known_writers": sorted(
            f"0x{pc:08x}" for pc in discovered - PREVIOUS_ACTOR_TABLE_WRITERS
            if table_addr == ACTOR_POINTER_TABLE),
        "lost_known_writers": sorted(
            f"0x{pc:08x}" for pc in PREVIOUS_ACTOR_TABLE_WRITERS - discovered
            if table_addr == ACTOR_POINTER_TABLE),
        "recognizer_enumeration_complete": bool(writers.get("enumeration_complete")),
        "recognizer_residual_store_words": int(
            writers.get("recognizer_residual_store_words", -1)),
        "syntactic_store_word_universe": int(
            writers.get("syntactic_store_word_universe", -1)),
        "meaning": ("the six-PC set is the corrected KNOWN lower bound; the "
                    "positive recogniser's nonzero residual and the independent "
                    "corpus undecided-store measurement forbid an exhaustive claim"),
    }


def _prove_writer_value_domains(verifier: Verifier, index: dict, image: str,
                                region_lo: int, writers: dict) -> tuple[bool, list, str]:
    """Finding-1 closure: 'loads from the table' is not 'points into the region'
    until every enumerated writer's WRITTEN VALUE domain is machine-proved.

    Null writers are proved by encoding (the value register IS $zero). Each
    non-null writer must pass the C `progression@` proof in its containing
    extent: every definition of its value register is a shadowed/agreeing
    constant anchor, a uniform positive self-adjustment, or a terminal-epilogue
    reload -- with no reachability argument, so the delay-slot blind spot in
    the observability walk cannot decide a proof. The anchor must equal the
    declared region start; the proved domain is then {anchor + k*stride, k>=0}
    -- a LOWER bound and a lattice, deliberately no upper bound.
    """
    domains = []
    failures: list[str] = []
    for writer in writers["writers"]:
        pc = _int(writer["pc"])
        if writer.get("clears_to_null"):
            domains.append({"pc": writer["pc"], "kind": "null",
                            "basis": "value register is $zero by encoding",
                            "value_domain_proved": True})
            continue
        if writer.get("value_source_kind") == \
                "existing_entry_from_same_table_family":
            # 0x80049C10 is mechanically a MOVE, not a fresh publisher: a0 is
            # loaded at 0x80049C08 through one TABLE+(index<<2) base and stored
            # through another. That proves preservation conditional on the
            # source table invariant. It does NOT bootstrap that invariant.
            domains.append({
                "pc": writer["pc"],
                "kind": "same_table_entry_move",
                "value_register": writer["value_register"],
                "source_load_pc": writer.get("value_source_pc"),
                "instruction_fact_proved": True,
                "value_domain_proved": False,
                "conditional_preservation": (
                    "if the source slot is null or points into the declared actor "
                    "region, the destination receives a value in the same domain"),
                "what_would_prove_the_induction": [
                    "prove every source and destination slot index is inside the table",
                    "prove initial table contents are null or actor-region pointers",
                    "prove every non-move non-null publisher writes that domain",
                    "prove the table-writer universe exhaustive",
                    "then close the least fixed point under null clears and entry moves",
                ],
                "why_not_proof_today": (
                    "the source table-content invariant and writer exhaustiveness "
                    "are prerequisites; assuming either here would relabel the "
                    "desired induction hypothesis as its own proof"),
            })
            failures.append(
                f"non-null writer 0x{pc:08x} only preserves a same-table "
                "content invariant that is not yet proved")
            continue
        record = next((r for r in index["records"]
                       if r["image_id"] == image and r.get("entry")
                       and _int(r["entry"]) <= pc < _int(r["end"])), None)
        if record is None:
            domains.append({"pc": writer["pc"], "kind": "unproved",
                            "value_domain_proved": False,
                            "reason": "writer lies in no indexed extent"})
            failures.append(f"non-null writer 0x{pc:08x} lies in no indexed extent")
            continue
        q = verifier.ask(f"progression@{image}:{record['entry']}:{record['end']}"
                         f":{writer['value_register']}:0x{pc:08x}")[0]
        domains.append({"pc": writer["pc"], "kind": "anchored_progression",
                        "value_register": writer["value_register"],
                        "extent": f"{record['entry']}..{record['end']}",
                        "proof": q, "value_domain_proved": bool(q.get("verdict")
                            and _int(q.get("anchor") or 0) == region_lo)})
        if not q.get("verdict"):
            failures.append(
                f"non-null writer 0x{pc:08x}: {writer['value_register']} value "
                "domain is not an anchored progression")
        elif _int(q["anchor"]) != region_lo:
            failures.append(
                f"non-null writer 0x{pc:08x}: anchor {q['anchor']} != declared "
                f"region start 0x{region_lo:08x}")
    return not failures, domains, "; ".join(failures)


def _measure_table_writer_universe(verifier: Verifier, index: dict,
                                   table_addr: int, table_span: int,
                                   writers: dict) -> dict:
    """Finding-2 measurement: how many stores could alias the table and are
    NOT decided?

    The positive C spelling recogniser plus the index cross-check can only name
    stores they resolve; neither can exclude another unresolved computed-base
    store from aliasing the table. This runs the independent region analyser
    over the table WINDOW on every image and reports, exactly: the accesses it
    resolves into the window, the sites it excludes (convention tiers, its own
    disclosure), and the store sites it cannot decide. A nonzero undecided
    store count means the writer universe is NOT proved exhaustive -- the same
    open problem, in miniature, as Item 2 itself.
    """
    per_image = {}
    total_undecided_stores = 0
    enumerated = {_int(w["pc"]) for w in writers["writers"]}
    access_kinds: dict[tuple[str, int], set[str]] = {}
    for record in index["records"]:
        for access in record.get("memory_accesses") or []:
            access_kinds.setdefault(
                (record["image_id"], _int(access["pc"])), set()).add(
                    str(access.get("access") or ""))
    resolved_write_hits: set[int] = set()
    for image_meta in index["images"]:
        image_id = image_meta["image_id"]
        try:
            report = verifier.region_provenance(image_id, table_addr, table_span)
        except TypedStateError as exc:
            per_image[image_id] = {"unavailable": str(exc)}
            total_undecided_stores = -1
            continue
        undecided_stores = [u for u in report.get("unresolved_all") or []
                            if str(u.get("kind")) == "write"]
        hits = [str(p) for p in report.get("hit_pcs") or []]
        hit_writes = sorted(
            p for p in hits
            if "write" in access_kinds.get((image_id, _int(p)), set()))
        if image_id == RESIDENT_IMAGE:
            resolved_write_hits |= {_int(p) for p in hit_writes}
        undecided_pcs = sorted(str(row["pc"]) for row in undecided_stores)
        per_image[image_id] = {
            "resolved_into_window": len(hits),
            "hit_pcs": hits,
            "resolved_write_hit_pcs": hit_writes,
            "excluded_by_convention_tiers": report.get("exclusions_total"),
            "undecided_stores": len(undecided_stores),
            "undecided_store_pc_identity_sha256": _sha(
                json.dumps(undecided_pcs, separators=(",", ":")).encode()),
            "undecided_store_pc_first_16": undecided_pcs[:16],
            "undecided_indirect": report.get("indirect_unresolved"),
        }
        if total_undecided_stores >= 0:
            total_undecided_stores += len(undecided_stores)
    resident_hits = {_int(p) for p in
                     (per_image.get(RESIDENT_IMAGE) or {}).get("hit_pcs") or []}
    previous = (PREVIOUS_ACTOR_TABLE_WRITERS
                if table_addr == ACTOR_POINTER_TABLE else set())
    return {
        "window": [f"0x{table_addr:08x}", f"0x{table_addr + table_span:08x}"],
        "window_derivation": ("64 published slots plus the null terminator at "
                              "index <= 64: offsets 0..0x100, width 4"),
        "method": "tools/region_provenance.c over the table window, every image",
        "per_image": per_image,
        "enumerated_writers_missing_from_resolved_hits": sorted(
            f"0x{pc:08x}" for pc in enumerated if pc not in resident_hits),
        "resolved_write_hit_pcs": sorted(
            f"0x{pc:08x}" for pc in resolved_write_hits),
        "resolved_writers_not_previously_enumerated": sorted(
            f"0x{pc:08x}" for pc in (resolved_write_hits & enumerated) - previous),
        "known_writer_set_gained": sorted(
            f"0x{pc:08x}" for pc in enumerated - previous),
        "known_writer_set_lost": sorted(
            f"0x{pc:08x}" for pc in previous - enumerated),
        "writer_recognizer_syntactic_store_word_universe":
            writers.get("syntactic_store_word_universe"),
        "writer_recognizer_residual_store_words":
            writers.get("recognizer_residual_store_words"),
        "writer_recognizer_enumeration_complete":
            writers.get("enumeration_complete"),
        "corpus_undecided_stores": total_undecided_stores,
        "exhaustive": total_undecided_stores == 0,
        "meaning": ("a nonzero undecided count means stores exist whose "
                    "effective address no static analysis here has bounded "
                    "away from the table; the enumerated writer set is a "
                    "corrected KNOWN LOWER bound, not a census. The exact "
                    "undecided-PC identity is retained per image as a count, "
                    "sha256, and first-16 audit sample rather than asserted empty"),
    }


def _cluster_entry_edges(index: dict, cluster_image: str, c_lo: int, c_hi: int,
                         ) -> dict:
    """Finding-3 closure: entry integrity over the SAME seven-successor,
    all-image universe the gap-boundary census uses.

    An index-record scan sees calls, jumps and branches of one image; it does
    not see fallthrough, call-return or indirect-call-return continuations,
    and it skipped the overlays entirely. This walks EVERY image's reachable
    code (direct edges plus the armed verified jr targets on the resident
    image) and enumerates every successor of every reachable instruction that
    lands in [c_lo, c_hi), by kind, from sources outside it. Fallthrough obeys
    the context-sensitive delay-slot rule. The ONLY tolerated entry is `call`
    landing exactly on c_lo -- a typed caller; a jump, branch, fallthrough,
    call-return or proved-jr target landing at c_lo is an UNTYPED entry and is
    an intruder like any interior hit.
    """
    import struct as _struct
    import phase4_static_frontier as generator

    resident_meta = next((i for i in index["images"] if i["role"] == "resident"), None)
    resident_sha = (resident_meta or {}).get("sha256") or ""
    generator.load_jr_targets(generator.JR_ARTIFACT_PATH, resident_sha)
    gate_import = generator.load_gate_jr_targets(generator.GATE_ARTIFACT_PATH,
                                                 resident_sha)
    intruders: list[dict] = []
    callers: list[dict] = []
    images_walked = []
    for image_meta in index["images"]:
        image_id = image_meta["image_id"]
        path = ROOT / image_meta["path"]
        raw = path.read_bytes()
        base = _int(image_meta["file_va_base"])
        word_at: dict[int, int] = {}
        entries: list[int] = []
        for record in index["records"]:
            if record["image_id"] != image_id or not record.get("entry"):
                continue
            if record.get("range_type") not in ("code", "thunk"):
                continue
            lo, hi = _int(record["entry"]), _int(record["end"])
            entries.append(lo)
            for pc in range(lo, hi, 4):
                offset = pc - base
                if 0 <= offset + 4 <= len(raw):
                    word_at[pc] = _struct.unpack_from("<I", raw, offset)[0]
        reachable, block_starts, _ = generator.image_direct_cfg(word_at, sorted(entries))
        delay_slots = {pc + 4 for pc in reachable
                       if generator.control_flow(word_at[pc], pc)[0] is not None}
        images_walked.append(image_id)

        def record_hit(target, source, kind):
            if target is None:
                return
            inside_target = c_lo <= target < c_hi
            if not inside_target:
                return
            if image_id == cluster_image and c_lo <= source < c_hi:
                return                       # intra-cluster flow
            row = {"image": image_id, "source": f"0x{source:08x}",
                   "kind": kind, "target": f"0x{target:08x}"}
            if kind == "call" and target == c_lo:
                callers.append(row)
            else:
                intruders.append(row)

        for pc in sorted(reachable):
            word = word_at[pc]
            kind, target = generator.control_flow(word, pc)
            if kind is None:
                if pc not in delay_slots or pc in block_starts:
                    record_hit(pc + 4, pc, "fallthrough")
                continue
            if kind == "branch":
                for value in generator.branch_successors(word, pc, target):
                    record_hit(value, pc, "branch")
            elif kind == "jump":
                record_hit(target, pc, "jump")
            elif kind == "call":
                record_hit(target, pc, "call")
                record_hit(pc + 8, pc, "call_return")
            elif kind == "indirect_call":
                record_hit(pc + 8, pc, "indirect_call_return")
            elif kind == "indirect_jump":
                for value in generator.JR_TARGETS.get(pc, ()):
                    record_hit(value, pc, "resolved_indirect_jump")
    return {
        "universe": ("every instruction reachable from every indexed "
                     "code/thunk entry in ALL images, direct edges plus the "
                     "verified jr targets armed on the resident image; all "
                     "seven successor kinds enumerated; fallthrough uses the "
                     "context-sensitive delay-slot rule; the only tolerated "
                     "entry is `call` landing exactly on the cluster start"),
        "images_walked": images_walked,
        "jr_sources_armed": {
            "phase3": {"verified": bool(generator.JR_PROVENANCE.get("verified")),
                       "sites": generator.JR_PROVENANCE.get("sites")},
            "gate": {"verified": bool(gate_import.get("verified")),
                     "sites": gate_import.get("sites")},
        },
        "callers": callers,
        "intruders": intruders,
    }


def verify_proved_jr_cluster_argument(binding: dict, index: dict, ledger: dict,
                                      verifier: Verifier,
                                      regions: dict) -> tuple[bool, str, dict | None]:
    """Bound a target-root ISLAND's callee-saved base across its one proved edge.

    The island's only established entry is a gate-proved `jr` target, so no
    within-extent analysis can ever see a definition of its base register. The
    domain is propagated across EXACTLY that one edge -- this is deliberately
    not a general jr-state propagator -- and every link in the chain is
    re-derived from instructions or from the pinned index each run:

      1. The binding's function is a target-root island record; its
         `island_provenance.reached_by` names exactly one jr site, and the
         index's hash-pinned jr map proves that site targets the island entry.
      2. The declared cluster tiles exactly onto contiguous index records, the
         jr site and the island both lie inside it, and NO direct edge, proved
         jr target, or recursive call enters its interior from outside -- so
         the cluster's straight-line prologue governs every entry.
      3. The C verifier (rebuilt here) proves: the prologue purely copies an
         argument register into the bound register before any control flow;
         every OTHER write to it in the cluster is an sp-restore inside a
         TERMINAL epilogue; each direct call site decodes as `jal cluster`
         with a pure copy into that argument register in the delay slot; and
         the island's accesses through the register are enumerated for an
         exact-set reconciliation with the ledger.
      4. Each caller's copied source register is typed at the call site by the
         same machinery as typed_pointer_load: every observable definition
         reaching the call loads from the declared pointer table, no path
         arrives undefined, and the table's writers are enumerated image-wide
         and corroborated against the index.

    What this does NOT exclude, stated rather than implied: an unbounded
    indirect CALL (`jalr`) could in principle enter anywhere -- that is the
    standing Item-2 blocker class every binding in this file lives with, and
    it stays enumerated in the ledger untouched.
    """
    image = binding["image"]
    entry = _int(binding["function"])
    reg = binding["register"]
    table_addr = _int(binding["pointer_table"])
    c_lo = _int(binding["cluster"]["start"])
    c_hi = _int(binding["cluster"]["end"])

    # ---- 1. the island record and its one proved edge, from the pinned index
    record = next((r for r in index["records"]
                   if r.get("entry") and _int(r["entry"]) == entry
                   and r["image_id"] == image), None)
    if record is None:
        return False, f"rejected: no static-index record for {image}@0x{entry:08x}", None
    if record.get("source") != "target_root_island":
        return False, ("rejected: proved_jr_cluster_argument applies only to "
                       "target-root island records"), None
    isl_lo, isl_hi = entry, _int(record["end"])
    reached_by = [_int(pc) for pc in record["island_provenance"]["reached_by"]]
    if len(reached_by) != 1:
        return False, (f"rejected: island has {len(reached_by)} proved entry "
                       "edges; this binding propagates across exactly one"), None
    jr_pc = reached_by[0]
    site_targets: dict[int, set[int]] = {}
    for source in ("indirect_jump_targets", "indirect_jump_targets_from_gate"):
        for key, values in ((index.get(source) or {}).get("site_targets") or {}).items():
            site_targets.setdefault(_int(key), set()).update(_int(v) for v in values)
    if entry not in site_targets.get(jr_pc, set()):
        return False, (f"rejected: the pinned jr map does not prove "
                       f"0x{jr_pc:08x} -> 0x{entry:08x}"), None
    if not (c_lo <= jr_pc < c_hi) or not (c_lo <= isl_lo and isl_hi <= c_hi):
        return False, ("rejected: the jr site or the island lies outside the "
                       "declared cluster"), None

    # ---- 2. the cluster tiles onto records; nothing enters its interior -----
    rows = sorted((_int(r["entry"]), _int(r["end"])) for r in index["records"]
                  if r["image_id"] == image and r.get("entry")
                  and c_lo <= _int(r["entry"]) and _int(r["end"]) <= c_hi)
    if (not rows or rows[0][0] != c_lo or rows[-1][1] != c_hi
            or any(a[1] != b[0] for a, b in zip(rows, rows[1:]))):
        return False, ("rejected: the declared cluster does not tile exactly "
                       "onto contiguous index records"), None
    # Entry integrity over the SAME seven-successor, all-image universe the
    # gap-boundary census uses -- not an index-record scan of one image. A
    # proved jr target or any non-call successor landing exactly at c_lo is an
    # UNTYPED entry and rejects like an interior hit.
    edges = _cluster_entry_edges(index, image, c_lo, c_hi)
    if edges["intruders"]:
        return False, (f"rejected: {len(edges['intruders'])} successor(s) enter "
                       "the cluster from outside by a non-call edge, so the "
                       "prologue does not govern every entry"), {
            "entry_integrity": {**edges, "intruders": edges["intruders"][:10]}}
    # The walk's callers and the index's caller edges are two derivations of
    # the same set; require them to agree exactly.
    walk_caller_pcs = sorted(_int(row["source"]) for row in edges["callers"])
    callers: list[tuple[str, int, int, int, str]] = []
    for r in index["records"]:
        if not r.get("entry"):
            continue
        for edge in r.get("direct_calls") or []:
            if _int(edge["target"]) == c_lo:
                callers.append((r["image_id"], _int(r["entry"]), _int(r["end"]),
                                _int(edge["pc"]), str(r.get("name") or "")))
    index_caller_pcs = sorted(pc for _, _, _, pc, _ in callers)
    if walk_caller_pcs != index_caller_pcs:
        return False, ("rejected: the whole-image walk and the index disagree "
                       f"about the caller set ({walk_caller_pcs} vs "
                       f"{index_caller_pcs})"), {"entry_integrity": edges}
    if not callers:
        return False, "rejected: no direct caller of the cluster entry", None

    # ---- ledger sites, chosen by the ledger, never by this schema -----------
    targets = sorted({_int(s["pc"]) for s in ledger.get("unresolved_accesses") or []
                      if _names_function(str(s.get("function", "")), image, entry)
                      and str(s.get("base_register")) == reg})
    if not targets:
        return False, "rejected: the ledger has no unresolved site for this binding", None

    # ---- 3. the C-verified instruction facts --------------------------------
    # Cross-image caller typing is not implemented: the island@ decode and the
    # defsat typing both read one image. No overlay calls this cluster today;
    # if one ever does, this fails closed rather than typing the wrong bytes.
    foreign = [name for cimg, _, _, _, name in callers if cimg != image]
    if foreign:
        return False, (f"rejected: caller(s) {foreign} live outside {image}; "
                       "cross-image caller typing is not supported"), None
    call_pcs = sorted(pc for _, _, _, pc, _ in callers)
    island_facts = verifier.ask(
        f"island@{image}:0x{c_lo:08x}:0x{c_hi:08x}:0x{isl_lo:08x}:0x{isl_hi:08x}"
        f":{reg}:" + ",".join(f"0x{p:08x}" for p in call_pcs))[0]
    attest: dict = {
        "verifier_source": VERIFIER_SRC,
        "verifier_source_sha256": verifier.source_sha,
        "verifier_binary_sha256": verifier.binary_sha,
        "regenerated_here": True,
        "proved_edge": {"jr_site": f"0x{jr_pc:08x}", "target": f"0x{entry:08x}",
                        "pinned_in": "indirect_jump_targets(_from_gate).site_targets"},
        "cluster_records": len(rows),
        "cluster_entry_integrity": {
            "universe": edges["universe"],
            "images_walked": edges["images_walked"],
            "jr_sources_armed": edges["jr_sources_armed"],
            "intruders": [],
            "callers_agree_with_index": True,
            "callers_of_the_cluster_entry": [
                {"function": name, "call_pc": f"0x{pc:08x}"}
                for _, _, _, pc, name in callers],
        },
        "island_facts": island_facts,
        "residual_assumptions": [
            "unbounded indirect calls (jalr) are not excluded by any static "
            "evidence; they remain enumerated Item-2 blockers and are NOT "
            "covered by this binding",
            "callee-saved register discipline across calls inside the cluster "
            "is the PSX ABI convention this file's dataflow model assumes "
            "everywhere",
        ],
    }
    if not island_facts.get("verdict"):
        return False, ("rejected: the C verifier refuted the cluster facts "
                       "(see island_facts for the failing pc)"), attest
    island_access_pcs = sorted(_int(a["pc"]) for a in island_facts["island_accesses"])
    if island_access_pcs != targets:
        return False, (f"rejected: the island's register accesses "
                       f"{[f'0x{p:08x}' for p in island_access_pcs]} and the ledger's "
                       f"sites {[f'0x{p:08x}' for p in targets]} differ as sets"), attest

    # ---- 4. type each caller's copied source at its call site ---------------
    # Caller typing and writer closure are independent proof obligations.  A
    # stricter caller classifier must not erase the already-demoted binding's
    # writer/value measurements, so retain caller failures and still run those
    # gates.  Acceptance below requires every obligation to pass.
    caller_queries = []
    caller_typing_failures: list[str] = []
    for (_, r_lo, r_hi, pc, name), fact in zip(callers, island_facts["callers"]):
        src = fact["delay_slot_copies"]
        q = verifier.ask(f"defsat@{image}:0x{r_lo:08x}:0x{r_hi:08x}:{src}:0x{pc:08x}")[0]
        caller_queries.append({"function": name, "call_pc": f"0x{pc:08x}",
                               "source_register": src,
                               "every_observable_def_loads_one_address":
                                   q["every_observable_def_loads_one_address"],
                               "loaded_from": q["loaded_from"],
                               "entry_reachable_uses": q["entry_reachable_uses"],
                               "definitions": q["definitions"]})
        if (q["loaded_from"] is not None
                and _int(q["loaded_from"]) != table_addr):
            attest["caller_typing"] = caller_queries
            return False, (f"rejected: {name}'s {src} loads from {q['loaded_from']}, "
                           f"not the declared table 0x{table_addr:08x}"), attest
        if not q["every_observable_def_loads_one_address"]:
            caller_typing_failures.append(
                f"{name}'s {src} at 0x{pc:08x} is not uniformly loaded from "
                "one address")
            continue
        if q["entry_reachable_uses"]:
            caller_typing_failures.append(
                f"{name}'s {src} can reach the call undefined")
    attest["caller_typing"] = caller_queries
    attest["caller_typing_failures"] = caller_typing_failures

    # ---- corrected known writer lower bound, exact-set pinned ---------------
    writers = verifier.ask(f"writers@{image}:0x{table_addr:08x}")[0]
    index_only = _corroborate_table_writers(index, image, table_addr, writers)
    writer_identity = _attest_known_writer_identity(table_addr, writers)
    attest.update({
        "table_writers": writers["writers"],
        "table_writer_count": writers["writer_count"],
        "table_non_null_writers": writers["non_null_writers"],
        "table_writers_the_scan_missed": index_only,
        "writer_index_crosscheck_no_index_only": not index_only,
        "writer_enumeration_corroborated": False,
        "known_writer_identity": writer_identity,
        "writer_recognizer_residual": {
            "syntactic_store_word_universe":
                writers.get("syntactic_store_word_universe"),
            "unclassified_store_words":
                writers.get("recognizer_residual_store_words"),
            "enumeration_complete": writers.get("enumeration_complete"),
            "meaning": writers.get("residual_meaning"),
        },
    })
    if not writer_identity["exact_match"]:
        return False, ("rejected: corrected known writer PC identity drifted "
                       "(see known_writer_identity exact differences)"), attest
    if index_only:
        return False, (f"rejected: the static index resolves {len(index_only)} store(s) "
                       f"to 0x{table_addr:08x} that the scan did not find"), attest

    # ---- 5. the written-VALUE domains (review finding 1) --------------------
    # "Loads from the table" does not establish "points into the region" until
    # every enumerated writer's written value is machine-proved null or an
    # anchored progression starting at the region.
    region_lo = regions[binding["region"]][0]
    dom_ok, domains, dom_why = _prove_writer_value_domains(
        verifier, index, image, region_lo, writers)
    attest["writer_value_domains"] = domains
    attest["writer_value_domains_proved"] = dom_ok
    attest["writer_value_domains_failure"] = None if dom_ok else dom_why

    # ---- 6. the writer UNIVERSE (review finding 2) --------------------------
    # The enumerated writer set is a corrected KNOWN LOWER bound. Whether any
    # OTHER store can alias the table is measured over every image, and while
    # the undecided residual is nonzero the chain cannot claim proof: the same
    # open problem as Item 2 itself, in miniature. This gate is expected to
    # FAIL today; everything above it stays in the attestation so the one
    # missing link is exactly named.
    universe = _measure_table_writer_universe(verifier, index, table_addr,
                                              0x104, writers)
    attest["table_writer_universe"] = universe
    if not dom_ok or not universe["exhaustive"]:
        blockers = list(caller_typing_failures)
        if not dom_ok:
            blockers.append(f"writer value domain: {dom_why}")
        if not universe["exhaustive"]:
            blockers.append(
                "table-writer universe is not proved exhaustive: "
                f"{universe['corpus_undecided_stores']} store(s) across "
                f"{len(universe['per_image'])} images retain undecided effective "
                f"addresses relative to 0x{table_addr:08x}")
        return False, ("rejected: " + " | ".join(blockers) +
                       ". Neither a conditional same-table induction nor a "
                       "known six-writer lower bound closes Item 2"), attest

    if caller_typing_failures:
        return False, ("rejected: " + " | ".join(caller_typing_failures)), attest

    return True, (f"verified: {reg} at the island is the cluster's incoming "
                  f"{island_facts['prologue']['argument']} (pure copy at "
                  f"{island_facts['prologue']['copy_pc']}; sole other write is the "
                  "terminal epilogue restore); the island is entered only through "
                  f"the proved jr at 0x{jr_pc:08x}; all {len(callers)} caller(s) pass "
                  f"a value loaded from 0x{table_addr:08x}, whose "
                  f"{writers['writer_count']} image-wide writers "
                  f"({writers['non_null_writers']} non-null) are corroborated, "
                  "value-domain proved, and exhaustively bounded"), attest


def verify_typed_pointer_load(binding: dict, index: dict, ledger: dict,
                              verifier: Verifier,
                              regions: dict) -> tuple[bool, str, dict | None]:
    """Prove the base really is loaded from the declared pointer table.

    Three things must hold, and all three are answered by reading instructions:

      1. Every definition of the register that can reach the sites being bounded
         loads from ONE address, and that address is the declared table.
      2. No site is reachable from the function entry without passing a
         definition -- otherwise the register can arrive holding the caller's
         value and the definitions govern nothing.
      3. The corrected known writer lower bound is exact-set pinned and checked
         against the index.
      4. Every enumerated writer's value domain is proved.
      5. The table-writer universe is proved exhaustive.

    The last two conditions are the same hard gates used by
    proved_jr_cluster_argument. A fresh verifier rejected the former
    grandfathering exception after the premise supporting it was falsified.
    """
    table = binding["pointer_table"]
    if table is None:
        return False, "rejected: typed_pointer_load needs a pointer_table", None
    table_addr = _int(table)
    entry = _int(binding["function"])
    image = binding["image"]

    record = next((r for r in index["records"]
                   if r.get("entry") and _int(r["entry"]) == entry
                   and r["image_id"] == image), None)
    if record is None:
        return False, f"rejected: no static-index record for {image}@0x{entry:08x}", None
    end = _int(record["end"])

    # The sites to bound are taken from the LEDGER, not from the schema: the
    # document does not get to choose which sites its own binding is tested on.
    targets = sorted({_int(s["pc"]) for s in ledger.get("unresolved_accesses") or []
                      if _names_function(str(s.get("function", "")), image, entry)
                      and str(s.get("base_register")) == binding["register"]})
    if not targets:
        return False, "rejected: the ledger has no unresolved site for this binding", None

    img = image
    pcs = ",".join(f"0x{p:08x}" for p in targets)
    defs, writers = verifier.ask(f"{img}:0x{entry:08x}:0x{end:08x}:{binding['register']}:{pcs}",
                                 f"writers@{img}:0x{table_addr:08x}")
    # The C scan finds a store by matching the offset and walking back for a lui
    # carrying the right upper half. That heuristic can MISS a writer whose base
    # was materialised far away or arrived as an argument -- the direction that
    # would make an incomplete writer set look complete. So cross-check it
    # against the addresses the static index resolved independently, by full
    # constant propagation, and report any writer only the index saw.
    index_only = _corroborate_table_writers(index, image, table_addr, writers)
    writer_identity = _attest_known_writer_identity(table_addr, writers)

    attest = {
        "verifier_source": VERIFIER_SRC,
        "verifier_source_sha256": verifier.source_sha,
        "verifier_binary_sha256": verifier.binary_sha,
        "regenerated_here": True,
        "targeted_sites": defs["targeted_sites"],
        "definitions": defs["definitions"],
        "every_observable_def_loads_one_address":
            defs["every_observable_def_loads_one_address"],
        "loaded_from": defs["loaded_from"],
        "entry_reachable_uses": defs["entry_reachable_uses"],
        "table_writers": writers["writers"],
        "table_writer_count": writers["writer_count"],
        "table_non_null_writers": writers["non_null_writers"],
        "table_writers_the_scan_missed": index_only,
        "writer_index_crosscheck_no_index_only": not index_only,
        "writer_enumeration_corroborated": False,
        "known_writer_identity": writer_identity,
        "writer_recognizer_residual": {
            "syntactic_store_word_universe":
                writers.get("syntactic_store_word_universe"),
            "unclassified_store_words":
                writers.get("recognizer_residual_store_words"),
            "enumeration_complete": writers.get("enumeration_complete"),
            "meaning": writers.get("residual_meaning"),
        },
    }
    if (defs["loaded_from"] is not None
            and _int(defs["loaded_from"]) != table_addr):
        return False, (f"rejected: loaded from {defs['loaded_from']}, not the declared "
                       f"table 0x{table_addr:08x}"), attest
    if defs["entry_reachable_uses"]:
        return False, (f"rejected: {defs['entry_reachable_uses']} site(s) reachable from "
                       "entry without any definition"), attest
    if not writer_identity["exact_match"]:
        return False, ("rejected: corrected known writer PC identity drifted "
                       "(see known_writer_identity exact differences)"), attest
    if index_only:
        return False, (f"rejected: the static index resolves {len(index_only)} store(s) to "
                       f"0x{table_addr:08x} that the scan did not find, so the writer set "
                       "is not shown to be complete"), attest

    # Like the cluster binding, retain the independent writer/value gates even
    # when stricter table-base dataflow finds an earlier definition failure.
    # This preserves both blockers without letting either substitute for the
    # other; the success path still requires the complete conjunction.
    definition_failures = []
    if not defs["every_observable_def_loads_one_address"]:
        definition_failures.append(
            "the definitions reaching these sites do not all load from one address")
    attest["definition_gate_failures"] = definition_failures

    # ---- the two links the 2026-08-06 review named, GATED here --------------
    # The 2026-08-07 fresh verifier rejected the old grandfathering exception:
    # once the four-writer exhaustiveness premise was falsified, a binding that
    # consumes the same table cannot remain proof while these predicates fail.
    region_lo = regions[binding["region"]][0]
    dom_ok, domains, dom_why = _prove_writer_value_domains(
        verifier, index, image, region_lo, writers)
    universe = _measure_table_writer_universe(verifier, index, table_addr,
                                              0x104, writers)
    attest["writer_value_domains"] = domains
    attest["writer_value_domains_proved"] = dom_ok
    attest["writer_value_domains_failure"] = None if dom_ok else dom_why
    attest["table_writer_universe"] = universe
    attest["hard_truth_gate"] = {
        "required_predicates": [
            "writer_value_domains_proved",
            "table_writer_universe.exhaustive",
        ],
        "writer_value_domains_proved": dom_ok,
        "table_writer_universe_exhaustive": universe["exhaustive"],
        "accepted": dom_ok and universe["exhaustive"],
        "decision": (
            "2026-08-07 fresh verifier: the falsified writer-exhaustiveness "
            "premise cannot be grandfathered as proof"),
    }
    if not dom_ok or not universe["exhaustive"]:
        blockers = list(definition_failures)
        if not dom_ok:
            blockers.append(f"writer value domain: {dom_why}")
        if not universe["exhaustive"]:
            blockers.append(
                "table-writer universe is not proved exhaustive: "
                f"{universe['corpus_undecided_stores']} store(s) across "
                f"{len(universe['per_image'])} images retain undecided effective "
                f"addresses relative to 0x{table_addr:08x}")
        return False, ("rejected: " + " | ".join(blockers) +
                       ". The prior four-writer premise is falsified and cannot "
                       "be grandfathered as proof"), attest

    if definition_failures:
        return False, ("rejected: " + " | ".join(definition_failures)), attest

    return True, (f"verified: all {defs['targeted_sites']} sites governed by definitions "
                  f"loading from 0x{table_addr:08x}; that table has "
                  f"{writers['writer_count']} writers whose value domains and "
                  "complete writer universe are proved"), attest


def _ask_batched(verifier: Verifier, queries: list[str], size: int = 128) -> list[dict]:
    """Keep argv/stdout bounded while still amortising image loads and C startup."""
    answers: list[dict] = []
    for offset in range(0, len(queries), size):
        answers.extend(verifier.ask(*queries[offset:offset + size]))
    return answers


def _indirect_transfer_closure(index: dict) -> dict:
    """Name every indexed indirect transfer and whether its target set closes.

    A missing target set is not an empty set.  It is a potential entry into any
    concurrently resident extent and therefore blocks an interval promotion.
    The two retained jr maps are resident-image artifacts and are accepted only
    for exact resident sites the static index actually decodes as indirect
    jumps; every jalr remains unknown because no retained source proves a
    complete call-target domain.  Malformed, empty, or conflicting maps retain
    an unknown domain instead of aborting the audit or choosing a source.
    """
    known: dict[tuple[str, int], tuple[int, ...]] = {}
    incomplete: set[tuple[str, int]] = set()
    provenance: dict[tuple[str, int], list[str]] = {}
    malformed_catalog = False

    images = index.get("images") if isinstance(index, dict) else None
    resident_rows = ([row for row in images
                      if isinstance(row, dict)
                      and row.get("role") == "resident"
                      and isinstance(row.get("image_id"), str)
                      and row["image_id"]]
                     if isinstance(images, list) else [])
    resident_image = (resident_rows[0]["image_id"]
                      if len(resident_rows) == 1 else None)
    if resident_image is None:
        malformed_catalog = True

    def exact_address(raw: object) -> int | None:
        if type(raw) not in (int, str):
            return None
        try:
            value = _int(raw)
        except (TypeError, ValueError):
            return None
        if not 0 <= value <= 0xffffffff or value & 3:
            return None
        return value

    for source in ("indirect_jump_targets", "indirect_jump_targets_from_gate"):
        source_doc = index.get(source)
        if source_doc is None:
            continue
        if not isinstance(source_doc, dict):
            malformed_catalog = True
            continue
        if source_doc.get("verified") is not True:
            malformed_catalog = True
            continue
        rows = source_doc.get("site_targets")
        if rows is None:
            continue
        if not isinstance(rows, dict):
            malformed_catalog = True
            continue
        source_keys: set[tuple[str, int]] = set()
        for pc_raw, target_rows in rows.items():
            pc = exact_address(pc_raw)
            if pc is None:
                malformed_catalog = True
                continue
            if resident_image is None:
                malformed_catalog = True
                continue
            key = (resident_image, pc)
            if key in source_keys:
                incomplete.add(key)
                known.pop(key, None)
                continue
            source_keys.add(key)
            provenance.setdefault(key, []).append(source)
            if not isinstance(target_rows, list) or not target_rows:
                incomplete.add(key)
                known.pop(key, None)
                continue
            parsed: list[int] = []
            domain_valid = True
            for target_raw in target_rows:
                target = exact_address(target_raw)
                if target is None or target in parsed:
                    domain_valid = False
                    break
                parsed.append(target)
            if not domain_valid:
                incomplete.add(key)
                known.pop(key, None)
                continue
            targets = tuple(sorted(parsed))
            if key in incomplete:
                continue
            if key in known and known[key] != targets:
                incomplete.add(key)
                known.pop(key, None)
                continue
            known[key] = targets

    sites: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for record in index["records"]:
        if not record.get("entry") or not record.get("end"):
            continue
        common = {
            "image": record["image_id"],
            "function": record.get("name"),
            "extent": [record["entry"], record["end"]],
        }
        for raw in record.get("indirect_jumps") or []:
            pc = _int(raw["pc"])
            key = (record["image_id"], pc)
            if key in seen:
                raise TypedStateError(f"duplicate indirect transfer {key}")
            seen.add(key)
            complete = (not malformed_catalog and key in known
                        and key not in incomplete)
            sites.append({
                **common,
                "id": f"indirect_jump:{record['image_id']}:0x{pc:08x}",
                "kind": "indirect_jump",
                "pc": f"0x{pc:08x}",
                "register": raw.get("register"),
                "target_domain_complete": complete,
                "targets": ([f"0x{target:08x}" for target in known[key]]
                            if complete else []),
                "target_provenance": sorted(provenance.get(key, [])),
            })
        for raw in record.get("indirect_calls") or []:
            pc = _int(raw["pc"])
            key = (record["image_id"], pc)
            if key in seen:
                raise TypedStateError(f"duplicate indirect transfer {key}")
            seen.add(key)
            sites.append({
                **common,
                "id": f"indirect_call:{record['image_id']}:0x{pc:08x}",
                "kind": "indirect_call",
                "pc": f"0x{pc:08x}",
                "register": raw.get("register"),
                "target_domain_complete": False,
                "targets": [],
                "target_provenance": [],
            })
    sites.sort(key=lambda row: (row["kind"], row["image"], _int(row["pc"])))
    jumps = [row for row in sites if row["kind"] == "indirect_jump"]
    calls = [row for row in sites if row["kind"] == "indirect_call"]
    unknown_jumps = [row for row in jumps if not row["target_domain_complete"]]
    unknown_calls = [row for row in calls if not row["target_domain_complete"]]
    return {
        "definition": (
            "every indirect_jumps and indirect_calls row in the complete static "
            "index record universe; only agreeing nonempty, validated exact jr "
            "site-target maps tied to the decoded resident site close a domain, "
            "and an absent, empty, malformed, or conflicting set is a blocker, "
            "never empty"),
        "site_count": len(sites),
        "indirect_jump_site_count": len(jumps),
        "complete_indirect_jump_site_count": len(jumps) - len(unknown_jumps),
        "unknown_indirect_jump_site_count": len(unknown_jumps),
        "indirect_call_site_count": len(calls),
        "unknown_indirect_call_site_count": len(unknown_calls),
        "unknown_transfer_site_ids": sorted(
            row["id"] for row in unknown_jumps + unknown_calls),
        "target_domains_complete": not unknown_jumps and not unknown_calls,
        "sites": sites,
    }


def _images_can_coexist(index: dict, source: str, target: str) -> bool:
    """Conservatively decide whether two indexed images can be resident.

    Distinct images whose verified load spans overlap cannot occupy those bytes
    at the same time.  Disjoint spans can coexist even when both images are
    overlays (for example, independent swap regions).  Missing or malformed
    image metadata must fail closed for an external-entry proof, so it is
    treated as possible coexistence rather than silently excluding a source.
    """
    if source == target:
        return True
    if not isinstance(index, dict):
        return True
    images = index.get("images")
    if not isinstance(images, list):
        return True
    by_id: dict[str, list[dict]] = {}
    for row in images:
        if not isinstance(row, dict):
            return True
        image_id = row.get("image_id")
        if (not isinstance(image_id, str) or not image_id.strip()
                or image_id in by_id):
            return True
        by_id[image_id] = [row]
    if len(by_id.get(source, [])) != 1 or len(by_id.get(target, [])) != 1:
        return True
    try:
        source_meta = by_id[source][0]
        target_meta = by_id[target][0]
        if (source_meta.get("identity_verified") is not True
                or target_meta.get("identity_verified") is not True):
            return True
        # JSON booleans are Python integers and int(1.5) silently truncates.
        # Neither is admissible image metadata: coercing either could turn an
        # unknown lifetime relation into a false proof of mutual exclusion.
        source_base_raw = source_meta["file_va_base"]
        target_base_raw = target_meta["file_va_base"]
        source_size_raw = source_meta["size"]
        target_size_raw = target_meta["size"]
        if (type(source_base_raw) not in (int, str)
                or type(target_base_raw) not in (int, str)
                or type(source_size_raw) is not int
                or type(target_size_raw) is not int):
            return True
        source_lo = _int(source_base_raw)
        target_lo = _int(target_base_raw)
        source_size = source_size_raw
        target_size = target_size_raw
        if source_size <= 0 or target_size <= 0:
            return True
        source_hi = source_lo + source_size
        target_hi = target_lo + target_size
        if (not 0 <= source_lo < source_hi <= 0x100000000
                or not 0 <= target_lo < target_hi <= 0x100000000):
            return True
    except (KeyError, TypeError, ValueError):
        return True
    return source_hi <= target_lo or target_hi <= source_lo


def _external_interior_entries(
        index: dict, image: str, lo: int, hi: int,
        transfer_closure: dict | None = None,
) -> list[dict]:
    """Every proved OR still-unknown external edge into ``(lo, hi)``.

    ``indexdom@`` proves only paths from the declared extent entry.  Direct and
    complete-jr targets are compared exactly.  Every concurrently resident
    indirect site without a complete target domain is retained as a potential
    interior entry and blocks promotion until another proof excludes the
    extent.  This is deliberately stronger than the old "known hits only"
    query, which silently treated 160 unknown transfer domains as empty.
    """
    closure = transfer_closure or _indirect_transfer_closure(index)
    hits: list[dict] = []
    for record in index["records"]:
        source_image = record.get("image_id")
        if (not record.get("entry")
                or not _images_can_coexist(index, source_image, image)):
            continue
        r_lo = _int(record["entry"])
        if source_image == image and r_lo == lo:
            continue                         # modelled by the C extent CFG
        for edge in ((record.get("direct_jumps") or [])
                     + (record.get("direct_calls") or [])):
            target = _int(edge["target"])
            if lo < target < hi:
                hits.append({"kind": "jump_or_call", "image": source_image,
                             "from": record.get("name"), "pc": edge["pc"],
                             "target": edge["target"],
                             "target_domain_complete": True})
        for branch in record.get("branches") or []:
            for successor in branch.get("successors") or []:
                target = _int(successor)
                if lo < target < hi:
                    hits.append({"kind": "branch", "image": source_image,
                                 "from": record.get("name"), "pc": branch["pc"],
                                 "target": successor,
                                 "target_domain_complete": True})

    for site in closure["sites"]:
        source_image = site["image"]
        source_pc = _int(site["pc"])
        if (not _images_can_coexist(index, source_image, image)
                or (source_image == image and lo <= source_pc < hi)):
            continue                         # internal sites are C barriers
        if site["target_domain_complete"]:
            for target_raw in site["targets"]:
                target = _int(target_raw)
                if lo < target < hi:
                    hits.append({
                        "kind": "resolved_indirect_jump",
                        "image": source_image,
                        "from": site.get("function"),
                        "pc": site["pc"],
                        "target": target_raw,
                        "target_domain_complete": True,
                        "provenance": site["target_provenance"],
                    })
        else:
            hits.append({
                "kind": f"unknown_{site['kind']}_target_domain",
                "image": source_image,
                "from": site.get("function"),
                "pc": site["pc"],
                "target": None,
                "target_domain_complete": False,
                "reason": (
                    "unknown indirect target domain cannot exclude entry into "
                    f"0x{lo:08x}..0x{hi:08x}"),
                "source_site_id": site["id"],
            })

    def identity(row: dict) -> tuple:
        return (row["kind"], row.get("image"), _int(row["pc"]),
                _int(row["target"]) if row.get("target") is not None else -1)

    unique = {identity(row): row for row in hits}
    # A concrete edge into this exact extent is the best first breaker; unknown
    # global domains follow, still retained exhaustively in the same list.
    return [unique[key] for key in sorted(
        unique, key=lambda key: (key[3] < 0, key))]


def _instruction_word_at(
        verifier: "Verifier", index: dict, image: str, pc: int,
        cache: dict[tuple[str, int], str | None],
) -> str | None:
    """Read an external breaker's exact word through the shared C verifier."""
    key = (image, pc)
    if key in cache:
        return cache[key]
    record = next((row for row in index["records"]
                   if row.get("entry") and row["image_id"] == image
                   and _int(row["entry"]) <= pc < _int(row["end"])), None)
    if record is None:
        cache[key] = None
    else:
        query = verifier.ask(
            f"indexdom@{image}:{record['entry']}:{record['end']}:zero:0x{pc:08x}")[0]
        cache[key] = query.get("site_word")
    return cache[key]


def _ps1_ram_alias_ranges(window_lo: int, window_hi: int) -> list[tuple[int, int]]:
    """All CPU-address aliases of a byte window in the 2 MiB PS1 main RAM.

    Main RAM repeats four times across the first 8 MiB of physical space and
    is visible in the direct, KSEG0, and KSEG1 address spellings.  A numeric
    interval that misses 0x8008xxxx can still hit +0x200000/+0x400000 and write
    the same bytes, so virtual non-overlap alone is not proof.
    """
    width = window_hi - window_lo
    if width <= 0:
        raise TypedStateError("watched window must be non-empty")
    offset = window_lo & (PS1_RAM_SIZE - 1)
    if offset + width > PS1_RAM_SIZE:
        raise TypedStateError("watched window crosses a PS1 RAM mirror boundary")
    aliases = []
    for segment in PS1_RAM_SEGMENT_BASES:
        for mirror in range(0, PS1_RAM_MIRROR_SPAN, PS1_RAM_SIZE):
            start = segment + mirror + offset
            aliases.append((start, start + width))
    return aliases


def _ps1_ram_window_exclusion(low: int, high: int,
                              window_lo: int, window_hi: int) -> dict:
    aliases = _ps1_ram_alias_ranges(window_lo, window_hi)
    overlaps = [(a, b) for a, b in aliases if low < b and high > a]
    if overlaps:
        mode = "ps1_ram_alias_overlap"
    elif low >= window_hi:
        mode = "lower_bound_with_all_ps1_ram_aliases_excluded"
    elif high <= window_lo:
        mode = "proved_scaled_max_with_all_ps1_ram_aliases_excluded"
    else:
        # The canonical window itself is one alias, so this can occur only for
        # a non-RAM spelling supplied by a future consumer. Fail closed.
        mode = "canonical_window_overlap"
    return {
        "window": [f"0x{window_lo:08x}", f"0x{window_hi:08x}"],
        "mode": mode,
        "ps1_ram_aliases_checked": [
            [f"0x{a:08x}", f"0x{b:08x}"] for a, b in aliases],
        "overlapping_aliases": [
            [f"0x{a:08x}", f"0x{b:08x}"] for a, b in overlaps],
        "excluded": not overlaps and mode != "canonical_window_overlap",
    }


def _site_location(site: dict, index: dict) -> tuple[str, int, int, str, int]:
    qualified = str(site.get("function") or "")
    if ":" not in qualified or "@" not in qualified:
        raise TypedStateError(f"site {site.get('id')} lacks a qualified function")
    image = qualified.split(":", 1)[0]
    entry = _int(qualified.rsplit("@", 1)[1])
    end, _ = _extent(index, image, entry)
    register = str(site.get("base_register", site.get("base_reg", "")))
    pc = _int(site["pc"])
    return image, entry, end, register, pc


def upgrade_convention_with_index_intervals(
        by_convention: list[dict], windows: list[tuple[int, int]],
        verifier: Verifier, index: dict,
        verdict_by_pc: dict[int, list[tuple[str, str]]],
) -> tuple[list[dict], list[dict], dict]:
    """Replace convention with proof only where indexdom@ subsumes it.

    The base register must reduce, at the exact access PC, to table_address on
    every observable reaching definition.  Each table-address addend is then
    queried at the exact addu PC.  The C derivation already includes any sll
    scaling, so its max is a byte-offset max; an OUT_OF_BOUND upgrade is allowed
    only when TABLE + that proved max + displacement + width stays strictly
    below the window.  No Tier-3 hint or loop convention is reused.
    """
    base_specs: list[str] = []
    locations: list[tuple[str, int, int, str, int]] = []
    for site in by_convention:
        image, entry, end, register, pc = _site_location(site, index)
        locations.append((image, entry, end, register, pc))
        base_specs.append(
            f"{image}:0x{entry:08x}:0x{end:08x}:{register}:0x{pc:08x}")
    base_answers = _ask_batched(verifier, base_specs)

    class_tally: dict[str, int] = {}
    candidates: list[tuple[dict, tuple[str, int, int, str, int], dict,
                           list[dict]]] = []
    failure_rows: list[dict] = []
    for site, location, answer in zip(by_convention, locations, base_answers):
        observable = [row for row in answer["definitions"] if row["observable"]]
        classes = sorted({row["class"] for row in observable})
        label = "+".join(classes) if classes else "no_observable_definition"
        class_tally[label] = class_tally.get(label, 0) + 1
        valid = (not answer["entry_reachable_uses"] and observable
                 and all(_proved_table_address_definition(row)
                         for row in observable))
        if valid:
            candidates.append((site, location, answer, observable))
        else:
            definition_failures = [
                {key: row.get(key) for key in
                 ("pc", "word", "class", "table_address_failure")
                 if row.get(key) is not None}
                for row in observable if row.get("table_address_failure")]
            failure_rows.append({
                "id": site.get("id"),
                "outcome": "not_an_exact_table_address_interval_candidate",
                "base_definition_classes": classes,
                "entry_reachable_uses": answer["entry_reachable_uses"],
                "base_definition_failures": definition_failures,
            })

    # Deduplicate identical index questions. One scaled index often feeds a run
    # of adjacent fields; rerunning the same proof per field would add cost and
    # make the receipt look like more evidence than it is.
    index_specs: dict[str, None] = {}
    for _site, location, _answer, definitions in candidates:
        image, entry, end, _register, _pc = location
        for definition in definitions:
            index_specs[
                f"indexdom@{image}:0x{entry:08x}:0x{end:08x}:"
                f"{definition['index']}:{definition['pc']}"] = None
    spec_list = list(index_specs)
    index_answers = dict(zip(spec_list, _ask_batched(verifier, spec_list)))

    transfer_closure = _indirect_transfer_closure(index)
    external_cache: dict[tuple[str, int, int], list[dict]] = {}
    instruction_word_cache: dict[tuple[str, int], str | None] = {}
    remaining: list[dict] = []
    upgraded: list[dict] = []
    compact_attempts: list[dict] = []
    outcome_tally: dict[str, int] = {}

    def tally(name: str) -> None:
        outcome_tally[name] = outcome_tally.get(name, 0) + 1

    candidate_ids = {site.get("id") for site, *_ in candidates}
    for site in by_convention:
        if site.get("id") not in candidate_ids:
            remaining.append(site)

    for site, location, base_answer, definitions in candidates:
        image, entry, end, register, pc = location
        ext_key = (image, entry, end)
        if ext_key not in external_cache:
            external_cache[ext_key] = _external_interior_entries(
                index, image, entry, end, transfer_closure)
        external = external_cache[ext_key]
        proofs = []
        failed = None
        for definition in definitions:
            spec = (f"indexdom@{image}:0x{entry:08x}:0x{end:08x}:"
                    f"{definition['index']}:{definition['pc']}")
            query = index_answers[spec]
            if not query.get("verdict") and failed is None:
                failed = query.get("breaking_instruction") or {
                    "pc": query.get("site_pc"), "word": query.get("site_word"),
                    "reason": "indexdom rejected without a breaker"}
            proofs.append((definition, query))
        if failed is not None:
            tally("interval_unproved")
            remaining.append(site)
            compact_attempts.append({
                "id": site.get("id"), "outcome": "interval_unproved",
                "breaking_instruction": failed})
            continue

        width = int(site.get("width") or 4)
        displacement = int(site.get("offset", site.get("disp", 0)))
        derivations = []
        address_ok = True
        for definition, query in proofs:
            interval = query["interval"]
            table = _int(definition["table"])
            low = table + int(interval["min"]) + displacement
            high = table + int(interval["max"]) + displacement + width
            no_wrap = 0 <= low <= 0xffffffff and 0 <= high <= 0x100000000
            if not no_wrap:
                address_ok = False
            per_window = []
            for window_lo, window_hi in windows:
                exclusion = (_ps1_ram_window_exclusion(
                    low, high, window_lo, window_hi) if no_wrap else {
                        "window": [f"0x{window_lo:08x}", f"0x{window_hi:08x}"],
                        "mode": "address_wrap_possible",
                        "ps1_ram_aliases_checked": [],
                        "overlapping_aliases": [],
                        "excluded": False,
                    })
                if not exclusion["excluded"]:
                    address_ok = False
                per_window.append(exclusion)
            derivations.append({
                "table_address_definition": {
                    key: definition.get(key) for key in
                    ("pc", "word", "table", "index", "hops",
                     "table_base_register", "table_base_proof")},
                "index_domain_query": query,
                "effective_address_interval": (
                    [f"0x{low:08x}", f"0x{high:08x}"] if no_wrap else None),
                "displacement": displacement,
                "width": width,
                "no_32bit_wrap": no_wrap,
                "window_exclusions": per_window,
            })
        if not address_ok:
            tally("proved_interval_does_not_exclude_every_window")
            remaining.append(site)
            overlaps = sorted({
                tuple(alias)
                for derivation in derivations
                for exclusion in derivation["window_exclusions"]
                for alias in exclusion["overlapping_aliases"]})
            compact_attempts.append({
                "id": site.get("id"),
                "outcome": "proved_interval_does_not_exclude_every_window",
                "failure_modes": sorted({
                    exclusion["mode"]
                    for derivation in derivations
                    for exclusion in derivation["window_exclusions"]
                    if not exclusion["excluded"]}),
                "overlapping_ps1_ram_aliases": [list(row) for row in overlaps],
                "limiting_instruction": {
                    "pc": proofs[0][1]["site_pc"],
                    "word": proofs[0][1]["site_word"]}})
            continue

        if external:
            tally("external_interior_entry")
            remaining.append(site)
            first_external = dict(external[0])
            first_external["word"] = _instruction_word_at(
                verifier, index, str(first_external["image"]),
                _int(first_external["pc"]), instruction_word_cache)
            compact_attempts.append({
                "id": site.get("id"), "outcome": "external_interior_entry",
                "external_entry_count": len(external),
                "first_external_entry": first_external})
            continue

        tally("upgraded_to_proof")
        upgraded_row = {
            **{key: value for key, value in site.items()
               if key not in ("tiers", "region_provenance")},
            "provenance": "instruction_derived_unsigned_index_interval",
            "prior_classification": {
                "bucket": "bounded_by_index_convention",
                "tiers": site.get("tiers"),
                "region_provenance": site.get("region_provenance"),
            },
            "instruction_interval_proof": {
                "base_register": register,
                "base_provenance_definitions": [
                    {key: definition.get(key) for key in
                     ("pc", "word", "class", "table", "index", "hops",
                      "table_base_register", "table_base_proof")}
                    for definition in definitions],
                "every_reaching_definition_whitelisted": True,
                "external_interior_entries": [],
                "derivations": derivations,
                "uses_index_sign_convention": False,
                "uses_loop_bound_convention": False,
                "scaled_offset_note": (
                    "indexdom queries the exact non-constant byte-offset addend "
                    "at TABLE+INDEX; any stride multiplication is the recorded "
                    "overflow-checked sll chain, so an upper exclusion uses the "
                    "proved scaled max rather than the prior Tier-3 hint"),
            },
        }
        upgraded.append(upgraded_row)
        verdict_by_pc[pc] = [
            (row_image, "bounded_by_proof" if row_image == image else verdict)
            for row_image, verdict in verdict_by_pc.get(pc, [])]
        compact_attempts.append({
            "id": site.get("id"), "outcome": "upgraded_to_proof",
            "prior_tiers": site.get("tiers")})

    upgraded_ids = sorted(str(row.get("id")) for row in upgraded)
    return remaining, upgraded, {
        "query": "instruction-derived unsigned interval for table-address indices",
        "query_form": "indexdom@IMAGE:START:END:REG:PC",
        "convention_site_universe": len(by_convention),
        "base_definition_class_tally": dict(sorted(class_tally.items())),
        "base_classification_failure_count": len(failure_rows),
        "base_classification_failures": failure_rows,
        "exact_table_address_candidates": len(candidates),
        "unique_index_queries": len(spec_list),
        "outcomes": dict(sorted(outcome_tally.items())),
        "upgraded_site_count": len(upgraded),
        "upgraded_site_ids": upgraded_ids,
        "attempts_for_exact_table_address_candidates": compact_attempts,
        "external_indirect_transfer_closure": transfer_closure,
        "upper_bound_rule": (
            "OUT_OF_BOUND is upgraded only when the C-proved scaled byte-offset "
            "max plus TABLE, displacement, and width is <= the window start; "
            "all PS1 2 MiB RAM mirrors in direct/KSEG0/KSEG1 spellings must also "
            "be excluded; the prior idx_bound/loop convention is never consumed"),
        "row_status_or_campaign_authority_changed": False,
    }


def second_opinion(still: list[dict], windows: list[tuple[int, int]],
                   verifier: Verifier,
                   verdict_by_pc: dict[int, list[tuple[str, str]]]) -> tuple[list, list, dict]:
    """Ask `region_provenance` about the sites this compiler could not bound.

    A site moves to the convention bucket only if that analyser excludes it from
    EVERY watched window -- missing one window is not missing the state.

    Three things are deliberately NOT swept under the rug:

      * Its scope is the RESIDENT image only. Overlay sites are untouched and are
        counted as out-of-scope, never as bounded.
      * Its Tier-2/Tier-3 exclusions rest on the non-negative, loop-bound-checked
        array-index convention. That is an assumption about how the code was
        written, so these sites are reported apart from this tool's own proofs
        and never folded into them.
      * A HIT is escalated, not filed. If it says one of these sites reaches a
        window, that is a real writer the frontier missed.
    """
    # Every image that carries an unresolved site gets its own run. Overlays all
    # load at the same address, so a verdict is keyed by (image, pc) throughout --
    # keying on pc alone would attribute one overlay's answer to all 20 others.
    images = sorted({str(s.get("function", "")).split(":", 1)[0]
                     for s in still if ":" in str(s.get("function", ""))})
    reports, unavailable = {}, {}
    for image in images:
        for lo, hi in windows:
            width = max(1, hi - lo)
            try:
                reports[(image, lo, width)] = verifier.region_provenance(image, lo, width)
            except TypedStateError as exc:
                unavailable[image] = str(exc)

    verdicts: dict[tuple[str, int], dict] = {}
    for (image, target, width), report in reports.items():
        hits = {_int(p) for p in report["hit_pcs"]}
        excl = {_int(e["pc"]): e for e in report["exclusions"]}
        unres = {_int(u["pc"]) for u in report["unresolved_all"]}
        for site in still:
            if str(site.get("function", "")).split(":", 1)[0] != image:
                continue
            pc = _int(site["pc"])
            slot = verdicts.setdefault((image, pc), {})
            if pc in hits:
                slot[f"0x{target:08x}"] = {"verdict": "HIT"}
            elif pc in excl:
                slot[f"0x{target:08x}"] = {
                    "verdict": excl[pc]["kind"],
                    # `region_base` is a RESIDUE-CLASS REPRESENTATIVE when
                    # verified_anchor is false -- the analyser saw an arithmetic
                    # progression and cannot prove which element starts it. Tier 1
                    # is invariant to that choice; Tiers 2 and 3 are not, and the
                    # analyser suppresses them for unanchored regions itself.
                    "region_base": excl[pc]["region_base"],
                    "verified_anchor": excl[pc]["verified_anchor"],
                    "stride": excl[pc]["stride"],
                    "idx_bound": excl[pc]["idx_bound"]}
            elif pc in unres:
                slot[f"0x{target:08x}"] = {"verdict": "unresolved"}
            else:
                slot[f"0x{target:08x}"] = {"verdict": "out_of_scope"}

    remaining, by_convention, hits_found = [], [], []
    counts: dict[str, int] = {}
    for site in still:
        pc = _int(site["pc"])
        image = str(site.get("function", "")).split(":", 1)[0]
        per_window = verdicts.get((image, pc), {})
        kinds = {v["verdict"] for v in per_window.values()}
        if "HIT" in kinds:
            hits_found.append({**site, "region_provenance": per_window})
            remaining.append({**site, "note": "region_provenance reports this REACHES a window"})
            counts["HIT"] = counts.get("HIT", 0) + 1
            continue
        if image in unavailable:
            remaining.append(site)
            counts["image_unavailable"] = counts.get("image_unavailable", 0) + 1
            continue
        # An UNANCHORED region (verified_anchor false) is one the analyser found as
        # an arithmetic progression without proving which element starts it. Only
        # Tier 1 survives that, because alignment is invariant to anchor choice
        # while Tiers 2 and 3 depend on the SIGN of the index relative to it. The
        # analyser suppresses the stronger tiers itself; this re-checks the
        # invariant on every site rather than trusting that it held -- extending
        # the run to a new class of image is exactly when such a rule silently
        # stops holding.
        for window, verdict in per_window.items():
            if (verdict["verdict"].startswith("EXCLUDED_")
                    and not verdict.get("verified_anchor")
                    and verdict["verdict"] != "EXCLUDED_ALIGNMENT"):
                raise TypedStateError(
                    f"{image} {site.get('pc')} window {window}: "
                    f"{verdict['verdict']} on an UNANCHORED region -- tiers beyond "
                    "alignment depend on the anchor and may not be applied here")
        if kinds and kinds <= {"EXCLUDED_ALIGNMENT", "EXCLUDED_NEGATIVE_INDEX",
                               "EXCLUDED_OUT_OF_BOUND"}:
            by_convention.append({**site, "region_provenance": per_window,
                                  "tiers": sorted(kinds)})
            for kind in kinds:
                counts[kind] = counts.get(kind, 0) + 1
            verdict_by_pc[pc] = [(i, "bounded_by_index_convention" if i == image else v)
                                 for i, v in verdict_by_pc.get(pc, [])]
            continue
        remaining.append(site)
        for kind in kinds or {"out_of_scope"}:
            counts[kind] = counts.get(kind, 0) + 1

    return remaining, by_convention, {
        "tool": REGION_PROVENANCE_SRC,
        "source_sha256": verifier._rp_source_sha,
        "binary_sha256": verifier._rp_binary_sha,
        "regenerated_here": True,
        "inputs": {"exe": RESIDENT_EXE, "functions": RESIDENT_FUNCS,
                   "exe_sha256": _sha((ROOT / RESIDENT_EXE).read_bytes()),
                   "functions_sha256": _sha((ROOT / RESIDENT_FUNCS).read_bytes())},
        "scope": ("every image carrying an unresolved site, resident and overlay. "
                  "An overlay run sees only that overlay, so its calls into the "
                  "resident executable stay unresolved and its functions get no "
                  "argument seeding from resident callers -- weaker than the "
                  "resident run, never less sound, because an unseeded register is "
                  "TOP and TOP yields no region and therefore no exclusion."),
        "images_analysed": sorted({image for image, _, _ in reports}),
        "images_unavailable": unavailable,
        "soundness": ("EXCLUDED_NEGATIVE_INDEX and EXCLUDED_OUT_OF_BOUND rely on the "
                      "non-negative, loop-bound-checked array-index convention -- an "
                      "assumption about how the code was written, not a fact the "
                      "instructions state. Kept out of bounded_by_proof for that reason. "
                      "EXCLUDED_ALIGNMENT is unconditional given the disassembled base "
                      "shape and is invariant to anchor choice, which is why it is the "
                      "only tier permitted on an unanchored region -- re-checked here "
                      "per site, fail-closed."),
        "unanchored_regions_restricted_to_alignment": True,
        "windows_queried": sorted({f"0x{t:08x}/{w}" for _, t, w in reports}),
        "site_verdicts": counts,
        "sites_reported_as_reaching_a_window": hits_found,
    }


def join_acceptance_fixture(spec: dict,
                           verdict_by_pc: dict[int, list[tuple[str, str]]]) -> dict:
    """Report the compiler against an INDEPENDENT fixture it did not choose.

    The fixture is the resolver's own unresolved STORE sites -- the sites that
    actually blocked F01. It is a different analysis over a different universe,
    so a fixture site can legitimately be absent from the frontier's blocker
    ledger (the frontier resolved a base the resolver could not). Every such site
    is listed in full: a fixture that quietly shrinks would make coverage look
    better than it is, which is the exact failure this join exists to prevent.

    The two analyses name the main executable differently ("SCUS" vs
    "SCUS_942_88") but agree on overlays, so the join is by pc with a
    prefix-compatible image required -- an image disagreement is reported, never
    resolved in the compiler's favour.
    """
    path = ROOT / spec["path"]
    if not path.is_file():
        raise TypedStateError(f"acceptance fixture missing: {spec['path']}")
    raw = path.read_bytes()
    doc = json.loads(raw)
    rows = [s for s in doc.get(spec["collection"]) or [] if s.get(spec["predicate"])]

    bases = [
        (f"fixture:{str(row.get('image') or '')}:"
         f"0x{_int(row['pc']):08x}:{str(row.get('function') or '')}")
        for row in rows]
    base_counts = {base: bases.count(base) for base in set(bases)}
    base_seen: dict[str, int] = {}
    fixture_ids: list[str] = []
    for base in bases:
        base_seen[base] = base_seen.get(base, 0) + 1
        fixture_ids.append(
            base if base_counts[base] == 1
            else f"{base}:occurrence-{base_seen[base]}")

    tally: dict[str, int] = {}
    verdict_site_ids: dict[str, list[str]] = {}
    absent, ambiguous = [], []
    for row, fixture_id in zip(rows, fixture_ids):
        pc = _int(row["pc"])
        f_image = str(row.get("image") or "")
        seen_here = verdict_by_pc.get(pc, [])
        # Prefer an EXACT image match. Prefix compatibility exists only to bridge
        # "SCUS" vs "SCUS_942_88", but it also makes LEVEL02_LEVEL match
        # LEVEL02_LEVEL1 -- two different overlays that share load addresses. When
        # the fixture names an image exactly, that is the answer, not a candidate.
        candidates = [(img, verdict) for img, verdict in seen_here if img == f_image]
        if not candidates:
            candidates = [(img, verdict) for img, verdict in seen_here
                          if img.startswith(f_image) or f_image.startswith(img)]
        if not candidates:
            absent.append({"id": fixture_id, "pc": f"0x{pc:08x}", "image": f_image,
                           "function": row.get("function"),
                           "seen_in_ledger_as": sorted({img for img, _ in
                                                        verdict_by_pc.get(pc, [])})})
            verdict_site_ids.setdefault("absent_from_ledger", []).append(fixture_id)
            continue
        verdicts = {verdict for _, verdict in candidates}
        if len(verdicts) > 1:
            ambiguous.append({"id": fixture_id, "pc": f"0x{pc:08x}",
                              "fixture_image": f_image,
                              "candidates": sorted(candidates)})
            verdict_site_ids.setdefault("ambiguous_join", []).append(fixture_id)
            continue
        verdict = verdicts.pop()
        tally[verdict] = tally.get(verdict, 0) + 1
        verdict_site_ids.setdefault(verdict, []).append(fixture_id)

    return {
        "path": spec["path"],
        "sha256": _sha(raw),
        "selector": f"{spec['collection']}[{spec['predicate']}]",
        "join_basis": "pc, requiring prefix-compatible image ids",
        "sites": len(rows),
        "distinct_pcs": len({_int(r["pc"]) for r in rows}),
        "joined_to_ledger": sum(tally.values()),
        "verdicts": tally,
        "fixture_site_ids": sorted(fixture_ids),
        "verdict_site_ids": {
            verdict: sorted(site_ids)
            for verdict, site_ids in sorted(verdict_site_ids.items())},
        "absent_from_ledger_count": len(absent),
        "absent_from_ledger": absent,
        "ambiguous_join": ambiguous,
        "note": ("absent_from_ledger sites are NOT covered by this compiler and "
                 "are not counted as bounded; they remain the resolver's blockers."),
    }


def _bucket_site_sets(result: dict) -> dict[str, set[str]]:
    """Return the exact ledger row-id set for every compiler bucket."""
    buckets = ("bounded_by_proof", "bounded_by_assertion_only",
               "bounded_by_index_convention", "still_unresolved")
    answer: dict[str, set[str]] = {}
    owner: dict[str, str] = {}
    for bucket in buckets:
        values: set[str] = set()
        for row in result.get(bucket) or []:
            site_id = str(row.get("id") or "")
            if not site_id:
                raise TypedStateError(f"{bucket} contains a row without an id")
            if site_id in owner:
                raise TypedStateError(
                    f"ledger row id {site_id} occurs in both {owner[site_id]} and {bucket}")
            owner[site_id] = bucket
            values.add(site_id)
        answer[bucket] = values
    return answer


def _movement(before: dict[str, set[str]], after: dict[str, set[str]]) -> dict:
    """Exact gained/lost sets for a stable universe, in both directions."""
    before_universe = set().union(*before.values())
    after_universe = set().union(*after.values())
    return {
        "baseline_universe_count": len(before_universe),
        "current_universe_count": len(after_universe),
        "baseline_only_ids": sorted(before_universe - after_universe),
        "current_only_ids": sorted(after_universe - before_universe),
        "categories": {
            category: {
                "baseline_count": len(before.get(category, set())),
                "current_count": len(after.get(category, set())),
                "gained_ids": sorted(after.get(category, set())
                                     - before.get(category, set())),
                "lost_ids": sorted(before.get(category, set())
                                   - after.get(category, set())),
            }
            for category in sorted(set(before) | set(after))
        },
    }


def _verdict_map_from_result(result: dict) -> dict[int, list[tuple[str, str]]]:
    """Reconstruct the fixture join map from a retained compiler result."""
    answer: dict[int, list[tuple[str, str]]] = {}
    for bucket in ("bounded_by_proof", "bounded_by_assertion_only",
                   "bounded_by_index_convention", "still_unresolved"):
        for row in result.get(bucket) or []:
            qualified = str(row.get("function") or "")
            if ":" not in qualified:
                continue
            image = qualified.split(":", 1)[0]
            answer.setdefault(_int(row["pc"]), []).append((image, bucket))
    return answer


def add_index_interval_movement(result: dict, fixture_spec: dict) -> None:
    """Pin exact ledger and fixture movements to the prerequisite commit."""
    command = ["git", "show", (f"{INDEX_INTERVAL_BASELINE_COMMIT}:"
                                f"{INDEX_INTERVAL_BASELINE_ARTIFACT}")]
    proc = subprocess.run(command, cwd=ROOT, check=False, capture_output=True)
    if proc.returncode:
        raise TypedStateError(
            "cannot read typed-state baseline from prerequisite commit: "
            + proc.stderr.decode("utf-8", errors="replace").strip())
    baseline_raw = proc.stdout
    baseline = json.loads(baseline_raw)
    baseline_fixture = join_acceptance_fixture(
        fixture_spec, _verdict_map_from_result(baseline))
    current_fixture = result["acceptance_fixture"]
    fixture_before = {
        key: set(values)
        for key, values in baseline_fixture["verdict_site_ids"].items()}
    fixture_after = {
        key: set(values)
        for key, values in current_fixture["verdict_site_ids"].items()}
    result["movement_from_b6cb61d35f9d"] = {
        "baseline_commit": INDEX_INTERVAL_BASELINE_COMMIT,
        "baseline_artifact": INDEX_INTERVAL_BASELINE_ARTIFACT,
        "baseline_artifact_sha256": _sha(baseline_raw),
        "comparison": (
            "exact stable row-id sets in both directions; no count is inferred "
            "from a sample"),
        "ledger": _movement(_bucket_site_sets(baseline),
                            _bucket_site_sets(result)),
        "acceptance_fixture": _movement(fixture_before, fixture_after),
    }

    ratchet_object = (f"{INDEXDOM_RA_RATCHET_COMMIT}:"
                      f"{INDEX_INTERVAL_BASELINE_ARTIFACT}")
    ratchet_proc = subprocess.run(
        ["git", "show", ratchet_object], cwd=ROOT, check=False,
        capture_output=True)
    if ratchet_proc.returncode:
        raise TypedStateError(
            "cannot read pre-ra-ratchet typed-state artifact: "
            + ratchet_proc.stderr.decode("utf-8", errors="replace").strip())
    ratchet_raw = ratchet_proc.stdout
    ratchet = json.loads(ratchet_raw)

    def outcome_sets(document: dict) -> dict[str, set[str]]:
        rows = document["second_opinion"]["instruction_interval_upgrade"][
            "attempts_for_exact_table_address_candidates"]
        answer: dict[str, set[str]] = {}
        for row in rows:
            answer.setdefault(str(row["outcome"]), set()).add(str(row["id"]))
        if sum(map(len, answer.values())) != len(rows):
            raise TypedStateError("interval diagnostic row ids are not unique")
        return answer

    result["diagnostic_outcome_movement_from_05bc6b8a251b"] = {
        "baseline_commit": INDEXDOM_RA_RATCHET_COMMIT,
        "baseline_artifact": INDEX_INTERVAL_BASELINE_ARTIFACT,
        "baseline_artifact_sha256": _sha(ratchet_raw),
        "meaning": (
            "exact diagnostic-stage row-id movement caused by rejecting a "
            "locally-defined-ra indirect target; this does not change any "
            "typed-state verdict category"),
        **_movement(outcome_sets(ratchet), outcome_sets(result)),
    }


def compile_typed_state(doc: dict, schema_sha: str, verifier: Verifier) -> dict:
    ledger_rel = doc["ledger"]
    ledger_path = ROOT / ledger_rel
    if not ledger_path.is_file():
        raise TypedStateError(f"blocker ledger missing: {ledger_rel}")
    ledger_raw = ledger_path.read_bytes()
    ledger = json.loads(ledger_raw)
    index = json.loads(INDEX_PATH.read_bytes())

    windows = [(_int(w["start"]), _int(w["end"])) for w in doc["windows"]]
    regions = {r["id"]: (_int(r["start"]), _int(r["end"])) for r in doc["regions"]}

    # ---- bindings, each checked rather than believed -----------------------
    accepted: dict[tuple[str, int, str], dict] = {}
    binding_report = []
    for binding in doc["region_bindings"]:
        if binding["region"] not in regions:
            raise TypedStateError(f"binding names unknown region {binding['region']}")
        kind = binding["provenance"]
        if kind == "caller_argument":
            ok, why, attest = verify_caller_argument(binding, index, ledger,
                                                     verifier, regions)
            binding = {**binding, "attestation": attest}
        elif kind == "typed_pointer_load":
            ok, why, attest = verify_typed_pointer_load(binding, index, ledger,
                                                       verifier, regions)
            binding = {**binding, "attestation": attest}
        elif kind == "proved_jr_cluster_argument":
            ok, why, attest = verify_proved_jr_cluster_argument(binding, index,
                                                                ledger, verifier,
                                                                regions)
            binding = {**binding, "attestation": attest}
        else:                       # external_owner
            ok, why = True, "ASSERTED by a named owner; not proof"
        binding_report.append({**binding, "accepted": ok, "verdict": why})
        if ok:
            # Keyed by (image, function entry, register). Keying by image alone
            # would let an `s1` binding proved for ONE function silently bound
            # every `s1` site in that image -- a different register in a
            # different frame.
            accepted[(binding["image"], _int(binding["function"]), binding["register"])] = {
                "region": binding["region"], "provenance": kind}

    # ---- bound the unresolved sites ---------------------------------------
    STORE_MNEMONICS = {"sb", "sh", "sw", "swl", "swr"}

    def normalise(site: dict) -> tuple[str, int | None, str, int, int, bool]:
        """The ledger's rows carry a qualified id: IMAGE:name@0xENTRY."""
        fn = str(site.get("function", ""))
        image = fn.split(":", 1)[0] if ":" in fn else ""
        entry = None
        if "@" in fn:
            try:
                entry = _int(fn.rsplit("@", 1)[1])
            except ValueError:
                entry = None
        reg = str(site.get("base_register", site.get("base_reg", "")))
        disp = int(site.get("offset", site.get("disp", 0)))
        width = int(site.get("width", 4))
        is_store = bool(site.get("store")) or \
            str(site.get("mnemonic", "")).lower() in STORE_MNEMONICS
        return image, entry, reg, disp, width, is_store

    sites = ledger.get("unresolved_accesses") or []
    bounded_proof, bounded_asserted, still = [], [], []
    # pc -> [(image, verdict)]. A LIST, not a single value: overlay images share
    # the same load addresses, so 0x800B39A8 exists in all 21 of them. Collapsing
    # to one entry silently attributes one overlay's verdict to every other.
    verdict_by_pc: dict[int, list[tuple[str, str]]] = {}
    for raw_site in sites:
        image, entry, reg, disp, width, is_store = normalise(raw_site)
        site = {**raw_site, "store": is_store}
        try:
            pc = _int(raw_site["pc"])
        except (KeyError, ValueError):
            pc = None
        binding = accepted.get((image, entry, reg)) if entry is not None else None
        if binding is None:
            still.append(site)
            if pc is not None:
                verdict_by_pc.setdefault(pc, []).append((image, "still_unresolved"))
            continue
        low, high = regions[binding["region"]]
        lo, hi = low + disp, high + disp + width
        if any(lo < w_hi and hi > w_lo for w_lo, w_hi in windows):
            still.append({**site, "note": "region+displacement can still overlap a window"})
            if pc is not None:
                verdict_by_pc.setdefault(pc, []).append((image, "still_unresolved"))
            continue
        row = {**site, "region": binding["region"], "provenance": binding["provenance"],
               "bound": [f"0x{lo:08x}", f"0x{hi:08x}"]}
        proven = binding["provenance"] != "external_owner"
        (bounded_proof if proven else bounded_asserted).append(row)
        if pc is not None:
            verdict_by_pc.setdefault(pc, []).append(
                (image, "bounded_by_proof" if proven else "bounded_by_assertion_only"))

    # ---- second opinion from the independent region analyser -----------------
    still, by_convention, corroboration = second_opinion(still, windows, verifier,
                                                         verdict_by_pc)
    by_convention, interval_proof, interval_receipt = \
        upgrade_convention_with_index_intervals(
            by_convention, windows, verifier, index, verdict_by_pc)
    bounded_proof.extend(interval_proof)
    corroboration["instruction_interval_upgrade"] = interval_receipt

    store = lambda rows: sum(1 for r in rows if r.get("store"))
    fixture = join_acceptance_fixture(doc["acceptance_fixture"], verdict_by_pc)
    result = {
        "schema": RESULT_ID,
        "row_id": doc["row_id"],
        "inputs": {"schema_sha256": schema_sha,
                   "ledger": ledger_rel, "ledger_sha256": _sha(ledger_raw),
                   "static_index_sha256": _sha(INDEX_PATH.read_bytes()),
                   "verifier_source": VERIFIER_SRC,
                   "verifier_source_sha256": verifier.source_sha,
                   "verifier_binary_sha256": verifier.binary_sha,
                   "verifier_image_map_sha256": verifier.image_map_sha,
                   "verifier_images": verifier.image_count},
        "bindings": binding_report,
        "acceptance_fixture": fixture,
        "second_opinion": corroboration,
        "counts": {
            "unresolved_sites_in_ledger": len(sites),
            "unresolved_stores_in_ledger": sum(
                1 for s in sites if normalise(s)[5]),
            "bounded_by_proof": len(bounded_proof),
            "bounded_stores_by_proof": store(bounded_proof),
            "bounded_by_assertion_only": len(bounded_asserted),
            "bounded_stores_by_assertion_only": store(bounded_asserted),
            "bounded_by_index_convention": len(by_convention),
            "bounded_stores_by_index_convention": store(by_convention),
            "still_unresolved": len(still),
            "still_unresolved_stores": store(still),
        },
        "bounded_by_proof": bounded_proof,
        "bounded_by_assertion_only": bounded_asserted,
        "bounded_by_index_convention": by_convention,
        "still_unresolved": still,
        "indirect_control_flow_blockers_untouched": {
            "indirect_jumps": len(ledger.get("indirect_jumps") or []),
            "direct_jumps_out": len(ledger.get("direct_jumps_out") or []),
            "unanalysed_extents": len(ledger.get("unanalysed_extents") or []),
            "note": ("carried through unchanged. Typing a base says nothing about "
                     "where control flow can go."),
        },
        "authority": AUTHORITY,
    }
    add_index_interval_movement(result, doc["acceptance_fixture"])
    return result


def survey_abi(doc: dict, index: dict, ledger: dict, verifier: Verifier,
               compiled: dict) -> dict:
    """Why can the ABI check not type each blocked group? A regenerable answer.

    Written because the honest result of the ABI accelerator on F01 is a NEGATIVE
    one, and a negative result stated in prose rots. This runs the same check
    over every (image, function, base register) group that carries a blocking
    store and buckets the verdicts, so "argument typing does not apply here" is a
    number anyone can reproduce rather than a claim to take on trust.
    """
    regions = {r["id"]: (_int(r["start"]), _int(r["end"])) for r in doc["regions"]}
    # The widest possible region: this survey asks whether a value can be
    # RECOVERED at all, not whether it lands in any particular place.
    probe_regions = dict(regions, __probe__=(0, 0xFFFFFFFF))

    fixture = json.loads((ROOT / doc["acceptance_fixture"]["path"]).read_bytes())
    blocking = {(str(s.get("image")), _int(s["pc"]))
                for s in fixture[doc["acceptance_fixture"]["collection"]] or []
                if s.get(doc["acceptance_fixture"]["predicate"])}
    blocking_images = {pc: {img for img, q in blocking if q == pc}
                       for _, pc in blocking}

    def is_blocking(image: str, pc: int) -> bool:
        """Exact image first. `LEVEL02_LEVEL` is a real image id that merely
        happens to prefix `LEVEL02_LEVEL1`, so prefix matching alone counts one
        overlay's site against the other."""
        names = blocking_images.get(pc)
        if not names:
            return False
        if image in names:
            return True
        return any(image.startswith(n) or n.startswith(image) for n in names)

    groups: dict[tuple[str, int, str], list[int]] = {}
    for site in ledger.get("unresolved_accesses") or []:
        qualified = str(site.get("function", ""))
        if ":" not in qualified or "@" not in qualified:
            continue
        image = qualified.split(":", 1)[0]
        try:
            entry = _int(qualified.rsplit("@", 1)[1])
        except ValueError:
            continue
        groups.setdefault((image, entry, str(site.get("base_register"))), []).append(
            _int(site["pc"]))

    # Sites already decided by another provenance are not an ABI shortfall. This
    # is keyed per SITE, not per group: bounding happens site by site, and a group
    # where one store was bounded and nine were not is nine stores of residual,
    # not zero. Marking the whole group decided would understate the residual by
    # exactly the amount that matters.
    decided: dict[tuple[str, int], str] = {}
    for bucket, label in (("bounded_by_proof", "proof"),
                          ("bounded_by_index_convention", "index_convention"),
                          ("bounded_by_assertion_only", "assertion")):
        for row in compiled.get(bucket) or []:
            qualified = str(row.get("function", ""))
            if ":" not in qualified:
                continue
            try:
                decided[(qualified.split(":", 1)[0], _int(row["pc"]))] = label
            except (KeyError, ValueError):
                continue

    rows, buckets, bucket_stores = [], {}, {}
    for (image, entry, register), pcs in sorted(groups.items()):
        blocking_pcs = [pc for pc in pcs if is_blocking(image, pc)]
        n = len(blocking_pcs)
        if not n:
            continue
        settled = [pc for pc in blocking_pcs if (image, pc) in decided]
        open_pcs = [pc for pc in blocking_pcs if (image, pc) not in decided]
        binding = {"image": image, "function": f"0x{entry:08x}", "register": register,
                   "region": "__probe__", "provenance": "caller_argument",
                   "detail": "survey", "pointer_table": None}
        try:
            ok, why, attest = verify_caller_argument(binding, index, ledger,
                                                     verifier, probe_regions)
        except TypedStateError as exc:
            ok, why, attest = False, f"error: {exc}", None
        kind = ("typed" if ok else
                "not_argument_derived" if "neither the incoming argument" in why else
                "no_direct_caller" if "no direct caller" in why else
                "caller_value_not_recoverable" if "does not materialise" in why else
                "callers_disagree" if "different values" in why else
                "no_ledger_site" if "no unresolved site" in why else "other")
        buckets[kind] = buckets.get(kind, 0) + 1
        bucket_stores[kind] = bucket_stores.get(kind, 0) + len(open_pcs)
        rows.append({"image": image, "function": f"0x{entry:08x}", "register": register,
                     "blocking_stores": n,
                     "blocking_stores_already_bounded": len(settled),
                     "blocking_stores_still_open": len(open_pcs),
                     "typed": ok, "verdict_kind": kind, "verdict": why,
                     "already_bounded_by": sorted({decided[(image, pc)]
                                                   for pc in settled}) or None,
                     "argument_value": (attest or {}).get("agreed_value")})

    return {
        "question": ("For each group of blocked stores, can argument typing decide "
                     "the base register?"),
        "method": ("the same verify_caller_argument the compiler uses, against the "
                   "widest possible region, so a group fails only when the VALUE "
                   "cannot be recovered -- never merely because it lands elsewhere"),
        "denominator_note": ("counted over LEDGER groups, so a pc present in two "
                             "images contributes to both; the acceptance_fixture "
                             "join in the main result counts fixture rows once. The "
                             "two totals differ slightly for that reason and agree "
                             "on how many are DECIDED."),
        "groups": len(rows),
        "blocking_stores_covered": sum(r["blocking_stores"] for r in rows),
        "blocking_stores_already_bounded": sum(r["blocking_stores_already_bounded"]
                                               for r in rows),
        "blocking_stores_still_open": sum(r["blocking_stores_still_open"] for r in rows),
        "verdict_groups": buckets,
        "verdict_blocking_stores": bucket_stores,
        "rows": sorted(rows, key=lambda r: -r["blocking_stores_still_open"]),
    }


def render(result: dict) -> bytes:
    return (json.dumps(result, indent=1, sort_keys=True) + "\n").encode()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("schema", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--survey", type=Path,
                    help="also write the ABI argument-typing survey here")
    args = ap.parse_args()
    if ROOT not in args.output.resolve().parents:
        raise TypedStateError("output must stay inside the repository")
    doc, schema_sha = load_schema(args.schema)
    index = json.loads(INDEX_PATH.read_bytes())
    verifier = Verifier(index)
    fresh = render(compile_typed_state(doc, schema_sha, verifier))
    if args.survey is not None:
        if ROOT not in args.survey.resolve().parents:
            raise TypedStateError("survey output must stay inside the repository")
        ledger = json.loads((ROOT / doc["ledger"]).read_bytes())
        report = survey_abi(doc, index, ledger, verifier, json.loads(fresh))
        rendered = render(report)
        if args.check:
            if not args.survey.is_file() or args.survey.read_bytes() != rendered:
                raise TypedStateError(f"retained survey is stale: {args.survey}")
        else:
            args.survey.write_bytes(rendered)
            print(f"[phase4-typed-state] wrote {args.survey}")
            for kind, n in sorted(report["verdict_groups"].items(),
                                  key=lambda kv: -report["verdict_blocking_stores"][kv[0]]):
                print(f"    {kind}: {n} groups / "
                      f"{report['verdict_blocking_stores'][kind]} still-open stores")
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != fresh:
            raise TypedStateError(f"retained output is stale: {args.output}")
        print("[phase4-typed-state] retained output is fresh")
        return 0
    args.output.write_bytes(fresh)
    counts = json.loads(fresh)["counts"]
    print(f"[phase4-typed-state] wrote {args.output}")
    print(f"  ledger: {counts['unresolved_sites_in_ledger']} unresolved "
          f"({counts['unresolved_stores_in_ledger']} stores)")
    print(f"  bounded by PROOF: {counts['bounded_by_proof']} "
          f"({counts['bounded_stores_by_proof']} stores)")
    print(f"  bounded by assertion only: {counts['bounded_by_assertion_only']} "
          f"({counts['bounded_stores_by_assertion_only']} stores)")
    print(f"  bounded by index CONVENTION (2nd opinion): "
          f"{counts['bounded_by_index_convention']} "
          f"({counts['bounded_stores_by_index_convention']} stores)")
    print(f"  still unresolved: {counts['still_unresolved']} "
          f"({counts['still_unresolved_stores']} stores)")
    so = json.loads(fresh)["second_opinion"]
    if so["sites_reported_as_reaching_a_window"]:
        print(f"  ** {len(so['sites_reported_as_reaching_a_window'])} SITE(S) REPORTED AS "
              f"REACHING A WINDOW -- real writers, investigate **")
    fx = json.loads(fresh)["acceptance_fixture"]
    print(f"  ACCEPTANCE FIXTURE {fx['selector']}: {fx['sites']} sites, "
          f"{fx['joined_to_ledger']} joined, "
          f"{fx['absent_from_ledger_count']} absent from the ledger")
    for verdict, n in sorted(fx["verdicts"].items()):
        print(f"    {verdict}: {n}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except TypedStateError as exc:
        raise SystemExit(f"[phase4-typed-state] ERROR: {exc}") from exc
