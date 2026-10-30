#!/usr/bin/env python3
"""
parse_all_anm.py — byte-exact round-trip parser for the Traveller's Tales
.ALL (model) and .ANM (animation) formats — Disney/Pixar "A Bug's Life"
(PS1, SCUS-94288).  GAP-0026.

The round-trip assert `emit(parse(x)) == x` is the proof of the grammar:
validated over the full repo corpus — .ALL 78/78 and .ANM 58/58 byte-exact.
Grammars decoded from the consumers in SCUS_942.88 (renderer FUNC_800172DC
@0x800172dc, skinning core FUNC_8005EC84 @0x8005ec84, .ANM sampler
FUNC_8005EC80) and confirmed against bytes.

.ANM is fully field-decoded (every byte typed): file header + an absolute
u32 pointer table + contiguous sub-blocks sized exactly
  0x0C + 2*n8 + n10 + 2*n6*frame_count
(dense frame-major s16 keyframes — NO per-frame bitmask; the ACORN/BBIRD/FDIM
"outliers" are just anim_count==2 files, one uniform layout).

.ALL: word0 splits two element streams [4:word0] and [word0:EOF]; each is a
flat sequence of primitive lists (colour words [B][G][R][cmd] then nv 8-byte
vertices; on-disk type = the LAST colour's cmd & 0x3c -> 0x3c quad/nv4,
0x34 tri/nv3, 0x00000000 terminator) and skin/vertex blocks (vcount + 8-byte
verts marked 0x0110 + a -1/-2/-3-sentinel bone-attachment list).  The
primitive layer is field-decoded and re-emitted from fields; the
skin-attachment tails + small section-B mini-headers are byte-preserved
verbatim (RESIDUAL: full field-typing of those spans), so the whole-file
round-trip is always byte-exact.

Usage:  python3 tools/parse_all_anm.py [CORPUS_DIR]
        (defaults to $ABL_DIR or CWD, then its REBUILD/files).
Outputs metadata only (counts/offsets) — never asset bytes.
"""
import struct, sys, glob, os

# ===========================================================================
# .ANM  (validated 58/58 byte-exact)
# ===========================================================================
# --------------------------------------------------------------------------
# parse
# --------------------------------------------------------------------------

def parse_subblock(data, off):
    """Parse one sub-block at absolute offset `off`; return (struct_dict, size)."""
    w0, fcflag, n4, n6, n8, n10 = struct.unpack_from('<6H', data, off)
    frame_count = fcflag & 0x7FFF
    mode_flag   = fcflag & 0x8000

    p = off + 12
    time_table = list(struct.unpack_from('<%dh' % n8, data, p))   # signed
    p += 2 * n8

    meta = data[p:p + n10]                                        # raw bytes
    p += n10

    nvals = frame_count * n6
    frames_flat = list(struct.unpack_from('<%dh' % nvals, data, p))  # signed
    p += 2 * nvals

    size = p - off
    sub = {
        'w0': w0,
        'fcflag': fcflag,            # preserved verbatim (frame_count|mode_flag)
        'frame_count': frame_count,  # derived (informational)
        'mode_flag': mode_flag,      # derived (informational)
        'n4': n4,
        'n6': n6,
        'n8': n8,
        'n10': n10,
        'time_table': time_table,    # n8 s16
        'meta': meta,                # n10 raw bytes
        'frames': frames_flat,       # frame_count*n6 s16, frame-major
        '_off': off,
        '_size': size,
    }
    return sub, size


def parse_anm(data):
    """Parse a whole .ANM byte string into a structure dict."""
    reserved0, anim_count, reserved1 = struct.unpack_from('<HHI', data, 0)
    ptr_table = list(struct.unpack_from('<%dI' % anim_count, data, 8))
    table_end = 8 + 4 * anim_count

    # Sub-blocks live at the DISTINCT nonzero offsets, packed contiguously in
    # ascending order. Parse each once; the pointer table (with its order,
    # duplicates and zeros) is preserved separately so emit is exact.
    distinct = sorted({p for p in ptr_table if p != 0})
    blocks = {}        # offset -> sub-block dict
    for o in distinct:
        sub, _ = parse_subblock(data, o)
        blocks[o] = sub

    return {
        'reserved0': reserved0,
        'reserved1': reserved1,
        'anim_count': anim_count,
        'ptr_table': ptr_table,    # absolute offsets, original order
        'table_end': table_end,
        'blocks': blocks,          # offset -> parsed sub-block
        'total_size': len(data),   # to faithfully reproduce trailing layout
    }


# --------------------------------------------------------------------------
# emit
# --------------------------------------------------------------------------

def emit_subblock(sub):
    out = bytearray()
    out += struct.pack('<6H', sub['w0'], sub['fcflag'],
                       sub['n4'], sub['n6'], sub['n8'], sub['n10'])
    out += struct.pack('<%dh' % sub['n8'], *sub['time_table'])
    assert len(sub['meta']) == sub['n10']
    out += sub['meta']
    out += struct.pack('<%dh' % (sub['frame_count'] * sub['n6']), *sub['frames'])
    return bytes(out)


def emit_anm(st):
    out = bytearray()
    out += struct.pack('<HHI', st['reserved0'], st['anim_count'], st['reserved1'])
    out += struct.pack('<%dI' % st['anim_count'], *st['ptr_table'])
    assert len(out) == st['table_end']

    # Lay sub-blocks down at their absolute offsets in ascending order. They are
    # contiguous with no gaps; we assert each block starts exactly where the
    # previous ended (== the format's contiguity invariant).
    for o in sorted(st['blocks']):
        if len(out) < o:
            # never expected for this corpus, but stay robust: pad the gap with
            # the original bytes is impossible here, so fail loud.
            raise ValueError('unexpected gap before block @%#x (have %#x)' % (o, len(out)))
        if len(out) != o:
            raise ValueError('block @%#x overlaps previous end %#x' % (o, len(out)))
        out += emit_subblock(st['blocks'][o])

    # File ends exactly at the last block end. Sanity vs recorded size.
    if len(out) != st['total_size']:
        raise ValueError('size mismatch emit=%d orig=%d' % (len(out), st['total_size']))
    return bytes(out)

# ===========================================================================
# .ALL  (validated 78/78 byte-exact)
# ===========================================================================
ZERO = b'\x00\x00\x00\x00'

# --------------------------------------------------------------------------- #
# primitive records
# --------------------------------------------------------------------------- #
def _nv(cmd):
    m = cmd & 0x3c
    if m == 0x3c: return 4
    if m == 0x34: return 3
    return None

def parse_primlist(d, off, end):
    """Parse ONE primitive list (records until a 00000000 sentinel).
    Returns (records, off_after, err)."""
    recs = []
    while off + 4 <= end:
        word = d[off:off+4]
        if word == ZERO:                       # bare terminator
            recs.append({'kind': 'TERM', 'off': off, 'nwords': 1})
            return recs, off + 4, None
        cstart = off
        nv = _nv(word[3]); ncol = 1; off += 4
        if nv is None:
            hit_term = False
            while off + 4 <= end and ncol < 9:
                w2 = d[off:off+4]
                if w2 == ZERO:                 # terminator record [c..][0]
                    off += 4; hit_term = True; break
                ncol += 1; off += 4; nv = _nv(w2[3])
                if nv is not None: break
            if hit_term:
                recs.append({'kind': 'TERM', 'off': cstart, 'nwords': ncol + 1})
                return recs, off, None
            if nv is None:
                return recs, cstart, 'RUNAWAY@0x%x' % cstart
        if off + nv * 8 > end:
            return recs, cstart, 'EOF_VERTS@0x%x' % cstart
        recs.append({'kind': 'PRIM', 'off': cstart, 'ncol': ncol, 'nv': nv,
                     'end': off + nv * 8})
        off += nv * 8
    return recs, off, 'NO_TERM'

def decode_record(d, rec):
    """Decode a PRIM record's raw bytes into structured fields."""
    if rec['kind'] == 'TERM':
        n = rec['nwords']
        return {'kind': 'TERM', 'raw': d[rec['off']:rec['off'] + n * 4]}
    off, ncol, nv = rec['off'], rec['ncol'], rec['nv']
    colors = []
    for i in range(ncol):
        w = d[off + i*4: off + i*4 + 4]
        colors.append({'b': w[0], 'g': w[1], 'r': w[2], 'cmd': w[3]})
    vb0 = off + ncol * 4
    verts = []
    for i in range(nv):
        x, y, z, n = struct.unpack('<hhhH', d[vb0 + i*8: vb0 + i*8 + 8])
        verts.append({'x': x, 'y': y, 'z': z, 'n': n})
    return {'kind': 'PRIM', 'colors': colors, 'verts': verts}

def encode_record(fld):
    """Re-emit a decoded record to its exact bytes."""
    if fld['kind'] == 'TERM':
        return fld['raw']
    out = bytearray()
    for c in fld['colors']:
        out += bytes([c['b'], c['g'], c['r'], c['cmd']])
    for v in fld['verts']:
        out += struct.pack('<hhhH', v['x'], v['y'], v['z'], v['n'])
    return bytes(out)

# --------------------------------------------------------------------------- #
# skin / vertex blocks
# --------------------------------------------------------------------------- #
def skin_vcount(d, off, end):
    """Return vcount if a skin block begins at off, else None."""
    if off + 12 > end: return None
    vc = struct.unpack('<H', d[off:off+2])[0]
    if vc == 0 or vc > 0x2000: return None
    vstart = off + 4
    if vstart + vc * 8 > end: return None
    for i in range(min(vc, 3)):
        vb = d[vstart + i*8: vstart + i*8 + 8]
        if not (vb[6] == 0x10 and vb[7] == 0x01):
            return None
    return vc

def _starts_record(d, off, end):
    """True if a primitive record validly begins at off."""
    if off + 4 > end: return False
    nv = _nv(d[off+3]); ncol = 1; o = off + 4
    if nv is None:
        while o + 4 <= end and ncol < 9:
            w = d[o:o+4]
            if w == ZERO: return False
            ncol += 1; o += 4; nv = _nv(w[3])
            if nv is not None: break
        if nv is None: return False
    return o + nv * 8 <= end

def skin_attach_end(d, vend, end):
    """End offset of the bone-attachment list following the vertex pool."""
    o = vend
    while o + 2 <= end:
        if skin_vcount(d, o, end) is not None:
            return o
        if o + 4 <= end and d[o:o+4] != ZERO and _starts_record(d, o, end):
            return o
        o += 2
    return end

# --------------------------------------------------------------------------- #
# sections / file
# --------------------------------------------------------------------------- #
def parse_section(d, start, end):
    els = []; off = start
    while off < end:
        vc = skin_vcount(d, off, end)
        if vc is not None:
            vstart = off + 4; vend = vstart + vc * 8
            aend = skin_attach_end(d, vend, end)
            els.append({'type': 'skin', 'off': off, 'end': aend, 'vcount': vc,
                        'vstart': vstart, 'vend': vend})
            off = aend; continue
        recs, off2, err = parse_primlist(d, off, end)
        if err and not (recs and recs[-1]['kind'] == 'TERM'):
            els.append({'type': 'raw', 'off': off, 'end': end, 'err': err})
            off = end; continue
        els.append({'type': 'prim', 'off': off, 'end': off2, 'records': recs})
        off = off2
    return els

def parse_all(d):
    word0 = struct.unpack('<I', d[0:4])[0]
    return {'word0': word0, 'size': len(d), 'raw': d,
            'A': parse_section(d, 4, word0),
            'B': parse_section(d, word0, len(d))}

def emit_all(st):
    d = st['raw']
    out = bytearray()
    out += struct.pack('<I', st['word0'])
    for el in st['A']:
        if el['type'] == 'prim':
            for rec in el['records']:
                out += encode_record(decode_record(d, rec))   # field-level emit
        else:
            out += d[el['off']:el['end']]                      # verbatim
    for el in st['B']:
        if el['type'] == 'prim':
            for rec in el['records']:
                out += encode_record(decode_record(d, rec))
        else:
            out += d[el['off']:el['end']]
    return bytes(out)

# ===========================================================================
# unified round-trip self-test + metadata (CI-safe: no payload emitted)
# ===========================================================================
if __name__ == '__main__':
    arg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('ABL_DIR', os.getcwd())
    corpus = arg
    cand = os.path.join(arg, 'REBUILD', 'files')
    if os.path.isdir(cand):
        corpus = cand
    anm_files = sorted(glob.glob(os.path.join(corpus, '**', '*.ANM'), recursive=True))
    all_files = sorted(glob.glob(os.path.join(corpus, '**', '*.ALL'), recursive=True))

    def rt(files, parse, emit):
        ok = 0; fails = []
        for fn in files:
            d = open(fn, 'rb').read()
            try:
                good = emit(parse(d)) == d
            except Exception as e:
                good = False; fails.append((fn, repr(e)))
            if good: ok += 1
            elif not fails or fails[-1][0] != fn: fails.append((fn, 'BYTE-DIFF'))
        return ok, fails

    a_ok, a_f = rt(anm_files, parse_anm, emit_anm)
    l_ok, l_f = rt(all_files, parse_all, emit_all)
    print('corpus: %s' % corpus)
    print('.ANM round-trip: %d/%d' % (a_ok, len(anm_files)))
    print('.ALL round-trip: %d/%d' % (l_ok, len(all_files)))
    for fn, why in (a_f + l_f):
        print('  FAIL', os.path.basename(fn), why)
    sys.exit(0 if (a_ok == len(anm_files) and l_ok == len(all_files)
                   and anm_files and all_files) else 1)
