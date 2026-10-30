"""Small deterministic value-noise helpers (no external deps).

`periodic_noise(x, y, period, seed)` is seamless with the given period, which
is what lets transition tiles wobble organically yet still meet their
neighbours exactly at tile borders.
"""
import math, random

def _hash(ix, iy, seed):
    r = random.Random((ix * 73856093) ^ (iy * 19349663) ^ (seed * 83492791))
    return r.random()

def _smooth(t):
    return t * t * (3 - 2 * t)

def value_noise(x, y, scale, seed, period=None):
    x, y = x / scale, y / scale
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    def h(ax, ay):
        if period:
            p = period / scale
            ax, ay = int(ax % p), int(ay % p)
        return _hash(int(ax), int(ay), seed)
    v00, v10 = h(ix, iy), h(ix + 1, iy)
    v01, v11 = h(ix, iy + 1), h(ix + 1, iy + 1)
    sx, sy = _smooth(fx), _smooth(fy)
    return (v00 * (1 - sx) + v10 * sx) * (1 - sy) + (v01 * (1 - sx) + v11 * sx) * sy

def fbm(x, y, scale, seed, octaves=3, period=None):
    v, amp, tot, s = 0.0, 1.0, 0.0, scale
    for o in range(octaves):
        v += value_noise(x, y, s, seed + o * 101, period) * amp
        tot += amp
        amp *= 0.5
        s /= 2
    return v / tot
