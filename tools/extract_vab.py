#!/usr/bin/env python3
"""PS1 libsnd VAB (.VH + .VB) -> per-sample WAV extractor.  (GAP-0005)

Reproducible, committable replacement for the in-session VAB parser.  Splits each
VAB bank into its constituent VAG samples and decodes the SPU-ADPCM (VAG) bodies to
16-bit mono PCM WAVs, matching the known-good layout under ``extracted/audio_vab``.

VAB layout (PS1 libsnd ``VabHdr`` / ``ProgAtr`` / ``VagAtr``), verified against the
bytes of all 21 ABL banks:

  .VH  (header bank)
    +0x00  char  form[4]      magic 'pBAV'  (i.e. "VABp" little-endian)
    +0x04  s32   version
    +0x08  s32   vab id
    +0x0C  s32   total file size (VH + VB)
    +0x10  u16   reserved
    +0x12  u16   #programs (ps)
    +0x14  u16   #tones    (ts)
    +0x16  u16   #vags     (vs)
    +0x18  u8    master volume
    +0x19  u8    master pan
    +0x1A  u8    bank attr1
    +0x1B  u8    bank attr2
    +0x1C  u32   reserved
    +0x20  128 x 16-byte program attributes (ProgAtr), fixed 128 slots
    ...    ps x 16 x 32-byte tone attributes (VagAtr), 16 tones per *present* program
    ...    256 x u16 VAG size table; each entry is (sample_byte_size >> 3)

  .VB  (body bank)
    Concatenated VAG blocks, in order, sized by the VAG size table (entry << 3).
    The size table partitions the VB body sequentially with no gaps (validated:
    sum(sizes<<3) == len(.VB) for every ABL bank).

VAG / SPU-ADPCM decode: each 16-byte frame = 1 (shift,filter) byte + 1 flag byte +
14 data bytes (28 nibbles -> 28 PCM samples) using the 5 standard SPU filter
coefficient pairs and a per-block running 2-tap predictor.

Output: one directory per bank named ``<PARENTDIR>_<STEM>`` (e.g. ``SFX_GLOBAL``,
``LEVEL01_LEVEL1A``), each containing ``vag01.wav`` .. ``vagNN.wav`` (1-indexed,
zero-padded to 2 digits), PCM s16 mono @ 44100 Hz (the fixed rate the known-good set
used; VAB tone tables carry no reliable per-sample sample-rate, only MIDI center
note / pitch-bend used at playback time).

Pure stdlib (struct, wave).  Paths come from --root/--out or tools/_env.ABL_DIR; no
hardcoded host paths (GAP-0003 portability rule).
"""
import argparse
import glob
import os
import struct
import sys
import wave

try:
    from _env import ABL_DIR
except ImportError:  # allow running from outside tools/
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _env import ABL_DIR

VAB_MAGIC = b"pBAV"          # libsnd 'VABp' as stored
VAB_HDR_SIZE = 0x20          # 32-byte VabHdr
PROG_TABLE_SIZE = 128 * 16   # 128 fixed ProgAtr slots
TONE_ATTR_SIZE = 16 * 32     # 16 VagAtr * 32 bytes, per present program
VAG_TABLE_ENTRIES = 256      # u16 size table
ADPCM_FRAME = 16             # bytes per SPU-ADPCM frame
ADPCM_SAMPLES = 28           # PCM samples per frame
DEFAULT_RATE = 44100         # matches extracted/audio_vab known-good WAVs

# Standard PS1 SPU-ADPCM (VAG) filter coefficients (4.8 fixed-point, /64).
SPU_FILTERS = (
    (0, 0),
    (60, 0),
    (115, -52),
    (98, -55),
    (122, -60),
)


def _clamp16(x):
    if x > 32767:
        return 32767
    if x < -32768:
        return -32768
    return x


def decode_vag(block):
    """Decode one VAG / SPU-ADPCM body (bytes) -> list[int] of 16-bit PCM samples.

    Honors the per-frame loop/end flag (flag byte == 7 marks end-of-sample).
    """
    out = []
    hist1 = 0
    hist2 = 0
    n = len(block) - (len(block) % ADPCM_FRAME)
    for off in range(0, n, ADPCM_FRAME):
        shift_filter = block[off]
        flag = block[off + 1]
        shift = shift_filter & 0x0F
        flt = (shift_filter >> 4) & 0x0F
        if flt >= len(SPU_FILTERS):
            flt = 0
        f0, f1 = SPU_FILTERS[flt]
        if shift > 12:
            shift = 9  # SPU clamps invalid shift to 9 (treats as quiet)
        for i in range(14):
            byte = block[off + 2 + i]
            for nib in (byte & 0x0F, (byte >> 4) & 0x0F):
                s = nib << 12          # nibble into bits 15..12 (sign-extends)
                if s & 0x8000:
                    s -= 0x10000
                s >>= shift
                pred = s + ((hist1 * f0 + hist2 * f1) >> 6)
                pred = _clamp16(pred)
                out.append(pred)
                hist2 = hist1
                hist1 = pred
        if flag == 7:                  # end marker: stop after this frame
            break
    return out


def read_vag_sizes(vh):
    """Parse a .VH header (bytes) -> (list[int] vag byte-sizes, header dict)."""
    if vh[0:4] != VAB_MAGIC:
        raise ValueError("not a VAB header (bad magic %r)" % vh[0:4])
    version, vab_id, fsize = struct.unpack_from("<iii", vh, 0x04)
    reserved, ps, ts, vs = struct.unpack_from("<HHHH", vh, 0x10)
    tbl_off = VAB_HDR_SIZE + PROG_TABLE_SIZE + ps * TONE_ATTR_SIZE
    raw = struct.unpack_from("<%dH" % VAG_TABLE_ENTRIES, vh, tbl_off)
    sizes = [s << 3 for s in raw if s]   # nonzero entries are the present VAGs
    info = {
        "version": version, "vab_id": vab_id, "fsize": fsize,
        "programs": ps, "tones": ts, "vags": vs, "table_off": tbl_off,
    }
    return sizes, info


def split_vb(vb, sizes):
    """Partition the .VB body (bytes) into VAG blocks by the size list."""
    blocks = []
    off = 0
    for sz in sizes:
        blocks.append(vb[off:off + sz])
        off += sz
    return blocks, off


def write_wav(path, samples, rate=DEFAULT_RATE):
    w = wave.open(path, "wb")
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(struct.pack("<%dh" % len(samples), *samples))
    w.close()


def bank_dirname(vh_path):
    """<PARENTDIR>_<STEM>, e.g. .../SFX/GLOBAL.VH -> 'SFX_GLOBAL'."""
    stem = os.path.splitext(os.path.basename(vh_path))[0]
    parent = os.path.basename(os.path.dirname(os.path.abspath(vh_path)))
    return "%s_%s" % (parent, stem)


def find_vabs(sfx_root):
    """Find every .VH that has a sibling .VB under sfx_root, sorted."""
    out = []
    for vh in sorted(glob.glob(os.path.join(sfx_root, "**", "*.VH"), recursive=True)):
        vb = vh[:-3] + ".VB"
        if os.path.exists(vb):
            out.append((vh, vb))
    return out


def extract_bank(vh_path, vb_path, out_dir, rate=DEFAULT_RATE):
    """Extract one VAB bank -> vagNN.wav files in out_dir.  Returns count written."""
    vh = open(vh_path, "rb").read()
    vb = open(vb_path, "rb").read()
    sizes, info = read_vag_sizes(vh)
    total = sum(sizes)
    if total != len(vb):
        print("  WARN %s: size-table sum %d != .VB %d (bank may be malformed)"
              % (os.path.basename(vh_path), total, len(vb)), file=sys.stderr)
    blocks, _ = split_vb(vb, sizes)
    os.makedirs(out_dir, exist_ok=True)
    for i, blk in enumerate(blocks, start=1):
        samples = decode_vag(blk)
        write_wav(os.path.join(out_dir, "vag%02d.wav" % i), samples, rate)
    return len(blocks)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=None,
                    help="dir to search for *.VH/*.VB (default: <ABL_DIR>/REBUILD/files)")
    ap.add_argument("--out", default=None,
                    help="output dir (default: <ABL_DIR>/extracted/audio_vab)")
    ap.add_argument("--rate", type=int, default=DEFAULT_RATE,
                    help="WAV sample rate in Hz (default: %d)" % DEFAULT_RATE)
    ap.add_argument("--vh", default=None,
                    help="extract a single .VH (its sibling .VB is used)")
    args = ap.parse_args(argv)

    root = args.root or os.path.join(ABL_DIR, "REBUILD", "files")
    out = args.out or os.path.join(ABL_DIR, "extracted", "audio_vab")

    if args.vh:
        vb = args.vh[:-3] + ".VB"
        if not os.path.exists(vb):
            ap.error("no sibling .VB for %s" % args.vh)
        banks = [(args.vh, vb)]
    else:
        banks = find_vabs(root)

    if not banks:
        ap.error("no VAB banks (.VH + .VB) found under %s" % root)

    total_wavs = 0
    for vh_path, vb_path in banks:
        name = bank_dirname(vh_path)
        bank_out = os.path.join(out, name)
        n = extract_bank(vh_path, vb_path, bank_out, rate=args.rate)
        total_wavs += n
        print("%-22s %3d WAVs  <- %s" % (name, n, os.path.relpath(vh_path, root)))
    print("Done: %d banks, %d WAVs -> %s" % (len(banks), total_wavs, out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
