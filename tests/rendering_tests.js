// Calm-rendering and day-length tests (Prompt 16 rendering pass).
// Run: NODE_PATH=<nm> PORT=8777 node tests/rendering_tests.js
const { chromium } = require('playwright'); const fs = require('fs'); const zlib = require('zlib');
const PORT = process.env.PORT || 8777; const results = [];
function check(name, ok, detail) { results.push({ name, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail !== undefined ? '  — ' + detail : '')); }
const J = p => JSON.parse(fs.readFileSync('/root/mosslight/' + p, 'utf8'));
(async () => {
  // ---- sprites: few pixels, few tones (read the shipped PNGs through a browser canvas)
  const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 2000, height: 1300 } }); const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(`http://127.0.0.1:${PORT}/preview/play.html?lab=1&new=1`); await p.waitForFunction(() => window.BOOTED, null, { timeout: 60000 });
  const ev = (f, a) => p.evaluate(f, a);
  const sprites = await ev(async () => { const out = {}; for (const n of ['oak_0', 'oak_1', 'oak_2', 'oak_3', 'birch_0', 'birch_1', 'pine_0', 'pine_1', 'willow_0', 'rowan_0', 'shrub_0', 'shrub_1', 'fern_0']) { const im = new Image(); im.src = `../assets/objects/${n}.png`; await im.decode(); const c = document.createElement('canvas'); c.width = im.width; c.height = im.height; const g = c.getContext('2d'); g.drawImage(im, 0, 0); const d = g.getImageData(0, 0, im.width, im.height).data; const cols = new Set(); let px = 0; for (let i = 0; i < d.length; i += 4) if (d[i + 3] > 0) { px++; cols.add((d[i] << 16) | (d[i + 1] << 8) | d[i + 2]); } out[n] = { w: im.width, h: im.height, px, cols: cols.size }; } return out; });
  const oaks = ['oak_0', 'oak_1', 'oak_2', 'oak_3'].map(n => sprites[n]);
  check('oaks stay tree-sized beside the camper (PixelLab pilot: ≤ 3000 px, ≤ 14 colours, ≤ 80 px tall, ≤ 72 wide)', oaks.every(o => o.px <= 3000 && o.cols <= 14 && o.h <= 80 && o.w <= 72), JSON.stringify(oaks.map(o => `${o.w}x${o.h} ${o.px}px ${o.cols}c`)));
  check('every tree is posterised to a handful of tones (≤ 10 colours) and pines/birches stay slim', ['birch_0', 'birch_1', 'pine_0', 'pine_1', 'willow_0', 'rowan_0'].every(n => sprites[n].cols <= 10), ['birch_0', 'pine_1', 'willow_0', 'rowan_0'].map(n => `${n} ${sprites[n].px}px ${sprites[n].cols}c`).join(', '));
  check('shrubs and ferns stay small beside the camper (≤ 800 px)', ['shrub_0', 'shrub_1', 'fern_0'].every(n => sprites[n].px <= 800), ['shrub_0', 'shrub_1', 'fern_0'].map(n => sprites[n].px).join(', '));

  // ---- canopy speckle in the baked scene: neighbouring canopy pixels mostly share a tone
  const canopy = await ev(() => { const idx = DATA.idx.spring, E = DATA.entries.entries; const isLeaf = i => /^(oak|oak_b|birch|pine|rowan)$/.test((E[i] || {}).family || ''); let pairs = 0, change = 0; for (let y = 0; y < 480; y++) for (let x = 0; x < 767; x++) { const a = idx[y * 768 + x], c = idx[y * 768 + x + 1]; if (isLeaf(a) && isLeaf(c)) { pairs++; if (a !== c) change++; } } let leaf = 0; for (let i = 0; i < idx.length; i++) if (isLeaf(idx[i])) leaf++; return { rate: change / pairs, share: leaf / idx.length }; });
  check('canopy tone changes between neighbouring pixels stay moderate (≤ 25%: PixelLab leaf clumps carry more texture; the old noisy art was 21-40% at a third of the detail)', canopy.rate <= .25, `${(canopy.rate * 100).toFixed(1)}%, canopy covers ${(canopy.share * 100).toFixed(0)}% of the map`);

  // ---- soft shadows: no pixel-to-pixel jumps, a feathered edge, no isolated specks
  const sh = await ev(() => { const f = softMask(DATA.shadow.spring.noon), g = softMask(DATA.shadow.spring.long); let maxStep = 0, specks = 0, covered = 0; for (let y = 1; y < 479; y++) for (let x = 1; x < 767; x++) { const i = y * 768 + x; maxStep = Math.max(maxStep, Math.abs(f[i] - f[i + 1]), Math.abs(f[i] - f[i + 768])); if (f[i] > .02) covered++; if (f[i] > .5 && f[i - 1] < .1 && f[i + 1] < .1 && f[i - 768] < .1 && f[i + 768] < .1) specks++; } let longer = 0, nShort = 0; for (let i = 0; i < f.length; i++) { if (g[i] > .3) longer++; if (f[i] > .3) nShort++; } return { maxStep, specks, covered, longer, nShort }; });
  check('shadow field is soft: the biggest step between neighbouring pixels is small (≤ 0.22; a dithered edge jumps by 0.55-1)', sh.maxStep <= .22 && sh.covered > 3000, `max step ${sh.maxStep.toFixed(3)}, ${sh.covered} px of shade`);
  check('no isolated shadow specks, and the long (evening) shade is no more than ~1.6x the noon shade', sh.specks === 0 && sh.longer <= sh.nShort * 1.6, `${sh.specks} specks; noon ${sh.nShort} px, long ${sh.longer} px`);

  // ---- a still scene stays still (no shimmer): few pixels change in a quarter second
  const still = await ev(async () => { Survival.Weather.enabled = false; setPreset(1); WorldClock.paused = true; Social.setEnabled(false); Festival.setEnabled(false); Monsters.clearAll(); Player.setPos(300, 300); UIKit.S.reduceMotion = false; await new Promise(r => setTimeout(r, 800));
    const g = OFFC().getContext('2d'), vx = Camera.ix(), vy = Camera.iy(); const snap = () => g.getImageData(vx, vy, 640, 360).data.slice(); const diff = (a, c) => { let n = 0; for (let i = 0; i < a.length; i += 4) if (a[i] !== c[i] || a[i + 1] !== c[i + 1] || a[i + 2] !== c[i + 2]) n++; return n / (640 * 360); };
    const res = {}; for (const [k, w] of [['calm', .08], ['breezy', .5]]) { WeatherState.wind = w; WeatherState.windTarget = w; await new Promise(r => setTimeout(r, 300)); const a = snap(); await new Promise(r => setTimeout(r, 250)); res[k] = diff(a, snap()); } return res; });
  check('a calm still scene changes under 1.5% of its pixels per quarter second (the fire and breeze only)', still.calm < .015, `calm ${(still.calm * 100).toFixed(2)}%, breezy ${(still.breezy * 100).toFixed(2)}%`);

  // ---- water: no scanline banding (neighbouring rows of the pond agree), and quiet motion
  const water = await ev(async () => { Survival.Weather.enabled = false; setPreset(1); WorldClock.paused = true; Player.setPos(560, 300); await new Promise(r => setTimeout(r, 800)); const g = OFFC().getContext('2d'); const d = g.getImageData(0, 0, 768, 480).data, idx = DATA.idx.spring, C = CLSX(); const open = (x, y) => (C[idx[y * 768 + x]] & 2) && (C[idx[(y - 1) * 768 + x]] & 2) && (C[idx[(y - 2) * 768 + x]] & 2) && (C[idx[(y + 1) * 768 + x]] & 2); let rows = 0, n = 0; for (let y = 262; y < 420; y++) for (let x = 600; x < 740; x++) { if (!open(x, y)) continue; const a = (y * 768 + x) * 4, c = ((y - 1) * 768 + x) * 4; const dl = Math.abs((d[a] + d[a + 1] + d[a + 2]) - (d[c] + d[c + 1] + d[c + 2])); n++; if (dl > 48) rows++; } return n < 500 ? -1 : rows / n; });
  check('pond rows: no runtime striping beyond the painted ripple lines of the PixelLab water tile (≤ 40% of pixels differ sharply from the row above)', water <= .40, `${(water * 100).toFixed(1)}%`);

  // ---- day length: night pace unchanged, bright hours slower, spring daylight about 8 real minutes
  const clock = await ev(async () => { Survival.Weather.enabled = false; WorldClock.paused = false; const out = {}; for (const [k, h] of [['noon', 13], ['night', 23.5]]) { WorldClock.minutes = h * 60; const m0 = WorldClock.minutes, t0 = performance.now(); await new Promise(r => setTimeout(r, 2500)); out[k] = (WorldClock.minutes - m0) / ((performance.now() - t0) / 1000) * 60; }
    const sec = {}; const keep = SeasonState.season; for (const s of ['spring', 'summer', 'autumn', 'winter']) { SeasonState.season = s; let total = 0, bright = 0; for (let m = 0; m < 1440; m++) { WorldClock.minutes = m + .5; const dt = 60 / WorldClock.effScale(); total += dt; if (darknessAt(s, (m + .5) / 60) < .3) bright += dt; } sec[s] = { bright, total }; } SeasonState.season = keep; WorldClock.paused = true; out.sec = sec; return out; });
  check('night still runs at 240 game-min per real-min; midday runs at about 93', Math.abs(clock.night - 240) < 12 && Math.abs(clock.noon - 93) < 8, `noon ${clock.noon.toFixed(1)}, night ${clock.night.toFixed(1)}`);
  check('spring daylight lasts about 8 real minutes (420-540 s) and a whole day about 11', clock.sec.spring.bright >= 420 && clock.sec.spring.bright <= 540 && clock.sec.spring.total >= 600 && clock.sec.spring.total <= 700, `${Math.round(clock.sec.spring.bright)} s daylight of ${Math.round(clock.sec.spring.total)} s`);
  check('every season keeps its own light: summer longest, winter shortest, all at least 4 minutes', clock.sec.summer.bright > clock.sec.spring.bright && clock.sec.spring.bright > clock.sec.autumn.bright && clock.sec.autumn.bright > clock.sec.winter.bright && clock.sec.winter.bright >= 240, ['spring', 'summer', 'autumn', 'winter'].map(s => `${s} ${Math.round(clock.sec[s].bright)}s`).join(', '));
  const walk = await ev(() => { Survival.Energy.set(100); const e0 = Survival.Energy.current; Survival.tick(0, 60, true); return e0 - Survival.Energy.current; });
  check('walking energy still follows game time (1 energy per game hour), so a slower day does not change the economy', Math.abs(walk - 1) < .01, `${walk.toFixed(2)} per game hour`);

  check('no page errors', errs.length === 0, errs.slice(0, 3).join(' | '));
  fs.writeFileSync('/root/mosslight/tests/rendering_results.json', JSON.stringify({ results, passed: results.filter(r => r.ok).length, total: results.length }, null, 1));
  console.log(`${results.filter(r => r.ok).length}/${results.length} passed`); await b.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
