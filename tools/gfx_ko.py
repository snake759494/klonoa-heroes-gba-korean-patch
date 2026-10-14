# Redraw Japanese image text from original tile/palette assemblies with native-size Korean fonts.
# Covers BG0B/BG0W/BG0V, title AN/CT/BPE assets, encyclopedia UI, and the vision title cards.
# Text sources: work/tr/ko_gfx.py
import os, sys, struct, importlib.util
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import bdf, mapgfx
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
FONTDIR = os.path.join(ROOT, "work", "fonts")
_F = {}
def font(name):
    if name not in _F: _F[name] = bdf.load(os.path.join(FONTDIR, name + ".bdf"))
    return _F[name]

def text_mask(text, fname):
    """tight ink mask (H x W bool) of a single-line text; returns (mask, advance_width)"""
    G = font(fname)
    pen = 0; pts = []
    for ch in text:
        g = G.get(ord(ch))
        if g is None: raise KeyError("%s missing %r" % (fname, ch))
        w, h, x, y = g["bbx"]; wb = (w + 7) // 8 * 8
        for i, r in enumerate(g["rows"]):
            yy = -(y + h) + i          # relative to baseline (negative = above)
            for xx in range(w):
                if (r >> (wb - 1 - xx)) & 1: pts.append((pen + x + xx, yy))
        pen += g["dw"]
    if not pts: return np.zeros((1, max(pen, 1)), bool), pen
    x0 = min(p[0] for p in pts); x1 = max(p[0] for p in pts); y0 = min(p[1] for p in pts); y1 = max(p[1] for p in pts)
    m = np.zeros((y1 - y0 + 1, x1 - x0 + 1), bool)
    for x, y in pts: m[y - y0, x - x0] = True
    return m, pen

def hangul_top_bottom(fname):
    """ink rows of a full Hangul syllable relative to baseline -> used to align lines of mixed text"""
    G = font(fname); g = G[ord("한")]; w, h, x, y = g["bbx"]
    return -(y + h), -y - 1

def line_mask(text, fname):
    """mask with fixed vertical box = Hangul ink box (so lines align regardless of content)"""
    G = font(fname)
    top, bot = hangul_top_bottom(fname)
    pen = 0; pts = []
    for ch in text:
        g = G[ord(ch)]; w, h, x, y = g["bbx"]; wb = (w + 7) // 8 * 8
        for i, r in enumerate(g["rows"]):
            yy = -(y + h) + i
            for xx in range(w):
                if (r >> (wb - 1 - xx)) & 1: pts.append((pen + x + xx, yy))
        pen += g["dw"]
    xs = [p[0] for p in pts] or [0]
    x0 = min(xs); x1 = max(xs)
    y0 = min([top] + [p[1] for p in pts]); y1 = max([bot] + [p[1] for p in pts])
    m = np.zeros((y1 - y0 + 1, x1 - x0 + 1), bool)
    for x, y in pts: m[y - y0, x - x0] = True
    return m, top - y0   # offset of the Hangul top inside the mask

def draw(img, mask, x, y, body, shadow=None, clip=None):
    H, W = img.shape
    if shadow is not None:
        for (yy, xx) in zip(*np.nonzero(mask)):
            X, Y = x + xx + 1, y + yy + 1
            if 0 <= X < W and 0 <= Y < H and (clip is None or clip[Y, X]): img[Y, X] = shadow
    for (yy, xx) in zip(*np.nonzero(mask)):
        X, Y = x + xx, y + yy
        if 0 <= X < W and 0 <= Y < H and (clip is None or clip[Y, X]): img[Y, X] = body

def tracked_line_mask(text, fname, tracking=0):
    """Native-size BDF glyphs with optional pixel spacing; no glyph scaling."""
    G = font(fname); top, bot = hangul_top_bottom(fname); pen = 0; pts = []
    for i, ch in enumerate(text):
        g = G.get(ord(ch))
        if g is None: raise KeyError("%s missing %r" % (fname, ch))
        w, h, x, y = g["bbx"]; wb = (w + 7) // 8 * 8
        for row, bits in enumerate(g["rows"]):
            yy = -(y + h) + row
            for xx in range(w):
                if (bits >> (wb - 1 - xx)) & 1: pts.append((pen + x + xx, yy))
        pen += g["dw"] + (tracking if i + 1 < len(text) else 0)
    x0 = min([0] + [p[0] for p in pts]); x1 = max([pen, 1] + [p[0] + 1 for p in pts])
    m = np.zeros((bot - top + 1, x1 - x0), bool)
    for x, y in pts: m[y - top, x - x0] = True
    return m, -x0

def grow(mask, radius):
    if radius <= 0: return mask.copy()
    out = np.zeros_like(mask); h, w = mask.shape
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            sy0, sy1 = max(0, -dy), min(h, h - dy)
            sx0, sx1 = max(0, -dx), min(w, w - dx)
            if sy0 < sy1 and sx0 < sx1:
                out[sy0 + dy:sy1 + dy, sx0 + dx:sx1 + dx] |= mask[sy0:sy1, sx0:sx1]
    return out

def paint(img, mask, x, y, color):
    h, w = mask.shape; H, W = img.shape
    sx0, sy0 = max(0, -x), max(0, -y); sx1, sy1 = min(w, W - x), min(h, H - y)
    if sx0 < sx1 and sy0 < sy1:
        sub = mask[sy0:sy1, sx0:sx1]
        dst = img[y + sy0:y + sy1, x + sx0:x + sx1]
        dst[sub] = color

def outlined_text(img, text, fname, center, top, body, outline, radius=1, shadow=None, tracking=0, highlight=None):
    m, _ = tracked_line_mask(text, fname, tracking)
    x = center - m.shape[1] // 2
    if shadow is not None: paint(img, m, x + 1, top + 2, shadow)
    if radius > 1: paint(img, grow(m, radius), x, top, outline)
    if radius > 0: paint(img, grow(m, 1), x, top, outline)
    paint(img, m, x, top, body)
    if highlight is not None:
        hi = np.zeros_like(m); hi[:max(1, m.shape[0] // 3)] = m[:max(1, m.shape[0] // 3)]
        paint(img, hi, x, top, highlight)
    return x, m.shape[1]

def _pack_tile(px, bpp):
    if bpp == 8: return bytes(np.asarray(px, dtype=np.uint8).reshape(64))
    out = bytearray(32)
    for y in range(8):
        for x in range(0, 8, 2): out[y * 4 + x // 2] = int(px[y, x]) | (int(px[y, x + 1]) << 4)
    return bytes(out)

def rebuild_ct(data, img, entries, c, dedupe_flips=False):
    """Repack the same-size CT tilemap after editing its index image."""
    tsz = 64 if c["bpp"] == 8 else 32; cap = c["tsize"] // tsz
    tiles = bytearray(c["tsize"]); newmap = bytearray(c["msize"]); ids = {}; tile_count = 0
    for i, e in enumerate(entries):
        row, col = divmod(i, c["mw"]); tile = _pack_tile(img[row * 8:row * 8 + 8, col * 8:col * 8 + 8], c["bpp"])
        flags = 0
        found = ids.get(tile)
        if found is not None:
            ti, flags = found
        elif dedupe_flips:
            variants = ((np.fliplr(img[row * 8:row * 8 + 8, col * 8:col * 8 + 8]), 0x400),
                        (np.flipud(img[row * 8:row * 8 + 8, col * 8:col * 8 + 8]), 0x800),
                        (np.flipud(np.fliplr(img[row * 8:row * 8 + 8, col * 8:col * 8 + 8])), 0xc00))
            for pixels, candidate_flags in variants:
                found = ids.get(_pack_tile(pixels, c["bpp"]))
                if found is not None:
                    ti, stored_flags = found
                    flags = stored_flags ^ candidate_flags
                    break
            else:
                found = None
        if found is None:
            ti = tile_count
            if ti >= cap: raise ValueError("CT tile capacity exceeded: %d > %d" % (ti + 1, cap))
            ids[tile] = (ti, 0); tiles[ti * tsz:(ti + 1) * tsz] = tile
            tile_count += 1
            if dedupe_flips:
                block = img[row * 8:row * 8 + 8, col * 8:col * 8 + 8]
                ids[_pack_tile(np.fliplr(block), c["bpp"])] = (ti, 0x400)
                ids[_pack_tile(np.flipud(block), c["bpp"])] = (ti, 0x800)
                ids[_pack_tile(np.flipud(np.fliplr(block)), c["bpp"])] = (ti, 0xc00)
        # Retain the palette bank and apply the flip needed to reproduce this source tile.
        struct.pack_into("<H", newmap, i * 2, (e & 0xf000) | flags | ti)
    out = bytearray(data)
    out[c["tiles"]:c["tiles"] + c["tsize"]] = tiles
    out[c["map"]:c["map"] + c["msize"]] = newmap
    return bytes(out), tile_count

def edit_bpe_ct(rom, addr, edit, dedupe_flips=False, palette_updates=None):
    import bpe, ctgfx
    old_size = struct.unpack_from("<I", rom, addr)[0]
    original = bytearray(bpe.decode(rom[addr:addr + old_size]))
    img, entries, c = ctgfx.image(original)
    edit(img, entries, c)
    for index, word in (palette_updates or {}).items():
        struct.pack_into("<H", original, c["pal"] + index * 2, word)
    rebuilt, used = rebuild_ct(original, img, entries, c, dedupe_flips=dedupe_flips)
    # A 4 KiB block gives the logo art its best ratio while keeping BPE encoding fast.
    block = 0x1000 if len(rebuilt) > 0x4000 else (0x2000 if len(rebuilt) > 0x1000 else 0x400)
    encoded = bpe.encode(rebuilt, block)
    if len(encoded) > old_size:
        encoded = min((bpe.encode(rebuilt, b) for b in (0x400, 0x800, 0x1000, 0x2000, 0x4000)), key=len)
    if len(encoded) > old_size:
        raise ValueError("BPE resource does not fit in place at %08X: %d > %d" % (addr, len(encoded), old_size))
    if bpe.decode(encoded) != rebuilt: raise ValueError("BPE roundtrip failed at %08X" % addr)
    rom[addr:addr + len(encoded)] = encoded
    return {"addr": addr, "compressed": (old_size, len(encoded)), "decoded": len(rebuilt), "tiles": used}

def title_art(width, height):
    """Convert the drawn logotype to hardware pixels; no font is loaded."""
    from PIL import Image
    source = Image.open(os.path.join(ROOT, "work", "tr", "title_logo_drawn.png")).convert("RGBA")
    alpha = source.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    source = source.crop(alpha.getbbox())
    source.thumbnail((width, height), Image.Resampling.LANCZOS)
    return source


def title_logo(rom):
    palette_updates = {}
    def edit(img, entries, c):
        from PIL import Image
        assert (c["w"], c["h"], c["bpp"]) == (240, 128, 8)
        source = title_art(224, 116)
        art = Image.new("RGBA", (240,128))
        art.alpha_composite(source, ((240-source.width)//2, (128-source.height)//2))
        rgba = np.asarray(art)
        opaque = rgba[:,:,3] >= 128
        samples = Image.new("RGB", (int(opaque.sum()),1))
        samples.putdata([tuple(map(int,p)) for p in rgba[:,:,:3][opaque]])
        q = samples.quantize(colors=48, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
        img[:] = 0
        img[opaque] = np.asarray(q,dtype=np.uint8).reshape(-1)+1
        colors = q.getpalette()
        for i in range(48):
            r,g,b = colors[i*3:i*3+3]
            palette_updates[i+1] = (r>>3)|((g>>3)<<5)|((b>>3)<<10)
    return edit_bpe_ct(rom,0xa28028,edit,dedupe_flips=True,palette_updates=palette_updates)


def title_logo_pattern(rom):
    def edit(img, entries, c):
        import ctgfx, bpe
        assert (c["w"],c["h"],c["bpp"]) == (256,256,4)
        # Reuse the same drawn motif in the original repeating 128x64 layout.
        a=0x28a5c8; n=struct.unpack_from("<I",rom,a)[0]
        raw=bpe.decode(rom[a:a+n])
        pal=np.asarray(ctgfx.palette(raw,c),dtype=np.int32)
        art=np.asarray(title_art(116,58))
        rgb=art[:,:,:3].astype(np.int32)
        distances=((rgb[:,:,None,:]-pal[None,None,1:,:])**2).sum(axis=3)
        pixels=(distances.argmin(axis=2)+1).astype(np.uint8)
        pixels[art[:,:,3]<128]=0
        img[:]=0
        h,w=pixels.shape
        for y in range(0,256,64):
            for x in (0,128): img[y+(64-h)//2:y+(64-h)//2+h,x+(128-w)//2:x+(128-w)//2+w]=pixels
        for y in (64,192): img[y:y+64]=np.roll(img[y:y+64],64,axis=1)
        entries[:]=[e & 0x0fff for e in entries]
    return edit_bpe_ct(rom,0x28a5c8,edit,dedupe_flips=True)

def system_image_text(rom):
    """Translate remaining small CT image strings that are not part of BG0B/Pf tables."""
    def start_strip(img, entries, c):
        assert (c["w"], c["h"], c["bpp"]) == (240, 8, 4)
        # Replace 前へ / メニュー / つぎへ, keeping the L/R and START controls intact.
        bg = 3
        for x0, x1, text, center in ((26, 53, "이전", 39), (127, 159, "메뉴", 143), (185, 213, "다음", 199)):
            sub = img[:, x0:x1]; sub[(sub == 1) | (sub == 2) | (sub == 3) | (sub == 5) | (sub == 6)] = bg
            m, _ = tracked_line_mask(text, "Galmuri7")
            paint(img, m, center - m.shape[1] // 2 + 1, 1, 2)
            paint(img, m, center - m.shape[1] // 2, 0, 1)
    def help_strip(img, entries, c):
        assert (c["w"], c["h"], c["bpp"]) == (240, 8, 4)
        img[:] = 0
        text = "←→:페이지 넘기기  ↑↓:메시지 넘기기  B버튼:닫기"
        m, _ = tracked_line_mask(text, "Galmuri7")
        if m.shape[1] > c["w"]: raise ValueError("encyclopedia help line too wide: %d" % m.shape[1])
        paint(img, m, (c["w"] - m.shape[1]) // 2, 0, 1)
    def stat_labels(img, entries, c):
        assert (c["w"], c["h"], c["bpp"]) == (240, 48, 4)
        # HP / AT / DF / AG are Latin abbreviations. Replace the two Japanese labels only.
        img[0:8, 0:60] = 9
        img[40:48, 0:96] = 8
        for text, y, body in (("속성", 0, 4), ("격파 수", 40, 4)):
            m, _ = tracked_line_mask(text, "Galmuri7")
            paint(img, m, 2, y, body)
    return [edit_bpe_ct(rom, 0x273818, start_strip),
            edit_bpe_ct(rom, 0x273a2c, help_strip),
            edit_bpe_ct(rom, 0x273f18, stat_labels)]

# ---------------- tile I/O ----------------
def read_tile(rom, a):
    t = np.frombuffer(bytes(rom[a:a + 32]), dtype=np.uint8)
    return np.stack([t & 15, t >> 4], 1).reshape(8, 8).copy()
def write_tile(rom, a, px):
    b = bytearray(32)
    for y in range(8):
        for x in range(0, 8, 2): b[y * 4 + x // 2] = int(px[y, x]) | (int(px[y, x + 1]) << 4)
    rom[a:a + 32] = bytes(b)

class MapRegion:
    """rectangle of a BG0B tilemap; pixels gathered from/written to the referenced tiles (no flips expected)"""
    def __init__(s, rom, mapoff, r0, r1, c0, c1):
        s.rom = rom; s.a, _ = mapgfx.find(bytes(rom[:0x1000000]), "BG0B"); s.tiles = s.a + 0x1b90
        s.cells = []
        s.img = np.zeros(((r1 - r0) * 8, (c1 - c0) * 8), np.uint8)
        for r in range(r0, r1):
            for c in range(c0, c1):
                e = struct.unpack_from("<H", rom, s.a + mapoff + 64 * r + 2 * c)[0]
                assert not (e & 0xc00), "flipped tile in region"
                t = e & 0x3ff; s.cells.append((r - r0, c - c0, t))
                s.img[(r - r0) * 8:(r - r0) * 8 + 8, (c - c0) * 8:(c - c0) * 8 + 8] = read_tile(rom, s.tiles + 32 * t)
    def commit(s):
        seen = {}
        for r, c, t in s.cells:
            px = s.img[r * 8:r * 8 + 8, c * 8:c * 8 + 8]
            if t in seen: assert (seen[t] == px).all(), "shared tile %x modified inconsistently" % t
            seen[t] = px.copy(); write_tile(s.rom, s.tiles + 32 * t, px)

def erase(img, rect, text_colors, bg):
    x0, y0, x1, y1 = rect
    sub = img[y0:y1, x0:x1]
    for c in text_colors: sub[sub == c] = bg

# ---------------- individual graphics ----------------
def popup(rom, mapoff, r0, r1, c0, c1, lines, fname="Galmuri11"):
    R = MapRegion(rom, mapoff, r0, r1, c0, c1)
    H, W = R.img.shape
    inner = (3, 3, W - 3, H - 3)
    erase(R.img, inner, (11, 14), 3)
    masks = [line_mask(t, fname) for t in lines]
    for m, _ in masks: assert m.shape[1] <= W - 8, "popup line too wide: %d > %d" % (m.shape[1], W - 8)
    lh = max(m.shape[0] for m, _ in masks); gap = 4
    total = lh * len(masks) + gap * (len(masks) - 1)
    y = inner[1] + (inner[3] - inner[1] - total) // 2
    x = 6
    for m, off in masks:
        draw(R.img, m, x, y, 11, 14)
        y += lh + gap
    R.commit()

def map_menu(rom, labels, fname="Galmuri11"):
    R = MapRegion(rom, 0x6d0, 2, 12, 9, 23)
    img = R.img
    for k, text in enumerate(labels):
        top = 8 + 16 * k           # outer border row of button k
        x0, x1 = 19, 92            # interior columns (text area)
        rect = (x0, top + 2, x1 + 1, top + 14)
        erase(img, rect, (1, 5), 3)
        # bottom highlight row (top+13) had shadow pixels 5 -> restore highlight color 10
        row = img[top + 13, x0:x1 + 1]; row[row == 5] = 10
        m, off = line_mask(text, fname)
        assert m.shape[1] <= x1 - x0 - 1, "menu label too wide: " + text
        x = x0 + (x1 - x0 + 1 - m.shape[1]) // 2
        y = top + 2 - off + 0
        clip = np.zeros_like(img, bool); clip[top + 2:top + 14, x0:x1 + 1] = True
        draw(img, m, x, y, 1, 5, clip)
    R.commit()

def start_text(rom, mapoff, text, fname="Galmuri7"):
    R = MapRegion(rom, mapoff, 15, 16, 11, 21)
    img = R.img
    x0 = 45
    sub = img[1:8, x0:]
    sub[sub == 13] = 4; sub[sub == 2] = 4
    top = img[0:1, x0:]            # row 0 is the border line (color 2); old glyph tops (dakuten) poke into it
    top[top == 13] = 2
    m, off = line_mask(text, fname)
    assert x0 + 1 + m.shape[1] <= img.shape[1], "START text too wide"
    y = 1 - off
    clip = np.zeros_like(img, bool); clip[1:8, x0:] = True
    draw(img, m, x0 + 1, y, 13, 2, clip)
    R.commit()

def banner(rom, tag, sub, text, body, bg, text_colors, inner, fonts=("Galmuri11", "Galmuri9", "Galmuri11-Condensed")):
    a, size = mapgfx.find(bytes(rom[:0x1000000]), tag, sub)
    img = np.zeros((16, 64), np.uint8)
    for k in range(16): img[(k // 8) * 8:(k // 8) * 8 + 8, (k % 8) * 8:(k % 8) * 8 + 8] = read_tile(rom, a + 32 * k)
    x0, y0, x1, y1 = inner
    erase(img, (x0, y0, x1, y1), text_colors, bg)
    for fname in fonts:
        m, off = line_mask(text, fname)
        if m.shape[1] <= (x1 - x0) - 2 and m.shape[0] <= (y1 - y0): break
    else: raise ValueError("banner text too wide: " + text)
    x = x0 + ((x1 - x0) - m.shape[1]) // 2
    y = y0 + ((y1 - y0) - m.shape[0]) // 2
    draw(img, m, x, y, body)
    for k in range(16): write_tile(rom, a + 32 * k, img[(k // 8) * 8:(k // 8) * 8 + 8, (k % 8) * 8:(k % 8) * 8 + 8])
    return fname


# ---------------- 'AN' sprite resources (title menu, res 0x2f of TP table 0x8fda70) ----------------
TPROOT=0x8fda70
def tp_entry(rom, idx, root=TPROOT):
    u=lambda a: struct.unpack_from("<I", rom, a)[0]
    return root + u(root + u(root + 8) + 4 * idx)
def an_frame(rom, an, frame_off):
    import angfx
    b = bytes(rom[an:an + 0x10000]); tiles = an + struct.unpack_from("<I", rom, an + 0x10)[0]
    ps = angfx.pieces(b, frame_off)
    x0 = min(p["x"] for p in ps); y0 = min(p["y"] for p in ps)
    W = max(p["x"] + p["w"] for p in ps) - x0; H = max(p["y"] + p["h"] for p in ps) - y0
    img = np.zeros((H, W), np.uint8); cells = []
    for p in ps:
        tw = p["w"] // 8
        for k in range(tw * (p["h"] // 8)):
            X = p["x"] - x0 + (k % tw) * 8; Y = p["y"] - y0 + (k // tw) * 8; t = p["chunk"] + k
            img[Y:Y + 8, X:X + 8] = read_tile(rom, tiles + 32 * t); cells.append((X, Y, t))
    return img, cells, tiles
def an_commit(rom, img, cells, tiles):
    for X, Y, t in cells: write_tile(rom, tiles + 32 * t, img[Y:Y + 8, X:X + 8])
def title_button(rom, an, frame_off, text, bg, body, shadow, x_lo, x_hi, center, erase_hi=None, fname="Galmuri11"):
    img, cells, tiles = an_frame(rom, an, frame_off)
    rows = (2, 14)                     # interior rows (text + shadow)
    sub = img[rows[0]:rows[1], x_lo:(erase_hi or x_hi) + 1]
    sub[sub == body] = bg; sub[sub == shadow] = bg
    m, off = line_mask(text, fname)
    x = center - m.shape[1] // 2
    assert x >= x_lo and x + m.shape[1] <= x_hi, "title button text too wide: " + text
    y = rows[0] + ((rows[1] - rows[0]) - (m.shape[0] + 1)) // 2
    clip = np.zeros_like(img, bool); clip[rows[0]:rows[1], x_lo:x_hi + 1] = True
    draw(img, m, x, y, body, shadow, clip)
    an_commit(rom, img, cells, tiles)
def title_menu(rom, T):
    an = tp_entry(rom, 0x2f)
    assert rom[an:an + 2] == b"AN"
    # frames: (offset, text key, selected?) ; normal: bg 3 / text 1 / shadow 8 ; selected: bg 10 / text 12 / shadow 7
    # はじめから/つづきから share their right 32px piece -> text stays in the left 64px (x<=63), centred at x=40
    for off, key, sel in ((0x54, "start", 0), (0xa8, "start", 1), (0xfc, "continue", 0), (0x150, "continue", 1)):
        # the shared right piece holds the common "ら" of both texts: erase it in every frame (same result), never draw there
        if sel: title_button(rom, an, off, T[key], 10, 12, 7, 10, 63, 40, erase_hi=85)
        else:   title_button(rom, an, off, T[key], 3, 1, 8, 4, 63, 40, erase_hi=91)
    title_button(rom, an, 0x1a4, T["music"], 3, 1, 8, 4, 107, 56)
    title_button(rom, an, 0x208, T["music"], 10, 12, 7, 10, 101, 56)

# ---------------- raw 'CT' containers (options menu, res 0x0c) ----------------
def ct_load(rom, ct):
    import ctgfx
    c = ctgfx.parse(bytes(rom[ct:ct + 0x20])) if False else None
    b = bytes(rom[ct:ct + 0x20])
    w, h = struct.unpack_from("<HH", b, 2); bpp = b[6]
    palo, ntw, ts, to, ms, mo = struct.unpack_from("<6I", b, 8)
    assert bpp == 4
    mw, mh = w // 8, h // 8
    img = np.zeros((h, w), np.uint8); cells = []
    for r in range(mh):
        for q in range(mw):
            e = struct.unpack_from("<H", rom, ct + mo + 2 * (r * mw + q))[0]
            assert not (e & 0xc00), "flipped tile in CT"
            t = e & 0x3ff; a = ct + to + 32 * t
            img[r * 8:r * 8 + 8, q * 8:q * 8 + 8] = read_tile(rom, a); cells.append((q * 8, r * 8, a))
    return img, cells
def ct_commit(rom, img, cells):
    seen = {}
    for X, Y, a in cells:
        px = img[Y:Y + 8, X:X + 8]
        if a in seen: assert (seen[a] == px).all(), "shared CT tile %x modified inconsistently" % a
        seen[a] = px.copy()
    for a, px in seen.items(): write_tile(rom, a, px)
def ct_sub(rom, res, i):
    r = tp_entry(rom, res)
    u = lambda a: struct.unpack_from("<I", rom, a)[0]
    return r + u(r + u(r + 8) + 4 * i)
def put_text(img, text, x, y_top, body, shadow, fname, clip=None, center=False):
    m, off = line_mask(text, fname)
    if center: x = x - m.shape[1] // 2
    draw(img, m, x, y_top - off, body, shadow, clip)
    return m.shape[1]
def options_menu(rom, K):
    # buttons 112x16: normal (bg3/text1/shadow8) = sub n, selected (bg10/text12/shadow7, arrows at both ends) = sub n+1
    for n, text in K.OPT_BUTTONS.items():
        for sub, (bg, body, sh, x0, x1) in ((n, (3, 1, 8, 16, 94)), (n + 1, (10, 12, 7, 22, 87))):
            ct = ct_sub(rom, 0x0c, sub); img, cells = ct_load(rom, ct)
            reg = img[2:14, x0:x1 + 1]; reg[reg == body] = bg; reg[reg == sh] = bg
            # row 1 is the inner top line (8 normal / 9 selected); old dakuten poke into it
            line = img[1, x0:x1 + 1]; line[line == body] = (8 if sub == n else 9)
            clip = np.zeros_like(img, bool); clip[2:14, x0:x1 + 1] = True
            m, off = line_mask(text, "Galmuri11"); assert m.shape[1] <= x1 - x0 - 1, text
            put_text(img, text, 55, 2, body, sh, "Galmuri11", clip, center=True)
            ct_commit(rom, img, cells)
    # label "セリフのひょうじ" (bg 12, text 1, shadow 8)
    ct = ct_sub(rom, 0x0c, 11); img, cells = ct_load(rom, ct)
    reg = img[0:14, 16:95]; reg[reg == 1] = 12; reg[reg == 8] = 12
    clip = np.zeros_like(img, bool); clip[0:14, 16:95] = True
    put_text(img, K.OPT_LABEL, 55, 1, 1, 8, "Galmuri11", clip, center=True)
    ct_commit(rom, img, cells)
    # panel title "パネルのせんたく" (176x64, left box, bg 12, text 1, shadow 8)
    ct = ct_sub(rom, 0x0c, 16); img, cells = ct_load(rom, ct)
    reg = img[6:22, 8:82]; reg[reg == 1] = 12; reg[reg == 8] = 12
    clip = np.zeros_like(img, bool); clip[6:22, 8:82] = True
    put_text(img, K.OPT_PANEL_TITLE, 44, 8, 1, 8, "Galmuri11", clip, center=True)
    ct_commit(rom, img, cells)
    # key-config panels (176x56): sub 14 = left selected (blue), sub 15 = right selected
    for sub, left_blue in ((14, True), (15, False)):
        ct = ct_sub(rom, 0x0c, sub); img, cells = ct_load(rom, ct)
        for x0, texts, blue in ((12, K.KEY_A, left_blue), (100, K.KEY_B, not left_blue)):
            bg, body, sh = (10, 12, 7) if blue else (3, 1, 8)
            reg = img[3:55, x0:x0 + 74]; reg[reg == body] = bg; reg[reg == sh] = bg
            clip = np.zeros_like(img, bool); clip[3:55, x0:x0 + 72] = True
            for (l1, l2), top in zip(texts, (5, 33)):
                ind = lambda t: sum(font("Galmuri9")[ord(c)]["dw"] for c in t[:len(t) - len(t.lstrip(" "))]) if t.startswith(" ") else 0
                ind2 = font("Galmuri9")[ord("·")]["dw"] if l2.startswith(" ") else 0
                w1 = put_text(img, l1, x0 + 1, top, body, sh, "Galmuri9", clip)
                w2 = put_text(img, l2.lstrip(" "), x0 + 1 + ind2, top + 11, body, sh, "Galmuri9", clip)
                assert max(w1, w2) <= 70, (l1, l2)
        ct_commit(rom, img, cells)

# ---------------- vision title cards (res 0x23: BPE-compressed CT 176x48, relocated after redraw) ----------------
def outline_draw(img, mask, x, y, body=13, edge=7, clip_rows=None):
    H, W = img.shape
    ys, xs = np.nonzero(mask)
    for yy, xx in zip(ys, xs):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                X, Y = x + xx + dx, y + yy + dy
                if 0 <= X < W and 0 <= Y < H and (clip_rows is None or clip_rows[0] <= Y < clip_rows[1]) and img[Y, X] != body:
                    img[Y, X] = edge
    for yy, xx in zip(ys, xs):
        X, Y = x + xx, y + yy
        if 0 <= X < W and 0 <= Y < H: img[Y, X] = body
def ct_build(hdr, pal, img, max_tiles=128):
    """rebuild a 4bpp CT (single palette) from an index image: dedupe tiles (tile 0 = blank), map without flips"""
    H, W = img.shape; mw, mh = W // 8, H // 8
    tiles = [bytes(32)]; index = {bytes(32): 0}; mp = []
    for r in range(mh):
        for q in range(mw):
            px = img[r * 8:r * 8 + 8, q * 8:q * 8 + 8]
            b = bytearray(32)
            for y in range(8):
                for x in range(0, 8, 2): b[y * 4 + x // 2] = int(px[y, x]) | (int(px[y, x + 1]) << 4)
            b = bytes(b)
            if b not in index: index[b] = len(tiles); tiles.append(b)
            mp.append(index[b])
    assert len(tiles) <= max_tiles, "too many tiles: %d" % len(tiles)
    h = bytearray(hdr[:0x20])
    ts = 32 * len(tiles); to = 0x20 + len(pal); ms = 2 * len(mp); mo = to + ts
    hi = struct.unpack_from("<H", h, 0xe)[0]
    struct.pack_into("<HH", h, 0xc, len(tiles), hi)
    struct.pack_into("<IIII", h, 0x10, ts, to, ms, mo)
    return bytes(h) + bytes(pal) + b"".join(tiles) + b"".join(struct.pack("<H", m) for m in mp), len(tiles)
def card_redraw(d, title, place, extra=False):
    import ctgfx
    c = ctgfx.parse(d); img, ents, _ = ctgfx.image(d)
    H, W = img.shape
    pal = d[c["pal"]:c["pal"] + 32]
    # regions
    wing = np.isin(img, [1, 2, 3, 4, 5, 6]); wys, wxs = np.nonzero(wing)
    textc = np.isin(img, [7, 8, 9, 10, 11, 12, 13])
    # underline: row with the longest run of color 7 in the lower half
    ul = max(range(24, H - 8), key=lambda y: int((img[y] == 7).sum()))
    ulx = np.nonzero(img[ul] == 7)[0]; ul_x0 = int(ulx.min())
    top = 9 if extra else 0
    # JP title start (first black pixel of the title glyph band, right of the wing's core)
    band = img[top:ul, :]
    bx = np.nonzero((band == 13).any(0))[0]
    tx0 = int(bx.min())
    # erase title/furigana band, underline and place rows (keep wing colors 1-6 and the EXTRA header)
    for y in range(top, H):
        row = img[y]; row[np.isin(row, [7, 8, 9, 10, 11, 12, 13])] = 0
    # title
    for fname in ("Galmuri11-Bold", "Galmuri11-Condensed"):
        m, off = line_mask(title, fname)
        if tx0 + m.shape[1] + 1 <= W - 1: break
    else: raise ValueError("card title too wide: " + title)
    ty = top + ((ul - top) - m.shape[0]) // 2
    ty = max(ty, top + 1)
    outline_draw(img, m, tx0 + 1, ty)
    tx1 = tx0 + 1 + m.shape[1]
    # underline (3 rows: edge / body / edge)
    ux1 = min(W - 1, max(tx1 + 2, ul_x0 + 40))
    img[ul, ul_x0:ux1 + 1] = 7; img[ul + 1, ul_x0:ux1 + 1] = 13; img[ul + 1, ul_x0] = 7; img[ul + 1, ux1] = 7; img[ul + 2, ul_x0:ux1 + 1] = 7
    # place name centred under the title
    for fname in ("Galmuri9", "Galmuri7"):
        pm, poff = line_mask(place, fname)
        if pm.shape[1] + 2 <= W: break
    cx = (tx0 + tx1) // 2
    px = min(max(1, cx - pm.shape[1] // 2), W - 1 - pm.shape[1])
    py = ul + 3 + ((H - (ul + 3)) - pm.shape[0]) // 2
    outline_draw(img, pm, px, py)
    return ct_build(d[:0x20], pal, img)
def title_cards(rom, K, alloc):
    import bpe
    r = tp_entry(rom, 0x23)
    u = lambda a: struct.unpack_from("<I", rom, a)[0]
    first = u(r + 8)
    out = {}
    for i, (title, place) in K.CARDS.items():
        s = r + u(r + first + 4 * i); size = u(s)
        d = bpe.decode(bytes(rom[s:s + size]))
        nd, nt = card_redraw(d, title, place, extra=(42 <= i <= 48))
        enc = bpe.encode_literal(nd)
        a = alloc(len(enc), 4); rom[a:a + len(enc)] = enc
        struct.pack_into("<I", rom, r + first + 4 * i, a - r)
        out[i] = nt
    return out

# ---------------- compressed CT entries of a 'Pf' table in ROM (encyclopedia UI: master 0x267940 #3) ----------------
def pf_entry_addr(rom, t, i):
    n = struct.unpack_from("<h", rom, t + 2)[0]; base = t + 4 + 8 * n
    return base + struct.unpack_from("<I", rom, t + 4 + 4 * n + 4 * i)[0], base, n
def pf_ct_load(rom, t, i):
    import bpe
    a, base, n = pf_entry_addr(rom, t, i)
    size = struct.unpack_from("<I", rom, a)[0]
    return bpe.decode(bytes(rom[a:a + size]))
def pf_ct_store(rom, t, i, d, alloc):
    import bpe
    a, base, n = pf_entry_addr(rom, t, i)
    enc = bpe.encode_literal(d)
    na = alloc(len(enc), 4); rom[na:na + len(enc)] = enc
    struct.pack_into("<I", rom, t + 4 + 4 * n + 4 * i, na - base)
    struct.pack_into("<I", rom, t + 4 + 4 * i, len(enc))
def ct_edit(d, fn, extra_tiles=6):
    """decode CT d -> index image, fn(img) edits it, rebuild with dedup; tile count may grow by at most extra_tiles"""
    import ctgfx
    c = ctgfx.parse(d); img, ents, _ = ctgfx.image(d)
    pal = d[c["pal"]:c["pal"] + 2 * 16 * max(1, c["npal"])]
    fn(img)
    nd, nt = ct_build(d[:0x20], pal, img, max_tiles=c["nt"] + extra_tiles)
    return nd
def encyclopedia_gfx(rom, K, alloc):
    t = pf_entries(bytes(rom[:0x1000000]), 0x267940)[3] if False else None
    u = lambda a: struct.unpack_from("<I", rom, a)[0]
    n0 = struct.unpack_from("<h", rom, 0x267940 + 2)[0]
    m3 = 0x267940 + 4 + 8 * n0 + u(0x267940 + 4 + 4 * n0 + 4 * 3)
    assert rom[m3:m3 + 2] == b"Pf"
    # m3.2: nav bar 240x8 (white band bg 3, text 1 + shadow 2)
    def nav(img):
        prev, back, nxt = K.ENC_NAV
        for x0, x1 in ((27, 60), (127, 170), (185, 221)):
            reg = img[0:8, x0:x1]; reg[reg == 1] = 3; reg[reg == 2] = 3
        for text, x in ((prev, 29), (back, 128), (nxt, 199)):
            m, off = line_mask(text, "Galmuri7"); draw(img, m, x, 0 - off + 0, 1, 2)
    pf_ct_store(rom, m3, 2, ct_edit(pf_ct_load(rom, m3, 2), nav), alloc)
    # m3.3: help line 240x8 (transparent bg 0, text 1)
    def helpline(img):
        img[img == 1] = 0
        m, off = line_mask(K.ENC_HELP, "Galmuri7")
        assert m.shape[1] <= 238, "help line too wide"
        draw(img, m, (240 - m.shape[1]) // 2, 0 - off, 1)
    pf_ct_store(rom, m3, 3, ct_edit(pf_ct_load(rom, m3, 3), helpline, extra_tiles=0), alloc)
    # m3.7: label rows (8px each, bg 9/8 alternating, text 4 + shadow 2)
    def labels(img):
        for row, text in K.ENC_LABELS.items():
            y0 = row * 8; bg = 9 if row % 2 == 0 else 8
            reg = img[y0:y0 + 8, 0:80]; reg[reg == 4] = bg; reg[reg == 2] = bg
            m, off = line_mask(text, "Galmuri7")
            clip = np.zeros_like(img, bool); clip[y0:y0 + 8, 0:80] = True
            draw(img, m, 4, y0 - off, 4, 2, clip)
    pf_ct_store(rom, m3, 7, ct_edit(pf_ct_load(rom, m3, 7), labels), alloc)
def apply(rom, alloc=None):
    p = os.path.join(ROOT, "work", "tr", "ko_gfx.py")
    spec = importlib.util.spec_from_file_location("kg", p); K = importlib.util.module_from_spec(spec); spec.loader.exec_module(K)
    image_results = [title_logo(rom), title_logo_pattern(rom)] + system_image_text(rom)
    # popups: map offset per type, box rectangle (rows, cols)
    boxes = {6: (0x11d0, 2, 8, 10, 22), 7: (0x1750, 2, 8, 10, 22), 5: (0xc50, 2, 8, 8, 24)}
    for typ, lines in K.POPUP.items():
        off, r0, r1, c0, c1 = boxes[typ]; popup(rom, off, r0, r1, c0, c1, lines)
    map_menu(rom, K.MENU)
    start_text(rom, 0x150, K.START["menu"])
    start_text(rom, 0x6d0, K.START["back"])
    title_menu(rom, K.TITLE)
    options_menu(rom, K)
    if alloc is not None:
        title_cards(rom, K, alloc)
        encyclopedia_gfx(rom, K, alloc)
        import native_graphics_ko, json
        report=native_graphics_ko.apply(rom,alloc)
        with open(os.path.join(ROOT,"work","validation","native_graphics_applied.json"),"w",encoding="utf-8") as f: json.dump(report,f,ensure_ascii=False,indent=2)
    used = {}
    for sub, text in K.WORLD.items():
        used["W%d" % sub] = banner(rom, "BG0W", sub, text, 15, 2, (4, 5, 7, 10, 12, 14, 15), (0, 0, 64, 16))
    for sub, text in K.PLACE.items():
        used["V%d" % sub] = banner(rom, "BG0V", sub, text, 9, 13, (3, 6, 8, 9, 11), (2, 2, 62, 14))
    for i, result in enumerate(image_results): used["image_%d" % i] = result
    return used

if __name__ == "__main__":
    # preview: patch a copy of the original ROM and render the results
    from PIL import Image
    rom = bytearray(open(os.path.join(ROOT, "Klonoa Heroes - Densetsu no Star Medal (Japan).gba"), "rb").read())
    used = apply(rom)
    print(used)
    rb = bytes(rom)
    a, _ = mapgfx.find(rb, "BG0B"); tiles = a + 0x1b90
    pals = {k: mapgfx.pal(rb, k) for k in range(11, 16)}
    def draw_map(off, out):
        img = Image.new("RGB", (240, 136), (0, 0, 0))
        for r in range(17):
            for c in range(30):
                e = struct.unpack_from("<H", rb, a + off + 64 * r + 2 * c)[0]; t = e & 0x3ff; P = pals[e >> 12]
                px = read_tile(rb, tiles + 32 * t)
                for y in range(8):
                    for x in range(8):
                        if px[y, x]: img.putpixel((c * 8 + x, r * 8 + y), P[px[y, x]])
        img.resize((720, 408), Image.NEAREST).save(out)
    for off, n in ((0x11d0, "t6"), (0x1750, "t7"), (0xc50, "t5"), (0x6d0, "menu"), (0x150, "t0")):
        draw_map(off, os.path.join(ROOT, "shots", "ko_map_%s.png" % n))
    P13 = pals[13]
    ents = [(t, s, size, aa) for t, s, size, aa in mapgfx.tag_entries(rb) if t in ("BG0V", "BG0W")]
    img = Image.new("RGB", (4 * 150, ((len(ents) + 3) // 4) * 36), (20, 20, 20))
    for i, (t, s, size, aa) in enumerate(ents):
        x0 = (i % 4) * 150 + 10; y0 = (i // 4) * 36 + 2
        for k in range(16):
            px = read_tile(rb, aa + 32 * k)
            for y in range(8):
                for x in range(8):
                    v = px[y, x]
                    if v:
                        X = x0 + ((k % 8) * 8 + x) * 2; Y = y0 + ((k // 8) * 8 + y) * 2
                        for dy in (0, 1):
                            for dx in (0, 1): img.putpixel((X + dx, Y + dy), P13[v])
    img.save(os.path.join(ROOT, "shots", "ko_banners.png"))
    print("preview written")
