"""VRAM framebuffer diff helper — read the display framebuffer from VRAM (native, no
upscale noise) and diff raw BGR555 pixels. Pair with determinism (compare two runs at the
same frame phase) to isolate an edit from idle-animation noise."""
import base64, struct

def fb(d):
    """Read the currently-displayed framebuffer (native 512x224) as a tuple of u16 pixels."""
    g = d.call('gpu.getStatus', {})['crtc']['vram_source_rect']
    x, y, w, h = g[0], g[1], 512, 224
    r = d.call('gpu.readVramRect', {'x': x, 'y': y, 'width': w, 'height': h})
    return (x, y, w, h, struct.unpack('<%dH' % (w * h), base64.b64decode(r['base64'])))

def diff(a, b):
    """Count differing pixels + bbox (x,y,w,h) in native coords. Returns (count, bbox|None)."""
    _, _, w, h, pa = a
    _, _, _, _, pb = b
    n = 0; xmn = ymn = 10**9; xmx = ymx = -1
    for i, (p, q) in enumerate(zip(pa, pb)):
        if p != q:
            n += 1; x = i % w; y = i // w
            if x < xmn: xmn = x
            if x > xmx: xmx = x
            if y < ymn: ymn = y
            if y > ymx: ymx = y
    return n, (None if n == 0 else (xmn, ymn, xmx - xmn + 1, ymx - ymn + 1))
