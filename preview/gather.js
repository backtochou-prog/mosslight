// MOSSlight gathering: item database, inventory, tools, resource nodes with discovery conditions,
// journal, UI, save. Rides on Survival (energy/time) and WorldClock/WeatherState (conditions).
// Data: assets/items/{items.json,tools.json,nodes.json,icons.json,nodes_atlas.json}. Mirrors godot/gather/.
window.Gather = (() => {
  let W = null, ITEMS = {}, TOOLS = {}, NODE_DEFS = [], ICON = null, NATLAS = null, RARITY = [];
  const listeners = {}; const on = (e, cb) => (listeners[e] = listeners[e] || []).push(cb); const emit = (e, ...a) => (listeners[e] || []).forEach(cb => cb(...a));
  const RCOL = { common: '#b9bfa8', uncommon: '#8cc452', rare: '#6ab4d8', very_rare: '#c088b6', exceptional: '#f0b24a', legendary: '#ffd98a' };
  const rnd = (() => { let s = 1234567; return () => (s = (s * 1664525 + 1013904223) >>> 0) / 4294967296; })();   // deterministic drops

  // ---------------- item database
  const DB = { get: id => ITEMS[id], all: () => Object.values(ITEMS), tool: id => TOOLS[id],
    byCategory: cat => Object.values(ITEMS).filter(i => i.category === cat), rarityRank: r => RARITY.indexOf(r) };

  // ---------------- inventory: slots with stacks; merge, split, remove, select
  const Inventory = {
    size: 24, slots: [], selected: -1, weightLimit: null,
    init() { this.slots = new Array(this.size).fill(null); },
    count(id) { return this.slots.reduce((n, s) => n + (s && s.id === id ? s.qty : 0), 0); },
    add(id, qty = 1, meta = null) {
      const it = ITEMS[id]; if (!it) return 0; let left = qty;
      for (const s of this.slots) { if (s && s.id === id && !s.meta && s.qty < it.stack) { const n = Math.min(it.stack - s.qty, left); s.qty += n; left -= n; if (!left) break; } }
      while (left > 0) { const i = this.slots.indexOf(null); if (i < 0) break; const n = Math.min(it.stack, left); this.slots[i] = { id, qty: n, meta }; left -= n; }
      emit('inventory'); return qty - left; },
    remove(index, qty = null) { const s = this.slots[index]; if (!s) return 0; const n = qty == null ? s.qty : Math.min(qty, s.qty); s.qty -= n; if (s.qty <= 0) this.slots[index] = null; emit('inventory'); return n; },
    split(index) { const s = this.slots[index]; if (!s || s.qty < 2) return false; const j = this.slots.indexOf(null); if (j < 0) return false; const half = Math.floor(s.qty / 2); s.qty -= half; this.slots[j] = { id: s.id, qty: half, meta: s.meta }; emit('inventory'); return true; },
    merge(from, to) { const a = this.slots[from], b = this.slots[to]; if (!a) return false; if (!b) { this.slots[to] = a; this.slots[from] = null; emit('inventory'); return true; }
      if (a.id !== b.id || a.meta || b.meta) { this.slots[to] = a; this.slots[from] = b; emit('inventory'); return true; }   // swap
      const cap = ITEMS[a.id].stack; const n = Math.min(cap - b.qty, a.qty); b.qty += n; a.qty -= n; if (a.qty <= 0) this.slots[from] = null; emit('inventory'); return true; },
    weight() { return this.slots.reduce((w, s) => w + (s ? (ITEMS[s.id].weight || 0) * s.qty : 0), 0); },
    isFull() { return this.slots.every(Boolean); },
  };

  // ---------------- tools: durability, compatibility, efficiency
  const Tools = {
    owned: {}, active: 'hand',
    init() { for (const id of ['hand', 'knife', 'axe', 'pickaxe']) this.owned[id] = { id, durability: TOOLS[id].durability }; this.active = 'hand'; },
    get(id) { return this.owned[id]; },
    canUse(toolId, required) { const t = TOOLS[toolId]; return !!t && t.compat.includes(required) && (this.owned[toolId].durability === null || this.owned[toolId].durability > 0); },
    wear(toolId, n = 1) { const o = this.owned[toolId]; if (o && o.durability !== null) { o.durability = Math.max(0, o.durability - n); emit('tool', toolId); if (o.durability === 0) emit('tool_broken', toolId); } },
    select(id) { if (this.owned[id]) { this.active = id; emit('tool'); } },
    bestFor(required) { if (this.canUse(this.active, required)) return this.active; for (const id in this.owned) if (this.canUse(id, required)) return id; return null; },
  };

  // ---------------- resource nodes: state, conditions, respawn
  const Nodes = {
    list: [],
    init() { this.list = NODE_DEFS.map(d => ({ def: d, left: d.yields, depletedAt: null, state: 'full', uniqueTaken: [] })); },
    conditionsMet(n, now) {   // season / time window / weather; the reason is used for the journal "known conditions"
      const d = n.def; const season = W.SeasonState.season; const phase = W.Survival.Clock.phase(); const wx = W.WeatherState.kind;
      if (d.seasons && d.seasons !== 'all' && !d.seasons.split(',').includes(season)) return false;
      if (d.time === 'night' && !W.Survival.Clock.isNight()) return false;
      if (d.time === 'deep_night' && phase !== 'deep_night') return false;
      if (d.time === 'day' && !['dawn', 'day', 'sunset'].includes(phase)) return false;
      if (d.weather) { const ok = d.weather.split(','); const rainy = wx === 'light_rain' || wx === 'heavy_rain'; const after = W.WeatherState.recentRainHours < 6; if (!(ok.includes(wx) || (ok.includes('rain') && rainy) || (ok.includes('after_rain') && (after || rainy)))) return false; }
      return true; },
    visible(n) { return n.def.kind !== 'hidden' && (this.conditionsMet(n) || !['glowcap', 'ghostcap', 'nightlily', 'moth'].includes(n.def.kind)); },
    tick() {   // respawn by elapsed game hours (time mode) or at a season change (season mode)
      const h = W.Survival.Clock.day * 24 + W.WorldClock.hour();
      for (const n of this.list) {
        if (n.state === 'full') continue;
        const d = n.def; if (d.respawn_mode === 'none') continue;
        const elapsed = h - (n.depletedAt || h);
        if (d.respawn_mode === 'season' && W.SeasonState.season !== n.depletedSeason) { n.left = d.yields; n.state = 'full'; n.depletedAt = null; }
        else if (d.respawn_hours && elapsed >= d.respawn_hours) { n.left = d.yields; n.state = 'full'; n.depletedAt = null; }
        else if (d.respawn_hours && elapsed >= d.respawn_hours * 0.5) n.state = 'regrow';
      } },
    nearest(x, y) { let best = null, bd = 1e9; for (const n of this.list) { if (n.state !== 'full' && n.left <= 0) continue; if (!this.conditionsMet(n)) continue; const d = Math.hypot(n.def.x - x, n.def.y - y); if (d < n.def.r && d < bd) { best = n; bd = d; } } return best; },
  };

  // ---------------- gathering: one path for every node; time + energy go through Survival exactly once
  const Gathering = {
    attempt(n) {
      const d = n.def; const tool = Tools.bestFor(d.tool);
      if (n.left <= 0) return { ok: false, reason: 'Nothing left here for now.' };
      if (!Nodes.conditionsMet(n)) return { ok: false, reason: 'Nothing here right now.' };
      if (d.unique && d.drops.every(([id]) => d.unique.includes(id) && (n.uniqueTaken.includes(id) || Journal.found[id]))) return { ok: false, reason: 'Nothing more here.' };
      if (!tool) return { ok: false, reason: d.tool === 'axe' ? 'You need an axe for that.' : d.tool === 'pickaxe' ? 'You need a pickaxe for that.' : d.tool === 'knife' ? 'You need a knife to cut that.' : 'You cannot gather that by hand.' };
      if (Inventory.isFull()) return { ok: false, reason: 'Your pack is full.' };
      const r = W.Survival.Activities.perform(d.activity, 'node:' + d.id);       // energy + time, once
      if (!r.ok) return r;
      const eff = r.efficiency; const got = []; let skippedUnique = false;
      const table = d.drops.concat((d.night_extra && W.Survival.Clock.isNight()) ? d.night_extra : []);
      for (const [id, lo, hi] of table) {
        if (d.unique && d.unique.includes(id) && (n.uniqueTaken.includes(id) || Journal.found[id])) { skippedUnique = true; continue; }
        let q = lo + Math.floor(rnd() * (hi - lo + 1)); if (lo === 0 && q > 0 && rnd() > 0.55 * eff) q = 0;   // optional extras are a chance, scaled by efficiency
        q = Math.round(q * (eff >= 1 ? 1 : (rnd() < eff ? 1 : 0)));
        if (q > 0) { const added = Inventory.add(id, q); if (added) { got.push([id, added]); Journal.record(id, n); if (d.unique && d.unique.includes(id)) n.uniqueTaken.push(id); } }
      }
      if (!got.length && table.length && !skippedUnique) { const [id] = table[0]; const added = Inventory.add(id, 1); if (added) { got.push([id, 1]); Journal.record(id, n); } }   // never an empty-handed success
      if (TOOLS[tool].durability !== null && d.tool !== 'hand') Tools.wear(tool, 1);
      n.left -= 1; if (n.left <= 0) { n.state = 'depleted'; n.depletedAt = W.Survival.Clock.day * 24 + W.WorldClock.hour(); n.depletedSeason = W.SeasonState.season; }
      Stats.gathered += got.reduce((s, g) => s + g[1], 0); Stats.actions += 1;
      emit('gathered', n, got); FX.pop(n.def.x, n.def.y - 12, got);
      return { ok: true, got, node: n };
    },
  };
  const Stats = { gathered: 0, actions: 0 };

  // ---------------- journal: discoveries with known conditions
  const Journal = {
    found: {},    // id -> {first: {day, hour, season, weather, nodeKind}, count}
    record(id, n) { const f = this.found[id]; const ctx = { day: W.Survival.Clock.day, hour: Math.round(W.WorldClock.hour() * 10) / 10, season: W.SeasonState.season, weather: W.WeatherState.kind, phase: W.Survival.Clock.phase(), node: n ? n.def.kind : null };
      if (!f) { this.found[id] = { first: ctx, count: 1 }; emit('discovered', id, ctx); } else f.count += 1; },
    progress(cat) { const items = cat ? DB.byCategory(cat) : DB.all(); const n = items.filter(i => this.found[i.id]).length; return [n, items.length]; },
    entry(id) { const it = ITEMS[id]; const f = this.found[id]; if (!f) return { id, known: false, name: '???', rarity: it.rarity, category: it.category };
      return { id, known: true, name: it.name, description: it.description, rarity: it.rarity, category: it.category, habitat: it.habitat, seasons: it.seasons, time: it.time, weather: it.weather, first: f.first, count: f.count }; },
  };

  // ---------------- feedback: floating pickup text
  const FX = { pops: [], pop(x, y, got) { this.pops.push({ x, y, t: 0, text: got.map(([id, q]) => `+${q} ${ITEMS[id].name}`).join('  '), rare: got.some(([id]) => DB.rarityRank(ITEMS[id].rarity) >= 2) }); },
    tick(dt) { this.pops = this.pops.filter(p => (p.t += dt) < 1.6); } };

  // ---------------- UI: inventory + journal panels, tool bar, prompts
  const UI = {
    open: null, cursor: 0, journalCat: 0, journalCursor: 0, cats: ['natural', 'geological', 'botanical', 'abandoned', 'rare_find'],
    toggle(which) { this.open = this.open === which ? null : which; },
    drawIcon(g, id, x, y, scale = 1, table) { const pos = ICON.index[id]; if (!pos) return; const s = ICON.size; const src = W.iconIdx;
      for (let yy = 0; yy < s; yy++) for (let xx = 0; xx < s; xx++) { const pi = src[(pos[1] + yy) * (ICON.cols * s) + pos[0] + xx]; if (!pi) continue; const c = table[pi]; g.fillStyle = `rgb(${c[0] | 0},${c[1] | 0},${c[2] | 0})`; g.fillRect(x + xx * scale, y + yy * scale, scale, scale); } },
    card(g, x, y, w, h) { g.fillStyle = 'rgba(40,34,26,0.94)'; g.fillRect(x, y, w, h); g.strokeStyle = 'rgba(222,220,180,0.5)'; g.lineWidth = 1; g.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1); g.strokeStyle = 'rgba(222,220,180,0.18)'; g.strokeRect(x + 3.5, y + 3.5, w - 7, h - 7); },
    draw(g, vw, vh, safe, table) {
      // tool bar (always): four small slots, active one lit
      const tb = ['hand', 'knife', 'axe', 'pickaxe']; const tx0 = vw - 8 - safe - tb.length * 20, ty0 = 8 + safe;
      tb.forEach((id, i) => { const x = tx0 + i * 20; g.fillStyle = Tools.active === id ? 'rgba(90,70,40,0.9)' : 'rgba(24,30,28,0.72)'; g.fillRect(x, ty0, 19, 19); g.strokeStyle = Tools.active === id ? '#ffd98a' : 'rgba(222,220,180,0.4)'; g.strokeRect(x + 0.5, ty0 + 0.5, 18, 18); this.drawIcon(g, 'tool_' + id, x + 1, ty0 + 1, 1, table);
        const o = Tools.owned[id]; if (o && o.durability !== null) { g.fillStyle = 'rgba(0,0,0,0.5)'; g.fillRect(x + 2, ty0 + 17, 15, 1); g.fillStyle = o.durability > 10 ? '#8cc452' : '#c0392b'; g.fillRect(x + 2, ty0 + 17, Math.round(15 * o.durability / TOOLS[id].durability), 1); } });
      // pickup pops
      for (const p of FX.pops) { g.globalAlpha = Math.min(1, 1.6 - p.t); g.font = '9px ui-monospace, monospace'; g.textAlign = 'center'; g.fillStyle = p.rare ? '#ffd98a' : '#eedcb0'; g.fillText(p.text, p.x - W.Camera.ix(), p.y - W.Camera.iy() - p.t * 14); g.globalAlpha = 1; }
      if (this.open === 'inventory') this.drawInventory(g, vw, vh, safe, table);
      if (this.open === 'journal') this.drawJournal(g, vw, vh, safe, table);
    },
    drawInventory(g, vw, vh, safe, table) {
      const cols = 6, cell = 24, rows = Inventory.size / cols; const pw = cols * cell + 16 + 150, ph = rows * cell + 40; const x0 = Math.round(vw / 2 - pw / 2), y0 = Math.round(vh / 2 - ph / 2);
      this.card(g, x0, y0, pw, ph); g.font = '9px ui-monospace, monospace'; g.textAlign = 'left'; g.fillStyle = '#eedcb0'; g.fillText('Pack', x0 + 10, y0 + 14); g.fillStyle = 'rgba(238,220,176,0.55)'; g.fillText(`${Inventory.slots.filter(Boolean).length}/${Inventory.size} · ${Inventory.weight().toFixed(1)} kg`, x0 + 40, y0 + 14);
      for (let i = 0; i < Inventory.size; i++) { const cx = x0 + 10 + (i % cols) * cell, cy = y0 + 22 + Math.floor(i / cols) * cell; const sel = i === this.cursor;
        g.fillStyle = sel ? 'rgba(90,70,40,0.9)' : 'rgba(24,30,28,0.6)'; g.fillRect(cx, cy, cell - 2, cell - 2); g.strokeStyle = sel ? '#ffd98a' : 'rgba(222,220,180,0.25)'; g.strokeRect(cx + 0.5, cy + 0.5, cell - 3, cell - 3);
        const s = Inventory.slots[i]; if (s) { this.drawIcon(g, s.id, cx + 3, cy + 3, 1, table); g.fillStyle = RCOL[ITEMS[s.id].rarity]; g.fillRect(cx + 2, cy + cell - 4, 3, 1); if (s.qty > 1) { g.font = '8px ui-monospace, monospace'; g.textAlign = 'right'; g.fillStyle = '#eedcb0'; g.fillText(s.qty, cx + cell - 4, cy + cell - 4); } } }
      const dx = x0 + 10 + cols * cell + 6, dy = y0 + 22; const s = Inventory.slots[this.cursor];
      g.textAlign = 'left'; g.font = '9px ui-monospace, monospace';
      if (s) { const it = ITEMS[s.id]; this.drawIcon(g, s.id, dx, dy, 2, table); g.fillStyle = '#eedcb0'; g.fillText(it.name, dx + 30, dy + 10); g.fillStyle = RCOL[it.rarity]; g.fillText(it.rarity.replace('_', ' '), dx + 30, dy + 21); g.fillStyle = 'rgba(238,220,176,0.55)'; g.fillText(`${it.category} · ×${s.qty}`, dx + 30, dy + 32);
        const yy = this.wrap(g, it.description, dx, dy + 46, 140, 10, '#d9cfae'); g.fillStyle = 'rgba(238,220,176,0.55)'; this.wrap(g, 'found: ' + (it.habitat || '—'), dx, yy + 14, 140, 10, 'rgba(238,220,176,0.55)'); }
      else { g.fillStyle = 'rgba(238,220,176,0.45)'; g.fillText('empty slot', dx, dy + 10); }
      g.fillStyle = 'rgba(238,220,176,0.45)'; g.font = '8px ui-monospace, monospace'; g.fillText('arrows move · S split · X drop · 1-4 tools · I close', x0 + 10, y0 + ph - 8);
    },
    wrap(g, text, x, y, w, lh, col) { g.fillStyle = col; const words = text.split(' '); let line = '', yy = y; for (const wd of words) { const t = line ? line + ' ' + wd : wd; if (g.measureText(t).width > w) { g.fillText(line, x, yy); line = wd; yy += lh; } else line = t; } if (line) g.fillText(line, x, yy); return yy; },
    drawJournal(g, vw, vh, safe, table) {
      const pw = Math.min(vw - 20, 340), ph = Math.min(vh - 20, 180); const x0 = Math.round(vw / 2 - pw / 2), y0 = Math.round(vh / 2 - ph / 2);
      this.card(g, x0, y0, pw, ph); g.font = '9px ui-monospace, monospace'; g.textAlign = 'left';
      const cat = this.cats[this.journalCat]; const items = DB.byCategory(cat); const [n, tot] = Journal.progress(cat); const [na, ta] = Journal.progress();
      g.fillStyle = '#eedcb0'; g.fillText('Field guide', x0 + 10, y0 + 14); g.fillStyle = 'rgba(238,220,176,0.55)'; g.fillText(`${na}/${ta} found`, x0 + 80, y0 + 14);
      this.cats.forEach((c, i) => { g.fillStyle = i === this.journalCat ? '#ffd98a' : 'rgba(238,220,176,0.5)'; g.fillText(c.replace('_', ' '), x0 + 10 + i * 62, y0 + 28); });
      g.fillStyle = 'rgba(222,220,180,0.3)'; g.fillRect(x0 + 10, y0 + 32, pw - 20, 1);
      const cols = 7, cell = 22; items.forEach((it, i) => { const cx = x0 + 10 + (i % cols) * cell, cy = y0 + 38 + Math.floor(i / cols) * cell; const sel = i === this.journalCursor; const known = !!Journal.found[it.id];
        g.fillStyle = sel ? 'rgba(90,70,40,0.9)' : 'rgba(24,30,28,0.5)'; g.fillRect(cx, cy, cell - 2, cell - 2); if (sel) { g.strokeStyle = '#ffd98a'; g.strokeRect(cx + 0.5, cy + 0.5, cell - 3, cell - 3); }
        if (known) this.drawIcon(g, it.id, cx + 2, cy + 2, 1, table); else { g.globalAlpha = 0.28; this.drawIcon(g, it.id, cx + 2, cy + 2, 1, table.map(() => [70, 66, 80])); g.globalAlpha = 1; g.fillStyle = 'rgba(238,220,176,0.6)'; g.font = '8px ui-monospace, monospace'; g.fillText('?', cx + 8, cy + 14); g.font = '9px ui-monospace, monospace'; } });
      const it = items[Math.min(this.journalCursor, items.length - 1)]; if (!it) return; const e = Journal.entry(it.id); const dx = x0 + 10 + cols * cell + 8, dy = y0 + 40; const dw = pw - (dx - x0) - 10;
      if (e.known) { this.drawIcon(g, it.id, dx, dy, 2, table); g.fillStyle = '#eedcb0'; g.fillText(e.name, dx + 30, dy + 10); g.fillStyle = RCOL[e.rarity]; g.fillText(e.rarity.replace('_', ' '), dx + 30, dy + 21);
        let yy = this.wrap(g, e.description, dx, dy + 36, dw, 10, '#d9cfae') + 14; g.fillStyle = 'rgba(238,220,176,0.6)';
        g.fillText('habitat: ' + (e.habitat || 'unknown'), dx, yy); yy += 10; g.fillText('season: ' + e.seasons + '   time: ' + e.time, dx, yy); yy += 10; if (e.weather !== 'any') { g.fillText('weather: ' + e.weather, dx, yy); yy += 10; }
        this.wrap(g, `first found day ${e.first.day}, ${e.first.season}, ${e.first.phase.replace('_', ' ')} · ×${e.count}`, dx, yy, dw, 10, 'rgba(238,220,176,0.6)'); }
      else { g.fillStyle = 'rgba(238,220,176,0.5)'; g.fillText('Not yet found.', dx, dy + 10); g.fillStyle = RCOL[e.rarity]; g.fillText(e.rarity.replace('_', ' '), dx, dy + 21); this.wrap(g, 'Keep looking. Some things show only in certain seasons, weather or hours.', dx, dy + 36, dw, 10, 'rgba(217,207,174,0.6)'); }
      g.fillStyle = 'rgba(238,220,176,0.45)'; g.font = '8px ui-monospace, monospace'; g.fillText('← → entries · Q/E category · J close', x0 + 10, y0 + ph - 8);
    },
    key(k) {   // returns true if consumed
      if (k === 'i') { this.toggle('inventory'); return true; } if (k === 'j') { this.toggle('journal'); return true; }
      if (['1', '2', '3', '4'].includes(k)) { Tools.select(['hand', 'knife', 'axe', 'pickaxe'][+k - 1]); return true; }
      if (this.open === 'inventory') { const cols = 6; if (k === 'arrowleft') this.cursor = Math.max(0, this.cursor - 1); if (k === 'arrowright') this.cursor = Math.min(Inventory.size - 1, this.cursor + 1); if (k === 'arrowup') this.cursor = Math.max(0, this.cursor - cols); if (k === 'arrowdown') this.cursor = Math.min(Inventory.size - 1, this.cursor + cols);
        if (k === 's') Inventory.split(this.cursor); if (k === 'x') Inventory.remove(this.cursor, 1); if (k === 'escape') this.open = null; return true; }
      if (this.open === 'journal') { const items = DB.byCategory(this.cats[this.journalCat]); if (k === 'arrowleft') this.journalCursor = Math.max(0, this.journalCursor - 1); if (k === 'arrowright') this.journalCursor = Math.min(items.length - 1, this.journalCursor + 1); if (k === 'q') { this.journalCat = (this.journalCat + 4) % 5; this.journalCursor = 0; } if (k === 'e') { this.journalCat = (this.journalCat + 1) % 5; this.journalCursor = 0; } if (k === 'escape') this.open = null; return true; }
      return false; },
  };

  // ---------------- node rendering helper (sprite from the atlas, state-aware)
  function nodeSprite(n) { const st = n.state === 'full' ? 'full' : n.state; const key = `${n.def.kind}:${st}`; return NATLAS.index[key] || NATLAS.index[`${n.def.kind}:depleted`]; }

  // ---------------- save hooks
  const Save = {
    snapshot() { return { inventory: Inventory.slots, tools: Tools.owned, active: Tools.active, nodes: Nodes.list.map(n => ({ id: n.def.id, left: n.left, state: n.state, depletedAt: n.depletedAt, depletedSeason: n.depletedSeason || null, uniqueTaken: n.uniqueTaken })), journal: Journal.found, stats: Stats }; },
    restore(s) { if (!s) return; Inventory.slots = s.inventory.map(x => x ? { ...x } : null); while (Inventory.slots.length < Inventory.size) Inventory.slots.push(null); Tools.owned = s.tools; Tools.active = s.active;
      const by = Object.fromEntries(s.nodes.map(n => [n.id, n])); for (const n of Nodes.list) { const r = by[n.def.id]; if (r) { n.left = r.left; n.state = r.state; n.depletedAt = r.depletedAt; n.depletedSeason = r.depletedSeason; n.uniqueTaken = r.uniqueTaken || []; } }
      Journal.found = s.journal || {}; Object.assign(Stats, s.stats || {}); emit('inventory'); },
  };

  function init(data, world) {
    W = world; RARITY = data.items.rarities; data.items.items.forEach(i => ITEMS[i.id] = i); data.tools.tools.forEach(t => TOOLS[t.id] = t); NODE_DEFS = data.nodes.nodes; ICON = data.icons; NATLAS = data.natlas;
    for (const [id, a] of Object.entries(data.nodes.activities_extra)) if (!W.Survival.cfg().activities[id]) W.Survival.cfg().activities[id] = a;
    Inventory.init(); Tools.init(); Nodes.init();
    // save integration: extend the survival snapshot, restore after it
    const S = W.Survival.SaveState; const snap = S.snapshot.bind(S), load = S.load.bind(S);
    S.snapshot = () => Object.assign(snap(), { gather: Save.snapshot() }); S.load = (s) => { s = s || JSON.parse(localStorage.getItem(S.KEY) || 'null'); const ok = load(s); if (ok && s.gather) Save.restore(s.gather); return ok; };
    W.WeatherState.recentRainHours = 99;   // tracked by tick below
  }
  let lastHour = null;
  function tick(dt) { FX.tick(dt); const h = W.Survival.Clock.day * 24 + W.WorldClock.hour(); if (lastHour === null) lastHour = h; const dh = h - lastHour; lastHour = h;
    const wx = W.WeatherState.kind; if ((wx === 'light_rain' || wx === 'heavy_rain') && W.WeatherState.intensity > 0.3) W.WeatherState.recentRainHours = 0; else W.WeatherState.recentRainHours = Math.min(99, W.WeatherState.recentRainHours + Math.max(0, dh));
    Nodes.tick(); }
  return { init, tick, on, DB, Inventory, Tools, Nodes, Gathering, Journal, UI, FX, Stats, Save, nodeSprite, RCOL, items: () => ITEMS };
})();
