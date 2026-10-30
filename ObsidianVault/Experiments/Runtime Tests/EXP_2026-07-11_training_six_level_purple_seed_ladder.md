# EXP 2026-07-11: Training six-level purple seed ladder

## Question

Can ALLMODS add six purple tokens and extend the purple seed lane from four native
rows to six logical levels without touching the recovered original ASM or regressing
the cold boot into Training?

## Baseline diagnosis

Pristine media: SCUS-94288. Hash-pinned state:
`purple_seed_levels.movie.sav`, SHA-256
`a78f53720ed38902f38c4a6c7b35406b30013dba51a41d791d66df56a4df5d79`;
movie SHA-256
`49248c436682688146ed2994be1170739b3f0359a5b7e0c1a55aa60762fdf73f`.
At frame 133143 / cycle 75385487968,
the active seed was `0x800a0014`, record `0x80094ac4`, color byte
`0x80094ad2`, override `0x80094ad3`.

Controlled calls to retail `0x8005bdbc` showed count 4 selecting purple row 3
(type 6, extra `0x3000`) and count 5 spilling into yellow row 0 (type 14,
extra 0). This causally confirmed the retail `color*4 + count - 1` limit.

## Selector experiment

The MOD selector was injected into the validated state and `plant_spawn` was called
six times against the purple seed. Resulting slot tags/types/extras were:

| Tier | Tag | Type | Extra |
|---:|---:|---:|---:|
| 1 | 1 | 6 | `0x4000` |
| 2 | 2 | 6 | `0x4000` |
| 3 | 3 | 6 | `0x2000` |
| 4 | 4 | 6 | `0x2000` |
| 5 | 5 | 6 | `0x1000` |
| 6 | 6 | 6 | `0x3000` |

This confirms the six selector outputs. A direct type-6 handler call cannot serve as
a complete seed proof because that handler tail-jumps within the plant walker; the
operator's later real-seed test remains the behavioral authority.

## Cold-boot ownership diagnosis

Control builds established:

- ALLMODS without `six_seed_levels`: Training PASS.
- Token-only ALLMODS with all six appended tokens: Training PASS.
- Therefore the asset append was not the divergence source.

Read attribution showed the original high candidates being consumed as boot data,
including readers around `0x8006e188`, `0x8006ea00`, and `0x8006eaf8`. Later binary
isolation found additional hazards invisible to CPU-read counts: `0x8007f358` was
zero at frame 6900 after being cleared, and writing `0x8007fc88` changed cold-boot
behavior. Repurposing contact dispatch words `0x8001b5fc/0x8001b604` also regressed
the boot. A later operator test found continuous high-pitched audio with code placed
at `0x80080e94`; that range was removed as an audio/DMA ownership hazard and the
router was repacked into the surviving `0x8007fxxx` fragments.

## Final cold-boot result

Command:

`python3 tools/run_ps1_scenario.py tools/scenarios/duckstation/training_six_purple_tokens.yaml --output-dir /tmp/abl_training_six_purple_pass`

Result: PASS. At movie frame 6900:

- scene ID `0x11` (Training);
- runtime type-0x3f pointer `0x80121790` and count 73;
- appended entries 67 and 72 were kind `0x2c` at X `300` and `1000`;
- selector, native counter, type-6 route, and custom contact-sync words were resident.

An operator visual test then exposed an asset-side omission: Training init at
`0x800B3E98` added the tutorial `+8000 Y` hide delta to all ten kind-`0x2c`
records while its pointer array could reveal only four. The six appended records
were therefore loaded and uncollected but invisible. The resolved overlay now
keeps the four retail records gated and bypasses the hide for appended indices
67..72; the original recovered ASM remains untouched.

The corrected coordinates form a two-row cluster at X `300/650/1000`, Z
`-100/350`. Cold-boot capture `/tmp/abl_training_token_candidate2.png`
(SHA-256 `71188b6bec42079755f04fd84b5abd5607f453e90b098d6b4d592a76c22dd2bd`)
shows all six purple/gold token sprites in the opening view beside Flik.

## Audio regression confirmation

The first six-level build used `0x80080E94..0x80080EB0` as a speculative zero
range. The operator's continuous high-pitched tone report was treated as causal
evidence of non-CPU audio/DMA ownership. The router was repacked entirely into
declared `0x8007Fxxx` fragments; the rebuilt disc's bytes at
`0x80080E94..0x80080EB4` now exactly match pristine.

An isolated cold-boot SPU A/B replay to movie frame 5200 compared the final disc
against an otherwise identical control built without `six_seed_levels`. Both
produced the exact same complete 350-event SPU stream (JSON SHA-256
`a0a6692d29a64bcd3aa940a06f09aa90d81dfa5ac6b8c1ad6f3d22c89c806aee`),
with all 24 voices ended and no active samples. The declarative regression is
`tools/scenarios/duckstation/allmods_audio_regression.yaml`.

Movie SHA-256:
`5cff3e9e28af7964cec0c3b5190cca70b960ad3c0cff2bd1f5c741579def0c3c`.
DuckStation fork revision:
`fe0cca16b85e09a304cfde3c39669ce8c0adb8f5`; binary SHA-256:
`bd55f9db25fe169b0f98b9bd94baaf30e33be8a0e3174aff0719bf4ced5a9bcb`.
Every scenario instance used a fresh absolute `/tmp/abl-ps1-scenario-*` config,
dedicated loopback port/token, verified SCUS-94288 media, and PID-scoped cleanup.
