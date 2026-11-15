#!/usr/bin/env python3
"""Cluster byte differences between two same-size PE32 files and map them to sections/VAs."""
import struct, sys

def sections(data):
    pe = struct.unpack_from('<I', data, 0x3c)[0]
    nsec = struct.unpack_from('<H', data, pe + 6)[0]
    optsz = struct.unpack_from('<H', data, pe + 20)[0]
    imagebase = struct.unpack_from('<I', data, pe + 24 + 28)[0]
    secs = []
    off = pe + 24 + optsz
    for i in range(nsec):
        name = data[off:off+8].rstrip(b'\0').decode()
        vsize, va, rawsize, rawptr = struct.unpack_from('<IIII', data, off + 8)
        secs.append((name, va, vsize, rawptr, rawsize))
        off += 40
    return imagebase, secs

def off2va(imagebase, secs, o):
    for name, va, vsize, rawptr, rawsize in secs:
        if rawptr <= o < rawptr + rawsize:
            return name, imagebase + va + (o - rawptr)
    return '?', None

a = open(sys.argv[1], 'rb').read()
b = open(sys.argv[2], 'rb').read()
gap = int(sys.argv[3]) if len(sys.argv) > 3 else 8
ib, secs = sections(a)
print('imagebase %08x' % ib)
for s in secs:
    print('  %-8s va=%08x vsize=%08x raw=%08x rawsize=%08x' % s)
diffs = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
clusters = []
for d in diffs:
    if clusters and d - clusters[-1][1] <= gap:
        clusters[-1][1] = d
    else:
        clusters.append([d, d])
print('diff bytes', len(diffs), 'clusters', len(clusters))
for s, e in clusters:
    name, va = off2va(ib, secs, s)
    n = sum(1 for i in range(s, e + 1) if a[i] != b[i])
    print('%s %08x len=%4d changed=%4d  old=%s  new=%s' % (
        name, va or 0, e - s + 1, n,
        a[s:e+1].hex()[:48], b[s:e+1].hex()[:48]))
