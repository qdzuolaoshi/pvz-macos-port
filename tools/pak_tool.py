#!/usr/bin/env python3
"""List or extract a PopCap main.pak (XOR 0xF7 obfuscated) archive.

usage: pak_tool.py list <main.pak>
       pak_tool.py extract <main.pak> <outdir>
"""
import os, struct, sys


def read_index(path):
    raw = open(path, 'rb').read()
    data = bytes(b ^ 0xF7 for b in raw)
    if data[:4] != b'\xc0\x4a\xc0\xba':
        raise SystemExit('bad pak signature')
    if struct.unpack_from('<I', data, 4)[0] != 0:
        raise SystemExit('unsupported pak version')
    pos = 8
    entries = []
    while True:
        flags = data[pos]; pos += 1
        if flags & 0x80:
            break
        n = data[pos]; pos += 1
        name = data[pos:pos + n].decode('latin-1'); pos += n
        size = struct.unpack_from('<I', data, pos)[0]; pos += 4
        pos += 8  # FILETIME
        entries.append((name, size))
    out = []
    for name, size in entries:
        out.append((name, data[pos:pos + size]))
        pos += size
    return out


def main():
    cmd, pak = sys.argv[1], sys.argv[2]
    entries = read_index(pak)
    if cmd == 'list':
        for name, blob in entries:
            print('%9d  %s' % (len(blob), name))
        print('files:', len(entries))
    elif cmd == 'extract':
        outdir = sys.argv[3]
        for name, blob in entries:
            rel = name.replace('\\', '/')
            dst = os.path.join(outdir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f:
                f.write(blob)
        print('extracted', len(entries), 'files to', outdir)


if __name__ == '__main__':
    main()
