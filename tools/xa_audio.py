#!/usr/bin/env python3
"""CD-XA ADPCM codec for A Bug's Life (PS1) streamed music.  (GAP-0031 / B5)

Decode + ENCODE the XA-ADPCM audio payload of a CD-XA Form-2 sector, plus an
in-place channel payload swap that replaces one interleaved channel of a real
``BUGXASTR/AUDIOn.XA`` file while preserving every sector subheader, EDC and
padding byte (so file size / disc LBA / channel layout / loop flags are
untouched).

Why in-place swap (not re-multiplex): AUDIO1.XA carries 8 stereo music tracks
interleaved at sector stride 8 (channel 0 = sectors 0,8,16,..). The original
loop is driven by the XA subheader EOF bit (submode 0x80) on each channel's
last audio sector. Swapping only the 2304-byte ADPCM payload keeps that control
structure byte-exact, so the game loops the new music exactly as it looped the
original.

XA-ADPCM sector layout (this file, "2336 mode" = no 16-byte sync/header):
    [0x000:0x008]  subheader  (file, channel, submode, coding) x2
    [0x008:0x918]  18 sound groups x 128 bytes = 2304 bytes ADPCM payload
    [0x918:0x92c]  20 bytes reserved/trailing
    [0x92c:0x920]  4 bytes EDC (0 for Form-2)
                   (8 + 2304 + 20 + 4 = 2336)

Sound group (128 bytes), 4-bit / 8 sound units x 28 samples (37.8 kHz stereo):
    bytes 0..15  header: per-unit parameter byte stored twice for resilience.
                 Verified layout (locked empirically vs jpsxdec, see --verify):
                   params[u] for u in 0..3  at header[4+u]  (copy at header[0+u])
                   params[u] for u in 4..7  at header[12+(u-4)] (copy at header[8..11])
                 param byte: low nibble = shift (0..12), high nibble = filter (0..3)
    bytes 16..127 data: 28 data-words x 4 bytes. word i (offset 16+4*i), byte b:
                   low  nibble -> unit b   sample i
                   high nibble -> unit b+4 sample i
    Stereo: even units (0,2,4,6) = LEFT, odd units (1,3,5,7) = RIGHT.

ADPCM math (standard SPU/XA 2-tap predictor, 4 XA filters):
    s = signext4(nibble) << 12; s >>= shift
    s += (K0[f]*old1 + K1[f]*old2) >> 6 ; clamp to int16; old2=old1; old1=s

Pure stdlib (struct, wave). Round-trip validated against jpsxdec (--verify).
"""
import argparse
import os
import struct
import sys
import wave

SECTOR = 2336
PAYLOAD_OFF = 8
GROUPS = 18
GROUP = 128
UNITS = 8
SAMPLES = 28

# XA filter coefficients (scaled by 64). XA uses 4 filters (0..3).
K0 = [0, 60, 115, 98]
K1 = [0, 0, -52, -55]


def _clamp16(x):
    if x > 32767:
        return 32767
    if x < -32768:
        return -32768
    return x


def _signext4(n):
    return n - 16 if n >= 8 else n


# ---------------------------------------------------------------- decode

def decode_group(buf, st):
    """Decode one 128-byte sound group -> (left[112], right[112]) int lists.

    st = [oldL1, oldL2, oldR1, oldR2] persistent predictor state, mutated.
    """
    params = [buf[4 + u] if u < 4 else buf[12 + (u - 4)] for u in range(UNITS)]
    out = [[], []]  # left, right
    for u in range(UNITS):
        p = params[u]
        shift = p & 0x0F
        filt = (p >> 4) & 0x03
        if shift > 12:
            shift = 9  # PS1 hardware clamps invalid shift to 9
        ch = u & 1  # even -> left(0), odd -> right(1)
        o1 = st[0] if ch == 0 else st[2]
        o2 = st[1] if ch == 0 else st[3]
        k0, k1 = K0[filt], K1[filt]
        col = u >> 1  # which nibble column pair; byte index = (u&1)? handled below
        for i in range(SAMPLES):
            word = buf[16 + 4 * i:16 + 4 * i + 4]
            b = word[u & 3]
            nib = (b >> 4) if (u >= 4) else (b & 0x0F)
            s = _signext4(nib) << 12
            s >>= shift
            s += (k0 * o1 + k1 * o2) >> 6
            s = _clamp16(s)
            o2 = o1
            o1 = s
            out[ch].append(s)
        if ch == 0:
            st[0], st[1] = o1, o2
        else:
            st[2], st[3] = o1, o2
    return out[0], out[1]


def decode_sector_payload(sect):
    """Decode one 2336-byte sector -> (left, right) interleaved sample order."""
    st = [0, 0, 0, 0]
    left, right = [], []
    for g in range(GROUPS):
        off = PAYLOAD_OFF + g * GROUP
        l, r = decode_group(sect[off:off + GROUP], st)
        left.extend(l)
        right.extend(r)
    return left, right


# ---------------------------------------------------------------- encode

def _encode_unit(samples28, o1, o2):
    """Pick best (shift,filter) + nibbles for 28 samples given predictor state.
    Returns (param_byte, nibbles[28], new_o1, new_o2). Mimics the decoder so the
    hardware reproduces these exact samples."""
    best = None
    for filt in range(4):
        k0, k1 = K0[filt], K1[filt]
        for shift in range(13):
            p1, p2 = o1, o2
            err = 0
            nibs = []
            for s in samples28:
                pred = (k0 * p1 + k1 * p2) >> 6
                # target residual scaled
                target = s - pred
                # inverse of: out = (signext(nib)<<12)>>shift ; want nib
                # quantise: nib_val ~ target >> (12-shift) rounded
                d = target << shift
                q = (d + 0x800) >> 12  # round to nearest
                if q > 7:
                    q = 7
                if q < -8:
                    q = -8
                nib = q & 0x0F
                # reconstruct exactly as decoder
                rec = _signext4(nib) << 12
                rec >>= shift
                rec += pred
                rec = _clamp16(rec)
                err += (rec - s) * (rec - s)
                nibs.append(nib)
                p2 = p1
                p1 = rec
            if best is None or err < best[0]:
                best = (err, (filt << 4) | shift, nibs, p1, p2)
    _, param, nibs, no1, no2 = best
    return param, nibs, no1, no2


def encode_sector_payload(left, right):
    """Encode 18*8/2*28 = 2016 stereo samples (left[2016],right[2016]) -> 2304B."""
    assert len(left) == GROUPS * (UNITS // 2) * SAMPLES, len(left)
    assert len(right) == len(left)
    out = bytearray(GROUPS * GROUP)
    st = [0, 0, 0, 0]  # oldL1,oldL2,oldR1,oldR2
    li = ri = 0
    for g in range(GROUPS):
        base = g * GROUP
        params = [0] * UNITS
        unit_nibs = [None] * UNITS
        for u in range(UNITS):
            if (u & 1) == 0:  # left
                seg = left[li:li + SAMPLES]
                li += SAMPLES
                param, nibs, st[0], st[1] = _encode_unit(seg, st[0], st[1])
            else:  # right
                seg = right[ri:ri + SAMPLES]
                ri += SAMPLES
                param, nibs, st[2], st[3] = _encode_unit(seg, st[2], st[3])
            params[u] = param
            unit_nibs[u] = nibs
        # write header (params twice)
        for u in range(4):
            out[base + 0 + u] = params[u]
            out[base + 4 + u] = params[u]
            out[base + 8 + u] = params[u + 4]
            out[base + 12 + u] = params[u + 4]
        # write data words
        for i in range(SAMPLES):
            wo = base + 16 + 4 * i
            for bidx in range(4):
                lo = unit_nibs[bidx][i] & 0x0F
                hi = unit_nibs[bidx + 4][i] & 0x0F
                out[wo + bidx] = (hi << 4) | lo
    return bytes(out)


SAMPLES_PER_SECTOR = GROUPS * (UNITS // 2) * SAMPLES  # 2016 per channel (L or R)


# ---------------------------------------------------------------- WAV io

def read_wav_stereo_37800(path):
    """Return (left[], right[]) int16 lists at 37800Hz stereo. Caller pre-converts."""
    w = wave.open(path, "rb")
    assert w.getsampwidth() == 2, "need 16-bit PCM"
    ch = w.getnchannels()
    sr = w.getframerate()
    n = w.getnframes()
    raw = w.readframes(n)
    w.close()
    if ch == 2:
        vals = struct.unpack("<%dh" % (n * 2), raw)
        left = list(vals[0::2])
        right = list(vals[1::2])
    else:
        vals = list(struct.unpack("<%dh" % n, raw))
        left = vals
        right = list(vals)
    return left, right, sr


def write_wav_stereo(path, left, right, sr=37800):
    w = wave.open(path, "wb")
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(sr)
    inter = bytearray(len(left) * 4)
    struct.pack_into("<%dh" % (len(left) * 2), inter, 0,
                     *[v for pair in zip(left, right) for v in pair])
    w.writeframes(bytes(inter))
    w.close()


# ---------------------------------------------------------------- channel swap

def channel_audio_sectors(data, channel):
    """Return list of sector indices that are AUDIO (submode bit2) for channel."""
    idxs = []
    n = len(data) // SECTOR
    for i in range(n):
        base = i * SECTOR
        if data[base + 1] == channel and (data[base + 2] & 0x04):
            idxs.append(i)
    return idxs


def splice_payloads(xa_path, channel, src_xa, out_path, loop_fill=True):
    """Splice ADPCM payloads from a psxavenc single-channel .xa (`src_xa`, 2336B
    sectors) into `channel` of `xa_path`, preserving all subheaders/EDC/padding.
    psxavenc is the authoritative (hardware-verified) encoder; this only moves
    its 2304-byte payloads into the interleaved channel slots and loops to fill."""
    data = bytearray(open(xa_path, "rb").read())
    src = open(src_xa, "rb").read()
    assert len(src) % SECTOR == 0, "src not 2336-byte sectors (use psxavenc -t xa)"
    payloads = [src[i * SECTOR + PAYLOAD_OFF:i * SECTOR + PAYLOAD_OFF + GROUPS * GROUP]
                for i in range(len(src) // SECTOR)]
    sectors = channel_audio_sectors(data, channel)
    if not payloads:
        raise SystemExit("empty source")
    silence = b"\x00" * (GROUPS * GROUP)             # zero ADPCM payload = silence
    for k, si in enumerate(sectors):
        if k < len(payloads):
            pl = payloads[k]
        elif loop_fill:
            pl = payloads[k % len(payloads)]          # music: repeat to fill (loop)
        else:
            pl = silence                              # one-shot (voice): pad silence, no repeat
        base = si * SECTOR
        data[base + PAYLOAD_OFF:base + PAYLOAD_OFF + GROUPS * GROUP] = pl
    open(out_path, "wb").write(data)
    return len(sectors), len(payloads)


def replace_channel(xa_path, channel, left, right, out_path, loop_fill=True):
    """Replace ADPCM payload of `channel` in xa_path with audio (left,right).
    Subheaders/EDC/padding preserved byte-exact. Loops source to fill if shorter."""
    data = bytearray(open(xa_path, "rb").read())
    sectors = channel_audio_sectors(data, channel)
    need = len(sectors) * SAMPLES_PER_SECTOR
    if loop_fill and len(left) < need:
        reps = (need + len(left) - 1) // len(left)
        left = (left * reps)[:need]
        right = (right * reps)[:need]
    li = 0
    for k, si in enumerate(sectors):
        l = left[li:li + SAMPLES_PER_SECTOR]
        r = right[li:li + SAMPLES_PER_SECTOR]
        li += SAMPLES_PER_SECTOR
        if len(l) < SAMPLES_PER_SECTOR:  # final partial -> pad silence
            l = l + [0] * (SAMPLES_PER_SECTOR - len(l))
            r = r + [0] * (SAMPLES_PER_SECTOR - len(r))
        payload = encode_sector_payload(l, r)
        base = si * SECTOR
        data[base + PAYLOAD_OFF:base + PAYLOAD_OFF + GROUPS * GROUP] = payload
    open(out_path, "wb").write(data)
    return len(sectors), need


# ---------------------------------------------------------------- CLI

def cmd_decode(args):
    data = open(args.xa, "rb").read()
    sectors = channel_audio_sectors(data, args.channel)
    left, right = [], []
    for si in sectors:
        l, r = decode_sector_payload(data[si * SECTOR:(si + 1) * SECTOR])
        left.extend(l)
        right.extend(r)
    write_wav_stereo(args.out, left, right)
    print("decoded %d sectors -> %s (%d samples)" % (len(sectors), args.out, len(left)))


def cmd_verify(args):
    """Decode channel 0 with our codec and compare RMS to a reference WAV."""
    data = open(args.xa, "rb").read()
    sectors = channel_audio_sectors(data, args.channel)[:args.n]
    left, right = [], []
    for si in sectors:
        l, r = decode_sector_payload(data[si * SECTOR:(si + 1) * SECTOR])
        left.extend(l)
        right.extend(r)
    rl, rr, sr = read_wav_stereo_37800(args.ref)
    m = min(len(left), len(rl))
    err = sum((left[i] - rl[i]) ** 2 for i in range(m)) / m
    import math
    print("ref sr=%d, compared %d samples, RMS err(L)=%.2f" % (sr, m, math.sqrt(err)))
    if math.sqrt(err) < 2.0:
        print("DECODE MATCHES reference (layout locked).")
    else:
        print("MISMATCH — layout wrong. first 8 ours:", left[:8], "ref:", rl[:8])


def cmd_roundtrip(args):
    """Encode a WAV into a fresh single-channel buffer, decode it back, report SNR."""
    left, right, sr = read_wav_stereo_37800(args.wav)
    assert sr == 37800, "resample to 37800 first (use ffmpeg)"
    nsec = (len(left) + SAMPLES_PER_SECTOR - 1) // SAMPLES_PER_SECTOR
    import math
    se = 0
    sig = 0
    cnt = 0
    li = 0
    st = [0, 0, 0, 0]
    for s in range(nsec):
        l = left[li:li + SAMPLES_PER_SECTOR]
        r = right[li:li + SAMPLES_PER_SECTOR]
        li += SAMPLES_PER_SECTOR
        if len(l) < SAMPLES_PER_SECTOR:
            l = l + [0] * (SAMPLES_PER_SECTOR - len(l))
            r = r + [0] * (SAMPLES_PER_SECTOR - len(r))
        payload = encode_sector_payload(l, r)
        sect = bytearray(SECTOR)
        sect[PAYLOAD_OFF:PAYLOAD_OFF + len(payload)] = payload
        dl, dr = decode_sector_payload(sect)
        for i in range(len(dl)):
            d = dl[i] - l[i]
            se += d * d
            sig += l[i] * l[i]
            cnt += 1
    snr = 10 * math.log10(sig / se) if se else 99
    print("roundtrip %d sectors, SNR=%.1f dB (lossy ADPCM; ~>20dB is good)" % (nsec, snr))


def main():
    ap = argparse.ArgumentParser(description="CD-XA ADPCM codec (ABL music)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("decode", help="decode a channel to WAV")
    d.add_argument("xa")
    d.add_argument("--channel", type=int, default=0)
    d.add_argument("--out", required=True)
    d.set_defaults(func=cmd_decode)

    v = sub.add_parser("verify", help="decode N sectors and RMS-compare to ref WAV")
    v.add_argument("xa")
    v.add_argument("--ref", required=True)
    v.add_argument("--channel", type=int, default=0)
    v.add_argument("--n", type=int, default=200)
    v.set_defaults(func=cmd_verify)

    r = sub.add_parser("roundtrip", help="encode+decode a 37800Hz stereo WAV, report SNR")
    r.add_argument("wav")
    r.set_defaults(func=cmd_roundtrip)

    rep = sub.add_parser("replace", help="swap a channel's audio in an XA file")
    rep.add_argument("xa")
    rep.add_argument("--channel", type=int, required=True)
    rep.add_argument("--wav", required=True, help="37800Hz 16-bit stereo WAV")
    rep.add_argument("--out", required=True)
    rep.add_argument("--no-loop-fill", action="store_true")
    def _rep(a):
        l, r, sr = read_wav_stereo_37800(a.wav)
        assert sr == 37800, "resample to 37800 first"
        ns, need = replace_channel(a.xa, a.channel, l, r, a.out,
                                   loop_fill=not a.no_loop_fill)
        print("replaced channel %d: %d audio sectors (%d samples capacity) -> %s"
              % (a.channel, ns, need, a.out))
    rep.set_defaults(func=_rep)

    sp = sub.add_parser("splice", help="splice psxavenc .xa payloads into a channel")
    sp.add_argument("xa", help="target AUDIOn.XA (interleaved, 2336B sectors)")
    sp.add_argument("--channel", type=int, required=True)
    sp.add_argument("--src", required=True, help="psxavenc single-channel .xa")
    sp.add_argument("--out", required=True)
    sp.add_argument("--no-loop-fill", action="store_true")
    def _sp(a):
        ns, np_ = splice_payloads(a.xa, a.channel, a.src, a.out,
                                  loop_fill=not a.no_loop_fill)
        print("spliced %d src sectors into channel %d (%d audio sectors) -> %s"
              % (np_, a.channel, ns, a.out))
    sp.set_defaults(func=_sp)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Longer XA voice lines — extend a channel by converting its gap-8 data-slots
# to audio and moving the EOF marker (size-preserving; see Plan - Longer XA voice).
# ---------------------------------------------------------------------------
def _channel_run(data, channel):
    """The channel's contiguous gap-8 interleave run (audio sectors + following gap-8
    'data' slots, submode 0x48). This is the region usable for continuous 37800/stereo
    playback; the tail (non-gap-8) is not."""
    secs = [i for i in range(len(data) // SECTOR) if data[i * SECTOR + 1] == channel]
    if not secs:
        raise SystemExit(f"channel {channel} not present")
    run = [secs[0]]
    for s in secs[1:]:
        if s - run[-1] == 8:
            run.append(s)
        else:
            break
    return run


def voice_capacity(xa_path, channel):
    """(current_audio_sectors, gap8_run_capacity) for a voice channel."""
    data = open(xa_path, "rb").read()
    run = _channel_run(data, channel)
    aud = sum(1 for i in run if data[i * SECTOR + 2] & 0x04)
    return aud, len(run)


def extend_xa_voice(xa_path, channel, src_xa, out_path):
    """Replace + EXTEND a voice channel: splice src ADPCM into the channel's gap-8 run
    (converting trailing data-slots 0x48 -> audio 0x64 as needed) and set the XA EOF (0x80)
    on the new last audio sector; clear it elsewhere; slots past the audio become data (0x48).
    Size-preserving. Returns (used, capacity, src_sectors). Truncates if src > capacity."""
    data = bytearray(open(xa_path, "rb").read())
    src = open(src_xa, "rb").read()
    assert len(src) % SECTOR == 0, "src not 2336-byte sectors (psxavenc -t xa)"
    payloads = [src[i * SECTOR + PAYLOAD_OFF: i * SECTOR + PAYLOAD_OFF + GROUPS * GROUP]
                for i in range(len(src) // SECTOR)]
    run = _channel_run(data, channel)
    coding = data[next(i for i in run if data[i * SECTOR + 2] & 0x04) * SECTOR + 3]  # audio coding byte
    used = min(len(payloads), len(run))
    silence = b"\x00" * (GROUPS * GROUP)
    for k, si in enumerate(run):
        base = si * SECTOR
        if k < used:                                    # audio sector (EOF on the last one)
            sm = 0x64 | (0x80 if k == used - 1 else 0)
            data[base + 2] = sm; data[base + 6] = sm
            data[base + 3] = coding; data[base + 7] = coding
            data[base + PAYLOAD_OFF:base + PAYLOAD_OFF + GROUPS * GROUP] = payloads[k]
        else:                                           # past the line: data slot, silenced, no EOF
            data[base + 2] = 0x48; data[base + 6] = 0x48
            data[base + PAYLOAD_OFF:base + PAYLOAD_OFF + GROUPS * GROUP] = silence
    open(out_path, "wb").write(data)
    return used, len(run), len(payloads)
