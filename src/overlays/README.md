# src/overlays - byte-matched overlay C (docs/SUBSTRATE.md)

This directory contains 15 byte-matched clean-room C functions across the
level overlays. `tools/build_overlay.py` rebuilds each touched blob and requires
its original SHA-1. Overlay identities are part of the key because different
files reuse the same Region-A/Region-B virtual addresses.

The authoritative semantic-name store is `analysis/overlay_symbols.json`;
all 158 tracked overlay code functions are named.
