// Gathering / inventory / journal tests — the test route from Prompt 07 plus conditions, tools, respawn, save/load.
const { chromium } = require('playwright'); const fs = require('fs');
const PORT = process.env.PORT || 8770; const results = [];
function check(name, ok, detail) { results.push({ name, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? '  — ' + detail : '')); }
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 2000, height: 1200 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(`http://127.0.0.1:${PORT}/preview/play.html?dev=1`);
  await p.waitForFunction(() => window.Gather && window.Survival && Gather.Nodes.list.length > 0, { timeout: 30000 });
  const ev = (f, a) => p.evaluate(f, a);
  const shot = async (n) => { await p.waitForTimeout(300); const c = await p.$('#c'); await c.screenshot({ path: `/root/mosslight/renders/gather_${n}.png` }); };
  const gatherAt = (id) => ev(id => { const n = Gather.Nodes.list.find(n => n.def.id === id); Player.setPos(n.def.x, n.def.y + 6); Interaction.update(0.016); return Gather.Gathering.attempt(n); }, id);
  const nodeState = (id) => ev(id => { const n = Gather.Nodes.list.find(n => n.def.id === id); return { state: n.state, left: n.left }; }, id);
  await ev(() => { setPreset(1); WorldClock.paused = true; SeasonState.season = 'spring'; Survival.Clock.setHour(10); Survival.Energy.set(100); });
  const n0 = await ev(() => [Object.keys(Gather.items()).length, Gather.Nodes.list.length]); check('data-driven catalog loaded: 50 items, 30 nodes', n0[0] === 50 && n0[1] === 30, `${n0[0]} items, ${n0[1]} nodes`);
  // route 1: branch
  let r = await gatherAt('branches_log'); check('1. find a branch (hand)', r.ok && r.got.some(g => g[0] === 'branch'), JSON.stringify(r.got));
  const e1 = await ev(() => [Survival.Energy.current, WorldClock.hour()]); check('gathering spends configured energy and time exactly once', e1[0] === 98 && Math.abs(e1[1] - (10 + 6 / 60)) < 0.01, `energy ${e1[0]}, clock ${e1[1].toFixed(2)} h`);
  // route 2: mushroom (spring, hand)
  r = await gatherAt('mush_log'); check('2. gather a mushroom', r.ok && r.got.some(g => g[0] === 'mushroom_brown'), JSON.stringify(r.got));
  // route 3: flower (daisies, day, spring)
  r = await gatherAt('daisies_s'); check('3. pick a flower', r.ok && r.got.some(g => g[0] === 'daisy'), JSON.stringify(r.got));
  await shot('pickup_feedback');
  // route 4: stones
  r = await gatherAt('stones_outcrop'); check('4. collect stones', r.ok && r.got.some(g => g[0] === 'stone'), JSON.stringify(r.got));
  // tool compatibility: oak needs axe; mint needs knife; deposit needs pickaxe. Hand only fails; selecting the tool works.
  await ev(() => { Gather.Tools.owned.axe.durability = 0; }); r = await gatherAt('oak_wood'); check('axe required: broken axe refuses the oak', !r.ok, r.reason);
  await ev(() => { Gather.Tools.owned.axe.durability = 40; Gather.Tools.select('axe'); }); r = await gatherAt('oak_wood'); const dur = await ev(() => Gather.Tools.owned.axe.durability);
  check('5. use a tool: axe on the oak yields a log and wears the axe', r.ok && r.got.some(g => g[0] === 'log') && dur === 39, `${JSON.stringify(r.got)}, durability ${dur}`);
  await ev(() => Gather.Tools.select('hand')); r = await gatherAt('deposit_ruin'); check('pickaxe node refuses bare hands but auto-picks an owned compatible tool', r.ok, r.ok ? 'picked up pickaxe automatically: ' + JSON.stringify(r.got) : r.reason);
  await ev(() => { delete Gather.Tools.owned.knife; }); r = await gatherAt('mint_pond'); check('knife node refused without a knife', !r.ok, r.reason); await ev(() => { Gather.Tools.owned.knife = { id: 'knife', durability: 60 }; });
  r = await gatherAt('mint_pond'); check('knife node works with a knife', r.ok && r.got.some(g => g[0] === 'mint'));
  // route 6-7: inventory: stacking, split, remove, open panel, inspect
  const inv = await ev(() => Gather.Inventory.slots.filter(Boolean).map(s => [s.id, s.qty]));
  check('stacks merge: one slot per item type so far', new Set(inv.map(x => x[0])).size === inv.length, JSON.stringify(inv));
  await ev(() => { Gather.Inventory.add('stone', 29); }); const st = await ev(() => Gather.Inventory.slots.filter(s => s && s.id === 'stone').map(s => s.qty)); check('stack limit 30 overflows into a second slot', st.length === 2 && st[0] === 30, JSON.stringify(st));
  await ev(() => { Gather.UI.open = 'inventory'; const i = Gather.Inventory.slots.findIndex(s => s && s.id === 'stone'); Gather.UI.cursor = i; Gather.UI.key('s'); }); const st2 = await ev(() => Gather.Inventory.slots.filter(s => s && s.id === 'stone').map(s => s.qty)); check('split halves a stack', st2.length === 3 && st2.includes(15), JSON.stringify(st2));
  await ev(() => { Gather.UI.key('x'); }); const st3 = await ev(() => Gather.Inventory.count('stone')); check('remove drops one', st3 === (30 + st[1] - 1), `${st3} stones`);
  await ev(() => { Gather.UI.open = 'inventory'; Gather.UI.cursor = 0; }); await shot('inventory'); check('6. inventory panel opens', await ev(() => Gather.UI.open === 'inventory'));
  check('7. inspect: selected item has name, rarity, description', await ev(() => { const s = Gather.Inventory.slots[Gather.UI.cursor]; const it = Gather.DB.get(s.id); return !!(it.name && it.rarity && it.description); }));
  await ev(() => { Gather.UI.open = null; });
  // route 8: journal
  await ev(() => { Gather.UI.open = 'journal'; Gather.UI.journalCat = 2; Gather.UI.journalCursor = 0; }); await shot('journal'); const jp = await ev(() => Gather.Journal.progress()); check('8. journal records discoveries with progress', jp[0] >= 5 && jp[1] === 50, `${jp[0]}/${jp[1]}`);
  const je = await ev(() => [Gather.Journal.entry('daisy').known, Gather.Journal.entry('ghostcap').known, Gather.Journal.entry('ghostcap').name]); check('undiscovered entries are hidden as ???', je[0] === true && je[1] === false && je[2] === '???');
  await ev(() => { Gather.UI.open = null; });
  // route 9: rare resource under conditions — moondew only at night; ghostcap only deep night after rain in spring/autumn
  let vis = await ev(() => Gather.Nodes.conditionsMet(Gather.Nodes.list.find(n => n.def.id === 'moondew_ruin'))); check('moondew unavailable by day', vis === false);
  await ev(() => { Survival.Clock.setHour(22.5); }); vis = await ev(() => Gather.Nodes.conditionsMet(Gather.Nodes.list.find(n => n.def.id === 'moondew_ruin'))); r = await gatherAt('moondew_ruin'); check('9. moondew collectible at night', vis && r.ok && r.got.some(g => g[0] === 'moondew'), JSON.stringify(r.got));
  await shot('night_moondew');
  let gc = await ev(() => Gather.Nodes.conditionsMet(Gather.Nodes.list.find(n => n.def.id === 'ghostcap_forest'))); check('ghostcap needs deep night AND recent rain (dry 22:30 → no)', gc === false);
  await ev(() => { Survival.Clock.setHour(1.0); WeatherState.set('light_rain', 0.8); WeatherState.intensity = 0.8; Gather.tick(0.1); }); gc = await ev(() => Gather.Nodes.conditionsMet(Gather.Nodes.list.find(n => n.def.id === 'ghostcap_forest'))); r = await gatherAt('ghostcap_forest');
  check('ghostcap appears at 01:00 in rain and can be picked', gc && r.ok && r.got[0][0] === 'ghostcap', JSON.stringify(r.got));
  await ev(() => { WeatherState.set('clear', 0); WeatherState.intensity = 0; });
  const mn = await ev(() => { Survival.Clock.setHour(23); const n = Gather.Nodes.list.find(n => n.def.id === 'deposit_ruin'); let hits = 0; for (let i = 0; i < 4 && n.left > 0; i++) { const r = Gather.Gathering.attempt(n); if (r.ok && r.got.some(g => g[0] === 'moonstone')) hits++; } return [hits, n.left, n.state]; });
  check('deposit yields are limited and it depletes (no respawn)', mn[1] === 0 && mn[2] === 'depleted', `left ${mn[1]}, state ${mn[2]}, moonstone hits ${mn[0]} (night-only extra)`);
  // route 10: depletion + regeneration
  await ev(() => { Survival.Clock.setHour(10); }); for (let i = 0; i < 3; i++) await gatherAt('branches_log'); let ns = await nodeState('branches_log'); check('10a. branch pile depletes after its yields', ns.state === 'depleted' && ns.left === 0, JSON.stringify(ns));
  await shot('depleted_branches');
  await ev(() => { Survival.Clock.advance(7 * 60); Gather.tick(0.1); }); ns = await nodeState('branches_log'); check('10b. half-way: regrowing state', ns.state === 'regrow', JSON.stringify(ns));
  await ev(() => { Survival.Clock.advance(6 * 60); Gather.tick(0.1); }); ns = await nodeState('branches_log'); check('10c. respawns after 12 game hours', ns.state === 'full' && ns.left === 2, JSON.stringify(ns));
  const dz = await ev(() => { const n = Gather.Nodes.list.find(n => n.def.id === 'daisies_s'); n.left = 0; n.state = 'depleted'; n.depletedAt = 0; n.depletedSeason = 'spring'; Gather.tick(0.1); const a = n.state; SeasonState.season = 'summer'; Gather.tick(0.1); const b = n.state; SeasonState.season = 'spring'; return [a, b]; });
  check('season-mode nodes regrow only when the season changes', dz[0] === 'depleted' && dz[1] === 'full', dz.join('→'));
  // unique keepsakes never duplicate
  const uq = await ev(() => { const n = Gather.Nodes.list.find(n => n.def.id === 'lintel_key'); const r1 = Gather.Gathering.attempt(n); n.left = 1; n.state = 'full'; const r2 = Gather.Gathering.attempt(n); return [Gather.Inventory.count('key_old'), r1.ok, r2.ok]; });
  check('unique keepsake (brass key) cannot be found twice', uq[0] === 1 && uq[1] && !uq[2], `keys in pack: ${uq[0]}, second attempt ok=${uq[2]}`);
  // energy integration: exhausted refuses, zero refuses
  await ev(() => Survival.Energy.set(0)); r = await gatherAt('stones_path'); check('gathering refused at zero energy', !r.ok, r.reason); await ev(() => Survival.Energy.set(100));
  // save / load: depleted nodes stay depleted, inventory and journal intact, no duplication
  const before = await ev(() => { Survival.SaveState.save(); return { inv: Gather.Inventory.slots.filter(Boolean).map(s => [s.id, s.qty]), found: Object.keys(Gather.Journal.found).length, dep: Gather.Nodes.list.filter(n => n.state === 'depleted').map(n => n.def.id), axe: Gather.Tools.owned.axe.durability }; });
  await ev(() => { Gather.Inventory.init(); Gather.Journal.found = {}; Gather.Nodes.init(); Gather.Tools.owned.axe.durability = 40; Survival.SaveState.load(); });
  const after = await ev(() => ({ inv: Gather.Inventory.slots.filter(Boolean).map(s => [s.id, s.qty]), found: Object.keys(Gather.Journal.found).length, dep: Gather.Nodes.list.filter(n => n.state === 'depleted').map(n => n.def.id), axe: Gather.Tools.owned.axe.durability }));
  check('save/load restores inventory exactly (no loss, no duplication)', JSON.stringify(before.inv) === JSON.stringify(after.inv), `${before.inv.length} stacks`);
  check('save/load restores journal and tool durability', before.found === after.found && before.axe === after.axe, `found ${after.found}, axe ${after.axe}`);
  check('save/load keeps depleted nodes depleted', JSON.stringify(before.dep) === JSON.stringify(after.dep) && after.dep.length > 0, after.dep.join(','));
  // prompts readable at phone aspect
  await ev(() => { Camera.vw = 780; Camera.vh = 360; Camera.safe = 24; Touch.enabled = true; Survival.Clock.setHour(10); const n = Gather.Nodes.list.find(n => n.def.id === 'stones_outcrop'); Player.setPos(n.def.x, n.def.y + 6); Interaction.update(0.016); }); await shot('phone_prompt'); await ev(() => { Gather.UI.open = 'inventory'; }); await shot('phone_inventory'); await ev(() => { Gather.UI.open = null; Camera.vw = 640; Camera.vh = 360; Camera.safe = 0; Touch.enabled = false; });
  check('no page errors', errs.length === 0, errs.join(' | '));
  fs.writeFileSync('/root/mosslight/tests/gather_results.json', JSON.stringify({ results, passed: results.filter(r => r.ok).length, total: results.length }, null, 1));
  console.log(`${results.filter(r => r.ok).length}/${results.length} passed`); await b.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
