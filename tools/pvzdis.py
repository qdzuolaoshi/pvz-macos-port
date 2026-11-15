#!/usr/bin/env python3
"""Disassemble helpers for PvZ 1.0.0.1051 exe pairs (original vs 95 mod)."""
import sys, struct, pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

import os
D = os.environ.get('PVZ_GAME_DIR', 'game').rstrip('/') + '/'   # folder with both exe files of your own game copy
ORIG = open(D + 'PlantsVsZombies(原版启动).exe', 'rb').read()
MOD = open(D + 'PlantsVsZombies.exe', 'rb').read()
pe = pefile.PE(data=ORIG, fast_load=True)
IB = pe.OPTIONAL_HEADER.ImageBase
SECS = [(s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData) for s in pe.sections]
md = Cs(CS_ARCH_X86, CS_MODE_32)

def va2off(va):
    rva = va - IB
    if rva < 0x1000:
        return rva
    for v, vs, rp, rs in SECS:
        if v <= rva < v + max(vs, rs):
            return rp + rva - v
    raise ValueError(hex(va))

def dis(data, va, n, stop_on_ret=False, maxins=400):
    off = va2off(va)
    out = []
    for i, ins in enumerate(md.disasm(data[off:off + n], va)):
        out.append('  %08x  %-22s %s %s' % (ins.address, ins.bytes.hex(), ins.mnemonic, ins.op_str))
        if stop_on_ret and ins.mnemonic in ('ret', 'retn'):
            break
        if i > maxins:
            break
    return '\n'.join(out)

def u32(data, va):
    return struct.unpack_from('<I', data, va2off(va))[0]

def i32(data, va):
    return struct.unpack_from('<i', data, va2off(va))[0]

if __name__ == '__main__':
    which = sys.argv[1]
    va = int(sys.argv[2], 16)
    n = int(sys.argv[3], 0) if len(sys.argv) > 3 else 0x40
    if which in ('o', 'b'):
        print('--- ORIG %08x' % va)
        print(dis(ORIG, va, n))
    if which in ('m', 'b'):
        print('--- MOD %08x' % va)
        print(dis(MOD, va, n))


def func_start(data, va, limit=0x4000):
    """Heuristic: walk back to the byte after a run of >=2 int3 (0xCC) padding bytes."""
    off = va2off(va)
    for o in range(off, max(off - limit, 0x1000), -1):
        if data[o - 1] == 0xCC and data[o - 2] == 0xCC and data[o] != 0xCC:
            return va - (off - o)
    return None


def callers(data, target, text_lo=0x401000, text_hi=0x652000):
    """Find E8/E9 rel32 call/jmp sites in .text that target `target`."""
    res = []
    lo, hi = va2off(text_lo), va2off(text_hi - 1)
    for o in range(lo, hi - 5):
        if data[o] in (0xE8, 0xE9):
            rel = struct.unpack_from('<i', data, o + 1)[0]
            src = text_lo + (o - lo)
            if src + 5 + rel == target:
                res.append(src)
    return res
