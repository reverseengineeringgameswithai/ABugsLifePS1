# Ghidra cross-check layer — A Bug's Life RE

Headless Ghidra setup used **only as a decompiler / cross-check layer** alongside the primary
radare2 + DuckStation workflow. `symbols/re_symbols.sym` is the authoritative symbol source;
Ghidra consumes it and never writes back. See `PILOT_REPORT.md` for the verdict.

## Prereqs
- Ghidra 12.1.2 Flatpak (`org.ghidra_sre.Ghidra`), already installed with `filesystems=home;`
  (no `flatpak override` needed to read this project dir).
- One-time: the headless launcher needs its config file:
  ```sh
  flatpak run --command=sh org.ghidra_sre.Ghidra -c \
    '[ -f /var/config/ghidra.properties ] || cp /app/lib/ghidra/support/launch.properties.orig /var/config/ghidra.properties'
  ```

## Re-import + re-analyze from scratch (after the EXE or base assumptions change)
```sh
flatpak run --command=sh org.ghidra_sre.Ghidra -c '
/app/lib/ghidra/support/analyzeHeadless \
  '"$PWD"'/ghidra/project ABLPilot \
  -import '"$PWD"'/SCUS_942.88 \
  -processor "MIPS:LE:32:default" \
  -loader BinaryLoader -loader-baseAddr 0x8000f800 \
  -scriptPath '"$PWD"'/ghidra/scripts \
  -postScript ABLPilot.java '"$PWD"'/symbols/re_symbols.sym '"$PWD"'/ghidra/out "8001cdc0,800526f4,80053814" \
  -overwrite'
```
`0x8000f800` base ⇒ file offset `0x800` maps to VA `0x80010000` (PS-X EXE; see
`docs/EXECUTABLE_AND_OVERLAYS.md`).

## Re-sync symbols / decompile more functions (program already imported — fast, no re-analysis)
```sh
flatpak run --command=sh org.ghidra_sre.Ghidra -c '
/app/lib/ghidra/support/analyzeHeadless \
  '"$PWD"'/ghidra/project ABLPilot \
  -process SCUS_942.88 -noanalysis \
  -scriptPath '"$PWD"'/ghidra/scripts \
  -postScript ABLPilot.java '"$PWD"'/symbols/re_symbols.sym '"$PWD"'/ghidra/out "<comma,sep,hex,addrs>"'
```
The last arg is the list of function addresses to decompile (hex, no `0x`). Output → `ghidra/out/ghidra_<addr>.c`.

## PsyQ signature project (ABLPsx — separate from ABLPilot)
A SECOND headless project used only for PsyQ SDK library identification, via the
`ghidra_psx_ldr` extension (release 2026.07.02 for Ghidra 12.1.2, installed at
`~/.var/app/org.ghidra_sre.Ghidra/config/ghidra/ghidra_12.1.2_FLATPAK/Extensions/ghidra_psx_ldr`).
Its PsxLoader parses the PS-X EXE header itself (no BinaryLoader/baseAddr needed), sets gp,
auto-detects the PsyQ version from `Ps` lib markers (**detected: 4.0.0**), and its
"PsyQ Signatures" analyzer names matched library functions.
```sh
flatpak run --command=sh org.ghidra_sre.Ghidra -c '
/app/lib/ghidra/support/analyzeHeadless \
  '"$PWD"'/ghidra/project ABLPsx \
  -import '"$PWD"'/SCUS_942.88 \
  -loader PsxLoader \
  -scriptPath '"$PWD"'/ghidra/scripts \
  -postScript ExportPsyqMatches.java '"$PWD"'/extracted/re_baseline \
  -overwrite'
```
Matches flow into `symbols/re_symbols.sym` ONLY via `tools/merge_psyq_symbols.py`
(hand-curated names always win; oracle 0x8006B130==SsVabOpenHead aborts on drift).
2026-07-08 run: 644 EXE-range matches, map 129 → 761 symbols; corrected one prior
mislabel (0x8006B1C0 = SsVabOpenHeadWithMode, real SsVabTransBody = 0x8006B59C).


## $gp context + function export (SetGpAndExport.java)
Sets MIPS `gp = 0x80081d98` register context over the resident text range, re-analyzes,
exports `extracted/re_baseline/ghidra_functions.csv` (address,name; FUN_* auto-names exported
empty — `re_symbols.sym` stays authoritative), and re-decompiles the sample functions to
`ghidra/out/ghidra_<addr>_gp.c` for the before/after `unaff_gp` comparison:
```sh
flatpak run --command=sh org.ghidra_sre.Ghidra -c '
/app/lib/ghidra/support/analyzeHeadless \
  '"$PWD"'/ghidra/project ABLPilot \
  -process SCUS_942.88 \
  -scriptPath '"$PWD"'/ghidra/scripts \
  -postScript SetGpAndExport.java '"$PWD"'/extracted/re_baseline '"$PWD"'/ghidra/out "8001cdc0,800526f4,80053814"'
```
Afterwards fold the export into the inventory + census:
`python tools/re_baseline.py --inventory --report && python tools/function_census.py`.

## GUI (optional, to browse the same project)
```sh
flatpak run org.ghidra_sre.Ghidra   # then open project ghidra/project/ABLPilot
```

## Not configured (by design)
- **GhidraMCP** — deliberately not set up; this layer is headless decompile/cross-check only.
- ~~`$gp` register context~~ — DONE 2026-07-08 via `SetGpAndExport.java` (see below);
  gp-relative globals now resolve (`unaff_gp` 28 → 0 on the pilot samples).
