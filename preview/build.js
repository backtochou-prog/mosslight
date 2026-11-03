// MOSSlight crafting + construction. Data: assets/build/{recipes,components,build_atlas}.json.
// Uses the existing Inventory, Survival (time/energy), Interaction and save snapshot; adds no parallel systems.
window.Build = (() => {
  let W = null, COMP = {}, RECIPES = [], STN = {}, CFG = null, A = null, IDX = null, AW = 0, baseCol = null;
  const T = 16; let uid = 1;
  const S = { list: [], F: new Map(), L: new Map(), Wl: new Map(), R: new Map(), N: new Map(), roofGroups: [], unlocked: {}, stationsBuilt: {}, rooms: [], stage: 1, stageReached: { 1: 1 }, allStages: false };
  const key = (x, y) => x + ',' + y;
  const FX = { msg: null, t: 0, say(m, t = 2.6) { this.msg = m; this.t = t; if (window.UIKit && UIKit.note) UIKit.note(m, t); } };   // short sentences go to the one note line
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
    check() { for (const r of RECIPES) { if (S.unlocked[r.id]) continue; const u = r.unlock; const ok = u.type === 'start' || (u.type === 'station' && S.stationsBuilt[u.id]) || (u.type === 'item' && (W.Gather.Journal.found[u.id] || inv().count(u.id) > 0)); if (ok) { const first = Object.keys(S.unlocked).length > 0; S.unlocked[r.id] = true; if (first && u.type !== 'start' && window.UIKit) UIKit.toast({ kicker: 'New recipe', title: r.name, icon: r.icon }); } } },
    start(id, station) { const r = RECIPES.find(x => x.id === id); if (!r) return { ok: false, reason: 'Unknown recipe.' }; if (this.job) return { ok: false, reason: 'Already working.' };
      if (!S.unlocked[id]) return { ok: false, reason: 'You have not worked out how to make that yet.' };
      if (r.station !== (station || this.station)) return { ok: false, reason: 'That needs a ' + STN[r.station] + '.' };
      if (!have(r.ingredients)) return { ok: false, reason: 'Still need ' + missing(r.ingredients).join(', ') + '.' };
      if (!W.Survival.Energy.canDo({ heavy: r.energy >= 5, energy: r.energy })) return { ok: false, reason: 'You are too tired for that.' };
      if (r.tool) { const T = W.Gather.Tools, o = T.get(r.tool), inf = T.info(r.tool); if (!o) return { ok: false, reason: 'You do not have that tool.' };
        if (r.repair && o.durability >= inf.durability) return { ok: false, reason: `Your ${inf.name.toLowerCase()} is in good shape.` };
        if (r.tier !== undefined && (o.tier || 0) >= r.tier) return { ok: false, reason: `You already have a ${inf.name.toLowerCase()}.` };
        if (r.tier !== undefined && (o.tier || 0) < r.tier - 1) return { ok: false, reason: `Make the ${(W.Gather.DB.tool(r.tool).tiers[r.tier - 1] || {}).name || 'previous tool'} first.` }; }
      else if (!canHold(r.result, r.qty) && !Object.keys(r.ingredients).length) return { ok: false, reason: 'Your pack is full.' };
      this.job = { id, r, t: 0, dur: Math.max(0.5, Math.min(2, r.minutes / 20)) }; return { ok: true }; },
    cancel() { if (!this.job) return false; FX.say('Stopped. Nothing was used.'); this.job = null; return true; },   // ingredients are only taken at completion
    tick(dt) { if (!this.job) return; this.job.t += dt; if (this.job.t >= this.job.dur) this.finish(); },
    finish() { const { r } = this.job; this.job = null; if (!have(r.ingredients)) return FX.say('Something went missing from your pack.');
      const a = W.Survival.Activities.performCustom('craft:' + r.id, { label: r.name, heavy: r.energy >= 5, energy: r.energy, minutes: r.minutes, anim: 'build' }); if (!a.ok) return FX.say(a.reason);
      if (r.tool) { take(r.ingredients); const T = W.Gather.Tools; const ok = r.repair ? T.repair(r.tool) : T.upgrade(r.tool, r.tier); if (window.UIKit) UIKit.toast({ kicker: r.repair ? 'Mended' : 'Better tool', title: T.info(r.tool).name, sub: r.repair ? 'Good as new' : `Lasts ${T.info(r.tool).durability} uses`, icon: 'tool_' + r.tool, sting: r.repair ? null : 'recipe' }); if (window.Sound && Sound.play) Sound.play('craft_done'); this.check(); return ok; }
      take(r.ingredients); const got = inv().add(r.result, r.qty);
      if (got < r.qty && window.Monsters && Monsters.drops) Monsters.drops.push({ id: r.result, q: r.qty - got, x: W.Player.x + 10, y: W.Player.y + 4, from: null });   // what does not fit waits on the ground at your feet
      if (window.UIKit) UIKit.toast({ kicker: 'Crafted', title: r.name + (r.qty > 1 ? ' ×' + r.qty : ''), sub: got === r.qty ? null : 'Pack full: the rest is at your feet', icon: r.icon || r.result }); if (got !== r.qty) FX.say('Your pack is full; the rest is on the ground at your feet.'); if (window.Sound && Sound.play) Sound.play('craft_done'); W.Gather.FX.pop(W.Player.x, W.Player.y - 30, [[r.result, got]]); this.check(); return true; },
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
    findRooms(); const st = homeStage(); if (st > S.stage) { for (let k = S.stage + 1; k <= st; k++) if (!S.stageReached[k]) { S.stageReached[k] = W.Survival.Clock.day; if (window.UIKit && !S.quietStage) UIKit.toast({ kicker: 'Your home', title: CFG.stages[k], sub: (STAGE_GIFT[k] || [''])[0], glyph: 'shelter', rare: true, sting: 'milestone' }); if (!S.quietStage && window.MOSS_AUTOSAVE) setTimeout(() => MOSS_AUTOSAVE('home'), 0); } } S.stage = st;
    Craft.check(); if (W.relight) W.relight();
  }
  const objectCell = (x, y) => [Math.floor(x / T), Math.floor(y / T)];
  // ---------------- rooms and home stages: a room is roofed floor space closed in on every side by finished walls
  const STAGE_GIFT = { 2: ['Sleep in your own room: a full night\'s rest, whatever the hour, and nothing gets in past a closed door.', { fullRest: true }],
    3: ['A bed of your own: +10 energy each morning. Stage 4 walls, roofs and defences can now be built.', { fullRest: true, maxEnergy: 10 }],
    4: ['Stone and iron: +20 health, and Brutes do half damage to your walls. Metal walls can now be built.', { fullRest: true, maxEnergy: 10, maxHealth: 20, wallArmor: .5 }],
    5: ['A fortified estate: +20 energy, and from the watch platform you see night creatures on your map.', { fullRest: true, maxEnergy: 20, maxHealth: 20, wallArmor: .5, watch: true }] };
  function findRooms() { S.rooms = [];
    for (const g of S.roofGroups) { const cells = [...g].filter(c => !S.Wl.has(c)); if (!cells.length) continue; const inside = new Set(cells); let closed = true; const walls = new Set();
      for (const c of cells) { const r = S.R.get(c); if (!r || !finished(r)) { closed = false; break; } const [x, y] = c.split(',').map(Number);
        for (const n of [key(x + 1, y), key(x - 1, y), key(x, y + 1), key(x, y - 1)]) { if (inside.has(n)) continue; const w = S.Wl.get(n); if (!w || !finished(w)) { closed = false; break; } walls.add(w); } if (!closed) break; }
      if (!closed) continue; const ws = [...walls]; const objs = S.list.filter(e => COMP[e.type].layer === 'object' && finished(e) && inside.has(key(...objectCell(e.x, e.y))));
      S.rooms.push({ cells: inside, walls: ws, size: cells.length, door: ws.some(w => w.opening && COMP[w.opening].kind === 'door'), window: ws.some(w => w.opening && COMP[w.opening].kind === 'window'), bed: objs.some(e => COMP[e.type].sleep),
        floored: cells.every(c => S.L.has(c) && finished(S.L.get(c))), base: Math.min(...ws.map(w => COMP[w.type].stage || 2), ...cells.map(c => COMP[S.R.get(c).type].stage || 2)), metal: ws.filter(w => COMP[w.type].mat === 'metal').length }); } }
  function roomStage(r) { if (!r.door) return 1; let st = 2; if (r.base >= 3 && r.size >= 6 && r.bed && r.window) st = 3; else return st;
    const fenced = S.list.filter(e => COMP[e.type].layer === 'fence' && finished(e)).length >= 4; if (r.base >= 4 && r.floored && fenced) st = 4; else return st;
    const defs = S.list.filter(e => ['spikes', 'barricade'].includes(e.type) && finished(e)).length, watch = S.list.some(e => e.type === 'watch_platform' && finished(e)); if (r.metal >= 4 && watch && defs >= 2) st = 5; return st; }
  function homeStage() { return Math.max(1, ...S.rooms.map(roomStage)); }
  function sheltered(x, y) { const k = key(Math.floor(x / T), Math.floor(y / T)); return S.rooms.some(r => r.cells.has(k)); }
  function homeBonus() { let b = {}; for (let k = 2; k <= S.stage; k++) b = Object.assign({}, b, (STAGE_GIFT[k] || [])[1] || {}); return b; }
  // what a stage needs next, in words, for the build page
  function stageNeeds() { const st = S.stage; if (st >= 5) return null; const best = S.rooms.slice().sort((a, b) => roomStage(b) - roomStage(a))[0];
    if (st === 1) return 'Next: a Woodland shelter. Close in a roofed room with walls on every side and a door.';
    if (st === 2) return 'Next: an Established homestead. A room of 6+ cells with stage-3 walls and roof (timber-frame or better), a window and a bed.' + (best ? ` Now: ${best.size} cells${best.window ? '' : ', no window'}${best.bed ? '' : ', no bed'}${best.base >= 3 ? '' : ', walls or roof too simple'}.` : '');
    if (st === 3) return 'Next: a Reinforced residence. Stage-4 walls and roof (stone, reinforced or slate), every cell floored, and 4+ pieces of fence around the yard.';
    return 'Next: a Fortified woodland estate. 4+ metal-plated walls on the home, a watch platform and 2+ spikes or barricades.'; }

  // ---------------- placement validation: one function, always a reason
  function validate(type, p, rot = 0, ignore = null) {
    const d = COMP[type]; const cell = !(d.layer === 'object') || d.mount; const cx = p.cx, cy = p.cy; const x0 = cx * T, y0 = cy * T;
    if (d.stage >= 3 && !S.allStages && S.stage < d.stage - 1) return `Build a ${CFG.stages[d.stage - 1].toLowerCase()} first (home stage ${d.stage - 1}).`;          // each stage opens the next
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
  // structures under attack: a broken piece comes down with no refund
  function structureAt(x, y) { const k = key(Math.floor(x / T), Math.floor(y / T)); const w = S.Wl.get(k); if (w && !(w.open)) return w; const n = S.N.get(k); if (n && !n.open) return n; return S.list.find(e => { const d = COMP[e.type]; if (d.layer !== 'object' || d.ground || d.mount || !d.foot[0]) return false; const r = footRect(e, d); return x >= r[0] - 3 && x <= r[2] + 3 && y >= r[1] - 3 && y <= r[3] + 3; }) || null; }
  function hit(e, n) { const ar = homeBonus().wallArmor; if (ar && COMP[e.type].layer === 'wall' && (COMP[e.type].stage || 2) >= 4) n *= 1 - ar; e.dur -= n; if (e.dur > 0) return false; if (e.opening && COMP[e.opening].kind === 'door') { e.opening = null; e.dur = 20; rebuild(); FX.say('Something broke through a door.'); return true; } for (const o of S.list.filter(o => COMP[o.type].mount && o.cx === e.cx && o.cy === e.cy)) S.list.splice(S.list.indexOf(o), 1); if (e.slots) for (const s of e.slots) if (s) inv().add(s.id, s.qty); S.list.splice(S.list.indexOf(e), 1); FX.say(COMP[e.type].name + ' was destroyed.'); rebuild(); return true; }
  const lights = () => S.list.filter(e => COMP[e.type].light && finished(e) && e.on !== false).map(e => Object.assign({ x: e.x, y: e.y - 12 }, COMP[e.type].light));

  // ---------------- interaction: the objects say what they do
  function nearest(px, py) { let best = null, bd = 1e9; const consider = (e, x, y, label, act, r = 24) => { const d = Math.hypot(x - px, y - py); if (d < r && d < bd) { bd = d; best = { id: 'build:' + e.uid, label, x, y, r, buildAct: act, e }; } };
    for (const e of S.list) { const d = COMP[e.type]; const isCell = d.layer !== 'object'; const x = isCell ? e.cx * T + 8 : e.x, y = isCell ? e.cy * T + 11 : e.y;
      if (e.work) { if (d.layer !== 'object' || true) consider(e, x, y, `Work on ${d.name}`, () => work(e)); continue; }
      if (e.dur < (d.durability || 60) * 0.5) { consider(e, x, y, `Repair ${d.name}`, () => { const r = repair(e); FX.say(r.ok ? 'Repaired.' : r.reason); }); continue; }
      if (d.station) consider(e, x, y, `Use ${d.name}`, () => { Craft.station = d.station; UI.open = 'craft'; UI.cur = 0; UI.ccat = 0; }, 28);
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

  // ---------------- UI: the field-journal pages (see UI_STYLE_GUIDE.md). Every control is a kit hit, every key still works.
  const CATS = ['Foundation', 'Floor', 'Wall', 'Opening', 'Roof', 'Defense', 'Home'];
  const RCAT = { all: 'All', material: 'Materials', tackle: 'Tackle', furniture: 'Furniture', station: 'Stations', storage: 'Storage', lighting: 'Light', decor: 'Decor', kitchen: 'Kitchen', medicine: 'Medicine', garden: 'Garden', tool: 'Tools' };
  const LAYER_NOTE = { foundation: 'Laid on open ground. Floors, walls and roofs all stand on foundations.', floor: 'Laid over a foundation, inside the walls.', wall: 'Built on a foundation. Joins its neighbours; a straight east-west run can take a door or window.', opening: 'Set into a finished, straight east-west wall.', roof: 'Covers a foundation; needs walls or a support within three cells. Shelter from rain and snow.', fence: 'Runs along open ground and joins its neighbours.' };
  const K = () => window.UIKit, rnd = Math.round;
  const fit = (s, w, f = 1) => { const U = K(); s = String(s); if (U.measure(s, f) <= w) return s; while (s.length > 1 && U.measure(s + '.', f) > w) s = s.slice(0, -1); return s.replace(/[ ,·]+$/, '') + '.'; };
  // component art for the icon wells: the item icon when the piece is carried, else its own atlas sprite (trimmed, integer scale)
  const sprCache = new Map();
  function spriteCanvas(name, tab) { const s = A.index[name]; if (!s) return null; let m = sprCache.get(tab); if (!m) sprCache.set(tab, m = {}); if (m[name] !== undefined) return m[name];
    let x0 = s.w, y0 = s.h, x1 = -1, y1 = -1; for (let yy = 0; yy < s.h; yy++) for (let xx = 0; xx < s.w; xx++) if (IDX[(s.y + yy) * AW + s.x + xx]) { if (xx < x0) x0 = xx; if (xx > x1) x1 = xx; if (yy < y0) y0 = yy; if (yy > y1) y1 = yy; }
    if (x1 < 0) return m[name] = null; const w = x1 - x0 + 1, h = y1 - y0 + 1, c = document.createElement('canvas'); c.width = w; c.height = h; const cg = c.getContext('2d'), im = cg.createImageData(w, h);
    for (let yy = 0; yy < h; yy++) for (let xx = 0; xx < w; xx++) { const pi = IDX[(s.y + y0 + yy) * AW + s.x + x0 + xx]; if (!pi || !tab[pi]) continue; const t = tab[pi], o = (yy * w + xx) * 4; im.data[o] = t[0]; im.data[o + 1] = t[1]; im.data[o + 2] = t[2]; im.data[o + 3] = 255; }
    cg.putImageData(im, 0, 0); return m[name] = c; }
  function spriteName(d) { if (d.layer === 'foundation') return `fnd_${d.mat}_0`; if (d.layer === 'wall') return `wall_${d.mat}_10`; if (d.layer === 'roof') return `roof_${d.mat}_ridge_11`;
    if (d.layer === 'opening') return d.kind === 'window' ? 'window_wood' : 'door_closed_wood'; if (d.layer === 'fence') return d.kind === 'gate' ? d.sprite + '_closed' : 'fence_10'; return d.sprite; }
  function compIcon(g, d, x, y, size, tab) { x = rnd(x); y = rnd(y); if (d.item && items()[d.item]) { const s = size >= 32 ? 32 : 16; W.Gather.UI.icon(g, d.item, x + (size - s) / 2, y + (size - s) / 2, s, tab); return; }
    const c = spriteCanvas(spriteName(d), tab); if (!c) return; const sc = c.width * 2 <= size && c.height * 2 <= size ? 2 : 1, vw = Math.min(c.width, size / sc | 0), vh = Math.min(c.height, size / sc | 0);
    const sx = (c.width - vw) >> 1, sy = c.height - vh - ((c.height - vh) >> 2);      // crop tall pieces near their base, where the face is
    const sm = g.imageSmoothingEnabled; g.imageSmoothingEnabled = false; g.drawImage(c, sx, sy, vw, vh, x + rnd((size - vw * sc) / 2), y + rnd((size - vh * sc) / 2), vw * sc, vh * sc); g.imageSmoothingEnabled = sm; }
  // a little hammer, raised or striking (7x7)
  const HAMMER = [['..###..', '..###..', '...#...', '...#...', '...#...', '...#...', '.......'], ['.......', '.......', '#......', '.####..', '#......', '.......', '.......']];
  const drawHammer = (g, x, y, f, col) => { g.fillStyle = col; HAMMER[f].forEach((row, yy) => { for (let xx = 0; xx < 7; xx++) if (row[xx] === '#') g.fillRect(x + xx, y + yy, 1, 1); }); };
  const xMark = (g, x, y, col) => { g.fillStyle = col; for (let k = 0; k < 3; k++) { g.fillRect(x + k, y + k, 1, 1); g.fillRect(x + 2 - k, y + k, 1, 1); } };

  const UI = { open: null, cur: 0, cat: 0, ccat: 0, side: 0, store: null, place: null, off: [0, 0], ptr: null, rot: 0, moving: null, hit: [], turnT: -9, card: null, k: 1, strikes: 0,
    busy() { return !!(this.open || Craft.job); },
    listBuild() { const c = CATS[this.cat]; if (c === 'Home') return Object.values(COMP).filter(d => d.item && inv().count(d.item) > 0); return Object.values(COMP).filter(d => d.cat === c); },
    craftCats(all) { const out = ['all']; for (const r of all) if (!out.includes(r.category)) out.push(r.category); return out; },
    craftList() { const all = Craft.unlockedFor(Craft.station), cats = this.craftCats(all); if (this.ccat >= cats.length) this.ccat = 0; const c = cats[this.ccat]; return c === 'all' ? all : all.filter(r => r.category === c); },
    cursor() { if (this.ptr) return snap(this.ptr[0], this.ptr[1]); const P = W.Player; const dx = P.facing === 'side' ? (P.flip ? -1 : 1) : 0, dy = P.facing === 'up' ? -1 : P.facing === 'down' ? 1 : 0; return snap(P.x + dx * 18 + this.off[0] * 16, P.y - 4 + dy * 18 + this.off[1] * 16); },
    // the actions every key and every button share
    doBuild() { const l = this.listBuild(); if (l[this.cur]) { this.place = l[this.cur].id; this.open = null; this.rot = 0; this.off = [0, 0]; this.ptr = null; } },
    doCraft() { const l = this.craftList(); if (l[this.cur]) { const r = Craft.start(l[this.cur].id); if (!r.ok) FX.say(r.reason); else this.strikes = 0; } },
    doStore() { const e = this.store; if (!e) return; if (this.side) Storage.withdraw(e, this.cur); else Storage.deposit(e, this.cur); },
    setCat(i, n) { this.cat = (i + n) % n; this.cur = 0; this.turnT = K() ? K().now() : 0; },
    setCCat(i, n) { this.ccat = (i + n) % n; this.cur = 0; this.turnT = K() ? K().now() : 0; },
    key(k) { if (!W) return false;
      if (Craft.job) { if (k === 'escape' || k === 'x') Craft.cancel(); return true; }
      if (this.place) {
        if (k === 'escape' || k === 'b') { this.place = null; this.moving = null; this.ptr = null; this.off = [0, 0]; return true; }
        if (k === 'r') { this.rot = (this.rot + 1) % 4; return true; }
        if (k === 'arrowleft') { this.off[0]--; this.ptr = null; return true; } if (k === 'arrowright') { this.off[0]++; this.ptr = null; return true; } if (k === 'arrowup') { this.off[1]--; this.ptr = null; return true; } if (k === 'arrowdown') { this.off[1]++; this.ptr = null; return true; }
        if (k === 'e' || k === 'enter') { this.confirm(); return true; }
        if (k === 'x') { const e = at(this.cursor()); if (e) { const r = remove(e); FX.say(r.ok ? 'Taken down; part of the material comes back.' : r.reason); } else FX.say('Nothing built here to take down.'); return true; }
        if (k === 'm') { const e = at(this.cursor()); if (e && COMP[e.type].layer === 'object') { this.moving = e; this.place = e.type; this.rot = e.rot; FX.say('Moving ' + COMP[e.type].name + '.'); } else FX.say('Point at a piece of furniture to move it.'); return true; }
        return false; }
      if (this.open === 'build') { const l = this.listBuild(); if (k === 'arrowup' || k === 'w') this.cur = Math.max(0, this.cur - 1); else if (k === 'arrowdown' || k === 's') this.cur = Math.min(l.length - 1, this.cur + 1); else if (k === 'arrowleft' || k === 'q') this.setCat(this.cat - 1, CATS.length); else if (k === 'arrowright') this.setCat(this.cat + 1, CATS.length); else if (k === 'e' || k === 'enter') this.doBuild(); else if (k === 'escape' || k === 'b') this.open = null; return true; }
      if (this.open === 'craft') { const l = this.craftList(), n = this.craftCats(Craft.unlockedFor(Craft.station)).length; if (k === 'arrowup' || k === 'w') this.cur = Math.max(0, this.cur - 1); else if (k === 'arrowdown' || k === 's') this.cur = Math.min(l.length - 1, this.cur + 1); else if (k === 'arrowleft' || k === 'q') this.setCCat(this.ccat - 1, n); else if (k === 'arrowright') this.setCCat(this.ccat + 1, n); else if (k === 'e' || k === 'enter') this.doCraft(); else if (k === 'escape' || k === 'c') this.open = null; return true; }
      if (this.open === 'storage') { const e = this.store; const n = this.side ? e.slots.length : inv().size; if (k === 'arrowleft') this.cur = Math.max(0, this.cur - 1); else if (k === 'arrowright') this.cur = Math.min(n - 1, this.cur + 1); else if (k === 'arrowup') this.cur = Math.max(0, this.cur - 6); else if (k === 'arrowdown') this.cur = Math.min(n - 1, this.cur + 6); else if (k === 'tab' || k === 'q') { this.side = 1 - this.side; this.cur = 0; } else if (k === 'e' || k === 'enter') this.doStore(); else if (k === 'escape') this.open = null; return true; }
      if (W.Gather.UI.open) return false;
      if (k === 'b') { this.open = 'build'; this.cur = 0; return true; } if (k === 'c') { Craft.station = 'hand'; this.open = 'craft'; this.cur = 0; this.ccat = 0; return true; }
      return false; },
    confirm() { const p = this.cursor(), type = this.place; if (this.moving) { const r = move(this.moving, p, this.rot); FX.say(r.ok ? 'Moved.' : r.reason); if (r.ok) { this.moving = null; this.place = null; } return; } const r = place(type, p, this.rot); if (!r.ok) FX.say(r.reason); else { if (window.Sound && Sound.play) Sound.play('build_knock'); if (COMP[type].item && !inv().count(COMP[type].item)) { this.place = null; this.ptr = null; } } },
    // world taps only (view coordinates): panels take their taps through the kit before this is reached
    pointer(x, y, tap) { if (this.open) return !!tap; if (!this.place) return false;
      const c = this.card, ux = x / this.k, uy = y / this.k; if (c && ux >= c[0] - 4 && uy >= c[1] - 10 && ux < c[0] + c[2] + 4 && uy < c[1] + c[3] + 4) return !!tap;   // the hovering pointer over the placement card leaves the ghost alone
      const wx = x + W.Camera.ix(), wy = y + W.Camera.iy(); if (tap) { const a = this.ptr ? snap(this.ptr[0], this.ptr[1]) : null, b = snap(wx, wy); if (a && a.cx === b.cx && a.cy === b.cy && a.x === b.x && a.y === b.y) this.confirm(); } this.ptr = [wx, wy]; return tap; },
    status() { const p = this.cursor(), U = K(), kk = [this.place, p.cx, p.cy, p.x, p.y, this.rot, this.moving && this.moving.uid, S.list.length, inv().slots.filter(Boolean).length, U ? U.now() : 0].join('|'); if (this._st && this._st.k === kk) return this._st;
      const why = this.moving ? validate(this.place, p, this.rot, this.moving) : validate(this.place, p, this.rot); return this._st = { k: kk, p, why }; },
    // ---- shared drawing helpers
    frame(vw, vh, maxW = 500, maxH = 268) { const pw = Math.min(vw - 16, maxW), ph = Math.min(vh - 26, maxH), x0 = rnd(vw / 2 - pw / 2), y0 = Math.max(22, Math.min(vh - ph - 4, rnd((vh - ph) / 2 + 8))); return [x0, y0, pw, ph]; },
    turn(g, x, y, w, h) { const U = K(), t = (U.now() - this.turnT) / .28; if (t >= 1 || t < 0 || U.S.reduceMotion) return; const sx = rnd(x + w * (1 - t)); g.fillStyle = 'rgba(255,248,226,.55)'; g.fillRect(sx, y, 3, h); g.fillStyle = 'rgba(90,60,30,.16)'; g.fillRect(sx + 3, y, 6, h); },
    tabs(g, labs, cur, x, y, w, pick) { const U = K(), C = U.C; let pad = 12; const tot = p => labs.reduce((a, l) => a + U.measure(l) + p + 2, 0) + labs[cur].length; if (tot(pad) > w) pad = 6; let ls = labs; if (tot(pad) > w) ls = labs.map(l => l.slice(0, Math.max(3, Math.floor(l.length * .6)))); if (ls.reduce((a, l) => a + U.measure(l) + pad + 2, 0) + ls[cur].length > w) ls = labs.map(l => l.slice(0, 3));
      g.fillStyle = 'rgba(58,42,26,.4)'; g.fillRect(x - 2, y + 14, w + 4, 1); let tx = x;
      ls.forEach((l, i) => { const on = i === cur, tw = U.measure(l) + pad + (on ? l.length : 0);
        if (on) { g.fillStyle = C.paper; g.fillRect(tx, y, tw, 15); g.fillStyle = C.rust; g.fillRect(tx, y, tw, 1); g.fillStyle = 'rgba(58,42,26,.45)'; g.fillRect(tx, y + 1, 1, 14); g.fillRect(tx + tw - 1, y + 1, 1, 14); }
        else { g.fillStyle = C.paper3; g.fillRect(tx, y + 3, tw, 11); g.fillStyle = 'rgba(58,42,26,.25)'; g.fillRect(tx, y + 3, tw, 1); }
        U.text(g, l, tx + tw / 2, y + 11, { align: 'center', color: on ? C.ink : C.ink2, bold: on }); U.hit(tx, y, tw, 15, () => pick(i), 'tab'); tx += tw + 2; }); },
    // one ingredient line inside a row: icon + have/need, dim with an x when short
    costRow(g, cost, x, y, w, tab, names) { const U = K(), C = U.C, G = W.Gather.UI, ents = Object.entries(cost || {}); if (!ents.length) { U.text(g, 'nothing needed', x, y, { color: C.faint }); return; }
      const lab = ([id, n]) => `${inv().count(id)}/${n}` + (names ? ' ' + (items()[id] ? items()[id].name : id) : ''); const width = e => 10 + U.measure(lab(e)) + (inv().count(e[0]) < e[1] ? 5 : 0) + 7;
      if (names && ents.reduce((a, e) => a + width(e), 0) > w) return this.costRow(g, cost, x, y, w, tab, false);
      let cx = x; for (const e of ents) { const [id, n] = e, ok = inv().count(id) >= n, ew = width(e); if (cx + ew - 7 > x + w) { U.text(g, '...', cx, y, { color: C.faint }); break; }
        G.icon(g, id, cx, y - 7, 8, tab); if (!ok) g.globalAlpha = .55; U.text(g, lab(e), cx + 10, y, { color: ok ? C.ink2 : C.faint }); g.globalAlpha = 1; if (!ok) xMark(g, cx + 11 + U.measure(lab(e)), y - 4, C.rust); cx += ew; } },
    // a list column of 26 px rows with 20 px icon wells; paginated with tappable page buttons
    list(g, arr, x, y, w, bottom, rowFn, onPick) { const U = K(), C = U.C, rowH = 26, per = Math.max(1, Math.floor((bottom - y - 16) / rowH)), pages = Math.max(1, Math.ceil(arr.length / per)); if (this.cur > arr.length - 1) this.cur = Math.max(0, arr.length - 1); const page = Math.min(pages - 1, Math.floor(this.cur / per));
      arr.slice(page * per, page * per + per).forEach((it, k) => { const i = page * per + k, ry = y + k * rowH, on = i === this.cur, hov = U.Ptr.over && U.Ptr.x >= x - 3 && U.Ptr.x < x + w + 2 && U.Ptr.y >= ry && U.Ptr.y < ry + rowH - 1;
        if (on) { g.fillStyle = 'rgba(138,58,26,.08)'; g.fillRect(x - 3, ry, w + 5, rowH - 1); g.fillStyle = C.rust; g.fillRect(x - 3, ry + rowH - 2, w + 5, 1); g.fillRect(x - 3, ry + 3, 1, rowH - 6); } else if (hov) { g.fillStyle = 'rgba(255,250,235,.35)'; g.fillRect(x - 3, ry, w + 5, rowH - 1); }
        U.slot(g, x, ry + 3, 20, { sel: on }); rowFn(it, x, ry, on); U.hit(x - 3, ry, w + 5, rowH - 1, () => { if (this.cur === i) onPick(); this.cur = i; }, 'row'); });
      if (pages > 1) { const py = bottom - 14, bx = x + w - 58; U.button(g, bx, py, 18, 14, '<', () => { this.cur = Math.max(0, (page - 1) * per); this.turnT = U.now(); }, { disabled: page === 0 }); U.text(g, `${page + 1}/${pages}`, bx + 29, py + 10, { align: 'center', color: C.ink2 }); U.button(g, bx + 40, py, 18, 14, '>', () => { this.cur = Math.min(arr.length - 1, (page + 1) * per); this.turnT = U.now(); }, { disabled: page >= pages - 1 }); }
      return bottom - 14; },
    // the craft job: recipe icon, a progress bar and a hammer that taps along
    jobCard(g, x, y, w, tab, inPage) { const U = K(), C = U.C, j = Craft.job, f = Math.min(1, j.t / j.dur), h = 30; if (!inPage) U.tag(g, x, y, w, h);
      U.slot(g, x + 5, y + 5, 20); W.Gather.UI.icon(g, j.r.icon || j.r.result, x + 7, y + 7, 16, tab);
      const n = Math.floor(j.t / .3), fr = U.S.reduceMotion ? 0 : (j.t % .3 < .1 ? 1 : 0); if (n > this.strikes) { this.strikes = n; if (window.Sound && Sound.play) Sound.play('craft_tap'); }
      drawHammer(g, x + 27, y + 9, fr, C.ink); if (fr) { g.fillStyle = C.gold; g.fillRect(x + 26, y + 13, 1, 1); g.fillRect(x + 25, y + 16, 1, 1); g.fillRect(x + 28, y + 17, 1, 1); }
      const bw = w - 40 - 50; U.text(g, fit('Making ' + j.r.name, bw), x + 38, y + 12, { color: C.ink }); U.bar(g, x + 38, y + 19, bw, 4, f, { color: C.moss });
      U.button(g, x + w - 42, y + 7, 36, 16, 'Stop', () => Craft.cancel()); },
    detailHead(g, x, y, w, name, sub, drawIcon) { const U = K(), C = U.C; U.tag(g, x, y, 36, 36); drawIcon(x + 2, y + 2); const nx = x + 42, nw = w - 42;
      if (U.measure(name, 2) <= nw) U.text(g, name, nx, y + 14, { face: 2 }); else U.text(g, fit(name, nw), nx, y + 12, { bold: true }); U.text(g, fit(sub, nw), nx, y + 28, { color: C.faint }); U.divider(g, x, y + 43, w); return y + 56; },
    para(g, s, x, y, w, maxY, col) { const U = K(); const ls = U.lines(s, w); for (const l of ls) { if (y > maxY) break; U.text(g, l, x, y, { color: col }); y += 10; } return y; },
    needs(g, cost, x, y, w, maxY, tab) { const U = K(), C = U.C; for (const [id, n] of Object.entries(cost || {})) { if (y > maxY) break; const c = inv().count(id), ok = c >= n; W.Gather.UI.icon(g, id, x, y - 11, 16, tab);
        U.text(g, fit(items()[id] ? items()[id].name : id, w - 64), x + 20, y, { color: ok ? C.ink : C.ink2 }); U.text(g, `${c}/${n}`, x + w - 8, y, { align: 'right', color: ok ? C.moss : C.danger, bold: !ok }); if (!ok) xMark(g, x + w - 5, y - 5, C.danger); else { g.fillStyle = C.moss; g.fillRect(x + w - 5, y - 3, 1, 1); g.fillRect(x + w - 4, y - 2, 1, 1); g.fillRect(x + w - 3, y - 3, 1, 1); g.fillRect(x + w - 2, y - 4, 1, 1); } y += 17; } return y; },
    hint(g, s, x, y) { const U = K(); if (!U.touch() && U.S.hints) U.text(g, s, x, y, { color: U.C.faint }); },

    // ---- the crafting page
    drawCraft(g, vw, vh, tab) { const U = K(), C = U.C, touch = U.touch(); const all = Craft.unlockedFor(Craft.station), cats = this.craftCats(all), l = this.craftList(); const [x0, y0, pw, ph] = this.frame(vw, vh);
      g.save(); U.enter(g, 'craft', true, x0, y0, pw, ph); U.paper(g, x0, y0, pw, ph, { title: STN[Craft.station] === 'By hand' ? 'Crafting' : STN[Craft.station], sub: STN[Craft.station] === 'By hand' ? 'by hand' : `${all.length} recipes`, close: () => { this.open = null; } });
      const ty = y0 + 31; this.tabs(g, cats.map(c => RCAT[c] || c), this.ccat, x0 + 12, ty, pw - 24, i => this.setCCat(i, cats.length));
      const lx = x0 + 14, rTop = ty + 20, bottom = y0 + ph - 10, lw = Math.max(170, Math.min(240, rnd((pw - 28) * .5)));
      this.list(g, l, lx, rTop, lw, bottom, (r, x, ry, on) => { const ok = have(r.ingredients); W.Gather.UI.icon(g, r.icon, x + 2, ry + 5, 16, tab);
        const nm = r.name + (r.qty > 1 ? ' ×' + r.qty : ''); U.text(g, fit(nm, lw - 30), x + 26, ry + 11, { color: ok ? C.ink : C.ink2, bold: on }); if (ok) { g.fillStyle = C.moss; g.fillRect(x + lw - 4, ry + 6, 3, 3); }
        this.costRow(g, r.ingredients, x + 26, ry + 22, lw - 28, tab, true); }, () => this.doCraft());
      if (!l.length) this.para(g, Craft.station === 'hand' ? 'Nothing to make by hand yet. Gather fibre, branches and stones; recipes appear as you find things.' : 'Nothing to make here yet.', lx, rTop + 12, lw, bottom - 20, C.faint);
      this.hint(g, '← → kind · ↑ ↓ choose · E make', lx, bottom + 2);
      const dx = lx + lw + 14, dw = x0 + pw - 14 - dx, r = l[this.cur], bh = touch ? 18 : 16, by = bottom - bh; g.fillStyle = 'rgba(58,42,26,.18)'; for (let yy = rTop; yy < bottom; yy += 3) g.fillRect(dx - 7, yy, 1, 2);
      if (r) { let yy = this.detailHead(g, dx, rTop + 2, dw, r.name, `${r.qty > 1 ? 'makes ' + r.qty + ' · ' : ''}${(RCAT[r.category] || r.category).toLowerCase()}`, (ix, iy) => W.Gather.UI.icon(g, r.icon, ix, iy, 32, tab));
        const maxY = by - (Craft.job ? 22 : 8); yy = this.para(g, r.description || (items()[r.result] || {}).description || '', dx, yy, dw, maxY - 40, C.ink) + 3;
        yy = this.needs(g, r.ingredients, dx, yy + 8, dw, maxY - 10, tab);
        const unl = this.unlocks(r); if (unl && yy <= maxY - 10) yy = this.para(g, unl, dx, yy + 2, dw, maxY - 10, C.moss);
        if (yy <= maxY) U.text(g, `${r.minutes} min · ${r.energy ? r.energy + ' energy' : 'no energy'}`, dx, yy + 2, { color: C.ink2 });
        if (Craft.job) this.jobCard(g, dx - 5, by - 12, dw + 5, tab, true);
        else { const ok = have(r.ingredients), bw = Math.floor((dw - 4) / 2); U.button(g, dx, by, bw, bh, 'Craft', () => this.doCraft(), { primary: ok, disabled: !ok }); U.button(g, dx + bw + 4, by, dw - bw - 4, bh, 'Close', () => { this.open = null; }); } }
      else U.button(g, dx + dw - 60, by, 60, bh, 'Close', () => { this.open = null; });
      this.turn(g, x0 + 2, y0 + 2, pw - 4, ph - 4); g.restore(); },
    unlocks(r) { if (r.tool) { const T = W.Gather.Tools, o = T.get(r.tool), inf = T.info(r.tool); if (!o) return null; const tn = r.tier !== undefined ? W.Gather.DB.tool(r.tool).tiers[r.tier] : null; return `Your ${inf.name.toLowerCase()}: ${o.durability}/${inf.durability} uses left.` + (tn ? ` Becomes the ${tn.name.toLowerCase()}: ${tn.durability} uses, ${Math.round((tn.efficiency - 1) * 100)}% chance of an extra find.` : ''); }
      const st = Object.values(COMP).find(d => d.item === r.result && d.station); if (st) { const n = RECIPES.filter(x => x.station === st.station).length; return `Place it with Build to open ${n} more recipes.`; }
      const by = RECIPES.filter(x => x.unlock.type === 'item' && x.unlock.id === r.result && x.id !== r.id); if (by.length) return 'Teaches: ' + by.map(x => x.name).join(', ') + '.';
      if (Object.values(COMP).some(d => d.item === r.result)) return 'Placed from the Home page of Build.'; return null; },

    // ---- the building page
    drawBuild(g, vw, vh, tab) { const U = K(), C = U.C, touch = U.touch(); const l = this.listBuild(); const [x0, y0, pw, ph] = this.frame(vw, vh);
      g.save(); U.enter(g, 'build', true, x0, y0, pw, ph); U.paper(g, x0, y0, pw, ph, { title: 'Build', sub: `${CATS[this.cat].toLowerCase()} · home: ${CFG.stages[S.stage].toLowerCase()} (${S.stage}/5)`, close: () => { this.open = null; } });
      const ty = y0 + 31; this.tabs(g, CATS, this.cat, x0 + 12, ty, pw - 24, i => this.setCat(i, CATS.length));
      const lx = x0 + 14, rTop = ty + 20, bottom = y0 + ph - 10, lw = Math.max(170, Math.min(240, rnd((pw - 28) * .5)));
      const locked = d => d.stage >= 3 && !S.allStages && S.stage < d.stage - 1;
      this.list(g, l, lx, rTop, lw, bottom, (d, x, ry, on) => { const cost = costOf(d), lk = locked(d), ok = have(cost) && !lk; if (lk) g.globalAlpha = .45; compIcon(g, d, x, ry + 3, 20, tab); g.globalAlpha = 1;
        U.text(g, fit(d.name, lw - 30), x + 26, ry + 11, { color: ok ? C.ink : C.ink2, bold: on }); if (ok) { g.fillStyle = C.moss; g.fillRect(x + lw - 4, ry + 6, 3, 3); }
        if (lk) U.text(g, `opens at home stage ${d.stage - 1}`, x + 26, ry + 22, { color: C.faint }); else if (d.item) U.text(g, `in your pack: ${inv().count(d.item)}`, x + 26, ry + 22, { color: C.ink2 }); else this.costRow(g, cost, x + 26, ry + 22, lw - 28, tab, true); }, () => this.doBuild());
      if (!l.length) this.para(g, CATS[this.cat] === 'Home' ? 'Nothing to place yet. Furniture you craft lands in your pack, then shows up here.' : 'Nothing here yet.', lx, rTop + 12, lw, bottom - 20, C.faint);
      this.hint(g, '← → kind · ↑ ↓ choose · E place', lx, bottom + 2);
      const dx = lx + lw + 14, dw = x0 + pw - 14 - dx, d = l[this.cur], bh = touch ? 18 : 16, by = bottom - bh; g.fillStyle = 'rgba(58,42,26,.18)'; for (let yy = rTop; yy < bottom; yy += 3) g.fillRect(dx - 7, yy, 1, 2);
      if (d) { const stage = d.stage && CFG.stages[d.stage]; let yy = this.detailHead(g, dx, rTop + 2, dw, d.name, stage ? `stage ${d.stage} · ${stage.toLowerCase()}` : (d.layer === 'object' ? 'furniture' : d.layer), (ix, iy) => compIcon(g, d, ix, iy, 32, tab));
        const maxY = by - 8; const note = locked(d) ? `Opens when your home reaches stage ${d.stage - 1}, ${CFG.stages[d.stage - 1].toLowerCase()}. ${stageNeeds() || ''}` : (LAYER_NOTE[d.layer] || this.objNote(d)); yy = this.para(g, note, dx, yy, dw, maxY - 30, locked(d) ? C.rust : C.ink) + 3;
        if (!d.item) yy = this.needs(g, costOf(d), dx, yy + 8, dw, maxY - 10, tab); else { if (yy <= maxY - 10) U.text(g, `In your pack: ${inv().count(d.item)}`, dx, yy + 2, { color: C.ink2 }); yy += 12; }
        const mins = d.minutes || (d.item ? 5 : 10), stats = `${mins} min${d.energy ? ' · ' + d.energy + ' energy' : ''} · sturdiness ${d.durability || 60}`; if (yy <= maxY) U.text(g, fit(stats, dw), dx, yy + 2, { color: C.ink2 });
        const bw = Math.floor((dw - 4) / 2); U.button(g, dx, by, bw, bh, 'Build', () => this.doBuild(), { primary: true }); U.button(g, dx + bw + 4, by, dw - bw - 4, bh, 'Close', () => { this.open = null; }); }
      else U.button(g, dx + dw - 60, by, 60, bh, 'Close', () => { this.open = null; });
      this.turn(g, x0 + 2, y0 + 2, pw - 4, ph - 4); g.restore(); },
    objNote(d) { const bits = []; if (d.station) bits.push(`A place to work: opens the ${STN[d.station]} recipes.`); if (d.storage) bits.push(`Holds ${d.storage.slots} stacks${d.storage.filter ? ' of ' + d.storage.filter.join(', ') : ''}.`); if (d.sleep) bits.push('Rest here until morning.'); if (d.light) bits.push('Gives off light' + (d.toggle ? ' you can put out.' : '.'));
      if (d.support) bits.push('Holds a roof up within three cells.'); if (d.kind === 'gate') bits.push('Opens and closes.'); if (d.ground) bits.push('Lies flat on the floor.'); if (d.mount) bits.push('Hangs on a south-facing wall.'); if (d.side) bits.push('Can be turned.'); return bits.join(' ') || 'Stands where you put it.'; },

    // ---- the storage page: pack on the left, the chest on the right
    drawStorage(g, vw, vh, tab) { const U = K(), C = U.C, touch = U.touch(), G = W.Gather.UI; const e = this.store; if (!e || !e.slots) { this.open = null; return; }
      const sl = [inv().slots, e.slots], cols = 6, rows = Math.ceil(Math.max(inv().size, e.slots.length) / cols), [x0, y0, pw0, ph0] = this.frame(vw, vh, 480, 268);
      const cell = Math.max(20, Math.min(30, Math.floor((ph0 - 34 - 46) / rows), Math.floor((pw0 - 24 - 14) / (cols * 2)))), pw = Math.min(pw0, cols * cell * 2 + 38), ph = Math.min(ph0, 40 + rows * cell + 44), x = rnd(vw / 2 - pw / 2), y = Math.max(22, rnd((vh - ph) / 2 + 8)), s = cell - 2, isz = s >= 26 ? 24 : 16;
      g.save(); U.enter(g, 'storage', true, x, y, pw, ph); U.paper(g, x, y, pw, ph, { title: COMP[e.type].name, sub: `${e.slots.filter(Boolean).length}/${e.slots.length}`, close: () => { this.open = null; } });
      [0, 1].forEach(sd => { const ox = x + 12 + sd * (cols * cell + 14), on = sd === this.side; U.text(g, sd ? 'In the ' + COMP[e.type].name.toLowerCase() : 'Your pack', ox, y + 40, { color: on ? C.ink : C.ink2, bold: on }); if (on) { g.fillStyle = C.rust; g.fillRect(ox, y + 42, U.measure(sd ? 'In the ' + COMP[e.type].name.toLowerCase() : 'Your pack') + 1, 1); }
        sl[sd].forEach((st, i) => { const cx = ox + (i % cols) * cell, cy = y + 46 + Math.floor(i / cols) * cell, sel = on && i === this.cur, hov = U.Ptr.over && U.Ptr.x >= cx && U.Ptr.y >= cy && U.Ptr.x < cx + s && U.Ptr.y < cy + s;
          U.slot(g, cx, cy, s, { sel, empty: !st, hover: hov }); if (st) { const dim = !sd && !Storage.allowed(e, st.id); if (dim) g.globalAlpha = .45; G.icon(g, st.id, cx + (s - isz) / 2, cy + (s - isz) / 2, isz, tab); g.globalAlpha = 1;
            if (st.qty > 1) { const q = String(st.qty), qw = U.measure(q); g.fillStyle = 'rgba(236,223,189,.9)'; g.fillRect(cx + s - qw - 4, cy + s - 10, qw + 3, 9); U.text(g, q, cx + s - 2, cy + s - 2, { align: 'right' }); } }
          U.hit(cx, cy, s, s, () => { if (this.side === sd && this.cur === i) this.doStore(); else { this.side = sd; this.cur = i; } }, 'slot'); }); });
      g.fillStyle = 'rgba(58,42,26,.18)'; const mx = x + 12 + cols * cell + 5; for (let yy = y + 32; yy < y + 46 + rows * cell; yy += 3) g.fillRect(mx, yy, 1, 2);
      const sel = sl[this.side][this.cur], fy = y + ph - 12, bh = touch ? 18 : 16, bw = 84; U.divider(g, x + 12, y + 50 + rows * cell, pw - 24);
      if (sel && items()[sel.id]) { const it = items()[sel.id], ok = this.side || Storage.allowed(e, sel.id); U.text(g, fit(`${it.name} ×${sel.qty}`, pw - 24 - bw * 2 - 16), x + 14, fy - 9, { bold: true }); U.text(g, fit(ok ? (it.description || '') : 'That does not belong in here.', pw - 24 - bw * 2 - 16), x + 14, fy + 2, { color: ok ? C.ink2 : C.faint });
        U.button(g, x + pw - 12 - bw * 2 - 4, fy - bh + 3, bw, bh, this.side ? 'Take out' : 'Put in', () => this.doStore(), { primary: !!ok, disabled: !ok }); }
      else U.text(g, touch ? 'Tap a stack to choose it, tap again to move it.' : 'Choose a stack; E moves it across.', x + 14, fy - 4, { color: C.faint });
      U.button(g, x + pw - 12 - bw, fy - bh + 3, bw, bh, 'Close', () => { this.open = null; }); this.hint(g, 'Q switch side · E move', x + 14, y + ph + 12);
      g.restore(); },

    // ---- placement: a card along the bottom, with buttons that do exactly what the keys do
    drawPlace(g, vw, vh, safe, tab) { const U = K(), C = U.C, touch = U.touch(), d = COMP[this.place]; if (!d) { this.place = null; return; } const st = this.status(), why = st.why, hints = !touch && U.S.hints;
      const x = touch ? 66 + safe : rnd(vw / 2 - Math.min(vw - 20, 330) / 2), w = touch ? Math.max(200, vw - 142 - safe - x) : Math.min(vw - 20, 330), bh = 16, h = 46, y = vh - h - 8 - safe; this.card = [x, y, w, h];
      U.tag(g, x, y, w, h); compIcon(g, d, x + 4, y + 4, 20, tab);
      const title = (this.moving ? 'Moving ' : '') + d.name; U.text(g, fit(title, w - 34), x + 28, y + 11, { bold: true });
      if (!this.moving && !d.item) { const tw = U.measure(title) + title.length + 10; this.costRow(g, costOf(d), x + 28 + Math.min(w - 120, tw), y + 11, Math.max(60, w - 40 - tw), tab, false); }
      else if (d.item && !this.moving) U.text(g, `×${inv().count(d.item)}`, x + w - 6, y + 11, { align: 'right', color: C.ink2 });
      U.text(g, fit(why || (touch ? 'Tap the ground to move it, tap again or Place to build.' : 'Fits here.'), w - 34 - (hints ? 64 : 0)), x + 28, y + 22, { color: why ? C.danger : C.moss });
      const acts = [['Rotate', 'r', d.layer === 'object' && !d.mount], [this.moving ? 'Put' : 'Place', 'e', true, true], ['Move', 'm', true], ['Remove', 'x', true], ['Done', 'escape', true]];
      const keys = { r: 'R', e: 'E', m: 'M', x: 'X', escape: 'Esc' }, gap = 3, bw = Math.floor((w - 8 - gap * (acts.length - 1)) / acts.length);
      acts.forEach(([l, k, en, prim], i) => { const lab = hints && U.measure(l + ' ' + keys[k]) + 8 <= bw ? l + ' ' + keys[k] : l; U.button(g, x + 4 + i * (bw + gap), y + h - bh - 4, bw, bh, lab, () => this.key(k), { primary: prim && !why, disabled: !en }); });
      if (hints) U.text(g, 'arrows nudge', x + w - 6, y + 22, { align: 'right', color: C.faint }); },

    draw(g, vw, vh, safe, tab) { this.hit = []; const U = K(); if (!U) return; g.textAlign = 'left'; this.k = (this._vw || vw) / vw || 1; this.card = null;
      for (const k of ['craft', 'build', 'storage']) if (this.open !== k) U.openT(k, false);
      if (this.place && !this.open) this.drawPlace(g, vw, vh, safe, tab);
      if (this.open === 'build') this.drawBuild(g, vw, vh, tab); else if (this.open === 'craft') this.drawCraft(g, vw, vh, tab); else if (this.open === 'storage') this.drawStorage(g, vw, vh, tab);
      if (Craft.job && this.open !== 'craft') { const w = Math.min(200, vw - 20); this.jobCard(g, rnd(vw / 2 - w / 2), vh - 80 - safe, w, tab, false); } },
    // world-anchored: corner brackets around where the piece will go (view scale, before the UI layer)
    drawWorld(g, vw, vh) { this._vw = vw; if (!W || !this.place || this.open) return; const U = K(), C = U ? U.C : { moss: '#4c6a28', danger: '#9a2e16' }; const d = COMP[this.place]; if (!d) return; const st = this.status(), p = st.p, cx = W.Camera.ix(), cy = W.Camera.iy();
      let r; if (d.layer === 'object' && !d.mount) { const f = (this.rot % 2 && d.side_foot) || d.foot || [16, 4]; const fw = Math.max(8, f[0]), fh = Math.max(4, f[1]); r = [p.x - (fw >> 1), p.y - fh + 1, fw, fh]; } else r = [p.cx * T, p.cy * T, T, T];
      const x = rnd(r[0] - cx) - 1, y = rnd(r[1] - cy) - 1, w = r[2] + 2, h = r[3] + 2; g.fillStyle = st.why ? C.danger : (C.cream || '#f6ecd2'); const L = Math.min(4, w >> 1);
      for (const [a, b, dx, dy] of [[x, y, 1, 1], [x + w - 1, y, -1, 1], [x, y + h - 1, 1, -1], [x + w - 1, y + h - 1, -1, -1]]) { g.fillRect(dx > 0 ? a : a - L + 1, b, L, 1); g.fillRect(a, dy > 0 ? b : b - L + 1, 1, L); } } };
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
  const Save = { snapshot() { return { version: 2, uid, list: S.list.map(e => JSON.parse(JSON.stringify(e))), unlocked: S.unlocked, stageReached: S.stageReached }; }, restore(s) { if (!s) return; uid = s.uid; S.list = (s.list || []).filter(e => COMP[e.type]).map(e => JSON.parse(JSON.stringify(e))); S.unlocked = Object.assign({}, s.unlocked); S.stageReached = Object.assign({ 1: 1 }, s.stageReached || {}); S.stage = 1; S.quietStage = true; Craft.job = null; UI.open = null; UI.place = null; rebuild(); S.quietStage = false; for (let k = 2; k <= S.stage; k++) if (!S.stageReached[k]) S.stageReached[k] = W.Survival.Clock.day; } };
  function init(data, world) { W = world; A = data.atlas; AW = A.width; IDX = data.idx; CFG = data.components; data.components.components.forEach(c => COMP[c.id] = c); RECIPES = data.recipes.recipes; STN = data.recipes.stations; baseCol = W.DATA.col.slice(); Craft.check(); rebuild(); W.Gather.on('inventory', () => Craft.check());
    const SS = W.Survival.SaveState, snap_ = SS.snapshot.bind(SS), load = SS.load.bind(SS); SS.snapshot = () => Object.assign(snap_(), { build: Save.snapshot() }); SS.load = s => { s = s || SS.read(); const ok = load(s); if (ok && s.build) SS.guard('buildings', () => Save.restore(s.build)); return ok; }; }
  function tick(dt) { if (!W) return; if (FX.t > 0) FX.t -= dt; Craft.tick(dt); }
  return { sheltered, homeStage: () => S.stage, homeBonus, stageNeeds, rooms: () => S.rooms, STAGE_GIFT, unlockAllStages: v => { S.allStages = v !== false; }, init, tick, on: null, structureAt, hit, S, Craft, UI, FX, Storage, Save, place, remove, move, validate, work, damage, repair, nearest, lights, rebuild, render: R, comp: () => COMP, recipes: () => RECIPES, snap, baseY, have };
})();
