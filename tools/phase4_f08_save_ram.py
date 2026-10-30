#!/usr/bin/env python3
"""Extract the 2 MiB guest RAM image from a DuckStation save state, OFFLINE.

WHY THIS EXISTS. F11 located its progress counter with a save diff, but it did that
through a live emulator (`--port 23741`). This does the same thing with no emulator
at all -- it parses the `.sav` container directly. That matters whenever the fork is
mid-rebuild and a live instance would either be unavailable or, worse, silently a
different binary from the one the evidence was taken on.

FINDING THE RAM. The decompressed save blob is a serialized section stream, not a
memory dump, so RAM does not start at a fixed offset -- it moves with whatever is
serialized ahead of it. Rather than hardcode an offset that would rot on the next
save-state version bump, this LOCATES the RAM by matching the game's own resident
executable image inside the blob, then CROSS-CHECKS with a second anchor taken from
a distant part of the same executable. Two independent anchors must agree on the
same base or the tool refuses. An assumed offset that silently slides by a few bytes
would corrupt every address in the diff, which is exactly the class of error this
repository keeps paying for.

The EXE (SCUS_942.88) has a 2048-byte header; its load address is in that header at
+0x18 and the image follows. So EXE image byte i lives at RAM address
`load_addr + i`, and blob offset `ram_base + (load_addr + i - 0x80000000)`.

    tools/phase4_f08_save_ram.py level_08.sav --out /tmp/ram.bin
    tools/phase4_f08_save_ram.py --verify-all          # all five F08 fixtures
"""

from __future__ import annotations

import argparse
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXE = ROOT / "REBUILD" / "files" / "SCUS_942.88"
RAM_SIZE = 2 * 1024 * 1024
RAM_BASE_ADDR = 0x80000000
HEADER = "<II128s32sIIIIIIIIIIII"
MAGIC = 0x43435544

# Two anchors, deliberately far apart in the executable image. If a wrong match
# were found for one, the other would disagree and the tool fails instead of
# reporting addresses that are all off by a constant.
ANCHOR_LEN = 512


class SaveError(RuntimeError):
    pass


def read_header(b: bytes):
    if len(b) < struct.calcsize(HEADER):
        raise SaveError("file too small to hold a save-state header")
    f = struct.unpack_from(HEADER, b, 0)
    (magic, version, title, serial, _mpl, _omp, _msi,
     _sct, _sw, _sh, _scs, _os, dct, dcs, dus, od) = f
    if magic != MAGIC:
        raise SaveError("not a DuckStation save state (magic %08x)" % magic)
    return {"version": version,
            "serial": serial.split(b"\0")[0].decode("ascii", "replace"),
            "data_compression": dct, "data_compressed_size": dcs,
            "data_uncompressed_size": dus, "offset_to_data": od}


def decompress(b: bytes, h) -> bytes:
    blob = b[h["offset_to_data"]:h["offset_to_data"] + h["data_compressed_size"]]
    ctype = h["data_compression"]
    if ctype == 0:
        out = blob
    elif ctype == 1:
        import zlib
        out = zlib.decompress(blob)
    elif ctype == 2:
        # The `zstandard` module is not installed here; the CLI is. Use it rather
        # than adding a dependency for a read-only analysis tool.
        p = subprocess.run(["zstd", "-d", "-c", "-"], input=blob,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if p.returncode != 0:
            raise SaveError("zstd failed: %s" % p.stderr.decode()[:200])
        out = p.stdout
    elif ctype == 3:
        import lzma
        out = lzma.decompress(blob)
    else:
        raise SaveError("unknown compression type %d" % ctype)
    if len(out) != h["data_uncompressed_size"]:
        raise SaveError("decompressed %d bytes, header says %d"
                        % (len(out), h["data_uncompressed_size"]))
    return out


def exe_anchors():
    """Two distant slices of the resident executable, with their RAM addresses."""
    raw = EXE.read_bytes()
    load_addr = struct.unpack_from("<I", raw, 0x18)[0]
    image = raw[2048:]
    if len(image) < 0x40000:
        raise SaveError("executable image unexpectedly small (%d)" % len(image))

    def pick(off):
        # Skip runs of constant bytes -- a padding slice would match everywhere.
        for probe in range(off, min(off + 0x8000, len(image) - ANCHOR_LEN), 16):
            s = image[probe:probe + ANCHOR_LEN]
            if len(set(s)) > 32:
                return probe, s
        raise SaveError("no distinctive anchor near offset 0x%x" % off)

    o1, a1 = pick(0x1000)
    o2, a2 = pick(len(image) - 0x10000)
    return load_addr, [(load_addr + o1, a1), (load_addr + o2, a2)]


def locate_ram(blob: bytes):
    """Return (ram_base_offset, details). Requires both anchors to agree."""
    load_addr, anchors = exe_anchors()
    bases = []
    for addr, pat in anchors:
        hits = []
        start = 0
        while True:
            i = blob.find(pat, start)
            if i < 0:
                break
            hits.append(i)
            start = i + 1
            if len(hits) > 8:
                break
        if not hits:
            raise SaveError("anchor for RAM 0x%08X not found in the save blob -- "
                            "the state may be from a different build" % addr)
        for h in hits:
            bases.append((h - (addr - RAM_BASE_ADDR), addr, h))

    counts = {}
    for base, _addr, _h in bases:
        counts[base] = counts.get(base, 0) + 1
    agreed = [b for b, n in counts.items() if n >= 2]
    if len(agreed) != 1:
        raise SaveError("anchors did not agree on a single RAM base (candidates %s). "
                        "Refusing rather than picking one: a wrong base shifts every "
                        "address in the diff by a constant." % sorted(counts.items()))
    base = agreed[0]
    if base < 0 or base + RAM_SIZE > len(blob):
        raise SaveError("derived RAM base %d does not fit a 2 MiB image in a %d-byte "
                        "blob" % (base, len(blob)))
    return base, {"exe_load_addr": "0x%08X" % load_addr,
                  "anchors_agreed": len(agreed) == 1,
                  "anchor_addrs": ["0x%08X" % a for a, _ in anchors]}


def extract(path: Path):
    b = path.read_bytes()
    h = read_header(b)
    blob = decompress(b, h)
    base, det = locate_ram(blob)
    ram = blob[base:base + RAM_SIZE]
    return ram, {"file": path.name, "version": h["version"], "serial": h["serial"],
                 "blob_size": len(blob), "ram_base_offset": base, **det}


def read_u32(ram: bytes, addr: int) -> int:
    off = addr - RAM_BASE_ADDR
    if not (0 <= off <= RAM_SIZE - 4):
        raise SaveError("address 0x%08X outside main RAM" % addr)
    return struct.unpack_from("<I", ram, off)[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("sav", nargs="?", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--verify-all", action="store_true")
    a = ap.parse_args()

    targets = ([ROOT / n for n in ("level_08.sav", "LEVEL08_DIM.sav",
                                   "LEVEL08_MANNY.sav", "LEVEL08_ROSIE.sav",
                                   "LEVEL08_TUCKROLL.sav")]
               if a.verify_all else [a.sav])
    if not targets or targets[0] is None:
        ap.error("give a .sav or --verify-all")

    rc = 0
    for t in targets:
        try:
            ram, info = extract(t)
            # The scene id is a known resident u32; print it as a sanity signal.
            scene = read_u32(ram, 0x80082504)
            print("%-24s v%d %s  ram@%d  scene_id=%d"
                  % (info["file"], info["version"], info["serial"],
                     info["ram_base_offset"], scene))
            if a.out:
                a.out.write_bytes(ram)
                print("   wrote %d bytes to %s" % (len(ram), a.out))
        except SaveError as e:
            print("%-24s FAILED: %s" % (t.name, e))
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
