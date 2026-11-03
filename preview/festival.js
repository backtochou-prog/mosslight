// MOSSlight calendar and seasonal festivals. Data: assets/festivals/festivals.json (rules, spots, collectibles, music)
// and assets/events/fest_*.json (the composed scene layer, lights and grade, baked by tools/build_atmosphere.py).
// A festival is a real place-change: its own scene layer, depth map, lights, particles, sound, interactions and
// collectibles, with a beginning and an end. Nothing here ever starts a conversation or stops the player.
window.Festival = (() => {
  let D = null, W = null, T = 0, enabled = true; const SEASONS = ['spring', 'summer', 'autumn', 'winter'];
  const listeners = {}; const on = (e, cb) => (listeners[e] = listeners[e] || []).push(cb); const emit = (e, ...a) => (listeners[e] || []).forEach(cb => cb(...a));
  const day = () => W.Survival.Clock.day, hour = () => W.WorldClock.hour(); const say = (m, t) => W.Build.FX.say(m, t);
  // ================================================================= CALENDAR: 28-day seasons; changes season only at a day boundary
  const Cal = { len: 28, offset: 0, discovered: {}, lastDay: null,
    seasonOf(d) { return SEASONS[((Math.floor((d - 1) / this.len) + this.offset) % 4 + 4) % 4]; }, dos(d) { return ((d - 1) % this.len) + 1; }, year(d) { return Math.floor(((d - 1) + this.offset * this.len) / (this.len * 4)) + 1; },
    sync() { const s = W.SeasonState.season, i = SEASONS.indexOf(s); if (this.seasonOf(day()) !== s && i >= 0) this.offset = ((i - Math.floor((day() - 1) / this.len)) % 4 + 4) % 4; },   // respect a season set by hand or by a save
    onDay() { const s = this.seasonOf(day()); if (W.SeasonState.season !== s) { W.SeasonState.season = s; emit('season', s); } },
    discover(f, how) { if (this.discovered[f]) return false; this.discovered[f] = { how, day: day() }; emit('discovered', f, how); return true; },
    festivalOn(f) { const F = D.festivals[f]; return { season: F.season, day: F.day }; },
    daysUntil(f) { const F = D.festivals[f], d = day(); for (let k = 0; k < 112; k++) { const dd = d + k; if (this.seasonOf(dd) === F.season && this.dos(dd) === F.day) return k; } return 999; } };
  // ================================================================= ACTIVE FESTIVAL
  const S = { active: null, since: 0, records: {}, floating: [], fx: [] };
  function isOnNow(f) { const F = D.festivals[f]; const d = day(), h = hour(); const today = W.SeasonState.season === F.season && Cal.dos(d) === F.day; const yesterday = d > 1 && Cal.seasonOf(d - 1) === F.season && Cal.dos(d - 1) === F.day && W.SeasonState.season === Cal.seasonOf(d);
    if (F.to <= 24) return today && h >= F.from && h < F.to; return (today && h >= F.from) || (yesterday && h < F.to - 24); }
  function rec(f) { return S.records[f] = S.records[f] || { attended: [], found: {}, spots: {}, with: [], acts: [] }; }
  let forced = null;
  function check() { const want = forced || (enabled ? Object.keys(D.festivals).find(isOnNow) || null : null); if (want === S.active) return;
    if (S.active) end(); if (want) begin(want); }
  function begin(f) { S.active = f; S.since = T; const F = D.festivals[f]; W.applyEvent(F.scene, true); S.fx = []; S.floating = []; Cal.discover(f, 'attended'); const r = rec(f); const y = Cal.year(day()); if (!r.attended.includes(y)) r.attended.push(y); emit('begin', f); if (window.UIKit && UIKit.toast) UIKit.toast({ kicker: 'Festival', title: F.title, sub: `Today, ${F.from}:00 to ${F.to % 24}:00`, glyph: 'leaf', rare: true }); }
  function end() { const f = S.active; S.active = null; W.applyEvent('', true); S.fx = []; S.floating = []; Music.stop(); emit('end', f); }
  // ================================================================= INTERACTIONS: optional, found by walking up to them
  function spotsNow() { if (!S.active) return []; return D.festivals[S.active].spots || []; }
  function spotUsed(f, sp) { const r = rec(f), y = Cal.year(day()); const k = sp.id; const used = r.spots[k] || []; if (sp.once === 'ever') return used.length > 0; return used.includes(y) && (sp.limit || 1) <= used.filter(v => v === y).length; }
  function nearest(px, py) { if (!D || !enabled) return null; let best = null, bd = 1e9;
    for (const sp of spotsNow()) { const d = Math.hypot(sp.x - px, sp.y - py); if (d < (sp.r || 18) && d < bd && !spotUsed(S.active, sp)) { bd = d; best = sp; } }
    if (!best) { if (!S.active) clueNear(px, py); return null; } const sp = best; return { id: 'fest:' + sp.id, label: sp.label, x: sp.x, y: sp.y, r: sp.r || 18, buildAct: () => act(sp) }; }
  function giveItem(id, n = 1) { const got = W.Gather.Inventory.add(id, n); if (got) { W.Gather.Journal.record(id, null); W.Gather.FX.pop(W.Player.x, W.Player.y - 22, [[id, got]]); const r = rec(S.active); r.found[id] = (r.found[id] || 0) + got; emit('found', S.active, id); } else say('Your pack is full.'); return got; }
  function act(sp) { const f = S.active, r = rec(f), y = Cal.year(day()); (r.spots[sp.id] = r.spots[sp.id] || []).push(y); r.acts.push({ id: sp.id, day: day() }); if (r.acts.length > 60) r.acts.shift();
    if (sp.kind === 'kneel') { const g = W.Fishing.go(sp.habitat, true); if (!g.ok) r.spots[sp.id].pop(); return; }
    if (sp.kind === 'float') { S.floating.push({ x: sp.x + 4, y: sp.y, vx: 3 + Math.random() * 2, vy: -1.5, t: 0 }); say(sp.text, 5); emit('act', f, sp); return; }
    if (sp.kind === 'offer') { const inv = W.Gather.Inventory; const i = inv.slots.findIndex(s => s && ['natural', 'abandoned', 'botanical', 'geological'].includes((W.Gather.DB.get(s.id) || {}).category)); if (i < 0) { say('You have nothing you are ready to leave.'); r.spots[sp.id].pop(); return; } const id = inv.slots[i].id; inv.remove(i, 1); r.offered = r.offered || []; r.offered.push({ id, day: day() }); say(sp.text.replace('{item}', (W.Gather.DB.get(id) || {}).name), 5); emit('act', f, sp, id); return; }
    if (sp.item) { const first = !r.found[sp.item]; giveItem(sp.item, sp.qty || 1); if (sp.text) say(sp.text, 5); if (first && sp.first) say(sp.first, 6); }
    else if (sp.text) say(sp.text, 5); emit('act', f, sp); }
  function clueNear(px, py) { for (const [f, F] of Object.entries(D.festivals)) { const k = Cal.daysUntil(f); if (k < 1 || k > (F.clue_days || 3)) continue; const [x, y] = F.focus; if (Math.hypot(px - x, py - y) < 110 && Cal.discover(f, 'clue')) say(F.clue, 6); } }
  // ================================================================= FX: drawn into the game frame, palette-friendly, a few hundred particles at most
  function fxTick(dt) { const f = S.active; const F = f && D.festivals[f]; const dark = W.tableDark(); const want = F ? F.fx : null; const pf = S.fx; T += 0;
    const spawn = (n, mk) => { while (pf.length < n) pf.push(mk()); };
    if (want === 'petals') spawn(170, () => ({ x: Math.random() * 768, y: Math.random() * 480, vx: 8 + Math.random() * 8, vy: 6 + Math.random() * 5, ph: Math.random() * 6, c: Math.random() < .6 ? [250, 246, 238] : [236, 186, 214] }));
    if (want === 'fireflies') spawn(320, () => { const a = Math.random() * 6.28, r = Math.random() ** .5; const pond = Math.random() < .55; return { x: pond ? 630 + Math.cos(a) * 110 * r : Math.random() * 768, y: pond ? 262 + Math.sin(a) * 70 * r : 120 + Math.random() * 330, vx: 0, vy: 0, ph: Math.random() * 6, f: 1 + Math.random() }; });
    if (want === 'leaves') spawn(60, () => ({ x: Math.random() * 768, y: Math.random() * 480, vx: 14 + Math.random() * 10, vy: 10 + Math.random() * 6, ph: Math.random() * 6, c: [[214, 120, 40], [190, 70, 40], [230, 170, 60], [160, 90, 40]][Math.floor(Math.random() * 4)] }));
    if (want === 'snowglow') spawn(90, () => ({ x: Math.random() * 768, y: Math.random() * 480, vx: 4, vy: 9 + Math.random() * 6, ph: Math.random() * 6 }));
    for (const p of pf) { p.ph += dt; if (want === 'fireflies') { p.x += Math.sin(p.ph * .7 * p.f) * 6 * dt; p.y += Math.cos(p.ph * .5 * p.f) * 4 * dt; } else { p.x += (p.vx + Math.sin(p.ph * 1.7) * 6) * dt; p.y += p.vy * dt; if (p.x > 780) p.x -= 800; if (p.y > 490) p.y -= 500; } }
    if (!want) pf.length = 0;
    if (F && F.fx === 'leaves') { for (let i = 0; i < 2; i++) if (Math.random() < dt * 6) S.sparks = (S.sparks || []).concat([{ x: 520 + (Math.random() - .5) * 8, y: 182, vy: -18 - Math.random() * 16, vx: (Math.random() - .5) * 8, t: 0 }]); S.sparks = (S.sparks || []).filter(s => { s.t += dt; s.x += s.vx * dt; s.y += s.vy * dt; return s.t < 1.4; }); }
    for (const fl of S.floating) { fl.t += dt; fl.x += fl.vx * dt * .4; fl.y += Math.sin(fl.t * .7) * .1 + fl.vy * dt * .2; } }
  function drawFx(og, darkness) { const f = S.active; if (!f) return clueFx(og, darkness); const F = D.festivals[f]; og.save();
    if (F.fx === 'petals') for (const p of S.fx) { og.fillStyle = `rgba(${p.c[0]},${p.c[1]},${p.c[2]},.95)`; const fl = (p.ph * 3 | 0) % 3; og.fillRect(p.x | 0, p.y | 0, fl ? 2 : 1, fl === 1 ? 2 : 1); }
    if (F.fx === 'fireflies') { og.globalCompositeOperation = 'lighter'; for (const p of S.fx) { const b = (Math.sin(p.ph * 2.4 * p.f) * .5 + .5) ** 2 * Math.max(.25, darkness); if (b < .05) continue; og.fillStyle = `rgba(120,150,30,${b * .28})`; og.fillRect((p.x | 0) - 2, (p.y | 0) - 1, 5, 3); og.fillRect((p.x | 0) - 1, (p.y | 0) - 2, 3, 5); og.fillStyle = `rgba(190,230,90,${b * .55})`; og.fillRect((p.x | 0) - 1, p.y | 0, 3, 1); og.fillRect(p.x | 0, (p.y | 0) - 1, 1, 3); og.fillStyle = `rgba(245,255,170,${b})`; og.fillRect(p.x | 0, p.y | 0, 1, 1); } }
    if (F.fx === 'leaves') { for (const p of S.fx) { og.fillStyle = `rgb(${p.c[0]},${p.c[1]},${p.c[2]})`; og.fillRect(p.x | 0, p.y | 0, 2, 1); og.fillRect((p.x | 0) + ((p.ph * 2 | 0) % 2), (p.y | 0) + 1, 1, 1); } og.globalCompositeOperation = 'lighter'; for (const s of S.sparks || []) { og.fillStyle = `rgba(255,${180 - s.t * 80 | 0},80,${1 - s.t / 1.4})`; og.fillRect(s.x | 0, s.y | 0, 1, 1); } }
    if (F.fx === 'snowglow') { for (const p of S.fx) { og.fillStyle = 'rgba(240,248,255,.85)'; og.fillRect(p.x | 0, p.y | 0, 1, 1); } }
    og.globalCompositeOperation = 'lighter'; for (const fl of S.floating) { og.fillStyle = 'rgba(255,190,90,.35)'; og.fillRect((fl.x | 0) - 2, (fl.y | 0) - 6, 5, 6); og.fillStyle = 'rgba(255,230,160,.95)'; og.fillRect((fl.x | 0), (fl.y | 0) - 4, 2, 3); }
    og.restore(); }
  function clueFx(og, darkness) { for (const [f, F] of Object.entries(D.festivals)) { const k = Cal.daysUntil(f); if (k < 1 || k > (F.clue_days || 3)) continue; const [x, y] = F.focus; og.save(); og.globalCompositeOperation = 'lighter';
      for (let i = 0; i < 8; i++) { const a = T * .3 + i * .8, px = x + Math.cos(a) * (18 + i * 3), py = y - 10 + Math.sin(a * 1.3) * 8; og.fillStyle = F.fx === 'fireflies' ? `rgba(230,255,140,${.5 * darkness})` : F.fx === 'petals' ? 'rgba(250,240,240,.8)' : F.fx === 'leaves' ? 'rgba(220,130,50,.8)' : `rgba(200,230,255,${.6 * darkness + .2})`; og.fillRect(px | 0, py | 0, 1, 1); } og.restore(); } }
  // in the frame buffer: lantern reflections in summer, drowned lights under clear ice in winter
  function world(cx, darkness) { const f = S.active; if (!f) return; const F = D.festivals[f]; const { d, W: FW } = cx;
    if (F.under_ice && W.waterPixels) { const wp = W.waterPixels(); const dk = Math.min(1, darkness * 1.2); for (let n = 0; n < wp.length; n += 1) { const i = wp[n], o = i * 4; const x = i % FW, y = (i / FW) | 0; const glass = .55 * dk; d[o] += (14 - d[o]) * glass; d[o + 1] += (30 - d[o + 1]) * glass; d[o + 2] += (58 - d[o + 2]) * glass; if (((x + y * 3) % 61) < 1 && ((x * 7 + y) % 5) === 0) { d[o] += 60 * dk; d[o + 1] += 70 * dk; d[o + 2] += 80 * dk; } } }
    if (F.under_ice) { for (const [x, y, k] of F.under_ice) { const b = (.55 + .45 * Math.sin(T * (.6 + k * .13) + k)) * Math.min(1, darkness * 1.2); for (let yy = -2; yy <= 2; yy++) for (let xx = -3; xx <= 3; xx++) { const r2 = (xx * xx) / 9 + (yy * yy) / 4; if (r2 > 1) continue; const o = ((y + yy) * FW + x + xx) * 4; const a = b * (1 - r2) * .85; d[o] += (255 - d[o]) * a; d[o + 1] += (200 - d[o + 1]) * a * .9; d[o + 2] += (120 - d[o + 2]) * a * .5; } } }
    if (F.reflect) for (const [x, y] of F.reflect) { for (let k = 2; k < 18; k++) { if (k % 3 === 0) continue; const xx = x + Math.round(Math.sin(T * 2 + k * .9) * 1.2); const o = ((y + k) * FW + xx) * 4; const a = (1 - k / 18) * .5 * darkness; d[o] += (255 - d[o]) * a; d[o + 1] += (210 - d[o + 1]) * a; d[o + 2] += (130 - d[o + 2]) * a * .6; } } }
  // ================================================================= MUSIC: generated, different for each festival; quiet, and only near the place
  const Music = { node: null, t: 0, f: null, notes: 0,
    stop() { if (this.node) { try { this.node.gain.setTargetAtTime(0, this.ctx.currentTime, .6); } catch (_) {} } this.node = null; this.f = null; },
    tick(dt) { const A = W.Monsters.Audio; if (!A.ctx || !S.active) return; const F = D.festivals[S.active]; const ctx = this.ctx = A.ctx; if (this.f !== S.active) { this.stop(); this.node = ctx.createGain(); this.node.gain.value = 0; this.node.connect(A.master); this.f = S.active; }
      const [x, y] = F.focus; const near = Math.max(0, 1 - Math.hypot(W.Player.x - x, W.Player.y - y) / 420); this.node.gain.setTargetAtTime(.5 * near * (A.vol.music ?? .7), ctx.currentTime, .5); this.log = this.log || []; this.t -= dt; if (this.t > 0) return; const m = F.music;
      const tn = (freq, dur, type, vol, glide) => { const o = ctx.createOscillator(), g = ctx.createGain(); o.type = type; o.frequency.setValueAtTime(freq, ctx.currentTime); if (glide) o.frequency.exponentialRampToValueAtTime(glide, ctx.currentTime + dur); g.gain.setValueAtTime(0, ctx.currentTime); g.gain.linearRampToValueAtTime(vol, ctx.currentTime + Math.min(.06, dur / 4)); g.gain.exponentialRampToValueAtTime(.0005, ctx.currentTime + dur); o.connect(g); g.connect(this.node); o.start(); o.stop(ctx.currentTime + dur + .05); };
      const sc = m.scale, root = m.root; const step = sc[Math.floor(Math.random() * sc.length)]; const f0 = root * Math.pow(2, step / 12); this.notes++; this.log.push(S.active);
      if (m.voice === 'flute') { tn(f0, .9, 'sine', .08); if (Math.random() < .25) tn(2400 + Math.random() * 800, .12, 'sine', .02, 3400); this.t = .45 + Math.random() * .6; }
      else if (m.voice === 'pad') { for (const k of [0, 3, 7]) tn(f0 * Math.pow(2, k / 12) / 2, 2.6, 'triangle', .025); this.t = 2.2; }
      else if (m.voice === 'kalimba') { tn(f0, .5, 'sine', .07); if (Math.random() < .3) tn(f0 / 4, 1.8, 'sawtooth', .012); this.t = .35 + Math.random() * .5; }
      else if (m.voice === 'bells') { tn(f0 * 2, 3.2, 'sine', .05); tn(f0 * 5.04, 1.6, 'sine', .012); this.t = 1.2 + Math.random() * 1.6; } } };
  // ================================================================= CALENDAR SCREEN: one book page, the season as a ruled grid, a detail column
  const UI = { open: false, buttons: [], season: null, sel: null };
  const FGL = ['..#..', '.#.#.', '#.#.#', '.###.', '#.#.#', '.#.#.', '..#..'];   // an inked rosette: the festival mark
  function mark(g, x, y, ink, fill, faint) { FGL.forEach((row, yy) => { for (let xx = 0; xx < 5; xx++) if (row[xx] === '#') { g.fillStyle = faint ? (((xx + yy) & 1) ? 'rgba(94,74,50,.45)' : 'rgba(94,74,50,.2)') : ink; g.fillRect(x + xx * 2, y + yy * 2, 2, 2); } }); if (!faint && fill) { g.fillStyle = fill; g.fillRect(x + 4, y + 6, 2, 2); g.fillRect(x + 2, y + 4, 1, 1); g.fillRect(x + 7, y + 4, 1, 1); g.fillRect(x + 2, y + 9, 1, 1); g.fillRect(x + 7, y + 9, 1, 1); } }
  function ring(g, cx, cy, rx, ry, col) { g.fillStyle = col; const n = Math.ceil((rx + ry) * 3); for (let k = 0; k <= n + 3; k++) { const a = -2.2 + k / n * Math.PI * 2, w = 1 + .08 * Math.sin(a * 3); g.fillRect(Math.round(cx + Math.cos(a) * rx * w), Math.round(cy + Math.sin(a) * ry * w), 1, 1); } }   // hand-drawn: overshoots its start a little
  const btn = (x, y, w, h, fn, label) => { UIKit.hit(x, y, w, h, fn, label); UI.buttons.push({ x, y, w, h, fn }); };
  function untilDay(s, dd) { const d = day(); for (let k = 0; k < 112; k++) if (Cal.seasonOf(d + k) === s && Cal.dos(d + k) === dd) return k; return null; }
  function drawCal(g, vw, vh) { UI.buttons = []; const K = UIKit, C = K.C, P = K.Ptr; const cur = W.SeasonState.season, s = UI.season || cur, d = day(), dos = Cal.dos(d), here = s === cur;
    const pw = Math.min(vw - 16, 540), phMax = Math.min(vh - 28, 300), chF = Math.max(22, Math.min(40, Math.floor((phMax - 36 - 24) / 4))), ph = Math.min(phMax, 36 + chF * 4 + 26), x0 = Math.round(vw / 2 - pw / 2), y0 = Math.max(22, Math.round(vh / 2 - ph / 2) + 6);
    g.save(); K.enter(g, 'calendar', true, x0, y0, pw, ph); const Sname = s[0].toUpperCase() + s.slice(1);
    K.paper(g, x0, y0, pw, ph, { title: Sname, sub: `year ${Cal.year(d)}` + (here ? `, day ${dos} of ${Cal.len}` : ''), close: () => { UI.open = false; UI.season = null; UI.sel = null; } });
    // season arrows, beside the close box
    const turn = k => () => { UI.season = SEASONS[(SEASONS.indexOf(s) + k + 4) % 4]; UI.sel = null; }; const ax = x0 + pw - 30;
    K.button(g, ax - 72, y0 + 9, 16, 13, '<', null); btn(ax - 72, y0 + 9, 16, 13, turn(-1), 'prev season'); K.button(g, ax - 20, y0 + 9, 16, 13, '>', null); btn(ax - 20, y0 + 9, 16, 13, turn(1), 'next season');
    if (here) K.text(g, 'now', ax - 38, y0 + 19, { align: 'center', color: C.moss }); else { K.button(g, ax - 52, y0 + 9, 28, 13, 'now', null); btn(ax - 52, y0 + 9, 28, 13, () => { UI.season = null; UI.sel = null; }, 'this season'); }
    const fests = Object.entries(D.festivals).filter(([, F]) => F.season === s); const festOn = dd => fests.find(([, F]) => +F.day === dd);
    if (UI.sel == null) UI.sel = here ? dos : (fests.length && Cal.discovered[fests[0][0]] ? +fests[0][1].day : 1);
    // the grid: 4 weeks of 7 days
    const gx = x0 + 12, gy = y0 + 36, cw = Math.max(22, Math.min(38, Math.floor((pw * .58 - 16) / 7))), ch = chF, gw = cw * 7, gh = ch * 4;
    g.fillStyle = C.paper2; g.fillRect(gx, gy, gw, gh);
    for (let r = 0; r <= 4; r++) { g.fillStyle = r % 4 ? 'rgba(58,42,26,.22)' : 'rgba(58,42,26,.45)'; g.fillRect(gx, gy + r * ch, gw + 1, 1); }
    for (let c = 0; c <= 7; c++) { g.fillStyle = c % 7 ? 'rgba(58,42,26,.22)' : 'rgba(58,42,26,.45)'; g.fillRect(gx + c * cw, gy, 1, gh + 1); }
    let hover = null;
    for (let k = 0; k < Cal.len; k++) { const dd = k + 1, cx = gx + (k % 7) * cw, cy = gy + Math.floor(k / 7) * ch, today = here && dd === dos, past = here && dd < dos, fe = festOn(dd);
      const hot = P.over && P.x >= cx && P.x < cx + cw && P.y >= cy && P.y < cy + ch; if (hot) { hover = dd; g.fillStyle = 'rgba(255,250,235,.45)'; g.fillRect(cx + 1, cy + 1, cw - 1, ch - 1); }
      if (past) { g.fillStyle = 'rgba(94,74,50,.16)'; for (let q = 3; q < cw - 2; q += 4) g.fillRect(cx + q, cy + ch - 4 - Math.round(q * (ch - 8) / cw), 1, 1); }
      K.text(g, String(dd), cx + 4, cy + 10, { color: past ? C.faint : C.ink, bold: today });
      if (today) ring(g, cx + 4 + K.measure(String(dd)) / 2, cy + 7, K.measure(String(dd)) / 2 + 4, 6, C.rust);
      if (fe) { const [f, F] = fe, known = !!Cal.discovered[f]; mark(g, cx + Math.round(cw / 2) - 5, cy + ch - 17, C.ink2, F.color, !known); if (known && rec(f).attended.length) { g.fillStyle = C.moss; for (const [a, b] of [[0, 2], [1, 3], [2, 2], [3, 1], [4, 0]]) g.fillRect(cx + cw - 9 + a, cy + 4 + b, 1, 2); } }
      if (dd === UI.sel) { g.fillStyle = C.rust; for (const [a, b, sx, sy] of [[cx + 1, cy + 1, 1, 1], [cx + cw - 1, cy + 1, -1, 1], [cx + 1, cy + ch - 1, 1, -1], [cx + cw - 1, cy + ch - 1, -1, -1]]) { g.fillRect(Math.min(a, a + sx * 4), b, 4, 1); g.fillRect(a, Math.min(b, b + sy * 4), 1, 4); } }
      btn(cx, cy, cw, ch, () => { UI.sel = dd; }, 'day'); }
    // festival name on hover (keyboard and mouse); the selected day's name is in the detail column
    if (hover && festOn(hover) && hover !== UI.sel) { const [f, F] = festOn(hover), nm = Cal.discovered[f] ? F.title : 'something, this day?', k = hover - 1, tw = K.measure(nm) + 10, tx = Math.max(x0 + 6, Math.min(gx + (k % 7) * cw + cw / 2 - tw / 2, x0 + pw - tw - 6)), ty = gy + Math.floor(k / 7) * ch - 13; K.tag(g, Math.round(tx), Math.max(y0 + 26, ty), tw, 12); K.text(g, nm, Math.round(tx) + 5, Math.max(y0 + 26, ty) + 9, { color: C.ink2 }); }
    if (!K.touch() && K.S.hints) K.text(g, 'A D  seasons   V  close', gx, gy + gh + 13, { color: C.faint });
    // detail column: the selected day, from real festival records
    const rx = gx + gw + 14, rw = x0 + pw - 12 - rx, bot = y0 + ph - 10; let ry = gy + 8; g.fillStyle = 'rgba(58,42,26,.3)'; g.fillRect(rx - 7, gy, 1, gh);
    const line = (str, o = {}, lh = 10) => { for (const l of K.lines(str, rw)) { if (ry > bot) return; K.text(g, l, rx, ry, o); ry += lh; } };
    const k = untilDay(s, UI.sel), when = here && UI.sel === dos ? 'today' : here && UI.sel < dos ? `${dos - UI.sel} ${dos - UI.sel === 1 ? 'day' : 'days'} ago` : k === 1 ? 'tomorrow' : k != null ? `in ${k} days` : '';
    K.text(g, `Day ${UI.sel}`, rx, ry, { bold: true }); K.text(g, when, rx + rw, ry, { align: 'right', color: when === 'today' ? C.rust : C.faint }); ry += 5; K.divider(g, rx, ry, rw); ry += 12;
    const fe = festOn(UI.sel);
    if (fe) { const [f, F] = fe, known = Cal.discovered[f];
      if (!known) { line('Something, this season', { bold: true }); ry += 2; line(F.hint, { color: C.ink2 }); }
      else { const r = rec(f), n = r.attended.length; mark(g, rx, ry - 9, C.ink2, F.color); for (const l of K.lines(F.title, rw - 16)) { if (ry > bot) break; K.text(g, l, rx + 15, ry, { bold: true }); ry += 10; } ry += 1;
        line(`${F.from}:00 to ${F.to % 24}:00${F.to > 24 ? ' (next day)' : ''}. ${n ? 'Attended ' + n + (n > 1 ? ' times.' : ' time.') : 'Not yet attended.'}`, { color: n ? C.moss : C.ink2 }); ry += 2;
        line(F.blurb, { color: C.ink }); ry += 2;
        const got = F.collectibles.filter(id => r.found[id] || W.Gather.Journal.found[id]).map(id => (W.Gather.DB.get(id) || {}).name || id), left = F.collectibles.length - got.length; line(got.length ? 'Found: ' + got.join(', ') + (left ? `, and ${left} still hidden.` : '.') : `${left} keepsakes to find here.`, { color: got.length ? C.moss : C.ink2 }); } }
    else { line(here && UI.sel === dos ? 'An ordinary day in the clearing.' : 'Nothing marked for this day.', { color: C.ink2 }); ry += 4;
      for (const [f, F] of fests) { const kn = Cal.discovered[f]; line(kn ? `This season: ${F.title}, day ${F.day}.` : 'Something happens this season. ' + F.hint, { color: C.faint }); ry += 2; } }
    const fishLeft = W.Fishing.data().fish.filter(f => (f.seasons.includes(s) || f.seasons.includes('any')) && !W.Fishing.Book.rec[f.id]).length;
    const fl = K.lines(fishLeft ? `Fish of ${s} not yet in your book: ${fishLeft}` : `Every fish of ${s} is in your book.`, rw); if (ry + fl.length * 10 + 2 < bot) { const fy = Math.max(ry + 4, bot - (fl.length - 1) * 10 - 2); fl.forEach((l, i) => K.text(g, l, rx, fy + i * 10, { color: C.faint })); }
    K.pageTurn(g, 'calendar', x0, y0, pw, ph); g.restore(); }
  function key(k) { if (!D) return false; if (UI.open) { if (k === 'v' || k === 'escape') { UI.open = false; UI.season = null; UI.sel = null; } else if (k === 'arrowright' || k === 'd') { UI.season = SEASONS[(SEASONS.indexOf(UI.season || W.SeasonState.season) + 1) % 4]; UI.sel = null; } else if (k === 'arrowleft' || k === 'a') { UI.season = SEASONS[(SEASONS.indexOf(UI.season || W.SeasonState.season) + 3) % 4]; UI.sel = null; } return true; } if (k === 'v' && !W.Gather.UI.open && !W.Build.UI.busy()) { UI.open = true; return true; } return false; }
  // every calendar tap is a UIKit hit (UI coordinates); a tap the kit did not take still lands on the open book and goes no further
  function pointer(x, y, down) { return !!UI.open; }
  // ================================================================= TICK, SAVE
  let acc = 0; function tick(dt) { if (!D) return; T += dt; acc += dt; if (acc > .5) { acc = 0; check(); } fxTick(dt); Music.tick(dt); }
  const Save = { snapshot() { return { version: 1, records: S.records, discovered: Cal.discovered, offset: Cal.offset }; }, restore(s) { if (S.active) end(); S.records = (s && s.records) || {}; Cal.discovered = (s && s.discovered) || {}; Cal.offset = s && s.offset != null ? s.offset : Cal.offset; Cal.sync(); check(); } };
  function blocked(x, y) { if (!S.active) return false; for (const [a, b, c, d] of D.festivals[S.active].blockers || []) if (x >= a && x <= c && y >= b && y <= d) return true; return false; }
  function init(data, world) { D = data; W = world; Cal.sync(); W.Fishing.on('catch', Lc => { if (W.Fishing.S.vista !== 'tide' || !S.active) return; const r = rec(S.active); r.tideCatches = (r.tideCatches || 0) + 1; if (r.tideCatches >= 2 && !r.found.drowned_bell) { giveItem('drowned_bell'); say('Something comes up tangled in your line with the fish: a small brass bell. Under water, faintly, it was ringing.', 6); } }); W.Survival.on('day', () => { Cal.onDay(); check(); }); W.Survival.on('wake', () => { Cal.onDay(); check(); });
    const SS = W.Survival.SaveState, sn = SS.snapshot.bind(SS), ld = SS.load.bind(SS); SS.snapshot = () => Object.assign(sn(), { festival: Save.snapshot() }); SS.load = s => { s = s || SS.read(); const ok = ld(s); if (ok) SS.guard('festivals', () => Save.restore(s.festival)); return ok; }; }
  return { init, tick, key, pointer, nearest, blocked, on, Cal, S, UI, rec, act, Save, data: () => D, active: () => S.active, isOnNow, force: f => { forced = f; check(); }, setEnabled: v => { enabled = v; check(); }, render: { fx: drawFx, world, calendar: (g, vw, vh) => { if (!window.UIKit) return; if (UI.open) drawCal(g, vw, vh); else UIKit.openT('calendar', false); } }, Music };
})();
