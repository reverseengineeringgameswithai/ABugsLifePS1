# Phase 4 C03: FLIK letters

Date: 2026-08-03

Status: **substantiated partial; static boundary exhausted**

## Question

Resolve C03's source population, pickup-to-bitmask path, four-letter completion reward,
HUD/results consumers, and save/reset lifecycle using retained evidence and pristine ASM
before requesting another live DuckStation run.

Movie-viewer mapping is excluded because C17 owns that work.

## Capsule and fixture preflight

No retained Phase 4 capsule matching C03/FLIK letters was present. Three legacy fixtures
were found:

| Fixture | Date / format | SHA-256 | Classification |
|---|---|---|---|
| `collecting_FLIK_LEVEL01.movie.json` | 2026-07-06, movie v3, from boot | `04874b8f214a8a3adc12afbbbd49a7961017fb323f5f5e297ae23fab14884fd4` | Behavioral/poll-only |
| `collecting_FLIK_LEVELTRAINING.movie.json` | 2026-07-06, movie v3, from boot | `ad2bd05c18521ad885fe82c3bf448270390bbca2b426c8ce7f0565a14ac16df9` | Behavioral/poll-only |
| `collecting_flik.sav` | state fixture | `ef7eb5136af0f04dd00fc1cbd57c5a8e3b61ad88a1f1c7e3a66a7e716992887a` | Narrow runtime anchor |

The movies predate the Interpreter instrumentation discovery and contain no execution-
mode provenance. They must not be armed with CPU instrumentation: a CachedInterpreter
recording can silently switch to Interpreter and desync. Existing behavioral conclusions
remain usable, but neither movie is a traceable closure fixture.

## C-based pristine analysis

The following C programs were used against the checked-in pristine ASM and extracted
`LEVEL.DAT` records. Transient outputs remain under `/tmp`.

| Program | Source SHA-256 | Principal output | Output SHA-256 |
|---|---|---|---|
| `tools/phase4_c03_asm_extract.c` | `c8375c6e9164ef899500a6565bac02e6cc9afebb04a511bead94e28dc5e3e65c` | `/tmp/phase4_c03_letter_asm.txt` | `74fd565b68c15f85361ebc6ef35ba7dcc122ebbf18c131553a4d36a34c1ec6a4` |
| `tools/phase4_c03_dat_census.c` | `81532d3263d92656e0c80a60446f2b6c55756814cd863e5e0f0b5c2aa766ee90` | `/tmp/phase4_c03_dat_census.txt` | `460ecc2aa49f62a65efa40e21909d97e51052eb40bf7579131e21ee4a54bc352` |
| `tools/phase4_c03_mips_addrflow.c` | `9dcc0962f514133470c446a0f1e1ee4b795d4ba439d83779da98073a4d90cf7b` | `/tmp/phase4_c03_mips_addrflow.txt` | `52970283d72bfd1b9339b2da8b776226f09b25aeefcf94354b3866ac5650bf08` |

Additional bounded extracts:

- Dispatcher table: `/tmp/phase4_c03_dispatch_table.txt`, SHA-256
  `46082f7b51d69efb627ae002882cf173f608431173ce296cb3eaf2a845182ad6`.
- Player constructor: `/tmp/phase4_c03_player_ctor.txt`, SHA-256
  `6b51e0ed314769c475fe8619a7f1b3ef5af8d6134985583bd35a053207eef426`.
- Player-template callee: `/tmp/phase4_c03_player_template_copy.txt`, SHA-256
  `a28efc3b8a71b85c022e7c53a767f0eac52da841184502dc12ae1d679b4b04ba`.

## Observations

### Source breadth

The C census parsed the extracted pristine gameplay `LEVEL.DAT` records:

| Data set | F | L | I | K | Complete set |
|---|---:|---:|---:|---:|---|
| Parsed `LEVEL00` record | 0 | 0 | 0 | 0 | no |
| Each of `LEVEL01` through `LEVEL10` | 1 | 1 | 1 | 1 | yes |
| Gameplay total | 10 | 10 | 10 | 10 | 40 sources |

Training's separately observed runtime sources are not claimed to originate in the
parsed `LEVEL00` record.

All four letters use object type `0x3F`. The dispatcher subtracts `0x10` from the subtype
and routes `0x10/0x11/0x12/0x13` to F/L/I/K handlers at
`0x80053D04/0x80053E64/0x80053FC0/0x8005411C`.

### Pickup state and completion

The handlers OR bits `1/2/4/8` into byte `0x800A65A2`. The four completion bodies are
separate but structurally identical:

- F life-cap body: `0x80053DDC..0x80053DF8`.
- L life-cap body: `0x80053F38..0x80053F54`.
- I life-cap body: `0x80054094..0x800540B0`.
- K life-cap body: `0x800541F0..0x8005420C`.

Each branch requires an exact mask of `0x0F`. It snapshots Flik's position/state into
`0x800B3988..0x800B3998`, emits effect/SFX id `-11`, and increments lives at
`0x800A65A0` only when the prior value is below 9. On increment it emits id `-8` and
pulses the lives/progress HUD channel at `0x800B0188`. Every letter also pulses the FLIK
HUD channel at `0x800B0194`.

The conservative address-flow pass found only the F and L stores because the reference
ASM splits the I/K continuations into another file and therefore loses incoming register
constants. It found no direct store or recognized zero-fill covering `0x800A65A2` outside
the pickup path. This is a bounded negative result, not proof that no reset exists.

### Native runtime corroboration

Earlier isolated Training work recorded native mask progression
`0 -> 1 -> 3 -> 7 -> 0x0F`; all four source records were consumed by receiving the
`0x80000000` Y sentinel. That work also reached the results screen and observed the FLIK
result coin. The older FLIK5 gate experiment independently showed that completion is
withheld below the patched threshold and that satisfying the threshold advances lives
from 5 to 6. FLIK5 is corroboration of the shared gate, not pristine closure evidence.

### HUD, results, and persistence

- The SELECT HUD reads `0x800A65A2` and draws F/L/I/K tiles from bits `0..3`; its pulse
  behavior is tied to `0x800B0194` and clamps at the complete mask.
- The results overlay reads the same mask and counts set bits for the collected-letter
  presentation.
- Serializer `0x80055478` writes lives from `0x800A65A0`, the scene byte, header data,
  and the per-scene table. It does not serialize `0x800A65A2`.
- Deserializer `0x80055538` restores `0x800A65A0`; it does not restore the FLIK mask.
- Player construction at `0x8005B9A8` calls `0x8004DC0C`, whose zero-fill covers only
  the first `0x30` bytes of the player object. It does not cover offset `+0xA2`.

## Interpretation

The mask is transient gameplay/results state while the awarded life is persistent save
state. Source population is complete across all ten gameplay levels, and the handler,
HUD, results, life-cap, and serializer boundaries are statically pinned.

The exact instruction/path that clears or replaces the mask during the results-to-next-
level lifecycle is not present in the direct writer/recognized-fill census. It may be an
indirect store or a wider lifecycle operation that the conservative address propagation
cannot resolve. That path must not be claimed from absence.

## Closure decision

C03 remains `partial`, but its ASM/data portion is bounded-exhausted. More broad static
searching has sharply diminishing value. Full closure needs an Interpreter-mode re-record
of the existing LEVEL01 route:

`movies/phase4/interpreter/C03_flik_letters_lifecycle.movie.json`

Required behavior:

1. Naturally collect all four F/L/I/K letters on pristine media.
2. Continue through level completion and the results screen.
3. Continue until the next gameplay scene is active.

Replay at normal 60 Hz for the transition-sensitive portion. Arm write attribution for
`0x800A65A2` and `0x800A65A0` from frame 0, plus the four handler ranges. This will pin
the pristine fourth-letter life write, life-cap branch, source-consumption contact, and
the first reset/replacement of the mask. No cold boot is required because no disc/code/
asset mutation is involved; a hash-pinned state anchor is sufficient.

## Related evidence

- `ObsidianVault/Experiments/Runtime Tests/Experiment_-_FLIK5_five-letter_token_gate.md`
- `src_re/flik_emblem_results_menu.c`
- `src_re/level_complete_results_800b7da0.c`
- `src_re/hud_800526f4.c`
- `asm/nonmatchings/resident/80053814_FUNC_80053814.s`
- `asm/nonmatchings/resident/80053f48.s`
- `asm/nonmatchings/resident/80055478.s`
- `asm/nonmatchings/resident/80055538.s`

## 2026-08-04 closure addendum: initializer and cap branch attributed

Status after this addendum: **substantiated partial; bounded-exhausted**.

### Capsule and fixture decision

The central retained-capsule set still has no C03/FLIK-letter capsule, so the named missing
domains required a live run. The existing v4 Interpreter 100% fixture was sufficient for
the bounded question:

| Artifact | Identity |
|---|---|
| `movies/Phase4/Interpreter/100% Runs/LEVEL06.movie.json` | SHA-256 `b2a3ebcae0c82aa65ea6f5052561f72cc2e7bc291655b5500aae70031188e127`; 12,917 frames |
| `LEVEL06.movie.sav` | SHA-256 `93691960e8ddf2d981732994b591c855db19c7a453bae416e09399ac242509c4`; initial emulator frame 121,865 |
| pristine BIN mounted by the state | size 738,285,744; SHA-1 `0bc1a29748d4bd608d076495d085e825574880d1f` (matches the pinned retail baseline) |
| DuckStation binary | SHA-256 `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899` |

The isolated instance used `/tmp/duckstation-c03-lifecycle-20260804`, port `23903`, and an
explicit `[CPU] ExecutionMode=Interpreter` setting before the movie/state was loaded.
`movie.status` reported v4, `reproducible:true`, and `truncated:false`. Watches were armed
at playback index 0. Playback was accelerated only to the pre-transition boundary; the
results/cutscene/hub tail ran at normal speed. The owned instance was then stopped by its
config-scoped launcher.

### Natural writes and life-cap path

The movie begins with lives `9` and a stale pre-load mask `0x03`. Gameplay initialization
clears it, after which the route naturally collects the letters in I/K/L/F order:

| Movie frame | Writer PC | Mask transition |
|---:|---:|---:|
| 644 | `0xBFC02BB0` | `0x03 -> 0x00` |
| 3,196 | `0x80053FCC` | `0x00 -> 0x04` |
| 3,868 | `0x80054128` | `0x04 -> 0x0C` |
| 5,354 | `0x80053E70` | `0x0C -> 0x0E` |
| 5,744 | `0x80053D10` | `0x0E -> 0x0F` |

The F-last handler executes the exact-mask gate and `0x80053DDC..0x80053DEC` cap check,
does not execute increment store `0x80053DF8`, and resumes at `0x80053E5C`. Lives remain
9. This is the pristine natural cap branch, not a memory perturbation.

No later write to `0x800A65A2` occurs through all 12,917 frames. The mask remains `0x0F`
through results, the post-level Birdnest cutscene, and the Journey hub. Thus results and
the hub retain the completed set; they do not clear it.

### Exact reset mechanism

A bounded replay of movie frames 0..700 traced zero-fill entry `0x8005F7AC` with registers.
The only call covering the mask was:

`a0=0x800A6500, a1=0, a2=0xA8, ra=0x80046B70`

This lifts the generic BIOS byte store to call PC `0x80046B68` in `fcn.80046b20`. Pristine
ASM at `asm/nonmatchings/resident/80046b20.s` proves the intent:

- `0x80046B64` saves lives from player offset `+0xA0` into `s2`.
- `0x80046B68` zero-fills the player base through `+0xA7` (`0xA8` bytes).
- The FLIK mask at `+0xA2` lies inside that clear.
- `0x80046C00` restores lives to `+0xA0`; no corresponding mask restore exists.

The access event then attributes the actual `0x03 -> 0x00` byte write to BIOS PC
`0xBFC02BB0` at absolute frame 122,509/cycle 69,364,570,503. This resolves the previous
static census miss: the reset is a wide indirect zero-fill, not a direct absolute store.

### C reduction and transient evidence

`tools/phase4_c03_trace_reduce.c` (SHA-256
`25e42f365cfb36ee330848d395fd7b3b2564b2fac0458d6b4b3142565e265abd`) reduces the
zero-fill call stream, mask access events, and pickup execution trace. Its output is
`/tmp/phase4_c03_trace_reduce.txt` (SHA-256
`407ad8f76876b4070faec9b266010c3a6546b78f98deee12e73876ec16183582`). Inputs:

| Transient stream | SHA-256 |
|---|---|
| `/tmp/c03_zero_wrapper_events.json` | `c7f44b31eea9eb0a0c38f5e191d9ed9dc4f48b2cf14f37e7b5c5be9ded888bdd` |
| `/tmp/c03_mask_events_full.json` | `8b45f007535c7eb181bb3af112d29b77cfc9f040c15d55eee5474c85b618e2d9` |
| `/tmp/c03_lives_events_full.json` | `b5e3c8d2a1258967eeb92df8a0600d43020b6c6eab20e9beefc96317357297b4` |
| `/tmp/c03_letter_exec_full.json` | `8d82d1fd52c2905c1ffc8c8ed5e3990daca97895878aaae50b91f0633444c801` |

### Closure boundary

No further analysis of either retained 100% run can exercise the below-cap reward: both
LEVEL06 and LEVEL15 start at lives 9. LEVEL06 ends at the Journey hub; LEVEL15 is the final
level and ends at the save prompt. C03's remaining controls therefore require new behavior,
not a broader search of the same evidence:

1. Start with lives at 8 or below and naturally complete F/L/I/K to trace the pristine
   increment store dynamically (the store is already statically pinned).
2. Continue from results through the hub into any next gameplay scene to observe the
   already-attributed `fcn.80046b20` initializer on that exact continuous transition.

One v4 Interpreter movie can cover both. It does not need a cold boot or a literal 100%
item run: naturally collect all four letters, complete the level, enter another playable
level, and continue until Flik is active. Until that promoted full-closure control exists,
C03 is honestly `substantiated partial; bounded-exhausted` and is safe to move past.

## 2026-08-04 full closure: below-cap reward and continuous reinitialization

Status after this run: **confirmed; Phase 4 boundary exhausted**.

The operator recorded the requested fixture at
`movies/Phase4/Interpreter/C03_flik_letters_lifecycle.movie.json`. It is movie v4,
8,594 frames, state-anchored at emulator frame 5,307, and was replayed from movie frame 0
at normal speed with Interpreter configured before instrumentation. `movie.status` remained
`reproducible:true` and `truncated:false`.

| Artifact | SHA-256 |
|---|---|
| closure movie | `248e25975c8ec910710ef47803b53634674095dd2bb63865c5cecbf6091c701a` |
| `C03_flik_letters_lifecycle.movie.sav` | `c0f6eaf10d12e1102787e476e7e6a2c5a2effaa59e05a2fada562b78fd8cbfe0` |
| DuckStation binary | `f34aaacd7116994885a2a5a17a9f2c517ce5ed1bfc863826fa9d9750ea5d1899` |
| isolated Interpreter settings | `a718b36213265f5787f3f8779e67cf86d69178c359f2cc08a48b93a8be49a251` |

The state mounted the already-verified pristine retail BIN (size 738,285,744; SHA-1
`0bc1a29748d4bd608d076495d085e825574880d1f`). The isolated instance used
`/tmp/duckstation-c03-closure-20260804`, port `23904`, and was stopped by its owned
config-scoped launcher after capture.

### Exact continuous timeline

The movie starts at lives 5 and mask 0. All writes are instruction-attributed:

| Movie frame | Writer PC | Transition |
|---:|---:|---|
| 2,102 | `0xBFC02BB0` via call `0x80046B68` | initial player init; mask `0 -> 0`, lives `5 -> 0 -> 5` |
| 2,642 | `0x80053E70` | L: mask `0x00 -> 0x02` |
| 3,670 | `0x80054128` | K: mask `0x02 -> 0x0A` |
| 4,475 | `0x80053D10` | F: mask `0x0A -> 0x0B` |
| 5,069 | `0x80053FCC` | I: mask `0x0B -> 0x0F` |
| 5,069 | `0x800540B0` | natural reward: lives `5 -> 6` |
| 8,360 | `0xBFC02BB0` via call `0x80046B68` | next gameplay init; mask `0x0F -> 0`, lives `6 -> 0` |
| 8,360 | `0x80046C00` | restore preserved lives `0 -> 6` |

The mask-completion write occurs at cycle 5,874,505,707 and the life write at cycle
5,874,506,190: 483 cycles later in the same frame. Only one of the four reward-store PCs
executes, `0x800540B0`, matching I as the last letter. The second initializer is the same
`0x800A6500`/`0xA8` zero-fill already recovered from pristine ASM, now observed on the
continuous post-completion route requested by the original closure decision. Final values
are mask 0 and lives 6.

### C closure reduction

`tools/phase4_c03_closure_reduce.c` (SHA-256
`5f6e1025f743aafc30d1101b2f2776391c133d62de1d0fc5456149c0258847b3`) independently
reduces the two covering zero-fill calls, all mask/lives transitions, and the unique reward
store. Output `/tmp/phase4_c03_closure_reduce.txt` has SHA-256
`5bc6b53e1a9e0fc4fe0b9a3bc465a94b3bb98014a84cbee442de8aee2cd678ba`.

| Transient stream | SHA-256 |
|---|---|
| `/tmp/c03_closure_zero_events.json` | `088c9bd4081ce01b6cca055d5671dc6cb1bbd967b8b249ee66d04d466d2820ea` |
| `/tmp/c03_closure_mask_events.json` | `0acfd501d1ffcf11b1c39acf8d262cb73ec938ad4194b341e5697dde443e6735` |
| `/tmp/c03_closure_lives_events.json` | `d1777124d73886416069886b1437bafd0d7dee8b7ebaecbfd156fdfa68560653` |
| `/tmp/c03_closure_i_reward_exec.json` | `bb8348f77398db841ed6007e86f56dd4e851733dedbb73dd52c0824a37d2af9e` |

Both formerly optional controls are now satisfied on pristine media without perturbation:
the below-cap reward is dynamically attributed, and the continuous next-gameplay reset is
dynamically attributed. No C03 movie or promoted missing domain remains.
