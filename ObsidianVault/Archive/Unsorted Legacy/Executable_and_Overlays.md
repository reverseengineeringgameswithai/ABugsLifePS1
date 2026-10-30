---
kind: archived_legacy_note
archived: 2026-07-08
original_path: ObsidianVault/Executable and Overlays.md
aliases:
  - "Executable and Overlays"
migration_action: superseded
superseded_by:
  - SYS_executable_image
  - SYS_overlays_and_runtime_loading
confidence: confirmed
---

# Archived Legacy Note

- Original path: `ObsidianVault/Executable and Overlays.md`
- Archive reason: Support/root note; review before migration.

> This note is preserved for provenance. Do not treat its claims as current Canon unless a Canon note explicitly promotes them.

## Original note

---
title: Executable and Overlays
type: reference
updated: 2026-06-20
tags: [executable, overlays, mips, milestone3, gap-0020]
---

# Executable and overlays — M3 baseline

> Vault entry point for the detailed architecture record in `docs/EXECUTABLE_AND_OVERLAYS.md`. Metadata below was independently rechecked read-only against the owner-local ignored files on 2026-06-20. No executable or overlay bytes are committed.

## Main executable

| File | Size | SHA-1 | Load / entry | Role |
|---|---:|---|---|---|
| `SCUS_942.88` | 471,040 | `af43de22474f15664d0e17498fbd27faeb7ed111` | `0x80010000`, entry `0x8005F690`, payload end `0x80082800` | resident game + statically linked PsyQ libraries |

PS-X header fields, GP/BSS/stack cautions, and runtime regions are consolidated in [[MEM - Global memory map]].

## Overlay regions and files

| Region/file | Disc metadata | Load range | Known entry/functions | Role, confidence, modding relevance |
|---|---|---|---|---|
| Region A family — `LEVEL0N/LEVEL*.BIN` | 20 files at LBAs 2292–15367; inventory below | `0x800B39A0–0x800B5787` maximum; code normally starts `+4` | LEVEL01 base has 3 functions below; `LEVEL1.BIN` partial | **Verified swap base/family.** Per-level init/spawn/event logic is modding-relevant; exact scene→variant residency remains unknown. |
| Region B — `BITS/MEMORY.BIN` | LBA 255; 36,448 B (`0x8E60`); SHA-1 `947ef0246457c706f1e07cb6ce91fbdd269071d7` | `0x800B5788–0x800BE5E7` | init `+0x7D90` = `0x800BD518`; loader `0x8003F5B8` | **Verified file/load/init.** Memory-card/menu role is likely but breadth unknown; relevant to front-end/save modding. |
| Region B — `FMV/FMV.BIN` | LBA 1316; 509,800 B (`0x7C768`); SHA-1 `9738b2b68395e1b43662e15649616097b4b934fb` | `0x800B5788–0x80131EEF` if loaded contiguously | loader paths documented, entry not confirmed | **Verified file/base; role strongly supported by path/use.** Playback internals remain unknown; relevant only to FMV/front-end work. |

Loader evidence: resident [[FUNC_80046330]] is the universal file reader. `0x8003D620` loads Region A to `0x800B39A0`; `0x8003F5B8` loads `BITS/MEMORY.BIN` to Region B; `0x8003E7C0?` / `0x8003F504` are documented FMV paths. Question-marked function identities remain provisional.

The largest Region A file, `LEVEL07/LEVEL.BIN` (7,656 B / `0x1DE8`), ends exactly at `0x800B5788`, the Region B base. This independently explains the fixed Region A capacity; it does not prove both regions are simultaneously resident in every scene.

## Region A disc inventory

All rows derive read-only from owner-local `REBUILD/abl.xml` plus extracted file metadata. The LBA/size/hash facts are committed here; the XML and binary payloads remain ignored/local-only. Every non-placeholder row loads at the Region A base according to the documented loader family. All are potentially modding-relevant for their owning scene, but only LEVEL01 base behavior has been enumerated.

| File | LBA | Bytes | SHA-1 | Static status |
|---|---:|---:|---|---|
| `LEVEL00/LEVEL.BIN` | 2292 | 4 | `d6459ab29c7b9a9fbf0c7c15fa35faa30fbf8cc6` | header/placeholder only; no code payload |
| `LEVEL01/LEVEL.BIN` | 2905 | 1,680 | `62bc0f807c942e687e2a4bb09fe2cbc2d5f15edf` | 3 functions enumerated below |
| `LEVEL01/LEVEL1.BIN` | 3435 | 2,700 | `f75139705bb2d3688fd3d3a239fa59a23c3ec858` | partial boundaries below |
| `LEVEL02/LEVEL.BIN` | 4531 | 4,032 | `6eecee68f5efb8fcea27deca2a1ebf2a720639f2` | metadata only |
| `LEVEL02/LEVEL1.BIN` | 4841 | 4,272 | `3ec712c58b2785c25d9ce1ac9aa94f8b1ca655e9` | metadata only |
| `LEVEL03/LEVEL.BIN` | 6040 | 5,036 | `32d1a6c4a0f35c66a9dd5176e21e6e803298e503` | metadata only |
| `LEVEL03/LEVEL1.BIN` | 6498 | 3,184 | `396e080a5bd203d79d17bd4015714b55e5746813` | metadata only |
| `LEVEL04/LEVEL.BIN` | 7513 | 3,068 | `df5b1ba8737e5c6a598d704423de2542680824a0` | metadata only |
| `LEVEL04/LEVEL1.BIN` | 7970 | 4,924 | `0dca22ba15b678b51a2a066a31637c749b5aafdf` | metadata only |
| `LEVEL05/LEVEL.BIN` | 9005 | 2,400 | `c9b45c89285d076a02f3f551ca12ad8cff3eba23` | metadata only |
| `LEVEL05/LEVEL1.BIN` | 9398 | 4,672 | `9b7585f427097318e71ffdaad15310a45effc1cc` | metadata only |
| `LEVEL06/LEVEL.BIN` | 10813 | 1,608 | `7aaebc3f384598910f815a1e716812855f1f2977` | metadata only |
| `LEVEL06/LEVEL1.BIN` | 11247 | 1,820 | `0a809238da9f6b3aea23bb1b412fc302d547248d` | metadata only |
| `LEVEL07/LEVEL.BIN` | 11960 | 7,656 | `91fb8ce18d5ae76c937132a7cfbf98f8fe46f52a` | metadata only; fills Region A exactly |
| `LEVEL07/LEVEL1.BIN` | 12391 | 4,336 | `79702fa222a0ab71b95107d174d8f360ab8cef19` | metadata only |
| `LEVEL08/LEVEL.BIN` | 13212 | 3,500 | `56434787fa990456e186d553d97dc01e3a62ce90` | metadata only |
| `LEVEL08/LEVEL1.BIN` | 13750 | 4,064 | `afec834108e5a4ac06a53c42b8be29b1e1ac3797` | metadata only |
| `LEVEL09/LEVEL.BIN` | 14241 | 5,232 | `154cbfa38f10531c5201763ac9585a9b31864c28` | metadata only |
| `LEVEL09/LEVEL1.BIN` | 14731 | 532 | `0fc6c441ee8f8f66331cf53cfc3cbbb44a74013d` | metadata only |
| `LEVEL10/LEVEL.BIN` | 15367 | 2,080 | `83b01f53fb1ad5edda4336957d2987b029b3cb78` | metadata only |

Metadata reproduction (read-only, owner-local extraction required):

```bash
rg 'source="files/(BITS/MEMORY\.BIN|FMV/FMV\.BIN|LEVEL[0-9]+/LEVEL[0-9]*\.BIN)"' REBUILD/abl.xml
find REBUILD/files -type f \( -path '*/LEVEL*.BIN' -o -path '*/MEMORY.BIN' -o -path '*/FMV.BIN' \) -exec stat -c '%n %s' {} +
sha1sum REBUILD/files/BITS/MEMORY.BIN REBUILD/files/FMV/FMV.BIN REBUILD/files/LEVEL*/LEVEL*.BIN
```

## LEVEL01 `LEVEL.BIN` function enumeration

Manual r2 analysis at the correct code offset found three bounded functions:

| Address | File offset | Size | Role | Confidence / evidence |
|---|---:|---:|---|---|
| `0x800B39A4` | `0x4` | `0x148` (328 B) | `level_overlay_init` | **Verified behavior** — clears/copies 128-slot entity tables; calls resident `0x80061A48` and `0x8003E4E0` |
| `0x800B3AEC` | `0x14C` | `0xCC` (204 B) | fixed LEVEL01 entity spawner | **Verified behavior** — three calls to resident `0x80042C70` |
| `0x800B3BB8` | `0x218` | `0x39C` (924 B) | event/update handler | **Needs Evidence for final name** — command cursor, contact allocation, containment/proximity behavior documented |

Command used:

```bash
r2 -2 -q -a mips -b 32 -e cfg.bigendian=false -m 0x800b39a0 \
  -c 'e anal.gp=0x80081d98; af @ 0x800b39a4; af @ 0x800b3aec; af @ 0x800b3bb8; afl' \
  REBUILD/files/LEVEL01/LEVEL.BIN
```

The first automatic `aaa` pass incorrectly treated the four-byte header at `0x800B39A0` as code. Explicit analysis at `+4` is required. This is a concrete example of the function-boundary risk tracked by A3/GAP-0020.

## LEVEL01 `LEVEL1.BIN` partial result

- Universal init begins at `0x800B39A4` and returns at `0x800B3AEC`.
- Another prologue begins at `0x800B3B68`; calls include resident pickup/contact/gameplay functions.
- The file is not a drop-in same-offset copy of `LEVEL.BIN`; do not reuse the three-function labels blindly.

## Role/scene questions

- Which Region A variant is loaded for each LEVEL01 scene/subscene?
- Which exact functions in `MEMORY.BIN` own menus/save data versus generic memory-card services?
- What are the FMV overlay entry points and loader state gates?
- Do camera, AI/PATH, and event interpreters live in resident code or specific Region A variants?
- What is the safe symbol namespace for mutually swapped functions at the same virtual address?

## Minimum viable overlay baseline

### Confirmed and reproducible as metadata

- two swap bases and their maximum/observed ranges;
- the complete 20-file Region A inventory plus the two known Region B files, with LBAs, sizes, and hashes;
- resident loaders/file reader and the `MEMORY.BIN` init address;
- three bounded LEVEL01 base-overlay functions and a partial LEVEL01 variant boundary;
- module-residency caveats for symbols at reused virtual addresses.

### Static but owner-local

The hashes, r2 disassembly, and header words were rechecked against ignored extracted binaries. Anyone with their own matching SCUS-94288 image can reproduce them using the recorded hashes/commands; the payloads are intentionally not in Git.

### Local-only dynamic evidence

Prior vault notes cite fork traces for loader behavior. No live trace was rerun here, and those claims are not upgraded by the current dirty/unpreserved fork. Scene→variant residency still needs `transferLog` or loader breakpoints after GAP-0001 preservation.

### M3 disposition

The baseline bar is met: later milestones can cite the fixed regions, complete file inventory, loaders, metadata, and known LEVEL01 functions without assuming full overlay RE. **GAP-0020 remains In Progress — M3 baseline complete; broader overlay RE is deferred to the engine/gameplay milestones that need a specific module.**

## Next experiments

1. After GAP-0001 preservation, use `transferLog` during a fresh scene load to record file→destination→frame.
2. Import `symbols/re_symbols.sym`, load a named fixture, and enumerate Region A function bounds while the exact variant is resident.
3. Enumerate `MEMORY.BIN`/`FMV.BIN` offline at `0x800B5788` only when front-end/save/FMV work needs them, keeping module-qualified names.
4. Record hashes and module identity with every overlay trace; never persist extracted binary bytes in Git.

## Related

[[MEM - Global memory map]] · [[Symbol Map Baseline]] · [[Asset - LEVEL.BIN and overlays]] · [[FUNC_8003CF2C]] · [[FUNC_80046330]] · [[DuckStation Fork Reproducibility]] · `docs/EXECUTABLE_AND_OVERLAYS.md`
