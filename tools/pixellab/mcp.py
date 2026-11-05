"""Minimal client for PixelLab's official MCP server (https://api.pixellab.ai/mcp), used from build scripts.

The key is read from $PIXL_API_KEY or ~/.config/mosslight/pixellab.env and never printed or written to the repo.

    python3 tools/pixellab/mcp.py list                 # tool names and their argument schemas
    python3 tools/pixellab/mcp.py call NAME '{json}'   # call a tool, print the result
"""
import json, os, sys, urllib.request

URL = 'https://api.pixellab.ai/mcp'


def _key():
    k = os.environ.get('PIXL_API_KEY')
    if not k:
        p = os.path.expanduser('~/.config/mosslight/pixellab.env')
        for line in open(p):
            if line.startswith('PIXL_API_KEY='): k = line.split('=', 1)[1].strip()
    return k


class MCP:
    def __init__(self):
        self.key = _key(); self.sid = None; self.n = 0
        r = self._post({'jsonrpc': '2.0', 'id': self._id(), 'method': 'initialize',
                        'params': {'protocolVersion': '2025-03-26', 'capabilities': {}, 'clientInfo': {'name': 'mosslight-build', 'version': '1'}}})
        self._post({'jsonrpc': '2.0', 'method': 'notifications/initialized'}, notify=True)

    def _id(self):
        self.n += 1; return self.n

    def _post(self, body, notify=False, timeout=300):
        h = {'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream'}
        if self.sid: h['Mcp-Session-Id'] = self.sid
        req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=h, method='POST')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            sid = resp.headers.get('Mcp-Session-Id')
            if sid: self.sid = sid
            raw = resp.read().decode('utf-8', 'replace')
        if notify: return None
        msgs = []
        for line in raw.splitlines():
            if line.startswith('data:'):
                try: msgs.append(json.loads(line[5:].strip()))
                except Exception: pass
        if not msgs and raw.strip().startswith('{'): msgs = [json.loads(raw)]
        for m in msgs:
            if m.get('id') == body.get('id'): return m
        return msgs[-1] if msgs else None

    def list(self):
        return self._post({'jsonrpc': '2.0', 'id': self._id(), 'method': 'tools/list', 'params': {}})['result']['tools']

    def call(self, name, args):
        r = self._post({'jsonrpc': '2.0', 'id': self._id(), 'method': 'tools/call', 'params': {'name': name, 'arguments': args}})
        if 'error' in r: raise RuntimeError(r['error'])
        return r['result']


if __name__ == '__main__':
    m = MCP()
    if sys.argv[1] == 'list':
        for t in m.list():
            props = t.get('inputSchema', {}).get('properties', {})
            print('-', t['name'], ':', (t.get('description') or '').split('\n')[0][:160])
            print('   args:', ', '.join(f"{k}{'*' if k in t.get('inputSchema', {}).get('required', []) else ''}" for k in props))
    elif sys.argv[1] == 'call':
        print(json.dumps(m.call(sys.argv[2], json.loads(sys.argv[3] if len(sys.argv) > 3 else '{}')), indent=1)[:4000])


# ---------------------------------------------------------------- helpers for the art pipeline
def palette_hex(*fams):
    """The game's own colours (day table) for the given palette families, as '#rrggbb' strings. Art generated on these
    colours maps exactly back onto palette indices, so night, season and weather tables keep working."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    from pixelart.palette import PAL
    out = []
    for f in fams:
        for r in range(len(PAL.ramp(f))):
            rgb = PAL.day[PAL.index[(f, r)]]; out.append('#%02x%02x%02x' % tuple(int(v) for v in rgb[:3]))
    return out


def text_of(result):
    return '\n'.join(c.get('text', '') for c in result.get('content', []) if c.get('type') == 'text')


def download(job_id, out_dir, n, prefix='cand'):
    """Fetch every candidate of a finished image job (waits politely while it is still running)."""
    import time
    os.makedirs(out_dir, exist_ok=True); key = _key(); paths = []
    for i in range(n):
        url = f'{URL}/images/{job_id}/download?index={i}'
        for attempt in range(60):
            req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + key})
            try:
                with urllib.request.urlopen(req, timeout=120) as r: data = r.read(); break
            except urllib.error.HTTPError as e:
                if e.code in (423, 425, 429, 202): time.sleep(int(e.headers.get('Retry-After') or 10)); continue
                raise
        p = os.path.join(out_dir, f'{prefix}_{i:02d}.png'); open(p, 'wb').write(data); paths.append(p)
    return paths


def contact_sheet(paths, out, z=4, bg=(88, 151, 59)):
    """All candidates side by side on a meadow-green ground, numbered, scaled up for review."""
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert('RGBA') for p in paths]
    cw = max(i.width for i in ims); ch = max(i.height for i in ims); cols = min(len(ims), 5); rows = (len(ims) + cols - 1) // cols
    sheet = Image.new('RGBA', (cols * (cw + 4) + 4, rows * (ch + 12) + 4), bg + (255,))
    d = ImageDraw.Draw(sheet)
    for k, im in enumerate(ims):
        x = 4 + (k % cols) * (cw + 4); y = 4 + (k // cols) * (ch + 12)
        sheet.alpha_composite(im, (x, y + 8)); d.text((x, y - 2), str(k), fill=(255, 255, 255, 255))
    sheet = sheet.resize((sheet.width * z, sheet.height * z), Image.NEAREST); sheet.save(out); return out
