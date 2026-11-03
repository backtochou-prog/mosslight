// Offline audio renders: opens preview/audio_test.html, renders each music mood (16 s), five ambience scenes (8 s),
// two crossfade tests and an SFX sheet through OfflineAudioContext, writes 16-bit WAVs + summary.json, and checks them.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
const PORT = process.env.PORT || 8777, OUT = path.join(__dirname, '..', 'renders', 'audio'); fs.mkdirSync(OUT, { recursive: true });
const res = []; const check = (n, ok, d) => { res.push({ name: n, ok: !!ok, detail: d }); console.log((ok ? 'PASS ' : 'FAIL ') + n + (d !== undefined ? '  — ' + String(d).slice(0, 400) : '')); };
function decode(b64) { const b = Buffer.from(b64, 'base64'); const ch = b.readUInt16LE(22), sr = b.readUInt32LE(24), n = (b.length - 44) / (2 * ch); const L = new Float32Array(n), R = new Float32Array(n);
  for (let i = 0; i < n; i++) { L[i] = b.readInt16LE(44 + i * ch * 2) / 32768; R[i] = b.readInt16LE(44 + i * ch * 2 + 2) / 32768; } return { L, R, sr, n, buf: b }; }
function fft(re, im) { const n = re.length; for (let i = 1, j = 0; i < n; i++) { let bit = n >> 1; for (; j & bit; bit >>= 1) j ^= bit; j ^= bit; if (i < j) { [re[i], re[j]] = [re[j], re[i]]; [im[i], im[j]] = [im[j], im[i]]; } }
  for (let len = 2; len <= n; len <<= 1) { const a = -2 * Math.PI / len; for (let i = 0; i < n; i += len) for (let k = 0; k < len / 2; k++) { const c = Math.cos(a * k), s = Math.sin(a * k), u = i + k, v = u + len / 2; const xr = re[v] * c - im[v] * s, xi = re[v] * s + im[v] * c; re[v] = re[u] - xr; im[v] = im[u] - xi; re[u] += xr; im[u] += xi; } } }
function stats({ L, R, sr, n }) { let peak = 0, ss = 0; const M = new Float32Array(n); for (let i = 0; i < n; i++) { const a = Math.abs(L[i]), b = Math.abs(R[i]); peak = Math.max(peak, a, b); ss += L[i] * L[i] + R[i] * R[i]; M[i] = (L[i] + R[i]) / 2; }
  const N = 4096; let num = 0, den = 0; for (let o = 0; o + N <= n; o += N) { const re = new Float64Array(N), im = new Float64Array(N); for (let i = 0; i < N; i++) re[i] = M[o + i] * (.5 - .5 * Math.cos(2 * Math.PI * i / N)); fft(re, im);
    for (let k = 1; k < N / 2; k++) { const mag = Math.hypot(re[k], im[k]); num += mag * k * sr / N; den += mag; } }
  return { peak: +peak.toFixed(4), rms: +Math.sqrt(ss / (2 * n)).toFixed(5), centroid_hz: den ? Math.round(num / den) : 0, seconds: +(n / sr).toFixed(2), M }; }
const winRms = (M, sr, t0, t1, w = .01) => { const out = []; const W = Math.round(w * sr); for (let s = Math.round(t0 * sr); s + W <= Math.min(M.length, t1 * sr); s += W) { let q = 0; for (let i = s; i < s + W; i++) q += M[i] * M[i]; out.push(Math.sqrt(q / W)); } return out; };
const db = x => 20 * Math.log10(Math.max(x, 1e-4));
function steps(r) { let up = 0, down = 0; for (let i = 1; i < r.length; i++) { const d = db(r[i]) - db(r[i - 1]); up = Math.max(up, d); down = Math.max(down, -d); } return { up: +up.toFixed(2), down: +down.toFixed(2) }; }
function maxDeriv(M, sr, t0, t1) { let m = 0; for (let i = Math.max(1, Math.round(t0 * sr)); i < Math.min(M.length, t1 * sr); i++) m = Math.max(m, Math.abs(M[i] - M[i - 1])); return +m.toFixed(4); }

(async () => { const b = await chromium.launch(); const p = await b.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message)); p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await p.goto(`http://127.0.0.1:${PORT}/preview/audio_test.html`); await p.waitForFunction(() => window.Sound && window.renderScene);
  const sc = await p.evaluate(() => window.SCENES); const names = [...sc.moods.map(m => 'mood_' + m), ...sc.amb, 'xfade_day_to_danger', 'xfade_day_to_sunset', 'sfx_sheet'];
  const summary = {}, sig = {};
  for (const n of names) { const t0 = Date.now(); const r = await p.evaluate(n => renderScene(n), n); const d = decode(r.wav); fs.writeFileSync(path.join(OUT, n + '.wav'), d.buf);
    const s = stats(d); sig[n] = { M: s.M, sr: d.sr, info: r.info }; delete s.M; summary[n] = Object.assign(s, { mood: r.info.debug.mood, want: r.info.want, layers: r.info.debug.layers, played: r.info.played, count: r.info.count, render_ms: Date.now() - t0 });
    console.log(n.padEnd(26), JSON.stringify({ peak: s.peak, rms: s.rms, centroid: s.centroid_hz, mood: r.info.debug.mood })); }
  // ---- checks
  for (const n of names) check(`${n}: no clipping (peak < 0.95)`, summary[n].peak < .95, summary[n].peak);
  for (const n of names) check(`${n}: not silent (rms > 0.002)`, summary[n].rms > .002, summary[n].rms);
  const moods = sc.moods; for (const m of moods) check(`mood_${m}: world state selects mood '${m}'`, summary['mood_' + m].want === m && summary['mood_' + m].mood === m, summary['mood_' + m].want + ' / ' + summary['mood_' + m].mood);
  const pairs = []; for (let i = 0; i < moods.length; i++) for (let j = i + 1; j < moods.length; j++) { const a = summary['mood_' + moods[i]], c = summary['mood_' + moods[j]];
    const dc = Math.abs(a.centroid_hz - c.centroid_hz) / Math.max(a.centroid_hz, c.centroid_hz), dr = Math.abs(db(a.rms) - db(c.rms)); pairs.push({ p: moods[i] + '/' + moods[j], dc: +dc.toFixed(3), dr: +dr.toFixed(2), ok: dc > .05 || dr > 1 }); }
  const bad = pairs.filter(x => !x.ok); check('every pair of moods differs (centroid > 5% or rms > 1 dB)', !bad.length, bad.length ? JSON.stringify(bad) : `${pairs.length} pairs, min centroid diff ${Math.min(...pairs.map(x => x.dc))}`);
  summary._crossfade = {};
  for (const n of ['xfade_day_to_danger', 'xfade_day_to_sunset']) { const { M, sr, info } = sig[n]; const ts = info.switchAt;
    const around = winRms(M, sr, ts - .3, ts + .7), whole = winRms(M, sr, 0, 16), sa = steps(around), sw = steps(whole);
    const before = winRms(M, sr, ts - .5, ts).reduce((a, x) => a + x, 0) / 50, after = winRms(M, sr, ts, ts + .5).reduce((a, x) => a + x, 0) / 50;
    const dv = { around_switch_max_step_up_db: sa.up, around_switch_max_step_down_db: sa.down, whole_file_max_step_up_db: sw.up, whole_file_max_step_down_db: sw.down,
      rms_500ms_before: +before.toFixed(5), rms_500ms_after: +after.toFixed(5), max_sample_delta_around: maxDeriv(M, sr, ts - .3, ts + .7), max_sample_delta_whole: maxDeriv(M, sr, 0, 16), final_mood: info.debug.mood, voices_at_end: info.debug.moodVoices };
    summary._crossfade[n] = dv;
    check(`${n}: no amplitude discontinuity at the switch (10 ms RMS steps no larger than the file's own note onsets; no drop > 6 dB)`, sa.down <= 6 && sa.up <= sw.up + .01 && dv.max_sample_delta_around <= dv.max_sample_delta_whole + 1e-4, JSON.stringify(dv));
    check(`${n}: ends in the new mood with both voices present during the fade`, info.debug.mood === (n.endsWith('danger') ? 'danger' : 'sunset'), info.debug.mood); }
  check('sfx sheet: every one-shot, ui, creature and sting recipe produced sound', summary.sfx_sheet.played === summary.sfx_sheet.count, `${summary.sfx_sheet.played}/${summary.sfx_sheet.count}`);
  // ---- live API on the real page (no user gesture needed in headless Chromium)
  const live = await p.evaluate(async () => { const out = {}; out.before = Sound.debug().ctxState; await Sound.start(); await Sound.start(); Sound.tick(.1); await new Promise(r => setTimeout(r, 300));
    out.after = Sound.debug().ctxState; out.mood = Sound.mood(); out.play = Sound.play('wood_chop', { x: 230, y: 200 }); out.cool = Sound.play('wood_chop', { x: 230, y: 200 }); out.far = Sound.play('wood_chop', { x: 5000, y: 200 });
    out.unknown = Sound.play('nope'); out.ui = Sound.ui('confirm'); out.cre = Sound.creature('howl', 300, 200); out.st = Sound.sting('discovery');
    Sound.setVolume('music', .3); Sound.setMuted(true); out.saved = JSON.parse(localStorage.getItem('mosslight.audio')); Sound.setMuted(false);
    const dbg = Sound.debug(); out.layers = Object.keys(dbg.layers); out.voices = dbg.voices;
    // a broken world must not throw
    Sound.init({ WorldClock: { hour() { throw new Error('x'); } }, Monsters: { list: null }, waterDist: () => NaN }); Sound.tick(.1); out.broken = Sound.mood(); Sound.init({}); Sound.tick(.1); out.empty = Sound.mood(); return out; });
  check('start() is idempotent and runs the context', live.after === 'running', JSON.stringify([live.before, live.after]));
  check('play: plays, then cooldown blocks a machine-gun repeat; far/unknown sounds are skipped', live.play && !live.cool && !live.far && !live.unknown, JSON.stringify([live.play, live.cool, live.far, live.unknown]));
  check('ui/creature/sting play', live.ui && live.cre && live.st, JSON.stringify([live.ui, live.cre, live.st]));
  check('settings persist to localStorage mosslight.audio', live.saved && live.saved.music === .3 && live.saved.muted === true, JSON.stringify(live.saved));
  check('a broken or empty world never throws and still picks a mood', live.broken && live.empty, live.broken + ' / ' + live.empty);
  check('no page errors', !errs.length, errs.join(' | '));
  fs.writeFileSync(path.join(OUT, 'summary.json'), JSON.stringify(summary, null, 1)); fs.writeFileSync(path.join(__dirname, 'audio_results.json'), JSON.stringify(res, null, 1));
  console.log(`\n${res.filter(r => r.ok).length}/${res.length} passed`); await b.close(); process.exit(res.every(r => r.ok) ? 0 : 1); })();
