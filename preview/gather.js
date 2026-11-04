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
    init() { for (const id of ['hand', 'knife', 'axe', 'pickaxe']) this.owned[id] = { id, tier: 0, durability: TOOLS[id].durability }; this.active = 'hand'; },
    // tiers: a tool keeps its slot and gets better (name, durability, efficiency); mending restores the current tier in full
    info(id) { const t = TOOLS[id]; if (!t) return null; const o = this.owned[id] || {}; const tr = (t.tiers || [])[o.tier || 0] || {}; return { name: tr.name || t.name, durability: tr.durability !== undefined ? tr.durability : t.durability, efficiency: tr.efficiency || t.efficiency || 1, damage: tr.damage || t.damage, tier: o.tier || 0, tiers: (t.tiers || []).length }; },
    repair(id) { const o = this.owned[id]; if (!o || o.durability === null) return false; o.durability = this.info(id).durability; emit('tool', id); return true; },
    upgrade(id, tier) { const o = this.owned[id]; if (!o || tier <= (o.tier || 0) || tier >= this.info(id).tiers) return false; o.tier = tier; o.durability = this.info(id).durability; emit('tool', id); return true; },
    get(id) { return this.owned[id]; },
    canUse(toolId, required) { const t = TOOLS[toolId]; return !!t && t.compat.includes(required) && (this.owned[toolId].durability === null || this.owned[toolId].durability > 0); },
    wear(toolId, n = 1) { const o = this.owned[toolId]; if (o && o.durability !== null) { o.durability = Math.max(0, o.durability - n); emit('tool', toolId); if (o.durability === 0) { emit('tool_broken', toolId); if (window.UIKit) UIKit.note(`Your ${this.info(toolId).name.toLowerCase()} is worn out. Mend it by hand: open crafting (C) and look under Tools.`, 5); } } },
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
    visible(n) { return n.def.kind !== 'hidden' && (this.conditionsMet(n) || !['glowcap', 'ghostcap', 'nightlily', 'moth', 'starshard', 'nightglass', 'ember_vent', 'spore_patch'].includes(n.def.kind)); },
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
      const eff = r.efficiency, teff = Tools.info(tool).efficiency; const got = []; let skippedUnique = false; let bonus = teff > 1 && rnd() < teff - 1 ? 1 : 0;   // better tools: a chance of one extra of the main drop
      const table = d.drops.concat((d.night_extra && W.Survival.Clock.isNight()) ? d.night_extra : []);
      for (const [id, lo, hi] of table) {
        if (d.unique && d.unique.includes(id) && (n.uniqueTaken.includes(id) || Journal.found[id])) { skippedUnique = true; continue; }
        let q = lo + Math.floor(rnd() * (hi - lo + 1)); if (lo === 0 && q > 0 && rnd() > 0.55 * eff * teff) q = 0; if (lo > 0 && bonus) { q += bonus; bonus = 0; }   // optional extras are a chance, scaled by efficiency
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
      if (!f) { this.found[id] = { first: ctx, count: 1 }; emit('discovered', id, ctx);
        const U = window.UIKit, it = ITEMS[id]; if (U && it && UI.cats.includes(it.category)) U.toast({ kicker: 'New in the field guide', title: it.name, sub: oneLine(it.description, 34), icon: id, rare: DB.rarityRank(it.rarity) >= 2, rarity: it.rarity }); }
      else f.count += 1; },
    progress(cat) { const items = cat ? DB.byCategory(cat) : DB.all().filter(i => !['crafted', 'creature', 'fish', 'bait', 'tackle', 'festival', 'keepsake'].includes(i.category)); const n = items.filter(i => this.found[i.id]).length; return [n, items.length]; },
    entry(id) { const it = ITEMS[id]; const f = this.found[id]; if (!f) return { id, known: false, name: '???', rarity: it.rarity, category: it.category };
      return { id, known: true, name: it.name, description: it.description, rarity: it.rarity, category: it.category, habitat: it.habitat, seasons: it.seasons, time: it.time, weather: it.weather, first: f.first, count: f.count }; },
  };

  // ---------------- feedback: pickups fly into the pack, one calm note line, a puff of motes where it was picked
  const FX = { pops: [],
    pop(x, y, got) { if (!got || !got.length) return; const rare = got.some(([id]) => ITEMS[id] && DB.rarityRank(ITEMS[id].rarity) >= 2);
      const text = got.map(([id, q]) => `+${q} ${ITEMS[id] ? ITEMS[id].name : id}`).join(', ');
      this.pops.push({ x, y, t: 0, text, rare });                       // kept for callers; drawn as motes by UI.drawWorld
      const U = K(); if (U) { got.forEach(([id], i) => U.fly(id, Math.round(x + (i - (got.length - 1) / 2) * 7), y + 10)); U.note(text, 2.6); } },
    tick(dt) { this.pops = this.pops.filter(p => (p.t += dt) < 1.6); } };

  // ---------------- UI helpers: everything is drawn in the field-journal language of UIKit
  const K = () => window.UIKit;
  const TOOLBAR = ['hand', 'knife', 'axe', 'pickaxe'];
  const CAT_LABEL = { natural: 'Natural', geological: 'Geological', botanical: 'Botanical', abandoned: 'Abandoned', rare_find: 'Rare finds', festival: 'Festival' };
  const CAT_SHORT = { natural: 'Nature', geological: 'Stone', botanical: 'Plants', abandoned: 'Ruins', rare_find: 'Rare', festival: 'Fest' };
  const BLACK = Array.from({ length: 256 }, () => [0, 0, 0]);
  const iconCache = new WeakMap(), silCache = {};
  const cap = s => s ? s[0].toUpperCase() + s.slice(1) : s;
  const fit = (s, w, face = 1) => { const U = K(); s = String(s); if (U.measure(s, face) <= w) return s; while (s.length > 1 && U.measure(s + '…', face) > w) s = s.slice(0, -1).trimEnd(); return s + '…'; };
  const oneLine = (s, n) => { s = String(s || '').split(/(?<=\.)\s/)[0]; if (s.length <= n) return s; s = s.slice(0, n - 1); return s.slice(0, Math.max(8, s.lastIndexOf(' '))) + '…'; };
  const hhmm = h => { const m = Math.round((h || 0) * 60); return String(Math.floor(m / 60) % 24).padStart(2, '0') + ':' + String(m % 60).padStart(2, '0'); };
  function clueOf(it) { const h = it.habitat || ''; if (it.category === 'festival') return 'Given at one of the year\'s festivals'; if (/made by hand/.test(h)) return 'Made, not found: a recipe will show it';
    let c = DB.rarityRank(it.rarity) >= 4 ? 'Rumoured: ' + h.split(',')[0] : cap(h); if (it.tool && it.tool !== 'hand') c += ' (' + it.tool + ')'; return c || 'Somewhere in the clearing'; }
  function whenOf(it) { const p = []; if (it.seasons && it.seasons !== 'all') p.push(it.seasons.split(',').join(', ')); if (it.time === 'night') p.push('after dark'); if (it.time === 'deep_night') p.push('after midnight'); if (it.time === 'day') p.push('by day');
    if (it.weather && it.weather !== 'any') p.push(/rain/.test(it.weather) ? 'in or after rain' : it.weather === 'clear' ? 'under a clear sky' : it.weather.replace(/_/g, ' ')); return p.join(' · '); }
  // light colours meant for the old dark cards are re-inked so text stays readable on parchment
  function inkFor(col) { const U = K(); if (typeof col !== 'string') return U.C.ink; let r, g, b, a = 1; let m = /^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})/i.exec(col);
    if (m) { r = parseInt(m[1], 16); g = parseInt(m[2], 16); b = parseInt(m[3], 16); } else if ((m = /rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)\s*(?:,\s*([\d.]+))?/.exec(col))) { r = +m[1]; g = +m[2]; b = +m[3]; a = m[4] === undefined ? 1 : +m[4]; } else return col;
    if (r * .3 + g * .59 + b * .11 > 150) return a < .7 ? U.C.faint : U.C.ink2; return a < 1 ? `rgb(${r | 0},${g | 0},${b | 0})` : col; }
  // a pencil outline of an undiscovered thing: its edge pixels, plus a light hatch
  function silhouette(g, id, x, y, size) { const key = id + '@' + size; let s = silCache[key];
    if (!s) { const c = document.createElement('canvas'); c.width = c.height = size + 2; const cg = c.getContext('2d'); UI.drawIcon(cg, id, 1, 1, size / 16, BLACK, size >= 32); const d = cg.getImageData(0, 0, size + 2, size + 2).data; const A = (xx, yy) => xx < 0 || yy < 0 || xx >= size + 2 || yy >= size + 2 ? 0 : d[(yy * (size + 2) + xx) * 4 + 3] > 110;
      s = { o: [], h: [] }; for (let yy = 0; yy < size + 2; yy++) for (let xx = 0; xx < size + 2; xx++) { if (!A(xx, yy)) continue; if (!A(xx - 1, yy) || !A(xx + 1, yy) || !A(xx, yy - 1) || !A(xx, yy + 1)) s.o.push(xx - 1, yy - 1); else if ((xx + yy) % 4 === 0) s.h.push(xx - 1, yy - 1); } silCache[key] = s; }
    x = Math.round(x); y = Math.round(y); g.fillStyle = 'rgba(94,74,50,.55)'; for (let i = 0; i < s.o.length; i += 2) g.fillRect(x + s.o[i], y + s.o[i + 1], 1, 1); g.fillStyle = 'rgba(94,74,50,.16)'; for (let i = 0; i < s.h.length; i += 2) g.fillRect(x + s.h[i], y + s.h[i + 1], 1, 1); }
  // wrapped body text that stops (with an ellipsis) before maxY; returns the next free baseline
  function para(g, str, x, y, w, lh, maxY, o = {}) { const U = K(); const ls = U.lines(str, w, o.face || 1); let yy = y; for (let i = 0; i < ls.length; i++) { if (yy > maxY) break; let l = ls[i]; if (yy + lh > maxY && i < ls.length - 1) l = fit(l + ' …', w); U.text(g, l, x, yy, o); yy += lh; } return yy; }

  // ---------------- UI: pack, field guide, tool strip
  const UI = {
    open: null, cursor: 0, journalCat: 0, journalCursor: 0, cats: ['natural', 'geological', 'botanical', 'abandoned', 'rare_find', 'festival'],
    toolBump: -9, turnT: -9, slotBump: null,
    toggle(which) { this.open = this.open === which ? null : which; },
    drawIcon(g, id, x, y, scale = 1, table, hi = true) { if (W.extraIcon && W.extraIcon(g, id, x, y, scale)) return; const pos = ICON.index[id]; if (!pos) return;
      // hi-res (32 px) art by default; the 16 px grid remains the editable source
      const s = hi && W.iconIdx32 ? ICON.size * 2 : ICON.size; const src = hi && W.iconIdx32 ? W.iconIdx32 : W.iconIdx; const px0 = hi && W.iconIdx32 ? pos[0] * 2 : pos[0], py0 = hi && W.iconIdx32 ? pos[1] * 2 : pos[1]; const k = hi && W.iconIdx32 ? scale / 2 : scale;
      for (let yy = 0; yy < s; yy++) for (let xx = 0; xx < s; xx++) { const pi = src[(py0 + yy) * (ICON.cols * s) + px0 + xx]; if (!pi) continue; const c = table[pi]; g.fillStyle = `rgb(${c[0] | 0},${c[1] | 0},${c[2] | 0})`; g.fillRect(x + xx * k, y + yy * k, k, k); } },
    // crisp icon at any pixel size: rendered once at 16 or 32 px, then scaled nearest-neighbour
    icon(g, id, x, y, size, table) { x = Math.round(x); y = Math.round(y); if (W.extraIcon && !ICON.index[id]) { this.drawIcon(g, id, x, y, size / 16, table); return; }
      const hi = !(size <= 16 || (size % 16 === 0 && size < 32)); let m = iconCache.get(table); if (!m) iconCache.set(table, m = {}); const key = id + (hi ? '@2' : '@1');
      if (!m[key]) { const n = hi ? 32 : 16, c = document.createElement('canvas'); c.width = c.height = n; this.drawIcon(c.getContext('2d'), id, 0, 0, hi ? 2 : 1, table, hi); m[key] = c; }
      const sm = g.imageSmoothingEnabled; g.imageSmoothingEnabled = false; g.drawImage(m[key], x, y, size, size); g.imageSmoothingEnabled = sm; },
    // an opaque parchment card (other modules use this for their own panels)
    card(g, x, y, w, h) { const U = K(); if (U) { U.paper(g, Math.round(x), Math.round(y), Math.round(w), Math.round(h), { flat: h < 40, rule: h >= 60 && w >= 60 }); return; }
      g.fillStyle = '#ecdfbd'; g.fillRect(x, y, w, h); g.strokeStyle = '#5a3820'; g.lineWidth = 1; g.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1); },
    // word wrap in the Mossbook face; same signature as before, returns the baseline of the last line
    wrap(g, text, x, y, w, lh, col) { const U = K(); if (!U) { g.fillStyle = col; g.fillText(text, x, y); return y; } const f = g.font || ''; const px = +((/(\d+(?:\.\d+)?)px/.exec(f) || [0, 9])[1]); const face = /mossbook/i.test(f) && px >= 11 ? 2 : 1, bold = /bold/.test(f) && face === 1;
      const ls = U.lines(String(text), w, face); const align = g.textAlign === 'center' ? 'center' : (g.textAlign === 'right' || g.textAlign === 'end') ? 'right' : 'left'; const color = inkFor(col);
      ls.forEach((l, i) => U.text(g, l, x, y + i * lh, { face, bold, color, align })); return y + Math.max(0, ls.length - 1) * lh; },
    selectTool(id) { if (!Tools.owned[id]) return false; Tools.select(id); this.toolBump = K() ? K().now() : 0; return true; },
    act(a) { const i = this.cursor, sl = Inventory.slots[i]; if (!sl) return false; const it = ITEMS[sl.id]; let ok = false;
      if (a === 'use') ok = !!(it && it.use && W.onUse && W.onUse(it)) && Inventory.remove(i, 1) > 0;
      else if (a === 'split') ok = Inventory.split(i); else if (a === 'drop') ok = Inventory.remove(i, 1) > 0;
      if (ok && K()) this.slotBump = { i, t: K().now() }; return ok; },
    setCat(i) { const n = this.cats.length; i = ((i % n) + n) % n; if (i !== this.journalCat) this.turnT = K() ? K().now() : 0; this.journalCat = i; this.journalCursor = 0; },
    draw(g, vw, vh, safe, table) { const U = K(); if (!U) return;
      this.drawToolbar(g, vw, vh, safe, table);
      if (this.open !== 'inventory') U.openT('pack', false); if (this.open !== 'journal') U.openT('guide', false);
      if (this.open === 'inventory') this.drawInventory(g, vw, vh, safe, table);
      if (this.open === 'journal') this.drawJournal(g, vw, vh, safe, table);
      g.textAlign = 'left'; g.globalAlpha = 1; },
    // world-anchored: a small puff of motes where something was picked (view scale, under the UI layer)
    drawWorld(g, vw, vh, tab) { const U = K(); if (!FX.pops.length || !W.Camera) return; const cx = W.Camera.ix(), cy = W.Camera.iy();
      if (!U) { for (const p of FX.pops) { g.globalAlpha = Math.min(1, 1.6 - p.t); g.fillStyle = '#eedcb0'; g.textAlign = 'center'; g.fillText(p.text, p.x - cx, p.y - cy - p.t * 14); } g.globalAlpha = 1; return; }
      if (U.S.reduceMotion || U.S.particles === 'reduced') return;
      for (const p of FX.pops) { if (p.t > .6) continue; const k = p.t / .6, n = p.rare ? 9 : 6; g.globalAlpha = 1 - k;
        for (let i = 0; i < n; i++) { const a = (i / n) * Math.PI * 2 + p.x * .1, r = 3 + k * (8 + (i % 3) * 2); const x = Math.round(p.x - cx + Math.cos(a) * r), y = Math.round(p.y + 8 - cy + Math.sin(a) * r * .6 - k * 6);
          g.fillStyle = p.rare && i % 2 ? '#f0c860' : '#f6ecd2'; g.fillRect(x, y, 1, 1); if (i % 3 === 0 && k < .5) g.fillRect(x, y - 1, 1, 1); } }
      g.globalAlpha = 1; },
    // the tool strip: paper slots on a stitched leather band, top-right; tap a slot to take that tool
    drawToolbar(g, vw, vh, safe, table) { const U = K(), C = U.C; if (U.anyBook() || U.Map.open || U.paused() || this.open) return;
      /* tools stand in a column down the left edge, under the vitals slip, like a hotbar turned on its side: tap or click a tool to hold it */
      const touch = U.touch(), s = touch ? 28 : 22, gap = touch ? 4 : 2, isz = touch ? 24 : 16, packH = touch ? 0 : s + 5, now = U.now(), P = U.Ptr;
      const w = s + 6, h = TOOLBAR.length * (s + gap) - gap + 6 + packH, x0 = 6 + safe, y0 = 41 + safe;
      g.fillStyle = C.shadow; g.fillRect(x0 + 1, y0 + 2, w, h); g.fillStyle = C.leather; g.fillRect(x0, y0, w, h); g.fillStyle = C.leather2; g.fillRect(x0, y0, w, 1);
      g.fillStyle = 'rgba(246,236,210,.22)'; for (let k = y0 + 3; k < y0 + h - 3; k += 4) { g.fillRect(x0 + 1, k, 1, 2); g.fillRect(x0 + w - 2, k, 1, 2); }      // stitching
      const over = (x, y) => P.over && P.x >= x && P.y >= y && P.x < x + s && P.y < y + s; const sx = x0 + 3; let sy = y0 + 3, tip = null;
      if (!touch) { const lift = now - U.bumpT() < .18 && !U.S.reduceMotion ? 1 : 0, bx = sx + lift; U.slot(g, bx, sy, s, { hover: over(bx, sy) }); U.glyph(g, 'pack', bx + 6, sy + 7, lift ? C.rust : C.ink2, 2 > s / 11 ? 1 : 2);
        U.hit(sx, sy, s, s, () => U.openBook('pack'), 'pack'); if (over(sx, sy)) tip = [sy, 'Pack', null, 'I']; sy += s + 2; g.fillStyle = 'rgba(246,236,210,.3)'; g.fillRect(sx + 2, sy, s - 4, 1); sy += 3; }
      TOOLBAR.forEach((id, i) => { const o = Tools.owned[id], on = Tools.active === id, y = sy + i * (s + gap); const lift = on && now - this.toolBump < .16 && !U.S.reduceMotion ? 1 : 0, x = sx + (on ? 1 : 0) + lift;
        U.slot(g, x, y, s, { sel: on, empty: !o, hover: over(sx, y) });
        if (o) { const broken = o.durability === 0; if (broken) g.globalAlpha = .4; this.icon(g, 'tool_' + id, x + (s - isz) / 2, y + (s - isz) / 2 - 1, isz, table); g.globalAlpha = 1;
          if (o.durability !== null && TOOLS[id].durability) { const f = o.durability / Tools.info(id).durability, bw = s - 6; g.fillStyle = 'rgba(58,42,26,.28)'; g.fillRect(x + 3, y + s - 3, bw, 1); g.fillStyle = f > .25 ? C.moss : C.danger; g.fillRect(x + 3, y + s - 3, broken ? 0 : Math.max(1, Math.round(bw * f)), 1); } }
        else silhouette(g, 'tool_' + id, x + (s - 16) / 2, y + (s - 16) / 2 - 1, 16);
        U.hit(sx, y, s, s, () => this.selectTool(id), 'tool'); if (over(sx, y)) tip = [y, o ? Tools.info(id).name : 'No ' + id + ' yet', o && o.durability !== null ? `${o.durability}/${Tools.info(id).durability}` + (o.durability === 0 ? ' · mend it by hand (C)' : '') : null, String(i + 1)]; });
      if (tip && !touch) { const [ty, name, dur, key] = tip; const extra = (dur ? '  ' + dur : '') + (U.S.hints ? '  [' + key + ']' : ''); const tw = U.measure(name) + U.measure(extra) + 12, x = x0 + w + 4, y = Math.max(4, ty + 4);
        U.tag(g, x, y, tw, 14); U.text(g, name, x + 6, y + 10); if (extra) U.text(g, extra, x + 6 + U.measure(name), y + 10, { color: C.faint }); } },
    drawInventory(g, vw, vh, safe, table) { const U = K(), C = U.C, touch = U.touch(), now = U.now(), P = U.Ptr;
      const cols = 6, rows = Math.ceil(Inventory.size / cols), pw = Math.min(vw - 16, 480), availH = vh - 26;
      const cell = Math.max(24, Math.min(38, Math.floor((availH - 56) / rows), Math.floor((pw - 24 - 140) / cols))), ph = Math.min(availH, 34 + rows * cell + (!U.touch() && U.S.hints ? 22 : 14));
      const x0 = Math.round(vw / 2 - pw / 2), y0 = Math.max(22, Math.min(vh - ph - 4, Math.round((vh - ph) / 2 + 8)));
      g.save(); U.enter(g, 'pack', true, x0, y0, pw, ph);
      const used = Inventory.slots.filter(Boolean).length; U.paper(g, x0, y0, pw, ph, { title: 'Pack', sub: `${used}/${Inventory.size} · ${Inventory.weight().toFixed(1)} kg`, close: () => { this.open = null; } });
      const gx = x0 + 12, gy = y0 + 34, s = cell - 2, isz = s >= 34 ? 32 : s >= 26 ? 24 : 16;
      for (let i = 0; i < Inventory.size; i++) { const sl = Inventory.slots[i], bump = this.slotBump && this.slotBump.i === i && now - this.slotBump.t < .14 && !U.S.reduceMotion ? 1 : 0;
        const x = gx + (i % cols) * cell, y = gy + Math.floor(i / cols) * cell + bump, hov = P.over && P.x >= x && P.y >= y && P.x < x + s && P.y < y + s;
        U.slot(g, x, y, s, { sel: i === this.cursor, empty: !sl, hover: hov });
        if (sl && ITEMS[sl.id]) { const it = ITEMS[sl.id]; this.icon(g, sl.id, x + (s - isz) / 2, y + (s - isz) / 2, isz, table);
          if (DB.rarityRank(it.rarity) >= 1) { const n = DB.rarityRank(it.rarity) + 1; g.fillStyle = 'rgba(236,223,189,.85)'; g.fillRect(x + 1, y + 1, n * 4 + 1, 5); U.pips(g, x + 2, y + 2, it.rarity); }
          if (sl.qty > 1) { const q = String(sl.qty), qw = U.measure(q); g.fillStyle = 'rgba(236,223,189,.9)'; g.fillRect(x + s - qw - 4, y + s - 10, qw + 3, 9); U.text(g, q, x + s - 2, y + s - 2, { align: 'right' }); } }
        U.hit(x, y, s, s, () => { this.cursor = i; }, 'slot'); }
      if (!touch && U.S.hints) U.text(g, 'arrows move · I close', gx, gy + rows * cell + 9, { color: C.faint });
      // detail page: what the selected thing is, and what can be done with it
      const dx = gx + cols * cell + 10, dw = x0 + pw - 12 - dx, dy = gy, sl = Inventory.slots[this.cursor], bh = touch ? 18 : 16, by = y0 + ph - 12 - bh;
      g.fillStyle = 'rgba(58,42,26,.18)'; for (let yy = gy; yy < y0 + ph - 12; yy += 3) g.fillRect(dx - 6, yy, 1, 2);
      const hints = !touch && U.S.hints;
      if (sl && ITEMS[sl.id]) { const it = ITEMS[sl.id], rk = DB.rarityRank(it.rarity);
        U.tag(g, dx, dy, 36, 36, { edge: rk >= 2 ? C.gold : C.leather }); this.icon(g, sl.id, dx + 2, dy + 2, 32, table);
        const nx = dx + 42, nw = dw - 42; if (U.measure(it.name, 2) <= nw) U.text(g, it.name, nx, dy + 13, { face: 2 }); else U.text(g, fit(it.name, nw), nx, dy + 10, { bold: true });
        const pw2 = U.pips(g, nx, dy + 20, it.rarity); U.text(g, U.rarityLabel(it.rarity), nx + pw2 + 3, dy + 25, { color: U.RCOL[it.rarity] || C.ink2 });
        U.text(g, fit(`${(CAT_LABEL[it.category] || cap(it.category)).toLowerCase()} · ×${sl.qty}`, nw), nx, dy + 35, { color: C.faint });
        U.divider(g, dx, dy + 44, dw); let yy = dy + 56; const maxY = by - 6;
        if (sl.meta && sl.meta.cm) { U.text(g, fit(`${sl.meta.cm} cm · ${sl.meta.kg} kg · ${sl.meta.quality}`, dw), dx, yy, { color: C.gold }); yy += 11; }
        yy = para(g, it.description, dx, yy, dw, 10, maxY - 22, { color: C.ink }) + 3;
        const use = it.use && it.use.heal ? `Use: restores ${it.use.heal} health` : it.crafting ? 'Used for: ' + it.crafting : null; if (use && yy <= maxY - 10) { yy = para(g, use, dx, yy, dw, 10, maxY - 11, { color: C.ink2 }); }
        if (it.habitat && yy <= maxY) para(g, 'Found: ' + it.habitat, dx, yy, dw, 10, maxY, { color: C.faint });
      } else { U.text(g, 'An empty pocket', dx, dy + 12, { bold: true }); para(g, 'Things you gather, catch and make land here. Tap a filled slot to look at it.', dx, dy + 28, dw, 10, by - 8, { color: C.faint }); }
      const it = sl && ITEMS[sl.id], canUse = !!(it && it.use), canSplit = !!(sl && sl.qty > 1 && Inventory.slots.includes(null));
      const btns = [['Use', 'u', 'use', canUse, true], ['Split', 's', 'split', canSplit], ['Drop', 'x', 'drop', !!sl]]; if (dw >= 200) btns.push(['Close', 'i', 'close', true]);
      const bw = Math.floor((dw - (btns.length - 1) * 4) / btns.length);
      btns.forEach(([l, k, a, en, prim], i) => { const lab = hints && U.measure(l + ' ' + k.toUpperCase()) + 8 <= bw ? l + ' ' + k.toUpperCase() : l; U.button(g, dx + i * (bw + 4), by, bw, bh, lab, () => { if (a === 'close') this.open = null; else this.act(a); }, { primary: prim && en, disabled: !en }); });
      g.restore(); },
    drawJournal(g, vw, vh, safe, table) { const U = K(), C = U.C, touch = U.touch(), now = U.now();
      const pw = Math.min(vw - 16, 480), ph = Math.min(vh - 26, 264), x0 = Math.round(vw / 2 - pw / 2), y0 = Math.max(22, Math.min(vh - ph - 4, Math.round((vh - ph) / 2 + 8)));
      const cat = this.cats[this.journalCat], items = DB.byCategory(cat), [n, tot] = Journal.progress(cat), [na, ta] = Journal.progress();
      if (this.journalCursor > items.length - 1) this.journalCursor = Math.max(0, items.length - 1);
      g.save(); U.enter(g, 'guide', true, x0, y0, pw, ph);
      U.paper(g, x0, y0, pw, ph, { title: 'Field guide', sub: `${na} of ${ta} found`, close: () => { this.open = null; } });
      // section tabs: page markers laid out from the measured labels
      const ty = y0 + 31, avail = pw - 24; let labs = this.cats.map(c => CAT_LABEL[c]), pad = 12; const bw0 = l => U.measure(l) + l.length; const tot2 = (ls, p) => ls.reduce((a, l) => a + bw0(l) + p + 2, 0);
      if (tot2(labs, pad) > avail) pad = 8; if (tot2(labs, pad) > avail) { labs = this.cats.map(c => CAT_SHORT[c]); pad = 10; }
      g.fillStyle = 'rgba(58,42,26,.4)'; g.fillRect(x0 + 10, ty + 14, pw - 20, 1); let tx = x0 + 12;
      labs.forEach((l, i) => { const tw = bw0(l) + pad, on = i === this.journalCat;
        if (on) { g.fillStyle = C.paper; g.fillRect(tx, ty, tw, 15); g.fillStyle = C.rust; g.fillRect(tx, ty, tw, 1); g.fillStyle = 'rgba(58,42,26,.45)'; g.fillRect(tx, ty + 1, 1, 14); g.fillRect(tx + tw - 1, ty + 1, 1, 14); }
        else { g.fillStyle = C.paper3; g.fillRect(tx, ty + 3, tw, 11); g.fillStyle = 'rgba(58,42,26,.25)'; g.fillRect(tx, ty + 3, tw, 1); }
        U.text(g, l, tx + Math.floor((tw - (on ? bw0(l) : U.measure(l))) / 2), ty + 11, { color: on ? C.ink : C.ink2, bold: on }); U.hit(tx, ty, tw, 15, () => this.setCat(i), 'tab'); tx += tw + 2; });
      // entries: one row each, paginated
      const lx = x0 + 14, lw = Math.max(120, Math.min(190, Math.round(avail * .42))), rowH = 20, rTop = ty + 20, bottom = y0 + ph - 10, per = Math.max(1, Math.floor((bottom - 18 - rTop) / rowH));
      const pages = Math.max(1, Math.ceil(items.length / per)), page = Math.min(pages - 1, Math.floor(this.journalCursor / per));
      items.slice(page * per, page * per + per).forEach((it, k) => { const i = page * per + k, ry = rTop + k * rowH, on = i === this.journalCursor, known = !!Journal.found[it.id];
        if (on) { g.fillStyle = 'rgba(138,58,26,.08)'; g.fillRect(lx - 3, ry, lw + 5, rowH - 1); g.fillStyle = C.rust; g.fillRect(lx - 3, ry + rowH - 2, lw + 5, 1); g.fillRect(lx - 3, ry + 3, 1, rowH - 6); }
        if (known) { this.icon(g, it.id, lx + 1, ry + 2, 16, table); const rk = DB.rarityRank(it.rarity), pwid = rk >= 1 ? (rk + 1) * 4 + 3 : 0; U.text(g, fit(it.name, lw - 24 - pwid - (on ? it.name.length : 0)), lx + 22, ry + 13, { color: C.ink, bold: on }); if (rk >= 1) U.pips(g, lx + lw - pwid + 3, ry + 8, it.rarity); }
        else { silhouette(g, it.id, lx + 1, ry + 2, 16); U.text(g, fit(clueOf(it), lw - 24), lx + 22, ry + 13, { color: C.faint }); }
        U.hit(lx - 3, ry, lw + 5, rowH, () => { this.journalCursor = i; }, 'entry'); });
      const py = bottom - 14; U.text(g, `${n} of ${tot} here`, lx, py + 10, { color: C.faint });
      if (pages > 1) { const bx = lx + lw - 52; U.button(g, bx, py, 16, 14, '<', () => { this.journalCursor = Math.max(0, (page - 1) * per); this.turnT = U.now(); }, { disabled: page === 0 }); U.text(g, `${page + 1}/${pages}`, bx + 26, py + 10, { align: 'center', color: C.ink2 }); U.button(g, bx + 36, py, 16, 14, '>', () => { this.journalCursor = Math.min(items.length - 1, (page + 1) * per); this.turnT = U.now(); }, { disabled: page >= pages - 1 }); }
      // the entry itself
      const dx = lx + lw + 14, dw = x0 + pw - 14 - dx, dy = rTop + 2, hints = !touch && U.S.hints, maxY = bottom - (hints ? 12 : 2);
      g.fillStyle = 'rgba(58,42,26,.18)'; for (let yy = rTop; yy < bottom; yy += 3) g.fillRect(dx - 7, yy, 1, 2);
      const it = items[this.journalCursor];
      if (it) { const e = Journal.entry(it.id), rk = DB.rarityRank(it.rarity);
        U.tag(g, dx, dy, 36, 36, { fill: e.known ? C.paper : C.paper2, edge: e.known && rk >= 2 ? C.gold : C.leather }); if (e.known) this.icon(g, it.id, dx + 2, dy + 2, 32, table); else silhouette(g, it.id, dx + 2, dy + 2, 32);
        const nx = dx + 42, nw = dw - 42, title = e.known ? e.name : 'Not yet found'; if (U.measure(title, 2) <= nw) U.text(g, title, nx, dy + 13, { face: 2, color: e.known ? C.ink : C.ink2 }); else U.text(g, fit(title, nw), nx, dy + 10, { bold: true });
        const pw2 = U.pips(g, nx, dy + 20, it.rarity); U.text(g, U.rarityLabel(it.rarity), nx + pw2 + 3, dy + 25, { color: U.RCOL[it.rarity] || C.ink2 }); U.text(g, fit((CAT_LABEL[it.category] || cap(it.category)).toLowerCase(), nw), nx, dy + 35, { color: C.faint });
        U.divider(g, dx, dy + 44, dw); let yy = dy + 56; const w2 = whenOf(it);
        if (e.known) { const f = e.first || {};
          yy = para(g, e.description, dx, yy, dw, 10, maxY - 32, { color: C.ink }) + 4;
          if (yy <= maxY) { yy = para(g, 'Habitat: ' + (e.habitat || 'unknown'), dx, yy, dw, 10, maxY - 21, { color: C.ink2 }); }
          if (w2 && yy <= maxY - 21) yy = para(g, 'When: ' + w2, dx, yy, dw, 10, maxY - 21, { color: C.ink2 });
          if (yy <= maxY) { const node = f.node ? ', ' + f.node.replace(/_/g, ' ') : ''; yy = para(g, `First found day ${f.day}, ${hhmm(f.hour)}, ${f.season || ''}, ${(f.phase || '').replace(/_/g, ' ')}${f.weather && f.weather !== 'clear' ? ', ' + f.weather.replace(/_/g, ' ') : ''}${node}.`, dx, yy + 2, dw, 10, maxY - 10, { color: C.moss }); }
          if (yy <= maxY) U.text(g, e.count === 1 ? 'Found once so far.' : `Found ${e.count} times.`, dx, yy, { color: C.faint }); }
        else { yy = para(g, 'Pencilled note: ' + clueOf(it) + '.', dx, yy, dw, 10, maxY - 12, { color: C.ink2 }) + 3;
          if (yy <= maxY - 10) yy = para(g, w2 && rk <= 2 ? 'Seen ' + w2 + '.' : rk > 2 ? 'Conditions unknown.' : 'Any season, any hour.', dx, yy, dw, 10, maxY - 10, { color: C.ink2 }) + 3;
          if (yy <= maxY) para(g, 'Gather it once to fill in this page.', dx, yy, dw, 10, maxY, { color: C.faint }); } }
      else U.text(g, 'Nothing in this section yet.', dx, dy + 12, { color: C.faint });
      if (hints) { const h = '↑↓ entry · Q E section · J close'; if (U.measure(h) <= dw) U.text(g, h, x0 + pw - 14, bottom, { align: 'right', color: C.faint }); }
      // a quick page turn when the section or page changes
      const tt = (now - this.turnT) / .28; if (tt >= 0 && tt < 1 && !U.S.reduceMotion) { const sx = Math.round(x0 + 8 + (pw - 16) * (1 - tt)); g.fillStyle = 'rgba(255,248,226,.55)'; g.fillRect(sx, rTop, 3, bottom - rTop); g.fillStyle = 'rgba(90,60,30,.18)'; g.fillRect(sx + 3, rTop, 6, bottom - rTop); }
      g.restore(); },
    key(k) {   // returns true if consumed
      if (k === 'i') { this.toggle('inventory'); return true; } if (k === 'j') { this.toggle('journal'); return true; }
      if (['1', '2', '3', '4'].includes(k)) { this.selectTool(TOOLBAR[+k - 1]); return true; }
      if (this.open === 'inventory') { const cols = 6; if (k === 'arrowleft') this.cursor = Math.max(0, this.cursor - 1); if (k === 'arrowright') this.cursor = Math.min(Inventory.size - 1, this.cursor + 1); if (k === 'arrowup') this.cursor = Math.max(0, this.cursor - cols); if (k === 'arrowdown') this.cursor = Math.min(Inventory.size - 1, this.cursor + cols);
        if (k === 'u') this.act('use'); if (k === 's') this.act('split'); if (k === 'x') this.act('drop'); if (k === 'escape') this.open = null; return true; }
      if (this.open === 'journal') { const items = DB.byCategory(this.cats[this.journalCat]); if (k === 'arrowleft' || k === 'arrowup') this.journalCursor = Math.max(0, this.journalCursor - 1); if (k === 'arrowright' || k === 'arrowdown') this.journalCursor = Math.min(items.length - 1, this.journalCursor + 1); if (k === 'q') this.setCat(this.journalCat - 1); if (k === 'e') this.setCat(this.journalCat + 1); if (k === 'escape') this.open = null; return true; }
      return false; },
  };

  // ---------------- node rendering helper (sprite from the atlas, state-aware)
  function nodeSprite(n) { const st = n.state === 'full' ? 'full' : n.state; const key = `${n.def.kind}:${st}`; return NATLAS.index[key] || NATLAS.index[`${n.def.kind}:depleted`]; }

  // ---------------- save hooks
  const Save = {
    snapshot() { return { inventory: Inventory.slots, tools: Tools.owned, active: Tools.active, nodes: Nodes.list.map(n => ({ id: n.def.id, left: n.left, state: n.state, depletedAt: n.depletedAt, depletedSeason: n.depletedSeason || null, uniqueTaken: n.uniqueTaken })), journal: Journal.found, stats: Stats }; },
    restore(s) { if (!s) return; Inventory.slots = s.inventory.map(x => x ? { ...x } : null); while (Inventory.slots.length < Inventory.size) Inventory.slots.push(null); Tools.owned = s.tools || Tools.owned; for (const id in Tools.owned) if (Tools.owned[id].tier === undefined) Tools.owned[id].tier = 0; Tools.active = s.active || 'hand';
      const by = Object.fromEntries(s.nodes.map(n => [n.id, n])); for (const n of Nodes.list) { const r = by[n.def.id]; if (r) { n.left = r.left; n.state = r.state; n.depletedAt = r.depletedAt; n.depletedSeason = r.depletedSeason; n.uniqueTaken = r.uniqueTaken || []; } }
      Journal.found = s.journal || {}; Object.assign(Stats, s.stats || {}); emit('inventory'); },
  };

  function init(data, world) {
    W = world; RARITY = data.items.rarities; data.items.items.forEach(i => ITEMS[i.id] = i); data.tools.tools.forEach(t => TOOLS[t.id] = t); NODE_DEFS = data.nodes.nodes; ICON = data.icons; NATLAS = data.natlas;
    for (const [id, a] of Object.entries(data.nodes.activities_extra)) if (!W.Survival.cfg().activities[id]) W.Survival.cfg().activities[id] = a;
    Inventory.init(); Tools.init(); Nodes.init();
    // save integration: extend the survival snapshot, restore after it
    const S = W.Survival.SaveState; const snap = S.snapshot.bind(S), load = S.load.bind(S);
    S.snapshot = () => Object.assign(snap(), { gather: Save.snapshot() }); S.load = (s) => { s = s || S.read(); const ok = load(s); if (ok && s.gather) S.guard('pack and field guide', () => Save.restore(s.gather)); return ok; };
    W.WeatherState.recentRainHours = 99;   // tracked by tick below
  }
  let lastHour = null;
  function tick(dt) { FX.tick(dt); const h = W.Survival.Clock.day * 24 + W.WorldClock.hour(); if (lastHour === null) lastHour = h; const dh = h - lastHour; lastHour = h;
    const wx = W.WeatherState.kind; if ((wx === 'light_rain' || wx === 'heavy_rain') && W.WeatherState.intensity > 0.3) W.WeatherState.recentRainHours = 0; else W.WeatherState.recentRainHours = Math.min(99, W.WeatherState.recentRainHours + Math.max(0, dh));
    Nodes.tick(); }
  return { setUse: f => { W.onUse = f; }, setExtraIcon: f => { W.extraIcon = f; }, init, tick, on, DB, Inventory, Tools, Nodes, Gathering, Journal, UI, FX, Stats, Save, nodeSprite, RCOL, items: () => ITEMS };
})();
