"""Download the PixelLab protagonist (rotations + every animation group) into assets/pixellab/src/hero/.
Layout: rotations/<dir>.png, <animation>/<dir>/<i>.png. Files are what PixelLab rendered; the game sheet is built from them
by tools/pixelart/pl_hero.py."""
import os, re, sys, urllib.request
sys.path.insert(0, os.path.dirname(__file__))
from mcp import MCP, text_of

CHAR = 'eac84316-f0c4-4dea-b6a4-5086b838c049'
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'assets/pixellab/src/hero')


def get(url, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'mosslight'}), timeout=60) as r: open(path, 'wb').write(r.read())


def main():
    t = text_of(MCP().call('get_character', {'character_id': CHAR}))
    os.makedirs(OUT, exist_ok=True); open(os.path.join(OUT, 'character.txt'), 'w').write(t)
    for d, url in re.findall(r'^\s+(south|east|north|west): (https://\S+/rotations/\S+)$', t, re.M):
        get(url, os.path.join(OUT, 'rotations', d + '.png'))
    anim = None; n = 0
    for line in t.splitlines():
        h = re.match(r'^\s+([\w-]+) — (\d) dir .*?(\d+)f', line)
        if h: anim = h.group(1); nf = int(h.group(3)); continue
        u = re.match(r'^\s+(south|east|north|west): (https://\S+\{i\}\.png\S*)', line)
        if u and anim:
            for i in range(nf):
                p = os.path.join(OUT, anim, u.group(1), f'{i}.png')
                if not os.path.exists(p): get(u.group(2).replace('{i}', str(i)), p); n += 1
    print('downloaded', n, 'frames')


if __name__ == '__main__': main()
