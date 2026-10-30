#!/usr/bin/env python3
"""Run bounded pure/RAM-local MIPS32LE routines under a fail-closed Unicorn oracle."""
from __future__ import annotations

import argparse
from itertools import product
import hashlib
import json
from pathlib import Path
import struct
import sys
from typing import Any, Callable

import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "config/phase4_mips_oracle.yaml"
PILOT_PATH = ROOT / "analysis/phase4_mips_oracle_pilot.json"
SPEC_SCHEMA = "abl-phase4-mips-oracle-spec/1"
REPORT_SCHEMA = "abl-phase4-mips-oracle-report/1"
MASK32 = 0xFFFFFFFF
PAGE = 0x1000
PS1_RAM_START = 0x80000000
PS1_RAM_END = 0x80200000
MMIO_START = 0x1F801000
MMIO_END = 0x1F803000


class OracleError(RuntimeError):
    """Invalid spec, unsupported domain, or emulation contract failure."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, indent=1, sort_keys=True) + "\n").encode()


def u32(value: int) -> int:
    return value & MASK32


def s32(value: int) -> int:
    value &= MASK32
    return value - (1 << 32) if value & 0x80000000 else value


def _int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise OracleError(f"{field} must be an integer")
    if not 0 <= value <= MASK32:
        raise OracleError(f"{field} is outside unsigned 32-bit range")
    return value


def load_spec(path: Path = SPEC_PATH) -> dict[str, Any]:
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise OracleError(f"cannot load MIPS oracle spec {path}: {exc}") from exc
    if not isinstance(doc, dict) or doc.get("schema") != SPEC_SCHEMA:
        raise OracleError(f"MIPS oracle spec must use {SPEC_SCHEMA}")
    return doc


def validate_static_words(words: list[int]) -> list[str]:
    errors: list[str] = []
    for index, raw in enumerate(words):
        word = _int(raw, f"code_words[{index}]")
        opcode = word >> 26
        function = word & 0x3F
        if opcode == 0x10:
            errors.append(f"word {index}: COP0 is outside the oracle contract")
        if opcode == 0x12:
            errors.append(f"word {index}: COP2/GTE is outside the oracle contract")
        if opcode == 0x2F:
            errors.append(f"word {index}: CACHE is outside the oracle contract")
        if opcode == 0 and function in {0x0C, 0x0D}:
            errors.append(f"word {index}: syscall/break is outside the oracle contract")
    return errors


def validate_spec(doc: dict[str, Any]) -> list[dict[str, Any]]:
    engine = doc.get("engine") or {}
    if engine != {"name": "Unicorn", "version": "2.1.4",
                  "architecture": "MIPS32", "endianness": "little"}:
        raise OracleError("engine identity must be pinned to Unicorn 2.1.4 MIPS32LE")
    policy = doc.get("policy")
    if not isinstance(policy, dict):
        raise OracleError("MIPS oracle policy is missing")
    for key in ("code_base", "return_sentinel", "stack_base", "stack_size",
                "max_cases", "max_instructions"):
        _int(policy.get(key), f"policy.{key}")
    if set(policy.get("allowed_classes") or []) != {"pure", "ram_local"}:
        raise OracleError("only pure and ram_local routine classes may be allowed")
    required_rejections = {"MMIO", "DMA", "GTE", "COP0", "CD", "GPU", "SPU",
                           "interrupts", "self_modifying_code", "timing_sensitive"}
    if set(policy.get("rejected_domains") or []) != required_rejections:
        raise OracleError("device/timing rejection set is incomplete")
    pilots = doc.get("pilots")
    if not isinstance(pilots, list) or not pilots:
        raise OracleError("MIPS oracle spec needs at least one routine")
    seen: set[str] = set()
    result = []
    for raw in pilots:
        if not isinstance(raw, dict) or not isinstance(raw.get("id"), str) or \
                not raw["id"] or raw["id"] in seen:
            raise OracleError("routine IDs must be non-empty and unique")
        seen.add(raw["id"])
        if raw.get("class") not in set(policy["allowed_classes"]):
            raise OracleError(f"{raw['id']}: routine class is forbidden")
        words = raw.get("code_words")
        if not isinstance(words, list) or not words:
            raise OracleError(f"{raw['id']}: code_words is empty")
        static_errors = validate_static_words(words)
        if static_errors:
            raise OracleError(f"{raw['id']}: " + "; ".join(static_errors))
        code_bytes = len(words) * 4
        if code_bytes > 0x10000 or policy["code_base"] + code_bytes > policy["return_sentinel"]:
            raise OracleError(f"{raw['id']}: code extent is outside the bounded code window")
        routine_limit = raw.get("max_instructions", policy["max_instructions"])
        _int(routine_limit, f"{raw['id']}.max_instructions")
        if routine_limit == 0 or routine_limit > policy["max_instructions"]:
            raise OracleError(f"{raw['id']}: max_instructions exceeds policy")
        allowed_memory = raw.get("allowed_memory") or []
        memory_init = raw.get("memory_init") or []
        if raw["class"] == "pure" and (allowed_memory or memory_init):
            raise OracleError(f"{raw['id']}: pure routines may not declare data memory")
        if raw["class"] == "ram_local" and not allowed_memory:
            raise OracleError(f"{raw['id']}: ram_local routines need allowed_memory")
        domains = raw.get("input_domains")
        if not isinstance(domains, dict) or not domains:
            raise OracleError(f"{raw['id']}: input_domains is empty")
        total = 1
        for register, values in domains.items():
            if register not in {"a0", "a1", "a2", "a3"} or not isinstance(values, list) or not values:
                raise OracleError(f"{raw['id']}: invalid domain for {register}")
            for value in values:
                _int(value, f"{raw['id']}.{register}")
            total *= len(values)
        if total > policy["max_cases"]:
            raise OracleError(f"{raw['id']}: generated case count exceeds max_cases")
        observe = raw.get("observe") or {}
        if observe.get("type") != "register" or observe.get("name") not in {"v0", "v1"}:
            raise OracleError(f"{raw['id']}: only v0/v1 register observations are supported")
        evaluate_model(raw.get("model"), {name: values[0] for name, values in domains.items()})
        result.append(raw)
    return result


def evaluate_model(node: Any, registers: dict[str, int]) -> int:
    if not isinstance(node, dict):
        raise OracleError("model nodes must be mappings")
    if set(node) == {"reg"}:
        name = node["reg"]
        if name not in registers:
            raise OracleError(f"model references unknown input register {name!r}")
        return u32(registers[name])
    if set(node) == {"const"}:
        return _int(node["const"], "model.const")
    op = node.get("op")
    args = node.get("args")
    if op not in {"and", "or", "xor", "add32", "sub32", "shl32", "lshr",
                  "ashr", "slt_signed", "slt_unsigned", "eq", "select"} or \
            not isinstance(args, list):
        raise OracleError(f"unsupported model operation {op!r}")
    values = [evaluate_model(arg, registers) for arg in args]
    arity = 3 if op == "select" else 2
    if len(values) != arity:
        raise OracleError(f"model operation {op} needs {arity} arguments")
    if op == "and":
        return values[0] & values[1]
    if op == "or":
        return values[0] | values[1]
    if op == "xor":
        return values[0] ^ values[1]
    if op == "add32":
        return u32(values[0] + values[1])
    if op == "sub32":
        return u32(values[0] - values[1])
    if op == "shl32":
        return u32(values[0] << (values[1] & 31))
    if op == "lshr":
        return values[0] >> (values[1] & 31)
    if op == "ashr":
        return u32(s32(values[0]) >> (values[1] & 31))
    if op == "slt_signed":
        return int(s32(values[0]) < s32(values[1]))
    if op == "slt_unsigned":
        return int(values[0] < values[1])
    if op == "eq":
        return int(values[0] == values[1])
    return values[1] if values[0] else values[2]


def generated_cases(domains: dict[str, list[int]]) -> list[dict[str, int]]:
    names = sorted(domains)
    return [dict(zip(names, values)) for values in product(*(domains[name] for name in names))]


def _page_start(value: int) -> int:
    return value & ~(PAGE - 1)


def _page_stop(value: int) -> int:
    return (value + PAGE - 1) & ~(PAGE - 1)


def ps1_physical(value: int) -> int:
    """Normalize KSEG0/KSEG1 PS1 RAM addresses to Unicorn's physical map."""
    return value & 0x1FFFFFFF if value >= 0x80000000 else value


def import_unicorn() -> tuple[Any, Any]:
    try:
        import unicorn
        import unicorn.mips_const as mips
    except ImportError as exc:
        raise OracleError(
            "Unicorn is missing; install the pinned tools/requirements.txt environment") from exc
    if unicorn.__version__ != "2.1.4":
        raise OracleError(f"Unicorn version drift: expected 2.1.4, got {unicorn.__version__}")
    return unicorn, mips


def execute_case(routine: dict[str, Any], inputs: dict[str, int],
                 policy: dict[str, Any]) -> dict[str, Any]:
    unicorn, mips = import_unicorn()
    code_base = policy["code_base"]
    return_sentinel = policy["return_sentinel"]
    stack_base = policy["stack_base"]
    stack_size = policy["stack_size"]
    code_phys = ps1_physical(code_base)
    return_phys = ps1_physical(return_sentinel)
    stack_phys = ps1_physical(stack_base)
    code = b"".join(struct.pack("<I", word) for word in routine["code_words"])
    code_start = _page_start(code_phys)
    code_stop = _page_stop(code_phys + len(code))
    uc = unicorn.Uc(unicorn.UC_ARCH_MIPS,
                    unicorn.UC_MODE_MIPS32 | unicorn.UC_MODE_LITTLE_ENDIAN)
    mapped: set[tuple[int, int]] = set()

    def map_range(start: int, stop: int) -> None:
        start = _page_start(start)
        stop = _page_stop(stop)
        for page in range(start, stop, PAGE):
            if (page, PAGE) not in mapped:
                uc.mem_map(page, PAGE)
                mapped.add((page, PAGE))

    map_range(code_start, code_stop)
    map_range(return_phys, return_phys + 4)
    map_range(stack_phys, stack_phys + stack_size)
    # A private stack is always legal; all other data ranges are explicit.
    allowed_ranges: list[tuple[int, int]] = [(stack_phys, stack_phys + stack_size)]
    declared_ranges: list[tuple[int, int]] = []
    for index, row in enumerate(routine.get("allowed_memory") or []):
        if not isinstance(row, dict):
            raise OracleError(f"{routine['id']}: allowed_memory[{index}] is malformed")
        start = _int(row.get("start"), "allowed_memory.start")
        size = _int(row.get("size"), "allowed_memory.size")
        stop = start + size
        if size == 0 or not PS1_RAM_START <= start < stop <= PS1_RAM_END:
            raise OracleError(f"{routine['id']}: allowed memory is outside PS1 RAM")
        protected = ((code_base, code_base + len(code), "code"),
                     (return_sentinel, return_sentinel + 4, "return sentinel"),
                     (stack_base, stack_base + stack_size, "stack"))
        for protected_start, protected_stop, name in protected:
            if start < protected_stop and stop > protected_start:
                raise OracleError(f"{routine['id']}: allowed memory overlaps {name}")
        physical_start = ps1_physical(start)
        physical_stop = physical_start + size
        map_range(physical_start, physical_stop)
        allowed_ranges.append((physical_start, physical_stop))
        declared_ranges.append((physical_start, physical_stop))
    for index, row in enumerate(routine.get("memory_init") or []):
        if not isinstance(row, dict) or not isinstance(row.get("words"), list) or \
                not row["words"]:
            raise OracleError(f"{routine['id']}: memory_init[{index}] is malformed")
        address = _int(row.get("address"), "memory_init.address")
        payload = b"".join(struct.pack("<I", _int(word, "memory_init.word"))
                           for word in row["words"])
        physical_address = ps1_physical(address)
        if not any(start <= physical_address and physical_address + len(payload) <= stop
                   for start, stop in declared_ranges):
            raise OracleError(f"{routine['id']}: memory_init is outside allowed_memory")
        uc.mem_write(physical_address, payload)
    uc.mem_write(code_phys, code)
    uc.mem_write(return_phys, struct.pack("<I", 0))
    violations: list[str] = []
    instruction_count = 0

    def code_hook(_uc: Any, address: int, size: int, _user: Any) -> None:
        nonlocal instruction_count
        instruction_count += 1
        if address in {return_sentinel, return_phys}:
            return
        physical_address = ps1_physical(address)
        if not code_phys <= physical_address < code_phys + len(code):
            violations.append(f"control escaped code at 0x{address:08x}")
            _uc.emu_stop()

    def memory_hook(_uc: Any, access: int, address: int, size: int,
                    value: int, _user: Any) -> bool:
        is_write = access in {unicorn.UC_MEM_WRITE, unicorn.UC_MEM_WRITE_UNMAPPED,
                              unicorn.UC_MEM_WRITE_PROT}
        physical_address = ps1_physical(address)
        if is_write and physical_address < code_phys + len(code) and \
                physical_address + size > code_phys:
            violations.append(f"self-modifying write at 0x{address:08x}")
            _uc.emu_stop()
            return False
        if MMIO_START <= physical_address < MMIO_END:
            violations.append(f"MMIO access at 0x{address:08x}")
            _uc.emu_stop()
            return False
        if not any(start <= physical_address and physical_address + size <= stop
                   for start, stop in allowed_ranges):
            violations.append(f"undeclared data access at 0x{address:08x}+{size}")
            _uc.emu_stop()
        return False

    uc.hook_add(unicorn.UC_HOOK_CODE, code_hook)
    uc.hook_add(unicorn.UC_HOOK_MEM_READ | unicorn.UC_HOOK_MEM_WRITE, memory_hook)
    uc.hook_add(unicorn.UC_HOOK_MEM_INVALID, memory_hook)
    register_ids = {"a0": mips.UC_MIPS_REG_A0, "a1": mips.UC_MIPS_REG_A1,
                    "a2": mips.UC_MIPS_REG_A2, "a3": mips.UC_MIPS_REG_A3,
                    "v0": mips.UC_MIPS_REG_V0, "v1": mips.UC_MIPS_REG_V1}
    for name, value in inputs.items():
        uc.reg_write(register_ids[name], u32(value))
    uc.reg_write(mips.UC_MIPS_REG_SP, stack_base + stack_size - 16)
    uc.reg_write(mips.UC_MIPS_REG_RA, return_sentinel)
    try:
        uc.emu_start(code_base, return_sentinel,
                     count=min(routine.get("max_instructions", policy["max_instructions"]),
                               policy["max_instructions"]))
    except unicorn.UcError as exc:
        raise OracleError(f"{routine['id']}: Unicorn stopped: {exc}; {violations}") from exc
    pc = uc.reg_read(mips.UC_MIPS_REG_PC) & MASK32
    if violations:
        raise OracleError(f"{routine['id']}: " + "; ".join(violations))
    if pc != return_sentinel:
        raise OracleError(
            f"{routine['id']}: did not return before instruction limit; pc=0x{pc:08x}")
    observed = uc.reg_read(register_ids[routine["observe"]["name"]]) & MASK32
    return {"observed": observed, "instruction_count": instruction_count,
            "returned_to_sentinel": True}


def _fails(routine: dict[str, Any], inputs: dict[str, int], policy: dict[str, Any]) -> bool:
    expected = evaluate_model(routine["model"], inputs)
    return execute_case(routine, inputs, policy)["observed"] != expected


def shrink_failure(routine: dict[str, Any], failing: dict[str, int],
                   policy: dict[str, Any]) -> dict[str, int]:
    current = dict(failing)
    boundary = [0, 1, MASK32, 0x7FFFFFFF, 0x80000000]
    for name in sorted(current):
        candidates = boundary + [current[name] >> shift for shift in (1, 8, 16)]
        for candidate in dict.fromkeys(u32(value) for value in candidates):
            if candidate == current[name]:
                continue
            proposal = dict(current)
            proposal[name] = candidate
            if _fails(routine, proposal, policy):
                current = proposal
                break
    return current


def run_routine(routine: dict[str, Any], policy: dict[str, Any]) -> dict[str, Any]:
    code = b"".join(struct.pack("<I", word) for word in routine["code_words"])
    failures = []
    instruction_counts = []
    cases = generated_cases(routine["input_domains"])
    for inputs in cases:
        expected = evaluate_model(routine["model"], inputs)
        result = execute_case(routine, inputs, policy)
        instruction_counts.append(result["instruction_count"])
        if result["observed"] != expected:
            failures.append({"inputs": inputs, "expected": expected,
                             "observed": result["observed"]})
    minimal = shrink_failure(routine, failures[0]["inputs"], policy) if failures else None
    return {
        "id": routine["id"], "class": routine["class"],
        "code_sha256": sha256_bytes(code), "code_bytes": len(code),
        "generated_cases": len(cases), "passed_cases": len(cases) - len(failures),
        "failed_cases": len(failures), "max_instructions_observed": max(instruction_counts),
        "failures": failures, "minimal_counterexample": minimal,
        "status": "passed" if not failures else "model_mismatch",
    }


def mutation_guards(doc: dict[str, Any]) -> dict[str, bool]:
    gte = validate_static_words([0x4A000000])
    cop0 = validate_static_words([0x40026000])
    syscall = validate_static_words([0x0000000C])
    bad_class = False
    mutated = json.loads(json.dumps(doc))
    mutated["pilots"][0]["class"] = "timing_sensitive"
    try:
        validate_spec(mutated)
    except OracleError:
        bad_class = True
    return {"gte_rejected": bool(gte), "cop0_rejected": bool(cop0),
            "syscall_rejected": bool(syscall), "timing_class_rejected": bad_class,
            "all_passed": bool(gte and cop0 and syscall and bad_class)}


def build_report(spec_path: Path = SPEC_PATH) -> dict[str, Any]:
    doc = load_spec(spec_path)
    routines = validate_spec(doc)
    unicorn, _ = import_unicorn()
    results = [run_routine(routine, doc["policy"]) for routine in routines]
    guards = mutation_guards(doc)
    return {
        "schema": REPORT_SCHEMA,
        "spec": str(spec_path.relative_to(ROOT)) if spec_path.is_relative_to(ROOT) else str(spec_path),
        "spec_sha256": sha256_bytes(spec_path.read_bytes()),
        "generator_sha256": sha256_bytes(Path(__file__).read_bytes()),
        "engine": {"name": "Unicorn", "version": unicorn.__version__,
                   "architecture": "MIPS32", "endianness": "little"},
        "routines": results,
        "summary": {"routines": len(results),
                    "generated_cases": sum(row["generated_cases"] for row in results),
                    "passed_cases": sum(row["passed_cases"] for row in results),
                    "failed_cases": sum(row["failed_cases"] for row in results),
                    "all_models_match": all(row["status"] == "passed" for row in results)},
        "mutation_guards": guards,
        "boundary": {"behavioral_authority": False,
                     "supplements_native_duckstation_controls": True,
                     "allowed_classes": ["pure", "ram_local"],
                     "rejected_domains": doc["policy"]["rejected_domains"],
                     "automatic_campaign_promotion": False},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-pilot", action="store_true")
    mode.add_argument("--check-pilot", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--spec", type=Path, default=SPEC_PATH)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = build_report(args.spec.resolve())
    rendered = canonical_json(report)
    if args.write_pilot:
        if args.spec.resolve() != SPEC_PATH.resolve():
            raise OracleError("tracked pilot may only use the canonical synthetic spec")
        PILOT_PATH.write_bytes(rendered)
        print(f"[phase4-mips-oracle] wrote {PILOT_PATH.relative_to(ROOT)}")
        return 0
    if args.check_pilot:
        if not PILOT_PATH.is_file() or PILOT_PATH.read_bytes() != rendered:
            raise OracleError("retained MIPS oracle pilot is stale")
        print(f"[phase4-mips-oracle] PASS: {report['summary']['passed_cases']} cases")
        return 0
    if args.report is None:
        print(rendered.decode(), end="")
        return 0 if report["summary"]["all_models_match"] else 1
    report_path = args.report.resolve()
    try:
        report_path.relative_to(ROOT.resolve())
    except ValueError:
        pass
    else:
        raise OracleError("non-pilot MIPS reports must remain outside the repository")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_bytes(rendered)
    print(report_path)
    return 0 if report["summary"]["all_models_match"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OracleError as exc:
        print(f"phase4 MIPS oracle error: {exc}", file=sys.stderr)
        raise SystemExit(2)
