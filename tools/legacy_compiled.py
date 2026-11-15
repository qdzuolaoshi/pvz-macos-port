#!/usr/bin/env python3
"""Validate the 32-bit PvZ 1.0.0.1051 compiled-definition layout against every
compiled/*.compiled file of a pak extraction.

usage: legacy_compiled.py <dir containing compiled/>
"""
import os, struct, sys, zlib

# Legacy (32-bit) struct layouts: declaration order, each field 4 bytes, tracks/arrays 8 bytes.
def layout(decl):
    off, offs = 0, {}
    for name, kind in decl:
        offs[name] = off
        off += 8 if kind in ('track', 'array') else 4
    return offs, off

TRANSFORM_DECL = [(n, 'float') for n in ('x', 'y', 'kx', 'ky', 'sx', 'sy', 'f', 'a')] + \
    [('i', 'image'), ('font', 'font'), ('text', 'string')]
TRACK_DECL = [('name', 'string'), ('t', 'array')]
REANIM_DECL = [('track', 'array'), ('fps', 'float'), ('atlas', 'ptr')]
FIELD_DECL = [('FieldType', 'int'), ('x', 'track'), ('y', 'track')]
EMIT_TRACKS1 = ['SystemDuration', 'CrossFadeDuration', 'SpawnRate', 'SpawnMinActive', 'SpawnMaxActive',
                'SpawnMaxLaunched', 'EmitterRadius', 'EmitterOffsetX', 'EmitterOffsetY', 'EmitterBoxX',
                'EmitterBoxY', 'EmitterSkewX', 'EmitterSkewY', 'EmitterPath', 'ParticleDuration',
                'LaunchSpeed', 'LaunchAngle', 'SystemRed', 'SystemGreen', 'SystemBlue', 'SystemAlpha',
                'SystemBrightness']
EMIT_TRACKS2 = ['ParticleRed', 'ParticleGreen', 'ParticleBlue', 'ParticleAlpha', 'ParticleBrightness',
                'ParticleSpinAngle', 'ParticleSpinSpeed', 'ParticleScale', 'ParticleStretch',
                'CollisionReflect', 'CollisionSpin', 'ClipTop', 'ClipBottom', 'ClipLeft', 'ClipRight',
                'AnimationRate']
EMITTER_DECL = [('Image', 'image'), ('ImageCol', 'int'), ('ImageRow', 'int'), ('ImageFrames', 'int'),
                ('Animated', 'int'), ('ParticleFlags', 'int'), ('EmitterType', 'int'), ('Name', 'string'),
                ('OnDuration', 'string')] + [(n, 'track') for n in EMIT_TRACKS1] + \
    [('Field', 'array'), ('SystemField', 'array')] + [(n, 'track') for n in EMIT_TRACKS2]
PARTICLE_DECL = [('Emitter', 'array')]
TRAIL_DECL = [('Image', 'image'), ('MaxPoints', 'int'), ('MinPointDistance', 'float'), ('TrailFlags', 'int'),
              ('TrailDuration', 'track'), ('WidthOverLength', 'track'), ('WidthOverTime', 'track'),
              ('AlphaOverLength', 'track'), ('AlphaOverTime', 'track')]

# DefMap field order (fixup order) as in PvZ-Portable Definition.cpp.
TRANSFORM_MAP = [n for n, _ in TRANSFORM_DECL]
TRACK_MAP = ['name', 't']
REANIM_MAP = ['track', 'fps']
FIELD_MAP = ['FieldType', 'x', 'y']
EMITTER_MAP = ['Image', 'ImageRow', 'ImageCol', 'ImageFrames', 'Animated', 'ParticleFlags', 'EmitterType',
               'Name', 'SystemDuration', 'OnDuration', 'CrossFadeDuration', 'SpawnRate', 'SpawnMinActive',
               'SpawnMaxActive', 'SpawnMaxLaunched', 'EmitterRadius', 'EmitterOffsetX', 'EmitterOffsetY',
               'EmitterBoxX', 'EmitterBoxY', 'EmitterPath', 'EmitterSkewX', 'EmitterSkewY', 'ParticleDuration',
               'SystemRed', 'SystemGreen', 'SystemBlue', 'SystemAlpha', 'SystemBrightness', 'LaunchSpeed',
               'LaunchAngle', 'Field', 'SystemField', 'ParticleRed', 'ParticleGreen', 'ParticleBlue',
               'ParticleAlpha', 'ParticleBrightness', 'ParticleSpinAngle', 'ParticleSpinSpeed', 'ParticleScale',
               'ParticleStretch', 'CollisionReflect', 'CollisionSpin', 'ClipTop', 'ClipBottom', 'ClipLeft',
               'ClipRight', 'AnimationRate']
PARTICLE_MAP = ['Emitter']
TRAIL_MAP = ['Image', 'MaxPoints', 'MinPointDistance', 'TrailFlags', 'WidthOverLength', 'WidthOverTime',
             'AlphaOverLength', 'AlphaOverTime', 'TrailDuration']

class Schema:
    def __init__(self, decl, fmap, sub=None):
        self.kinds = dict(decl)
        self.offs, self.size = layout(decl)
        self.fmap = fmap
        self.sub = sub or {}

TRANSFORM = Schema(TRANSFORM_DECL, TRANSFORM_MAP)
TRACK = Schema(TRACK_DECL, TRACK_MAP, {'t': TRANSFORM})
REANIM = Schema(REANIM_DECL, REANIM_MAP, {'track': TRACK})
FIELD = Schema(FIELD_DECL, FIELD_MAP)
EMITTER = Schema(EMITTER_DECL, EMITTER_MAP, {'Field': FIELD, 'SystemField': FIELD})
PARTICLE = Schema(PARTICLE_DECL, PARTICLE_MAP, {'Emitter': EMITTER})
TRAIL = Schema(TRAIL_DECL, TRAIL_MAP)


class Reader:
    def __init__(self, buf):
        self.b, self.p = buf, 0
    def i32(self):
        v = struct.unpack_from('<i', self.b, self.p)[0]; self.p += 4; return v
    def raw(self, n):
        v = self.b[self.p:self.p + n]; self.p += n
        if len(v) != n:
            raise ValueError('short read')
        return v


def read_obj(r, schema, raw):
    obj = {}
    for name in schema.fmap:
        kind = schema.kinds[name]
        off = schema.offs[name]
        if kind in ('string', 'image', 'font'):
            n = r.i32()
            if n < 0 or n > 4096:
                raise ValueError('bad string len %d for %s' % (n, name))
            obj[name] = r.raw(n).decode('latin-1')
        elif kind == 'track':
            cnt_struct = struct.unpack_from('<i', raw, off + 4)[0]
            n = r.i32()
            if n != cnt_struct or n < 0 or n > 1000:
                raise ValueError('track count mismatch %s %d/%d' % (name, n, cnt_struct))
            obj[name] = [struct.unpack('<fffii', r.raw(20)) for _ in range(n)]
        elif kind == 'array':
            cnt = struct.unpack_from('<i', raw, off + 4)[0]
            sub = schema.sub[name]
            dsize = r.i32()
            if dsize != sub.size:
                raise ValueError('array %s defsize %d != %d' % (name, dsize, sub.size))
            raws = [r.raw(sub.size) for _ in range(cnt)]
            obj[name] = [read_obj(r, sub, rw) for rw in raws]
        elif kind == 'float':
            obj[name] = struct.unpack_from('<f', raw, off)[0]
        else:
            obj[name] = struct.unpack_from('<i', raw, off)[0]
    return obj


def parse(path, schema):
    data = open(path, 'rb').read()
    cookie, usize = struct.unpack_from('<II', data, 0)
    assert cookie == 0xDEADFED4
    buf = zlib.decompress(data[8:])
    assert len(buf) == usize
    r = Reader(buf)
    r.i32()  # schema hash
    raw = r.raw(schema.size)
    obj = read_obj(r, schema, raw)
    if r.p != len(buf):
        raise ValueError('consumed %d of %d' % (r.p, len(buf)))
    return obj


def schema_for(name):
    if name.endswith('.reanim.compiled'):
        return REANIM
    if name.endswith('.trail.compiled'):
        return TRAIL
    return PARTICLE


if __name__ == '__main__':
    root = sys.argv[1]
    ok = bad = 0
    for dp, _, fns in os.walk(os.path.join(root, 'compiled')):
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            try:
                o = parse(p, schema_for(fn))
                ok += 1
            except Exception as e:
                bad += 1
                print('FAIL', fn, e)
    print('ok', ok, 'bad', bad)
    print(REANIM.size, TRACK.size, TRANSFORM.size, EMITTER.size, FIELD.size, PARTICLE.size, TRAIL.size)
