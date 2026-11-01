// MOSSlight crafting + construction. Data: assets/build/{recipes,components,build_atlas}.json.
// Uses the existing Inventory, Survival (time/energy), Interaction and save snapshot; adds no parallel systems.
window.Build = (() => {
  let W = null, COMP = {}, RECIPES = [], STN = {}, CFG = null, A = null, IDX = null, AW = 0, baseCol = null;
  const T = 16; let uid = 1;
  const S = { list: [], F: new Map(), L: new Map(), Wl: new Map(), R: new Map(), N: new Map(), roofGroups: [], unlocked: {}, stationsBuilt: {} };
  const key = (x, y) => x + ',' + y;
  const FX = { msg: null, t: 0, say(m, t = 2.6) { this.msg = m; this.t = t; } };
  const inv = () => W.Gather.Inventory, items = () => W.Gather.items();
  const finished = e => !e.work;

  // ---------------- resources (the one existing inventory)
  const have = cost => Object.entries(cost || {}).every(([id, n]) => inv().count(id) >= n);
  const missing = cost => Object.entries(cost || {}).filter(([id, n]) => inv().count(id) < n).map(([id, n]) => `${n - inv().count(id)} ${items()[id] ? items()[id].name : id}`);
  function take(cost) { if (!have(cost)) return false; for (const [id, n] of Object.entries(cost || {})) { let left = n; const sl = inv().slots; for (let i = sl.length - 1; i >= 0 && left > 0; i--) if (sl[i] && sl[i].id === id) left -= inv().remove(i, Math.min(left, sl[i].qty)); } return true; }
  const canHold = (id, q) => { const it = items()[id]; let room = 0; for (const s of inv().slots) room += !s ? it.stack : (s.id === id ? it.stack - s.qty : 0); return room >= q; };

  // ---------------- recipes + crafting jobs
  const Craft = {
    job: null, station: 'hand',
    unlockedFor(st) { return RECIPES.filter(r => r.station === st && S.unlocked[r.id]); },
    check() { for (const r of RECIPES) { if (S.unlocked[r.id]) continue; const u = r.unlock; const ok = u.type === 'start' || (u.type === 'station' && S.stationsBuilt[u.id]) || (u.type === 'item' && (W.Gather.Journal.found[u.id] || inv().count(u.id) > 0)); if (ok) { const first = Object.keys(S.unlocked).length > 0; S.unlocked[r.id] = true; if (first && u.type !== 'start') FX.say('New recipe: ' + r.name); } } },
    start(id, station) { const r = RECIPES.find(x => x.id === id); if (!r) return { ok: false, reason: 'Unknown recipe.' }; if (this.job) return { ok: false, reason: 'Already working.' };
      if (!S.unlocked[id]) return { ok: false, reason: 'You have not worked out how to make that yet.' };
      if (r.station !== (station || this.station)) return { ok: false, reason: 'That needs a ' + STN[r.station] + '.' };
      if (!have(r.ingredients)) return { ok: false, reason: 'Still need ' + missing(r.ingredients).join(', ') + '.' };
      if (!W.Survival.Energy.canDo({ heavy: r.energy >= 5, energy: r.energy })) return { ok: false, reason: 'You are too tired for that.' };
      if (!canHold(r.result, r.qty) && !Object.keys(r.ingredients).length) return { ok: false, reason: 'Your pack is full.' };
      this.job = { id, r, t: 0, dur: Math.max(0.5, Math.min(2, r.minutes / 20)) }; return { ok: true }; },
    cancel() { if (!this.job) return false; FX.say('Stopped. Nothing was used.'); this.job = null; return true; },   // ingredients are only taken at completion
    tick(dt) { if (!this.job) return; this.job.t += dt; if (this.job.t >= this.job.dur) this.finish(); },
    finish() { const { r } = this.job; this.job = null; if (!have(r.ingredients)) return FX.say('Something went missing from your pack.');
      const a = W.Survival.Activities.performCustom('craft:' + r.id, { label: r.name, heavy: r.energy >= 5, energy: r.energy, minutes: r.minutes, anim: 'build' }); if (!a.ok) return FX.say(a.reason);
      take(r.ingredients); const got = inv().add(r.result, r.qty); FX.say(got === r.qty ? `Made ${r.qty > 1 ? r.qty + ' × ' : ''}${r.name}.` : 'Your pack is full; some of it stays on the bench.'); W.Gather.FX.pop(W.Player.x, W.Player.y - 30, [[r.result, got]]); this.check(); return true; },
  };

  // ---------------- world model
  function mask(map, cx, cy) { return (map.has(key(cx, cy - 1)) ? 1 : 0) | (map.has(key(cx + 1, cy)) ? 2 : 0) | (map.has(key(cx, cy + 1)) ? 4 : 0) | (map.has(key(cx - 1, cy)) ? 8 : 0); }
  function stamp(col, x0, y0, x1, y1, v = 1) { const w = W.DATA.play.width, h = W.DATA.play.height; for (let y = Math.max(0, y0); y < Math.min(h, y1); y++) for (let x = Math.max(0, x0); x < Math.min(w, x1); x++) col[y * w + x] = v; }
  const footRect = (e, d) => { const f = (e.rot % 2 && d.side_foot) || d.foot || [0, 0]; return [e.x - (f[0] >> 1), e.y - f[1] + 1, e.x + ((f[0] + 1) >> 1), e.y + 1]; };
  function rebuild() {
    for (const k of ['F', 'L', 'Wl', 'R', 'N']) S[k] = new Map();
    for (const e of S.list) { const d = COMP[e.type]; const m = { foundation: S.F, floor: S.L, wall: S.Wl, roof: S.R, fence: S.N }[d.layer]; if (m) m.set(key(e.cx, e.cy), e); }
    const col = W.DATA.col; col.set(baseCol);
    for (const e of S.list) { const d = COMP[e.type]; const x0 = (e.cx || 0) * T, y0 = (e.cy || 0) * T;
      if (d.layer === 'wall') { const m = mask(S.Wl, e.cx, e.cy); const door = e.opening && COMP[e.opening].kind === 'door';
        if (door && e.open) { stamp(col, x0, y0 + 5, x0 + 2, y0 + 12); stamp(col, x0 + 14, y0 + 5, x0 + 16, y0 + 12); continue; }
        if (m & 10 || !(m & 5)) stamp(col, x0 + (m & 8 ? 0 : 4), y0 + 5, x0 + (m & 2 ? 16 : 12), y0 + 12);
        if (m & 5) stamp(col, x0 + 4, y0 + (m & 1 ? 0 : 5), x0 + 12, y0 + (m & 4 ? 16 : 12)); }
      else if (d.layer === 'fence') { const m = mask(S.N, e.cx, e.cy); if (d.kind === 'gate') { if (e.open) { stamp(col, x0, y0 + 10, x0 + 3, y0 + 14); stamp(col, x0 + 13, y0 + 10, x0 + 16, y0 + 14); } else stamp(col, x0, y0 + 10, x0 + 16, y0 + 14); continue; }
        stamp(col, x0 + 6, y0 + 10, x0 + 10, y0 + 14); if (m & 2) stamp(col, x0 + 8, y0 + 10, x0 + 16, y0 + 14); if (m & 8) stamp(col, x0, y0 + 10, x0 + 8, y0 + 14); if (m & 1) stamp(col, x0 + 6, y0, x0 + 10, y0 + 10); if (m & 4) stamp(col, x0 + 6, y0 + 14, x0 + 10, y0 + 16); }
      else if (d.layer === 'object' && d.foot && d.foot[0] && !d.ground && !d.mount) { const r = footRect(e, d); stamp(col, r[0], r[1], r[2], r[3]); } }
    // roof groups (flood fill) so a whole roof lifts when the player steps inside
    S.roofGroups = []; const seen = new Set();
    for (const k of S.R.keys()) { if (seen.has(k)) continue; const g = new Set(), st = [k]; while (st.length) { const c = st.pop(); if (g.has(c) || !S.R.has(c)) continue; g.add(c); seen.add(c); const [x, y] = c.split(',').map(Number); st.push(key(x + 1, y), key(x - 1, y), key(x, y + 1), key(x, y - 1)); } S.roofGroups.push(g); }
    S.stationsBuilt = {}; for (const e of S.list) { const d = COMP[e.type]; if (d.station && finished(e)) S.stationsBuilt[d.station] = true; }
    Craft.check(); if (W.relight) W.relight();
  }
  const objectCell = (x, y) => [Math.floor(x / T), Math.floor(y / T)];

  // ---------------- placement validation: one function, always a reason
  function validate(type, p, rot = 0, ignore = null) {
    const d = COMP[type]; const cell = !(d.layer === 'object') || d.mount; const cx = p.cx, cy = p.cy; const x0 = cx * T, y0 = cy * T;
    const col = W.DATA.col, w = W.DATA.play.width; const free = (a, b, c, e) => { for (let y = b; y < e; y++) for (let x = a; x < c; x++) if (x < 0 || y < 0 || x >= w || y >= W.DATA.play.height || col[y * w + x]) return false; return true; };
    const onNode = (x, y) => W.Gather.Nodes.list.some(n => n.def.kind !== 'hidden' && n.def.kind !== 'tree_marker' && Math.abs(n.def.x - x) < 10 && Math.abs(n.def.y - y) < 10);
    const player = (a, b, c, e) => W.Player.x + 4 > a && W.Player.x - 4 < c && W.Player.y + 2 > b && W.Player.y - 2 < e;
    if (d.layer === 'foundation') { if (S.F.has(key(cx, cy))) return 'There is already a foundation here.'; if (!free(x0, y0, x0 + T, y0 + T)) return 'The ground here is blocked.'; if (onNode(x0 + 8, y0 + 8)) return 'Something is growing or lying here.'; return null; }
    if (d.layer === 'floor') { if (!S.F.has(key(cx, cy))) return 'Floors need a foundation.'; if (S.L.has(key(cx, cy))) return 'There is already a floor here.'; if (S.Wl.has(key(cx, cy))) return 'A wall stands here.'; return null; }
    if (d.layer === 'wall') { if (!S.F.has(key(cx, cy))) return 'Walls need a foundation beneath them.'; if (S.Wl.has(key(cx, cy))) return 'There is already a wall here.'; if (S.L.has(key(cx, cy))) return 'Lift the floor first.'; if (!free(x0, y0 + 5, x0 + T, y0 + 12)) return 'Something is in the way.'; if (player(x0, y0 + 5, x0 + T, y0 + 12)) return 'You are standing there.'; return null; }
    if (d.layer === 'opening') { const e = S.Wl.get(key(cx, cy)); if (!e) return (d.kind === 'door' ? 'Doors' : 'Windows') + ' go into a wall.'; if (e.work) return 'Finish the wall first.'; if (e.opening) return 'This wall already has an opening.'; const m = mask(S.Wl, cx, cy); if ((m & 10) !== 10 || (m & 5)) return 'Needs a straight east-west wall on both sides.'; return null; }
    if (d.layer === 'roof') { if (S.R.has(key(cx, cy))) return 'Already roofed.'; if (!S.F.has(key(cx, cy))) return 'A roof must sit over a foundation.'; let sup = false; for (let r = 0; r <= 3 && !sup; r++) for (const [a, b] of [[r, 0], [-r, 0], [0, r], [0, -r]]) { const c = key(cx + a, cy + b); const we = S.Wl.get(c); if (we && !we.work) sup = true; } if (!sup) sup = S.list.some(e => COMP[e.type].support && !e.work && Math.abs(e.x - (x0 + 8)) <= 48 && Math.abs(e.y - (y0 + 8)) <= 48); return sup ? null : 'Nothing here could hold a roof up: build walls or a support within three cells.'; }
    if (d.layer === 'fence') { if (S.N.has(key(cx, cy)) || S.Wl.has(key(cx, cy))) return 'Occupied.'; if (!free(x0, y0 + 10, x0 + T, y0 + 14)) return 'Something is in the way.'; if (player(x0, y0 + 10, x0 + T, y0 + 14)) return 'You are standing there.'; return null; }
    if (d.mount) { const e = S.Wl.get(key(cx, cy)); if (!e || e.work) return 'This hangs on a wall.'; if (mask(S.Wl, cx, cy) & 4) return 'Only a south-facing wall face can hold it.'; if (e.opening) return 'Not over an opening.'; if (S.list.some(o => COMP[o.type].mount && o.cx === cx && o.cy === cy && o !== ignore)) return 'Already something on this wall.'; return null; }
    if (d.ground) { const sp = A.index[d.sprite]; if (S.list.some(o => o !== ignore && COMP[o.type].ground && Math.abs(o.x - p.x) < 16 && Math.abs(o.y - p.y) < 8)) return 'Overlaps another rug.'; const c = W.DATA.col; return c[(p.y - 2) * w + p.x] && !S.F.size ? 'The ground here is blocked.' : null; }
    const f = (rot % 2 && d.side_foot) || d.foot; const a = p.x - (f[0] >> 1), b = p.y - f[1] + 1, c = p.x + ((f[0] + 1) >> 1), e = p.y + 1;
    if (ignore) { const r = footRect(ignore, d); stamp(col, r[0], r[1], r[2], r[3], 0); }
    const ok = free(a, b, c, e); if (ignore) rebuild();
    if (!ok) return 'Something is in the way.'; if (player(a, b, c, e)) return 'You are standing there.'; if (onNode(p.x, p.y)) return 'Something is growing or lying here.'; return null;
  }
  const costOf = d => d.item ? { [d.item]: 1 } : d.cost;

  // place = validate → resources → first work session. A big job stays a site and continues over days.
  function place(type, p, rot = 0) {
    const d = COMP[type]; const why = validate(type, p, rot); if (why) return { ok: false, reason: why };
    const cost = costOf(d); if (!have(cost)) return { ok: false, reason: 'Still need ' + missing(cost).join(', ') + '.' };
    const minutes = d.minutes || (d.item ? 5 : 10), energy = d.energy || 0;
    const sess = Math.min(minutes, CFG.session_minutes); if (!W.Survival.Energy.canDo({ heavy: energy >= 5, energy: Math.ceil(energy * sess / minutes) })) return { ok: false, reason: 'You are too tired to build that.' };
    take(cost);
    if (d.layer === 'opening') { const e = S.Wl.get(key(p.cx, p.cy)); e.opening = type; e.open = false; e.opdur = d.durability; }
    else { const e = { uid: uid++, type, cx: p.cx, cy: p.cy, x: p.x, y: p.y, rot: rot % 4, dur: d.durability || 60, work: minutes, on: true }; if (d.storage) e.slots = new Array(d.storage.slots).fill(null); S.list.push(e); work(e, true); }
    if (d.layer === 'opening') { W.Survival.Activities.performCustom('build:' + type, { label: d.name, heavy: false, energy, minutes, anim: 'build' }); }
    rebuild(); return { ok: true };
  }
  function work(e, quiet) { const d = COMP[e.type]; const total = d.minutes || (d.item ? 5 : 10); const sess = Math.min(e.work, CFG.session_minutes); const en = Math.ceil((d.energy || 0) * sess / total);
    const a = W.Survival.Activities.performCustom('build:' + e.type, { label: d.name, heavy: (d.energy || 0) >= 5, energy: en, minutes: sess, anim: 'build' }); if (!a.ok) { FX.say(a.reason); return false; }
    e.work -= sess; if (!e.work) { FX.say(d.name + (quiet ? ' placed.' : ' finished.')); rebuild(); } else FX.say(`${d.name}: about ${Math.ceil(e.work / 60)} hour${e.work > 60 ? 's' : ''} of work left.`); return true; }
  function at(p) { // topmost thing at a cursor position
    const objs = S.list.filter(e => COMP[e.type].layer === 'object' && Math.abs(e.x - p.x) <= 12 && e.y - p.y <= 12 && p.y - e.y <= 8); if (objs.length) return objs[objs.length - 1];
    return S.R.get(key(p.cx, p.cy)) || S.N.get(key(p.cx, p.cy)) || S.Wl.get(key(p.cx, p.cy)) || S.L.get(key(p.cx, p.cy)) || S.F.get(key(p.cx, p.cy)) || null; }
  function remove(e) { const d = COMP[e.type]; if (d.layer === 'foundation' && (S.Wl.has(key(e.cx, e.cy)) || S.L.has(key(e.cx, e.cy)) || S.R.has(key(e.cx, e.cy)))) return { ok: false, reason: 'Clear what stands on it first.' };
    if (d.layer === 'wall' && S.R.size) { const m = S.R.has(key(e.cx, e.cy)); if (m) return { ok: false, reason: 'Take the roof off first.' }; }
    if (d.storage && e.slots.some(Boolean)) return { ok: false, reason: 'Empty it first.' };
    if (d.layer === 'wall' && e.opening) { const od = COMP[e.opening]; refund(od.cost); e.opening = null; e.open = false; rebuild(); return { ok: true }; }
    if (d.item) inv().add(d.item, 1); else refund(d.cost); S.list.splice(S.list.indexOf(e), 1); rebuild(); return { ok: true }; }
  function refund(cost) { for (const [id, n] of Object.entries(cost || {})) { const q = Math.floor(n * CFG.demolish_refund); if (q) inv().add(id, q); } }
  function move(e, p, rot) { const d = COMP[e.type]; if (d.layer !== 'object') return { ok: false, reason: 'Only furniture can be moved.' }; const why = validate(e.type, p, rot, e); if (why) return { ok: false, reason: why }; e.x = p.x; e.y = p.y; e.cx = p.cx; e.cy = p.cy; e.rot = rot % 4; rebuild(); return { ok: true }; }
  function damage(e, n) { e.dur = Math.max(0, e.dur - n); }   // hook for the future monster milestone
  function repair(e) { const d = COMP[e.type]; const max = d.durability || 60; if (e.dur >= max) return { ok: false, reason: 'It is sound.' }; const first = Object.entries(costOf(d) || {})[0]; const c = d.item ? { plank: 1 } : { [first[0]]: 1 }; if (!have(c)) return { ok: false, reason: 'Still need ' + missing(c).join(', ') + '.' };
    const a = W.Survival.Activities.performCustom('build:repair', { label: 'Repair', heavy: false, energy: CFG.repair.energy, minutes: CFG.repair.minutes, anim: 'build' }); if (!a.ok) return a; take(c); e.dur = Math.min(max, e.dur + max * CFG.repair.amount); return { ok: true }; }
  const lights = () => S.list.filter(e => COMP[e.type].light && finished(e) && e.on !== false).map(e => Object.assign({ x: e.x, y: e.y - 12 }, COMP[e.type].light));

  // ---------------- interaction: the objects say what they do
  function nearest(px, py) { let best = null, bd = 1e9; const consider = (e, x, y, label, act, r = 24) => { const d = Math.hypot(x - px, y - py); if (d < r && d < bd) { bd = d; best = { id: 'build:' + e.uid, label, x, y, r, buildAct: act, e }; } };
    for (const e of S.list) { const d = COMP[e.type]; const isCell = d.layer !== 'object'; const x = isCell ? e.cx * T + 8 : e.x, y = isCell ? e.cy * T + 11 : e.y;
      if (e.work) { if (d.layer !== 'object' || true) consider(e, x, y, `Work on ${d.name}`, () => work(e)); continue; }
      if (e.dur < (d.durability || 60) * 0.5) { consider(e, x, y, `Repair ${d.name}`, () => { const r = repair(e); FX.say(r.ok ? 'Repaired.' : r.reason); }); continue; }
      if (d.station) consider(e, x, y, `Use ${d.name}`, () => { Craft.station = d.station; UI.open = 'craft'; UI.cur = 0; }, 28);
      else if (d.storage) consider(e, x, y, `Open ${d.name}`, () => { UI.open = 'storage'; UI.store = e; UI.side = 0; UI.cur = 0; });
      else if (d.sleep) consider(e, x, y, 'Rest until morning', () => W.Survival.Sleep.start());
      else if (d.toggle) consider(e, x, y, e.on ? `Put out ${d.name}` : `Light ${d.name}`, () => { e.on = !e.on; if (W.relight) W.relight(); });
      else if (d.kind === 'gate') consider(e, x, y + 2, e.open ? `Close ${d.name}` : `Open ${d.name}`, () => { e.open = !e.open; rebuild(); });
      else if (d.layer === 'wall' && e.opening && COMP[e.opening].kind === 'door') consider(e, x, y, e.open ? 'Close door' : 'Open door', () => { if (e.open && Math.abs(W.Player.x - x) < 8 && Math.abs(W.Player.y - y) < 5) return FX.say('You are in the doorway.'); e.open = !e.open; rebuild(); }, 20); }
    return best; }

  // ---------------- storage
  const Storage = {
    allowed(e, id) { const f = COMP[e.type].storage.filter; return !f || f.includes(items()[id].category); },
    transfer(from, i, to, fromStore) { const s = from[i]; if (!s) return false; const it = items()[s.id]; let left = s.qty; for (const t of to) if (t && t.id === s.id && t.qty < it.stack) { const n = Math.min(it.stack - t.qty, left); t.qty += n; left -= n; if (!left) break; }
      while (left > 0) { const j = to.indexOf(null); if (j < 0) break; const n = Math.min(it.stack, left); to[j] = { id: s.id, qty: n, meta: null }; left -= n; } if (left) s.qty = left; else from[i] = null; inv().count(s.id); return left === 0; },
    deposit(e, i) { const s = inv().slots[i]; if (!s) return false; if (!this.allowed(e, s.id)) { FX.say('That does not belong in here.'); return false; } return this.transfer(inv().slots, i, e.slots); },
    withdraw(e, i) { return this.transfer(e.slots, i, inv().slots); },
  };

  // ---------------- UI
  const CATS = ['Foundation', 'Floor', 'Wall', 'Opening', 'Roof', 'Defense', 'Home'];
  const UI = { open: null, cur: 0, cat: 0, side: 0, store: null, place: null, off: [0, 0], ptr: null, rot: 0, moving: null, hit: [],
    busy() { return !!(this.open || Craft.job); },
    listBuild() { const c = CATS[this.cat]; if (c === 'Home') return Object.values(COMP).filter(d => d.item && inv().count(d.item) > 0); return Object.values(COMP).filter(d => d.cat === c); },
    cursor() { if (this.ptr) return snap(this.ptr[0], this.ptr[1]); const P = W.Player; const dx = P.facing === 'side' ? (P.flip ? -1 : 1) : 0, dy = P.facing === 'up' ? -1 : P.facing === 'down' ? 1 : 0; return snap(P.x + dx * 18 + this.off[0] * 16, P.y - 4 + dy * 18 + this.off[1] * 16); },
    key(k) { if (!W) return false;
      if (Craft.job) { if (k === 'escape' || k === 'x') Craft.cancel(); return true; }
      if (this.place) { const type = this.place;
        if (k === 'escape' || k === 'b') { this.place = null; this.moving = null; this.ptr = null; this.off = [0, 0]; return true; }
        if (k === 'r') { this.rot = (this.rot + 1) % 4; return true; }
        if (k === 'arrowleft') { this.off[0]--; this.ptr = null; return true; } if (k === 'arrowright') { this.off[0]++; this.ptr = null; return true; } if (k === 'arrowup') { this.off[1]--; this.ptr = null; return true; } if (k === 'arrowdown') { this.off[1]++; this.ptr = null; return true; }
        if (k === 'e' || k === 'enter') { this.confirm(); return true; }
        if (k === 'x') { const e = at(this.cursor()); if (e) { const r = remove(e); FX.say(r.ok ? 'Taken down; part of the material comes back.' : r.reason); } return true; }
        if (k === 'm') { const e = at(this.cursor()); if (e && COMP[e.type].layer === 'object') { this.moving = e; this.place = e.type; this.rot = e.rot; FX.say('Moving ' + COMP[e.type].name + '.'); } return true; }
        return false; }
      if (this.open === 'build') { const l = this.listBuild(); if (k === 'arrowup' || k === 'w') this.cur = Math.max(0, this.cur - 1); else if (k === 'arrowdown' || k === 's') this.cur = Math.min(l.length - 1, this.cur + 1); else if (k === 'arrowleft' || k === 'q') { this.cat = (this.cat + CATS.length - 1) % CATS.length; this.cur = 0; } else if (k === 'arrowright') { this.cat = (this.cat + 1) % CATS.length; this.cur = 0; } else if (k === 'e' || k === 'enter') { if (l[this.cur]) { this.place = l[this.cur].id; this.open = null; this.rot = 0; this.off = [0, 0]; } } else if (k === 'escape' || k === 'b') this.open = null; return true; }
      if (this.open === 'craft') { const l = Craft.unlockedFor(Craft.station); if (k === 'arrowup' || k === 'w') this.cur = Math.max(0, this.cur - 1); else if (k === 'arrowdown' || k === 's') this.cur = Math.min(l.length - 1, this.cur + 1); else if (k === 'e' || k === 'enter') { if (l[this.cur]) { const r = Craft.start(l[this.cur].id); if (!r.ok) FX.say(r.reason); } } else if (k === 'escape' || k === 'c') this.open = null; return true; }
      if (this.open === 'storage') { const e = this.store; const n = this.side ? e.slots.length : inv().size; if (k === 'arrowleft') this.cur = Math.max(0, this.cur - 1); else if (k === 'arrowright') this.cur = Math.min(n - 1, this.cur + 1); else if (k === 'arrowup') this.cur = Math.max(0, this.cur - 6); else if (k === 'arrowdown') this.cur = Math.min(n - 1, this.cur + 6); else if (k === 'tab' || k === 'q') { this.side = 1 - this.side; this.cur = 0; } else if (k === 'e' || k === 'enter') { if (this.side) Storage.withdraw(e, this.cur); else Storage.deposit(e, this.cur); } else if (k === 'escape') this.open = null; return true; }
      if (W.Gather.UI.open) return false;
      if (k === 'b') { this.open = 'build'; this.cur = 0; return true; } if (k === 'c') { Craft.station = 'hand'; this.open = 'craft'; this.cur = 0; return true; }
      return false; },
    confirm() { const p = this.cursor(), type = this.place; if (this.moving) { const r = move(this.moving, p, this.rot); FX.say(r.ok ? 'Moved.' : r.reason); if (r.ok) { this.moving = null; this.place = null; } return; } const r = place(type, p, this.rot); if (!r.ok) FX.say(r.reason); else if (COMP[type].item && !inv().count(COMP[type].item)) this.place = null; },
    pointer(x, y, tap) { if (this.open) { if (tap) for (const h of this.hit) if (x >= h[0] && y >= h[1] && x < h[2] && y < h[3]) { h[4](); return true; } return false; } if (!this.place) return false; const wx = x + W.Camera.ix(), wy = y + W.Camera.iy(); if (tap) { const a = this.ptr ? snap(this.ptr[0], this.ptr[1]) : null, b = snap(wx, wy); if (a && a.cx === b.cx && a.cy === b.cy) this.confirm(); } this.ptr = [wx, wy]; return tap; },
    row(g, x, y, w, h, sel) { g.fillStyle = sel ? 'rgba(90,70,40,0.9)' : 'rgba(24,30,28,0.45)'; g.fillRect(x, y, w, h); if (sel) { g.strokeStyle = '#ffd98a'; g.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1); } },
    costLine(g, cost, x, y, maxW) { g.font = '8px ui-monospace, monospace'; let cx = x; for (const [id, n] of Object.entries(cost || {})) { const t = `${inv().count(id)}/${n} ${items()[id].name}`; g.fillStyle = inv().count(id) >= n ? 'rgba(238,220,176,0.75)' : '#e8705b'; g.fillText(t, cx, y); cx += g.measureText(t).width + 8; if (cx > x + maxW) { cx = x; y += 9; } } return y; },
    draw(g, vw, vh, safe, tab) { this.hit = []; const G = W.Gather.UI; g.textAlign = 'left';
      if (FX.t > 0) { g.font = '9px ui-monospace, monospace'; const tw = g.measureText(FX.msg).width + 14; g.fillStyle = 'rgba(40,34,26,0.92)'; g.fillRect(Math.round(vw / 2 - tw / 2), 44 + safe, Math.round(tw), 14); g.fillStyle = '#eedcb0'; g.textAlign = 'center'; g.fillText(FX.msg, vw / 2, 54 + safe); g.textAlign = 'left'; }
      if (Craft.job) { const pw = 120, x = vw / 2 - 60, y = vh - 78 - safe; G.card(g, x, y, pw, 26); g.font = '8px ui-monospace, monospace'; g.fillStyle = '#eedcb0'; g.fillText(Craft.job.r.name, x + 8, y + 11); g.fillStyle = 'rgba(0,0,0,.4)'; g.fillRect(x + 8, y + 15, pw - 16, 4); g.fillStyle = '#8cc452'; g.fillRect(x + 8, y + 15, (pw - 16) * Craft.job.t / Craft.job.dur, 4); }
      if (this.place) { const d = COMP[this.place]; const p = this.cursor(); const why = this.moving ? validate(this.place, p, this.rot, this.moving) : validate(this.place, p, this.rot); const pw = Math.min(vw - 20, 300), x = vw / 2 - pw / 2, y = vh - 56 - safe; G.card(g, x, y, pw, 40); g.font = '9px ui-monospace, monospace'; g.fillStyle = '#eedcb0'; g.fillText((this.moving ? 'Move: ' : '') + d.name, x + 8, y + 12); if (!this.moving) { const nw = g.measureText(d.name).width + 16; this.costLine(g, costOf(d), x + nw, y + 12, pw - nw - 10); } g.font = '8px ui-monospace, monospace'; g.fillStyle = why ? '#e8705b' : '#8cc452'; g.fillText(why || 'E place', x + 8, y + 23); g.fillStyle = 'rgba(238,220,176,.5)'; g.fillText('arrows nudge · R rotate · M move · X take down · Esc done', x + 8, y + 33); }
      if (this.open === 'build') { const l = this.listBuild(), pw = Math.min(vw - 20, 340), ph = Math.min(vh - 20, 210), x = Math.round(vw / 2 - pw / 2), y = Math.round(vh / 2 - ph / 2); G.card(g, x, y, pw, ph); g.font = '9px ui-monospace, monospace'; g.fillStyle = '#eedcb0'; g.fillText('Build', x + 10, y + 14);
        let tx = x + 10; CATS.forEach((c, i) => { g.font = '8px ui-monospace, monospace'; g.fillStyle = i === this.cat ? '#ffd98a' : 'rgba(238,220,176,.5)'; g.fillText(c, tx, y + 27); const tw = g.measureText(c).width; this.hit.push([tx, y + 18, tx + tw, y + 30, () => { this.cat = i; this.cur = 0; }]); tx += tw + 7; });
        const rh = 20, vis = Math.floor((ph - 48) / rh), top = Math.max(0, Math.min(this.cur - vis + 1, l.length - vis)); l.slice(Math.max(0, top), Math.max(0, top) + vis).forEach((d, k) => { const i = Math.max(0, top) + k, ry = y + 33 + k * rh; this.row(g, x + 8, ry, pw - 16, rh - 2, i === this.cur); g.font = '9px ui-monospace, monospace'; g.fillStyle = '#eedcb0'; g.fillText(d.name, x + 12, ry + 8); this.costLine(g, costOf(d), x + 12, ry + 16, pw - 30); this.hit.push([x + 8, ry, x + pw - 8, ry + rh - 2, () => { if (this.cur === i) { this.place = d.id; this.open = null; this.rot = 0; this.off = [0, 0]; } else this.cur = i; }]); });
        if (!l.length) { g.fillStyle = 'rgba(238,220,176,.5)'; g.fillText('Nothing to place yet: craft furniture with C.', x + 12, y + 46); } g.font = '8px ui-monospace, monospace'; g.fillStyle = 'rgba(238,220,176,.45)'; g.fillText('← → category · ↑ ↓ choose · E select · Esc close', x + 10, y + ph - 6); }
      if (this.open === 'craft') { const l = Craft.unlockedFor(Craft.station), pw = Math.min(vw - 20, 360), ph = Math.min(vh - 20, 220), x = Math.round(vw / 2 - pw / 2), y = Math.round(vh / 2 - ph / 2); G.card(g, x, y, pw, ph); g.font = '9px ui-monospace, monospace'; g.fillStyle = '#eedcb0'; g.fillText(STN[Craft.station], x + 10, y + 14);
        const rh = 24, vis = Math.floor((ph - 36) / rh), top = Math.max(0, Math.min(this.cur - vis + 1, l.length - vis)); l.slice(Math.max(0, top), Math.max(0, top) + vis).forEach((r, k) => { const i = Math.max(0, top) + k, ry = y + 20 + k * rh; this.row(g, x + 8, ry, pw - 16, rh - 2, i === this.cur); G.drawIcon(g, r.icon, x + 11, ry + 2, 1.125, tab); g.font = '9px ui-monospace, monospace'; g.fillStyle = have(r.ingredients) ? '#eedcb0' : 'rgba(238,220,176,.5)'; g.fillText(r.name + (r.qty > 1 ? ' ×' + r.qty : ''), x + 32, ry + 9); g.font = '8px ui-monospace, monospace'; g.fillStyle = 'rgba(238,220,176,.5)'; g.textAlign = 'right'; g.fillText(`${r.minutes} min · ${r.energy} energy`, x + pw - 12, ry + 9); g.textAlign = 'left'; this.costLine(g, r.ingredients, x + 32, ry + 18, pw - 50); this.hit.push([x + 8, ry, x + pw - 8, ry + rh - 2, () => { if (this.cur === i) { const a = Craft.start(r.id); if (!a.ok) FX.say(a.reason); } else this.cur = i; }]); });
        if (!l.length) { g.fillStyle = 'rgba(238,220,176,.5)'; g.fillText('Nothing here yet.', x + 12, y + 34); } g.font = '8px ui-monospace, monospace'; g.fillStyle = 'rgba(238,220,176,.45)'; g.fillText('↑ ↓ choose · E make · Esc stops work (nothing is used until done)', x + 10, y + ph - 6); }
      if (this.open === 'storage') { const e = this.store, cell = 24, cols = 6, sl = [inv().slots, e.slots], pw = cols * cell * 2 + 34, rows = Math.ceil(Math.max(inv().size, e.slots.length) / cols), ph = rows * cell + 66, x = Math.round(vw / 2 - pw / 2), y = Math.round(vh / 2 - ph / 2); G.card(g, x, y, pw, ph); g.font = '9px ui-monospace, monospace';
        [0, 1].forEach(sd => { const ox = x + 10 + sd * (cols * cell + 14); g.fillStyle = sd === this.side ? '#ffd98a' : 'rgba(238,220,176,.6)'; g.fillText(sd ? COMP[e.type].name : 'Pack', ox, y + 14); sl[sd].forEach((s, i) => { const cx = ox + (i % cols) * cell, cy = y + 20 + Math.floor(i / cols) * cell; const sel = sd === this.side && i === this.cur; g.fillStyle = sel ? 'rgba(90,70,40,.9)' : 'rgba(24,30,28,.6)'; g.fillRect(cx, cy, cell - 2, cell - 2); g.strokeStyle = sel ? '#ffd98a' : 'rgba(222,220,180,.25)'; g.strokeRect(cx + .5, cy + .5, cell - 3, cell - 3); if (s) { G.drawIcon(g, s.id, cx + 2, cy + 2, 1.125, tab); if (s.qty > 1) { g.font = '8px ui-monospace, monospace'; g.textAlign = 'right'; g.fillStyle = '#eedcb0'; g.fillText(s.qty, cx + cell - 4, cy + cell - 4); g.textAlign = 'left'; g.font = '9px ui-monospace, monospace'; } } this.hit.push([cx, cy, cx + cell, cy + cell, () => { if (this.side === sd && this.cur === i) { if (sd) Storage.withdraw(e, i); else Storage.deposit(e, i); } else { this.side = sd; this.cur = i; } }]); }); });
        const sel = sl[this.side][this.cur]; g.font = '8px ui-monospace, monospace'; if (sel) { const it = items()[sel.id]; g.fillStyle = '#eedcb0'; g.fillText(it.name, x + 10, y + ph - 26); G.wrap(g, it.description, x + 10, y + ph - 16, pw - 20, 9, 'rgba(238,220,176,.6)'); } g.fillStyle = 'rgba(238,220,176,.4)'; g.textAlign = 'right'; g.fillText('Q switch · E move stack · Esc close', x + pw - 10, y + ph - 26); g.textAlign = 'left'; }
    } };
  function snap(x, y) { const cx = Math.floor(x / T), cy = Math.floor(y / T); const type = UI.place; const d = type && COMP[type]; if (d && d.layer === 'object' && !d.mount) return { cx, cy, x: Math.round(x / 8) * 8, y: Math.round(y / 8) * 8 }; return { cx, cy, x: cx * T + 8, y: cy * T + 8 }; }

  // ---------------- drawing into the indexed frame (same palette table + lamp pools as the world)
  function blit(c, s, x, y, base, flip, mod) { if (!s) return; const { d, W: FW, H: FH, tab, dayTab, dep, LW, LI, LIGHTS, lightAmount, flick } = c; const x0 = x - (flip ? s.w - 1 - s.ox : s.ox), y0 = y - s.oy; const damaged = mod && mod.damaged, snow = mod && mod.snow, site = mod && mod.site, tint = mod && mod.tint;
    for (let yy = 0; yy < s.h; yy++) { const py = y0 + yy; if (py < 0 || py >= FH) continue; for (let xx = 0; xx < s.w; xx++) { const pi0 = IDX[(s.y + yy) * AW + s.x + (flip ? s.w - 1 - xx : xx)]; if (!pi0) continue; const px = x0 + xx; if (px < 0 || px >= FW) continue; const i = py * FW + px; if (base !== null && dep[i] > base) continue; if (site && (px + py) % 2) continue;
      let pi = pi0; if (damaged && (px * 7 + py * 13) % 9 === 0) pi = W.DATA.play.shade[W.DATA.play.shade[pi]]; if (snow && (px * 7 + py * 11) % 29) pi = snow[(py % 4 === 3) ? 2 : ((px * 5 + py) % 7 ? 4 : 3)];
      const t = tab[pi]; let r = t[0], g = t[1], b = t[2]; const lw = LW[i]; if (lw > 0 && lightAmount > 0) { const L = LIGHTS[LI[i]]; if (L.kind !== 'firefly') { const w = lw * lightAmount * flick[LI[i]]; const dc = dayTab[pi]; r += (dc[0] * L.color[0] * 1.08 + 18 - r) * w; g += (dc[1] * L.color[1] * 1.08 + 18 - g) * w; b += (dc[2] * L.color[2] * 1.08 + 18 - b) * w; } }
      if (tint) { r = r * .55 + tint[0] * .45; g = g * .55 + tint[1] * .45; b = b * .55 + tint[2] * .45; } const o = i * 4; c.d[o] = r; c.d[o + 1] = g; c.d[o + 2] = b; } } }
  function shade(c, x0, y0, x1, y1, f, base = null) { const { d, W: FW, H: FH, dep } = c; for (let y = Math.max(0, y0); y < Math.min(FH, y1); y++) for (let x = Math.max(0, x0); x < Math.min(FW, x1); x++) { const i = y * FW + x; if (base !== null && dep[i] > base) continue; const o = i * 4; d[o] *= f; d[o + 1] *= f; d[o + 2] *= f; } }
  function contact(c, cx, cy, rx, ry, f) { const { d, W: FW, H: FH, dep } = c; for (let y = Math.floor(cy - ry); y <= cy + ry; y++) for (let x = Math.floor(cx - rx); x <= cx + rx; x++) { if (((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 > 1 || x < 0 || y < 0 || x >= FW || y >= FH) continue; const i = y * FW + x; if (dep[i]) continue; const o = i * 4; d[o] *= f; d[o + 1] *= f; d[o + 2] *= f; } }
  const dmg = e => { const m = COMP[e.type].durability || 60; return e.dur < m * .5; };
  function spriteFor(e) { const d = COMP[e.type]; if (d.layer === 'wall') { const m = mask(S.Wl, e.cx, e.cy); if (e.opening && !e.work) { const k = COMP[e.opening].kind; return A.index[k === 'window' ? `window_${d.mat}` : `door_${e.open ? 'open' : 'closed'}_${d.mat}`]; } return A.index[`wall_${d.mat}_${m}`]; } if (d.layer === 'fence') { if (d.kind === 'gate') return A.index[`${d.sprite}_${e.open ? 'open' : 'closed'}`]; return A.index[`fence_${mask(S.N, e.cx, e.cy)}`]; } return A.index[(e.rot % 2 && d.side) || d.sprite]; }
  const baseY = e => { const d = COMP[e.type]; return d.layer === 'wall' ? e.cy * T + 11 : d.layer === 'fence' ? e.cy * T + 13 : d.mount ? e.cy * T + 12 : e.y; };
  function drawItem(c, e) { const d = COMP[e.type], s = spriteFor(e), mod = { damaged: dmg(e), site: !!e.work }; if (d.layer === 'wall' || d.layer === 'fence') blit(c, s, e.cx * T, baseY(e), baseY(e), false, mod); else if (d.mount) blit(c, s, e.cx * T + 8, e.cy * T + 4, baseY(e), false, mod); else blit(c, s, e.x, e.y, e.y, e.rot >= 2, mod); }
  const R = { 
    ground(c) { if (!W) return; const fnd = [...S.F.values()].sort((a, b) => a.cy - b.cy);
      for (const e of fnd) { const m = mask(S.F, e.cx, e.cy) & 14; if (!(m & 4)) shade(c, e.cx * T + 1, e.cy * T + 20, e.cx * T + 19, e.cy * T + 22, .78); blit(c, A.index[`fnd_${COMP[e.type].mat}_${m}`], e.cx * T, e.cy * T, null, false, { damaged: dmg(e), site: !!e.work }); }
      for (const e of S.L.values()) { blit(c, A.index[COMP[e.type].sprite], e.cx * T, e.cy * T, null, false, { site: !!e.work }); if (S.Wl.has(key(e.cx, e.cy - 1))) shade(c, e.cx * T, e.cy * T, e.cx * T + 16, e.cy * T + 5, .72); if (S.Wl.has(key(e.cx - 1, e.cy))) shade(c, e.cx * T, e.cy * T, e.cx * T + 2, e.cy * T + 16, .85); }
      for (const e of S.list) { const d = COMP[e.type]; if (d.ground) blit(c, A.index[d.sprite], e.x, e.y, null, false, { site: !!e.work }); }
      // contact + cast shadows: one light, upper-left, shadows fall lower-right
      for (const e of S.Wl.values()) { const m = mask(S.Wl, e.cx, e.cy); if (!(m & 4)) shade(c, e.cx * T + 1, e.cy * T + 12, e.cx * T + 17, e.cy * T + 15, .72); }
      for (const e of S.N.values()) contact(c, e.cx * T + 9, e.cy * T + 14, 7, 1.5, .78);
      for (const e of S.list) { const d = COMP[e.type]; if (d.layer !== 'object' || d.ground || d.mount) continue; const s = A.index[(e.rot % 2 && d.side) || d.sprite]; const hw = Math.max(3, s.w * .42); shade; contact(c, e.x + 2, e.y + 1, hw + 1, 2.2, .82); contact(c, e.x, e.y, hw, 1.2, .78); } },
    items(c, front) { if (!W) return; const py = c.pyBase; const l = S.list.filter(e => { const d = COMP[e.type]; return (d.layer === 'wall' || d.layer === 'fence' || (d.layer === 'object' && !d.ground)) && (baseY(e) > py) === front; }).sort((a, b) => baseY(a) - baseY(b) || a.uid - b.uid); for (const e of l) drawItem(c, e); },
    roofs(c) { if (!W) return; const pc = key(Math.floor(W.Player.x / T), Math.floor(W.Player.y / T)); const snow = c.season === 'winter' ? PAL_SNOW() : null;
      for (const g of S.roofGroups) { if (g.has(pc)) continue; const cells = [...g].map(k => k.split(',').map(Number)).sort((a, b) => a[1] - b[1]); const groupBase = Math.max(...cells.map(k => k[1])) * T + 16;
        for (const [cx, cy] of cells) { let top = cy, bot = cy; while (g.has(key(cx, top - 1))) top--; while (g.has(key(cx, bot + 1))) bot++; const n = bot - top + 1, i = cy - top, rd = Math.floor((n - 1) / 2); const part = i === n - 1 ? 'eave' : i === rd ? 'ridge' : i < rd ? 'north' : 'south'; const e = S.R.get(key(cx, cy));
          if (part === 'eave') shade(c, cx * T, cy * T - 13, cx * T + 16, cy * T - 9, .72, groupBase);    // the eave shades the wall below it
          blit(c, A.index[`roof_${COMP[e.type].mat}_${part}_${g.has(key(cx - 1, cy)) ? 0 : 1}${g.has(key(cx + 1, cy)) ? 0 : 1}`], cx * T, cy * T - 34, groupBase, false, { damaged: dmg(e), site: !!e.work, snow }); } } },
    ghost(c) { if (!W || !UI.place) return; const type = UI.place, d = COMP[type], p = UI.cursor(), rot = UI.rot; const why = UI.moving ? validate(type, p, rot, UI.moving) : validate(type, p, rot); const mod = { tint: why ? [220, 70, 60] : [120, 230, 120] }; const fake = { type, cx: p.cx, cy: p.cy, x: p.x, y: p.y, rot };
      let s; if (d.layer === 'foundation') { blit(c, A.index[`fnd_${d.mat}_0`], p.cx * T, p.cy * T, null, false, mod); return; } if (d.layer === 'floor') { blit(c, A.index[d.sprite], p.cx * T, p.cy * T, null, false, mod); return; }
      if (d.layer === 'roof') { blit(c, A.index[`roof_${d.mat}_south_11`], p.cx * T, p.cy * T - 34, null, false, mod); return; } if (d.layer === 'wall') { blit(c, A.index[`wall_${d.mat}_${mask(S.Wl, p.cx, p.cy)}`], p.cx * T, p.cy * T + 11, null, false, mod); return; }
      if (d.layer === 'opening') { const m = (S.Wl.get(key(p.cx, p.cy)) || {}).type; const mat = m ? COMP[m].mat : 'wood'; blit(c, A.index[d.kind === 'window' ? `window_${mat}` : `door_closed_${mat}`], p.cx * T, p.cy * T + 11, null, false, mod); return; }
      if (d.layer === 'fence') { blit(c, d.kind === 'gate' ? A.index[d.sprite + '_closed'] : A.index[`fence_${mask(S.N, p.cx, p.cy)}`], p.cx * T, p.cy * T + 13, null, false, mod); return; } if (d.mount) { blit(c, A.index[d.sprite], p.cx * T + 8, p.cy * T + 4, null, false, mod); return; } blit(c, A.index[(rot % 2 && d.side) || d.sprite], p.x, p.y, null, rot >= 2, mod); },
  };
  let snowCache = null; const PAL_SNOW = () => snowCache || (snowCache = (() => { const r = []; W.DATA.entries.entries.forEach((e, i) => { if (e.family === 'snow') r[e.rank] = i; }); return r; })());

  // ---------------- save: appended to the one snapshot; loading replaces, never duplicates
  const Save = { snapshot() { return { version: 1, uid, list: S.list.map(e => JSON.parse(JSON.stringify(e))), unlocked: S.unlocked }; }, restore(s) { if (!s) return; uid = s.uid; S.list = s.list.map(e => JSON.parse(JSON.stringify(e))); S.unlocked = Object.assign({}, s.unlocked); Craft.job = null; UI.open = null; UI.place = null; rebuild(); } };
  function init(data, world) { W = world; A = data.atlas; AW = A.width; IDX = data.idx; CFG = data.components; data.components.components.forEach(c => COMP[c.id] = c); RECIPES = data.recipes.recipes; STN = data.recipes.stations; baseCol = W.DATA.col.slice(); Craft.check(); rebuild(); W.Gather.on('inventory', () => Craft.check());
    const SS = W.Survival.SaveState, snap_ = SS.snapshot.bind(SS), load = SS.load.bind(SS); SS.snapshot = () => Object.assign(snap_(), { build: Save.snapshot() }); SS.load = s => { s = s || JSON.parse(localStorage.getItem(SS.KEY) || 'null'); const ok = load(s); if (ok && s.build) Save.restore(s.build); return ok; }; }
  function tick(dt) { if (!W) return; if (FX.t > 0) FX.t -= dt; Craft.tick(dt); }
  return { init, tick, on: null, S, Craft, UI, FX, Storage, Save, place, remove, move, validate, work, damage, repair, nearest, lights, rebuild, render: R, comp: () => COMP, recipes: () => RECIPES, snap, baseY, have };
})();
