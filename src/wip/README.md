# WIP committable-C (logic/structure-matched, not yet byte-exact)

This remaining clean-room C reimplementation matches the original in
**logic/structure** but is not yet byte-exact. It is preserved as decompilation
reference; the byte-exact match currently lives in hand assembly
(`asm/hand_written/`, gitignored) plus the Canon function note.

- `80059e44_contact_alloc.c` — structure + length matched (167/167 words); ~69 words of
  register-allocation divergence remain.
- `800593e8_contact_scatter_component.c` — all six table-A selector semantics are
  decoded; the compiler emits a 332-byte text body versus the retail 340-byte body
  (plus the correctly identified 24-byte jump table at `0x8001b778`).

`music_start` was promoted to `src/main/8004699c_music_start.c` after modelling its
clean-room-observed 24-byte outgoing-argument reservation explicitly; GCC 2.7.2 now
reproduces all 292 bytes under the `cleanroom_prototyped` declaration profile.
