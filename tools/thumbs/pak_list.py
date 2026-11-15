"""Read-only PopCap .pak lister/extractor (XOR 0xF7 obfuscated).

usage: python3 -I pak_list.py <main.pak> <substring> [outdir]
Lists entries whose name contains <substring> (case-insensitive); if outdir
is given, writes those entries there (flattened path with '/' -> '__').
"""
import hashlib
import os
import struct
import sys


def main():
    pak, sub = sys.argv[1], sys.argv[2].lower()
    outdir = sys.argv[3] if len(sys.argv) > 3 else None
    raw = open(pak, "rb").read()
    data = bytes(b ^ 0xF7 for b in raw)
    magic, ver = struct.unpack_from("<II", data, 0)
    assert magic == 0xBAC04AC0, hex(magic)
    pos = 8
    entries = []
    while True:
        flags = data[pos]
        pos += 1
        if flags & 0x80:
            break
        nlen = data[pos]
        pos += 1
        name = data[pos:pos + nlen].decode("latin-1")
        pos += nlen
        size, ftime = struct.unpack_from("<IQ", data, pos)
        pos += 12
        entries.append((name, size))
    off = pos
    for name, size in entries:
        if sub in name.lower():
            blob = data[off:off + size]
            print(f"{hashlib.sha256(blob).hexdigest()[:16]}  {size:8d}  {name}")
            if outdir:
                os.makedirs(outdir, exist_ok=True)
                fn = name.replace("\\", "/").replace("/", "__")
                with open(os.path.join(outdir, fn), "wb") as f:
                    f.write(blob)
        off += size
    print(f"# {len(entries)} entries total", file=sys.stderr)


if __name__ == "__main__":
    main()
