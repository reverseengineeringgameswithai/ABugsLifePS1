# MOD: Training six-level purple seed ladder

## Intended behavior

ALLMODS Training appends six retail purple seed-power tokens near Flik. Collecting
them leaves the native three-bit token counter intact and gives the purple seed lane
this logical plant ladder:

1. Blue / Super
2. Black / Blackberry
3. Green / Homing
4. White / Whiteberry
5. Purple / Mega-homing
6. Golden

The Whiteberry is a MOD-private white, red-class three-way spread. Its primary
uses the stock ballistic launch; two additional records use quarter-perpendicular
X/Z offsets. Blackberry remains the single fast shot at 2x velocity/4x gravity.

## Implementation boundary

- `asm/hand_written/8005bdbc_plant_spawn.s` remains untouched.
- `mod/mods/six_seed_levels.asm` is the separate resolved MOD patch.
- Retail purple plant selection is four rows. The MOD maps logical tiers 1..6 to
  row offsets `0,0,1,1,2,3` using `((tier - 1) * 5) >> 3`.
- Plant slot `+0x2a` carries logical tier 1..6. Type-6 maturity tags only tiers 2/4;
  the native Blue/Green contact handlers still run before the shared contact sync
  converts those tags to private effective selectors 5/6.
- The native selector at `0x800a6597` is normalized to red 0 for Black/White so
  retail five-column tables cannot be indexed out of range.
- Token counting and token descriptor reskin instructions remain byte-for-byte
  retail. Six tiers need no counter cave; the retail three-bit counter already
  represents 1..6.

## Training asset stage

`tools/training_purple_tokens.py` clones retail Training entry 58 (kind `0x2c`)
after the word/tutorial stages. It requires the incoming type-0x3f count to be 67
and appends indices 67..72 at:

- `(300, -50, -100)`
- `(650, -50, -100)`
- `(1000, -50, -100)`
- `(300, -50, 350)`
- `(650, -50, 350)`
- `(1000, -50, 350)`

The same asset stage patches only the resolved Training overlay block
`0x800B3E98..0x800B3EC8`. Retail hides every kind-`0x2c` record by `+8000 Y`
but caches only four pointers for the step-13 reveal; that made appended tokens
permanently invisible. The replacement preserves cache/hide behavior for indices
below 67 and bypasses it for appended indices 67..72, so the six test tokens are
visible immediately without altering the four retail tutorial tokens.

## Cave ownership findings

Cold-boot tracing invalidated several static `candidate_free` assumptions. The
`0x800819xx/0x80081bxx` candidates are boot-read data, `0x8007f358` is cleared after
EXE load, `0x8007fc88` changes boot behavior through a non-CPU consumer, and contact
dispatch-table entries `0x8001b5fc/0x8001b604` cannot be repurposed without a boot
regression. A first release also placed routing code at `0x80080e94`; operator testing
reported a continuous high-pitched audio regression. The range is now byte-for-byte
pristine and classified as audio/DMA-owned. The final router is packed only into
surviving `0x8007fxxx` fragments.

## Validation

- Layout declarations and generated output: valid for
  `blackberry,golddrop,grain_hud,six_seed_levels`.
- Consolidated build embedded all 13 staged files.
- Final Training DAT SHA-1: `2e581261b3bd2c640ffde5fbdb4a64641092d776`.
- Final Training overlay SHA-1: `55b0b6de1bb95f32c2eb086712b558df548c2c7f`.
- Final disc BIN SHA-256: `fea978e542c7b7d3867bb73752ddd1ce857b08e399d2828559de49037d3fc835`.
- Cold-boot scenario: `tools/scenarios/duckstation/training_six_purple_tokens.yaml`.
- Audio regression scenario: `tools/scenarios/duckstation/allmods_audio_regression.yaml`.
- Blackberry arc scenario: `tools/scenarios/duckstation/blackberry_ballistic_speed.yaml`.
- White spread/counter scenario: `tools/scenarios/duckstation/whiteberry_spread_balanced.yaml`.
- Cold-boot visual capture: `/tmp/abl_training_token_candidate2.png`, SHA-256
  `71188b6bec42079755f04fd84b5abd5607f453e90b098d6b4d592a76c22dd2bd`.
- Actual jump-on-seed interaction remains an operator test item, as requested.
