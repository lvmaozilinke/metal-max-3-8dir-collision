#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pack.py -- Metal Max 3 (NDS) ARM9 image codec.

Format reverse engineered from the 16 KB plaintext boot stub at 0x02000800
(ROM 0x4000) -- see REPORT.md.

The ROM's ARM9 area (ROM 0x4000..0x4000+ARM9SIZE) is loaded verbatim by the
DS loader to RAM 0x02000000.  Its first 0x4000 bytes are a plaintext stub
that decompresses the rest *in place*, backwards.

Stored layout of the ARM9 area (offsets relative to RAM 0x02000000):

    +0x0000 .. +0x4000        plaintext CRT0/MMU stub (executed first)
    +0x4000 .. +a             verbatim (raw) prefix of the image   [a >= 0x4000]
    +a      .. +a+C           compressed block, C bytes:
                                 [C-9]  : payload (tokens) -- read descending
                                 [C-9]  : 1 pad byte, never read
                                 [C-8:C]: 8-byte footer
    +a+C    .. +ARM9SIZE      don't care (overwritten by decompression)

Footer (little endian, at RAM dest-8 where dest = 0x02000000 + a + C):

    u32 w    = C | (extra << 24)      extra = 9  (8-byte footer + 1 quirk byte)
    u32 size = P - C                  P = total decompressed length

The stub then writes the decompressed stream of length P to
[a, a+P) i.e. [dest-C, dest+P-C), reading the token stream downwards from
dest-extra-1 down to dest-C.

Token format (all read from high address to low address):
    flag byte: bit7 = first token, bit6 = second, ... (8 tokens per flag byte)
    literal : 1 data byte
    match   : byte A (read first), byte B
              w = (A<<8)|B ; len = (A>>4)+3 (3..18) ; dist = (w & 0xFFF)+3 (3..4098)
              for k in range(len): out[wptr-1] = out[wptr+dist] ; wptr -= 1
"""

import struct
import sys

BASE = 0x02000000          # RAM address the ARM9 area is loaded at
DEST_FIELD_OFF = 0xB9C     # image offset of the 'dest' word used by the stub
EXTRA = 9                  # bytes skipped at the top of the compressed block
ARM9_SIZE_DEFAULT = 0xD1AF8  # header ARM9 size of mm3_test.nds


# --------------------------------------------------------------------------
# decoder
# --------------------------------------------------------------------------
def decode(region, arm9_size=None):
    """Decode a raw ARM9 area (bytes as loaded at RAM 0x02000000) -> image.

    `region` must start at image offset 0 (i.e. be ROM[0x4000:0x4000+ARM9SIZE]).
    Returns the fully decompressed image, length = a + P.
    """
    region = bytes(region)
    if arm9_size is None:
        arm9_size = len(region)
    dest = struct.unpack_from('<I', region, DEST_FIELD_OFF)[0]
    dest_off = dest - BASE
    if not (0x4000 <= dest_off <= len(region)):
        raise ValueError('bad dest 0x%08X' % dest)
    w, size = struct.unpack_from('<II', region, dest_off - 8)
    C = w & 0xFFFFFF
    extra = w >> 24
    a = dest_off - C
    if a < 0:
        raise ValueError('compsize larger than dest offset')
    r = dest_off - extra      # first byte read is r-1
    start = a                 # read stops when r <= start
    P = C + size              # total decompressed length (proved below)
    out = bytearray(P)
    p = P                     # write index into out
    while r > start:
        r -= 1
        flags = region[r]
        for _ in range(8):
            if flags & 0x80:
                A = region[r - 1]
                B = region[r - 2]
                r -= 2
                dist = (((A << 8) | B) & 0xFFF) + 3
                ln = (A >> 4) + 3
                for _ in range(ln):
                    p -= 1
                    out[p] = out[p + dist]
            else:
                r -= 1
                p -= 1
                out[p] = region[r]
            flags = (flags << 1) & 0xFF
            if r <= start:
                break
    if p != 0:
        raise ValueError('decoded %d bytes but expected %d' % (P - p, P))
    return region[:a] + bytes(out)


# --------------------------------------------------------------------------
# encoder
# --------------------------------------------------------------------------
def _lz77_tokens(R, max_chain=48, lazy=True):
    """Greedy/lazy LZ77 parse of R (the reversed image).

    Returns a list of tokens: ('L', bytevalue) or ('M', length, dist)
    with 3<=length<=18 and 3<=dist<=4098 (dist = distance in R).
    A match at output position j copies R[j-dist] .. byte by byte (overlap ok).
    """
    n = len(R)
    last = {}
    toks = []
    i = 0
    MAXLEN = 18
    MAXDIST = 4098
    MINLEN = 3

    def best(pos):
        if pos + MINLEN > n:
            return (0, 0)
        key = R[pos:pos + 3]
        lst = last.get(key)
        if not lst:
            return (0, 0)
        bl = MINLEN - 1
        bd = 0
        lo = pos - MAXDIST
        cnt = 0
        for p in reversed(lst):
            if p < lo:
                break
            if pos - p < 3:          # format cannot express distances < 3
                continue
            cnt += 1
            if cnt > max_chain:
                break
            # quick reject using the current best length
            if (bl >= MINLEN and pos + bl < n and p + bl < n
                    and R[p + bl] != R[pos + bl]):
                continue
            l = 3
            m = n - pos
            lim = MAXLEN if MAXLEN < m else m
            while l < lim and R[p + l] == R[pos + l]:
                l += 1
            if l > bl:
                bl = l
                bd = pos - p
                if l >= MAXLEN:
                    break
        if bl < MINLEN:
            return (0, 0)
        return (bl, bd)

    while i < n:
        ln, d = best(i)
        if ln and lazy and i + 1 < n:
            ln2, d2 = best(i + 1)
            if ln2 > ln:
                toks.append(('L', R[i]))
                last.setdefault(R[i:i + 3], []).append(i)
                i += 1
                ln, d = ln2, d2
        if ln:
            toks.append(('M', ln, d))
            for k in range(ln):
                q = i + k
                if q + 3 <= n:
                    last.setdefault(R[q:q + 3], []).append(q)
            i += ln
        else:
            toks.append(('L', R[i]))
            if i + 3 <= n:
                last.setdefault(R[i:i + 3], []).append(i)
            i += 1
    return toks


def _pack_tokens(toks):
    """Token list (in decode order) -> consumed byte stream (decode order)."""
    out = bytearray()
    i = 0
    n = len(toks)
    while i < n:
        flags = 0
        grp = toks[i:i + 8]
        body = bytearray()
        for k, t in enumerate(grp):
            if t[0] == 'M':
                flags |= 0x80 >> k
                ln, d = t[1], t[2]
                v = d - 3                      # 0..4095
                A = ((ln - 3) << 4) | (v >> 8)
                B = v & 0xFF
                body.append(A)
                body.append(B)
            else:
                body.append(t[1])
        out.append(flags)
        out += body
        i += 8
    return bytes(out)


def encode(image, a=0x4000, arm9_size=ARM9_SIZE_DEFAULT, max_chain=48, lazy=True,
           allow_gap=False):
    """Encode an ARM9 image into a raw ARM9 area of `arm9_size` bytes.

    image[a:] is compressed; image[:a] is stored verbatim (a >= 0x4000 is
    required because the first 0x4000 bytes are the executing stub).
    Returns (region, info dict).
    """
    image = bytes(image)
    if a < 0x4000:
        raise ValueError('a must be >= 0x4000 (stub must stay plaintext)')
    S = image[a:]
    R = S[::-1]
    toks = _lz77_tokens(R, max_chain=max_chain, lazy=lazy)
    cons = _pack_tokens(toks)
    C = len(cons) + 9
    P = len(S)
    if a + C > arm9_size:
        limit = arm9_size
        raise ValueError('does not fit: need %d bytes (0x%X), slot has %d (0x%X); '
                         'over by %d' % (a + C, a + C, limit, limit, a + C - limit))
    size_field = P - C
    dest = BASE + a + C
    stored = cons[::-1] + b'\xFF' + struct.pack('<II', C | (EXTRA << 24), size_field)
    assert len(stored) == C
    region = bytearray(arm9_size)
    region[:a] = image[:a]
    struct.pack_into('<I', region, DEST_FIELD_OFF, dest)
    region[a:a + C] = stored
    info = dict(a=a, C=C, P=P, size_field=size_field, dest=dest,
                used=a + C, slot=arm9_size, margin=arm9_size - (a + C),
                tokens=len(toks), ratio=C / P)
    return bytes(region), info


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def rom_arm9_region(rom):
    """Return (offset, size, bytes) of the ARM9 area described by an NDS header."""
    off, size = struct.unpack_from('<II', rom, 0x20)[0], struct.unpack_from('<I', rom, 0x2C)[0]
    return off, size, rom[off:off + size]


def patch_rom(rom, image, a=0x4000, max_chain=512, lazy=True):
    """Rebuild a whole ROM with `image` injected as the ARM9 binary.

    Returns (new_rom, info).  Only ROM[arm9_off : arm9_off+arm9_size] changes;
    the NDS header and every other byte are preserved.
    """
    off, size, reg = rom_arm9_region(rom)
    old = decode(reg)
    if len(image) != len(old):
        raise ValueError('image length must stay 0x%X (got 0x%X): the autoload '
                         'table address 0x02117FC0 is hard-coded in the stub'
                         % (len(old), len(image)))
    newreg, info = encode(image, a=a, arm9_size=size, max_chain=max_chain, lazy=lazy)
    out = bytearray(rom)
    out[off:off + size] = newreg
    info['arm9_off'] = off
    info['arm9_size'] = size
    return bytes(out), info


def _selftest(rom_path):
    rom = open(rom_path, 'rb').read()
    off, size, reg = rom_arm9_region(rom)
    img = decode(reg)
    print('ROM %s (%d bytes)' % (rom_path, len(rom)))
    print('ARM9 area: ROM 0x%X..0x%X (0x%X bytes), dest=0x%08X from image+0xB9C'
          % (off, off + size, size, struct.unpack_from('<I', img, 0xB9C)[0]))
    print('decoded image: 0x%X bytes' % len(img))
    newreg, info = encode(img, max_chain=512)
    exp = bytearray(img)
    struct.pack_into('<I', exp, 0xB9C, info['dest'])
    got = decode(newreg)
    print('re-encoded: C=0x%X used=0x%X slot=0x%X margin=%d bytes ratio=%.5f'
          % (info['C'], info['used'], info['slot'], info['margin'], info['ratio']))
    print('round trip byte-exact (only image+0xB9C recomputed):', got == bytes(exp))
    return 0 if got == bytes(exp) else 1


def main(argv):
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print('usage: pack.py selftest ROM')
        print('       pack.py decode   ROM OUT_IMAGE')
        print('       pack.py encode   IMAGE OUT_REGION')
        print('       pack.py patch    ROM IMAGE OUT_ROM [a] [max_chain]')
        return 0
    cmd = argv[1]
    if cmd == 'selftest':
        return _selftest(argv[2])
    if cmd == 'decode':
        rom = open(argv[2], 'rb').read()
        off, size, reg = rom_arm9_region(rom)
        open(argv[3], 'wb').write(decode(reg))
        print('wrote', argv[3])
        return 0
    if cmd == 'encode':
        img = open(argv[2], 'rb').read()
        reg, info = encode(img, max_chain=512)
        open(argv[3], 'wb').write(reg)
        print('C=0x%X used=0x%X margin=%d -> %s'
              % (info['C'], info['used'], info['margin'], argv[3]))
        return 0
    if cmd == 'patch':
        rom = open(argv[2], 'rb').read()
        img = open(argv[3], 'rb').read()
        a = int(argv[5], 0) if len(argv) > 5 else 0x4000
        mc = int(argv[6], 0) if len(argv) > 6 else 512
        out, info = patch_rom(rom, img, a=a, max_chain=mc)
        open(argv[4], 'wb').write(out)
        print('wrote %s (%d bytes); ARM9 area 0x%X..0x%X, C=0x%X, margin=%d'
              % (argv[4], len(out), info['arm9_off'],
                 info['arm9_off'] + info['arm9_size'], info['C'], info['margin']))
        return 0
    print('unknown command', cmd)
    return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
