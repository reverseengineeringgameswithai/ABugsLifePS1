#!/usr/bin/env python3
"""tools/vab_audio.py -- parse ABL SFX banks (PsyQ VAB: .VH header + .VB body),
decode SPU-ADPCM samples to WAV (preview), and splice a replacement sample in place.

A VAB bank = a .VH header (programs/tones + a 256-entry VAG size table) and a .VB body
(concatenated SPU-ADPCM samples, 16-byte blocks). ABL's global SFX bank is SFX/GLOBAL.VAB
(43 samples); there are per-level banks too. Sample K occupies a contiguous span of the VB
whose byte size is VH's size-table[K] (stored /8). Size-preserving replacement overwrites a
sample's VB span (SPU stops at the block's end-flag, so trailing pad is never played) → no
VH edits, no reflow, disc-LBA-safe (same philosophy as the XA/FMV tools).
"""
import struct, subprocess, wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PSXAVENC = ROOT / "psxavenc" / "build" / "psxavenc"
FILES = ROOT / "REBUILD" / "files"
SFX_DIR = FILES / "SFX"

_F0 = [0, 60, 115, 98, 122]        # SPU ADPCM predictor coefficients (/64)
_F1 = [0, 0, -52, -55, -60]


def parse_vh(vh_bytes):
    """Return dict(programs, tones, vags, sizes[1..vags], offsets[]) for a VAB header."""
    magic = vh_bytes[0:4]
    if magic != b"pBAV":
        raise SystemExit(f"not a VAB header (magic {magic!r})")
    progs, tones, vags = struct.unpack("<HHH", vh_bytes[18:24])
    tab_off = len(vh_bytes) - 512                      # 256 x u16 VAG size table (last 512 B)
    tab = struct.unpack("<256H", vh_bytes[tab_off:tab_off + 512])
    sizes = [t * 8 for t in tab]                       # entry K = size of VAG K, in bytes
    offs, acc = [], 0
    for k in range(1, vags + 1):                        # VAGs are 1-indexed in tone headers
        offs.append(acc); acc += sizes[k]
    return dict(programs=progs, tones=tones, vags=vags,
                sizes=sizes, offsets=offs, tab_off=tab_off)


def bank_vh_path(name):
    """Resolve a bank name/stem to its .VH path. GLOBAL is in SFX/; per-level banks live under
    LEVELnn/ — search REBUILD/files for <name>.VH. A full path is used verbatim."""
    if Path(name).suffix:
        return Path(name)
    if name.upper() == "GLOBAL":
        return SFX_DIR / "GLOBAL.VH"
    hits = list(FILES.glob(f"**/{name}.VH"))
    if not hits:
        raise SystemExit(f"bank {name}.VH not found under {FILES}")
    return hits[0]


def load_bank(name="GLOBAL"):
    """Load a bank by name/stem (GLOBAL or a per-level bank like LEVEL1A). Returns (vh, vb, meta)."""
    vhp = bank_vh_path(name)
    vbp = vhp.with_suffix(".VB")
    vh, vb = vhp.read_bytes(), vbp.read_bytes()
    return vh, vb, parse_vh(vh)


def sample_span(meta, k):
    """(offset, size) of VAG index k (1-based) in the VB."""
    if not 1 <= k <= meta["vags"]:
        raise SystemExit(f"vag {k} out of range 1..{meta['vags']}")
    return meta["offsets"][k - 1], meta["sizes"][k]


def vag_rates(vh_bytes, meta):
    """Map VAG index -> in-game SPU playback rate (Hz), from the tone headers: a tone plays its
    sample at 44100 * 2^((play_note - center_note)/12). ABL SFX are ~11-16 kHz (NOT 44 kHz) — this
    is the rate to encode/preview at so a replacement isn't pitch-shifted."""
    tb = 0x820                                          # ToneAtr array
    out = {}
    for slot in range((len(vh_bytes) - tb - 512) // 32):
        th = vh_bytes[tb + slot * 32: tb + slot * 32 + 32]
        if len(th) < 32:
            break
        vag = struct.unpack("<H", th[0x16:0x18])[0]
        if not vag:
            continue
        center, play = th[4], th[6]                     # center note, min(play) note
        rate = round(44100 * (2 ** ((play - center) / 12)))
        if 4000 <= rate <= 44100:                       # keep plausible rates (skip junk tones)
            out.setdefault(vag, rate)
    return out


def sample_rate(vh_bytes, meta, k, default=16000):
    """Best-guess in-game playback rate (Hz) for VAG k (from its tone), else `default`."""
    return vag_rates(vh_bytes, meta).get(k, default)


def decode_adpcm(data):
    """Decode SPU-ADPCM bytes (16-byte blocks) → list[int16 PCM]. Stops at end-flag."""
    out, s1, s2 = [], 0, 0
    for b in range(0, len(data) - 15, 16):
        blk = data[b:b + 16]
        shift = blk[0] & 0x0F
        filt = (blk[0] >> 4) & 0x07
        flags = blk[1]
        f0 = _F0[filt] if filt < len(_F0) else 0
        f1 = _F1[filt] if filt < len(_F1) else 0
        if shift > 12:
            shift = 9
        for i in range(14):
            byte = blk[2 + i]
            for nib in (byte & 0x0F, byte >> 4):
                s = nib - 16 if nib > 7 else nib       # sign-extend 4-bit
                s = (s << 12) >> shift
                s = s + (s1 * f0 + s2 * f1) // 64
                s = max(-32768, min(32767, s))
                out.append(s); s2 = s1; s1 = s
        if flags & 0x01:                                # end block
            break
    return out


def write_wav(pcm, path, rate=44100):
    w = wave.open(str(path), "wb")
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(struct.pack("<%dh" % len(pcm), *pcm))
    w.close()


def extract_wav(name, k, out_wav, rate=44100):
    """Decode VAG k of bank `name` to a WAV (preview)."""
    vh, vb, meta = load_bank(name)
    off, size = sample_span(meta, k)
    pcm = decode_adpcm(vb[off:off + size])
    write_wav(pcm, out_wav, rate)
    return len(pcm), size


def encode_vag_body(input_media, rate, tmp_dir):
    """Transcode any audio → mono WAV @ rate → SPU-ADPCM via psxavenc, return the raw
    ADPCM body (VAG file minus its 48-byte header)."""
    tmp_dir = Path(tmp_dir)
    wav = tmp_dir / "in.wav"; vag = tmp_dir / "out.vag"
    subprocess.run(["ffmpeg", "-y", "-i", str(input_media), "-ac", "1", "-ar", str(rate),
                    "-c:a", "pcm_s16le", str(wav)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([str(PSXAVENC), "-t", "vag", "-f", str(rate), "-L", "-a", "16",
                    str(wav), str(vag)], check=True,          # -L: end-flag (one-shot SFX)
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    body = vag.read_bytes()[48:]                        # strip the .VAG header
    return body


def splice_sample(vb_bytes, meta, k, new_body):
    """Size-preserving overwrite of VAG k's VB span with new_body (SPU-ADPCM). Truncates if
    longer (forcing an end-flag on the last kept block); zero-pads if shorter (SPU halts at
    the body's own end-flag, so the pad never plays). Returns a new VB bytes object."""
    off, size = sample_span(meta, k)
    body = bytearray(new_body)
    if len(body) > size:                                # truncate to the byte budget
        body = body[:size - (size % 16)]
        if len(body) >= 16:
            body[-15] |= 0x01                           # flags byte of last block: end
    body += b"\x00" * (size - len(body))                # zero-pad to the exact original size
    out = bytearray(vb_bytes)
    out[off:off + size] = body
    return bytes(out)


if __name__ == "__main__":
    import argparse, tempfile
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("list"); lp.add_argument("--bank", default="GLOBAL")
    ep = sub.add_parser("extract"); ep.add_argument("--bank", default="GLOBAL")
    ep.add_argument("--index", type=int, required=True); ep.add_argument("-o", required=True)
    ep.add_argument("--rate", type=int, default=44100)
    a = ap.parse_args()
    if a.cmd == "list":
        vh, vb, meta = load_bank(a.bank)
        print(f"{a.bank}: {meta['vags']} samples, {meta['programs']} programs, VB {len(vb)} B")
        for k in range(1, meta["vags"] + 1):
            off, size = sample_span(meta, k)
            print(f"  #{k:2}  off={off:6}  size={size:6}  (~{size//16*28/44100:.2f}s)")
    else:
        n, size = extract_wav(a.bank, a.index, a.o, a.rate)
        print(f"[ok] VAG {a.index}: {n} samples ({size} B) -> {a.o}")
