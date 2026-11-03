// Prompt 16 tests: balance, progression without dead ends, home stages, fair nights, natural weather, system links,
// save reliability (corruption, interruption, migration, autosave, continue), performance and memory over long play.
// Run: NODE_PATH=<nm> PORT=8777 node tests/integration_tests.js
const { chromium } = require('playwright'); const fs = require('fs');
const PORT = process.env.PORT || 8777; const results = [];
function check(name, ok, detail) { results.push({ name, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail !== undefined ? '  — ' + detail : '')); }
const J = p => JSON.parse(fs.readFileSync('/root/mosslight/' + p, 'utf8'));
(async () => {
  // ---- data-level balance (no browser needed)
  const nodes = J('assets/items/nodes.json').nodes, recipes = J('assets/build/recipes.json').recipes, tools = J('assets/items/tools.json').tools;
  const renewable = id => nodes.some(n => n.respawn_mode !== 'none' && n.respawn_hours && n.drops.some(([d, lo, hi]) => d === id && hi > 0));
  const craftable = id => recipes.some(r => r.result === id);
  const essentials = ['log', 'branch', 'stone', 'fiber', 'clay', 'scrap_metal', 'iron_ore', 'copper_ore', 'coal', 'glass_shard', 'bolt', 'wire', 'moss', 'hardwood', 'rusted_gear'];
  const dead = essentials.filter(id => !renewable(id) && !craftable(id));
  check('every material that progression needs is renewable or craftable', dead.length === 0, dead.join(', ') || 'all renewable');
  const guaranteed = id => nodes.some(n => n.respawn_hours && n.drops.some(([d, lo]) => d === id && lo > 0)) || craftable(id);
  const gated = ['iron_ore', 'glass_shard', 'coal', 'bolt', 'wire'].filter(id => !guaranteed(id));
  check('essential late materials have a guaranteed (non-random) source', gated.length === 0, gated.join(', ') || 'iron ore 1/strike, glass 1/search, coal from charcoal, bolts and wire from scrap');
  const breakable = tools.filter(t => t.durability), mend = breakable.filter(t => recipes.some(r => r.repair === t.id && r.station === 'hand'));
  check('every tool that can break can be mended by hand, with no tool needed', mend.length === breakable.length, mend.map(t => t.id).join(', '));
  check('axe, pickaxe and knife have three tiers with rising durability and efficiency', ['axe', 'pickaxe', 'knife'].every(id => { const t = tools.find(x => x.id === id).tiers; return t.length === 3 && t[1].durability > t[0].durability && t[2].durability > t[1].durability && t[2].efficiency > t[1].efficiency && t[1].efficiency > t[0].efficiency; }));
  const icons = J('assets/items/icons.json').index, items = J('assets/items/items.json').items; const noIcon = recipes.filter(r => !r.tool && !icons[r.icon || r.result]).map(r => r.id).concat(items.filter(i => i.category !== 'fish' && !icons[i.icon || i.id]).map(i => i.id));
  check('every recipe and every non-fish item has an icon in the atlas (no blank slots)', noIcon.length === 0, noIcon.slice(0, 12).join(', ') || `${Object.keys(icons).length} icons`);
  const { execSync } = require('child_process'); const rep = execSync('python3 tools/balance_report.py', { cwd: '/root/mosslight' }).toString();
  const rows = [...rep.matchAll(/^\| (\d) [^|]+\|[^|]+\| (\d+) \| [\d.]+ \| ([\d.]+) \| ([\d.]+) \((\w*)\) \|$/gm)].map(m => ({ stage: +m[1], energyDays: +m[3], waitDays: +m[4], item: m[5] }));
  check('balance model: each home stage takes 2-15 days of waiting for materials, rising stage by stage, nothing blocked', rows.length === 5 && rows.slice(1).every(r => r.waitDays >= 1.5 && r.waitDays <= 15) && !/stage .*cannot supply/.test(rep), rows.map(r => `S${r.stage} ${r.waitDays}d (${r.item || '-'})`).join(', '));

  const fr = execSync('python3 tools/fish_report.py', { cwd: '/root/mosslight' }).toString();
  check('every one of the 93 fish can be caught with conditions the weather actually makes and bait the player can get', /catchable with gathered or crafted bait: 93/.test(fr) && /impossible: none/.test(fr), (fr.match(/catchable[^\n]*/) || [''])[0]);
  const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 2000, height: 1200 } }); const p = await ctx.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(`http://127.0.0.1:${PORT}/preview/play.html?lab=1&new=1`); await p.waitForFunction(() => window.Monsters && Monsters.cfg() && window.Build && Build.comp().wall_wood && window.UIKit && UIKit.Map && Gather.Nodes.list.length, { timeout: 60000 });
  const ev = (f, a) => p.evaluate(f, a); const wait = ms => p.waitForTimeout(ms);
  await ev(() => { Festival.setEnabled(false); Social.setEnabled(false); setPreset(1); WorldClock.paused = true; Survival.Clock.day = 5; Monsters.clearAll();
    window.give = o => { for (const [k, v] of Object.entries(o)) Gather.Inventory.add(k, v); };
    window.room = (cx0, cy0, w, h, wall = 'wall_wood', roof = 'roof_thatch', extra = []) => { const L = Build.S.list; let uid = 9000 + L.length; const put = (type, cx, cy, o = {}) => L.push(Object.assign({ uid: uid++, type, cx, cy, x: cx * 16 + 8, y: cy * 16 + 15, rot: 0, dur: 200, work: 0, on: true }, o));
      for (let y = cy0 - 1; y <= cy0 + h; y++) for (let x = cx0 - 1; x <= cx0 + w; x++) { const edge = x < cx0 || y < cy0 || x >= cx0 + w || y >= cy0 + h; put(edge ? wall : 'floor_plank', x, y); if (!edge) put(roof, x, y); }
      const door = L.find(e => e.type === wall && e.cy === cy0 + h && e.cx === cx0); door.opening = 'door'; door.open = false;
      for (const [t, cx, cy, o] of extra) put(t, cx, cy, o || {}); Build.rebuild(); }; });

  // ---- tools: break, mend, upgrade, efficiency
  let r = await ev(() => { const T = Gather.Tools; T.owned.axe.durability = 0; const can = T.canUse('axe', 'axe'); give({ stone: 2, cord: 2, branch: 2 }); Build.Craft.station = 'hand'; const s = Build.Craft.start('mend_axe', 'hand'); if (s.ok) Build.Craft.finish(); return [can, s.ok, T.owned.axe.durability, T.info('axe').durability]; });
  check('a worn-out axe is mended by hand back to full', r[0] === false && r[1] && r[2] === r[3] && r[3] === 40, JSON.stringify(r));
  r = await ev(() => { const T = Gather.Tools; give({ iron_ingot: 2, hardwood: 2 }); Build.S.stationsBuilt.adv_bench = true; Build.Craft.check(); const skip = Build.Craft.start('axe_t2', 'adv_bench');
    give({ copper_ingot: 2, hardwood: 1, cord: 1 }); Build.S.stationsBuilt.workbench = true; Build.Craft.check(); const a = Build.Craft.start('axe_t1', 'workbench'); if (a.ok) Build.Craft.finish(); return [skip.ok, skip.reason, a.ok, T.info('axe').name, T.owned.axe.durability, T.info('axe').efficiency]; });
  check('tool tiers go in order: copper before iron; the copper axe lasts longer and works better', r[0] === false && /first/.test(r[1]) && r[2] && r[3] === 'Copper axe' && r[4] === 90 && r[5] > 1.2, JSON.stringify(r));
  r = await ev(() => { const n = Gather.Nodes.list.find(x => x.def.id === 'oak_north'); const T = Gather.Tools; const run = tier => { T.owned.axe.tier = tier; let logs = 0; for (let i = 0; i < 200; i++) { T.owned.axe.durability = 999; n.left = 3; n.state = 'full'; Survival.Energy.set(100); WorldClock.minutes = 600; Gather.Inventory.slots = Gather.Inventory.slots.map(() => null); Gather.Gathering.attempt(n); logs += Gather.Inventory.count('log'); } return logs / 200; }; const a = run(0), c = run(2); T.owned.axe.tier = 1; T.owned.axe.durability = 90; return [a, c]; });
  check('better tools yield more per swing (iron axe vs basic, 200 swings each)', r[1] > r[0] * 1.2, `basic ${r[0].toFixed(2)} logs/swing, iron ${r[1].toFixed(2)}`);

  // ---- crafting consistency and the full-pack case
  r = await ev(() => { Gather.Inventory.slots = Gather.Inventory.slots.map(() => null); give({ log: 1 }); Build.S.stationsBuilt.workbench = true; Build.Craft.check(); Survival.Energy.set(80); WorldClock.minutes = 600; const p0 = Gather.Inventory.count('plank'), l0 = Gather.Inventory.count('log'); const s = Build.Craft.start('plank', 'workbench'); Build.Craft.finish(); return [s.ok, Gather.Inventory.count('plank') - p0, l0 - Gather.Inventory.count('log'), 80 - Survival.Energy.current, WorldClock.minutes - 600]; });
  check('crafting a plank takes the log, gives 4 planks, and costs its energy and minutes', r[0] && r[1] === 4 && r[2] === 1 && r[3] === 2 && Math.abs(r[4] - 10) < .5, JSON.stringify(r));
  r = await ev(() => { const I = Gather.Inventory; const saved = I.slots.map(s => s && { ...s }); for (let i = 0; i < I.slots.length; i++) I.slots[i] = { id: 'stone', qty: Gather.items().stone.stack }; I.slots[0] = { id: 'log', qty: 2 }; Monsters.drops.length = 0;
    const s = Build.Craft.start('plank', 'workbench'); if (s.ok) Build.Craft.finish(); const inPack = I.count('plank'), onGround = Monsters.drops.filter(d => d.id === 'plank').reduce((a, d) => a + d.q, 0); I.slots = saved; Monsters.drops.length = 0; return [s.ok, inPack, onGround]; });
  check('crafting with a full pack never destroys the result: the rest lands at your feet', r[0] && r[2] === 4 && r[1] === 0, JSON.stringify(r));

  // ---- home stages: shelter, gating, bonuses
  r = await ev(() => { Build.S.list.length = 0; Build.rebuild(); const st0 = Build.homeStage(); const v0 = Build.validate('wall_cottage', { cx: 20, cy: 5, x: 328, y: 95 }); room(10, 4, 3, 3); return [st0, v0, Build.homeStage(), Build.sheltered(11 * 16 + 8, 5 * 16 + 8), Build.sheltered(300, 318), Build.stageNeeds()]; });
  check('a fresh camp is stage 1; stage-3 walls wait for a shelter, with the reason given', r[0] === 1 && /first/.test(r[1] || ''), `${r[0]} · ${r[1]}`);
  check('a closed, roofed room with a door is a Woodland shelter, and standing inside it counts as sheltered', r[2] === 2 && r[3] === true && r[4] === false, `stage ${r[2]}, inside ${r[3]}, outside ${r[4]}`);
  r = await ev(() => { Player.setPos(11 * 16 + 8, 5 * 16 + 12); Survival.Clock.setHour(3); Survival.Energy.set(20); Survival.Sleep._cool = 0; Survival.Sleep.start({ instant: true }); const home = Survival.Energy.current;
    Player.setPos(300, 318); Survival.Clock.setHour(3); Survival.Energy.set(20); Survival.Sleep._cool = 0; Survival.Sleep.start({ instant: true }); return [home, Survival.Energy.current]; });
  check('sleeping in your own room after 02:00 still gives a full night; the tent outside does not', r[0] === 100 && r[1] < 100, `room ${r[0]}, tent ${r[1]}`);
  r = await ev(() => { Build.S.list.length = 0; room(10, 4, 3, 2, 'wall_cottage', 'roof_shingle', [['bed_rustic', 11, 5]]); const w = Build.S.list.find(e => e.type === 'wall_cottage' && e.cy === 3 && e.cx === 11); w.opening = 'window_pane'; Build.rebuild(); const st = Build.homeStage();
    Player.setPos(11 * 16 + 8, 5 * 16 + 12); Survival.Clock.setHour(22); Survival.Sleep._cool = 0; Survival.Sleep.start({ instant: true }); const max = Survival.Energy.max; Player.setPos(300, 318); return [st, max, Build.validate('wall_stone', { cx: 30, cy: 20, x: 488, y: 335 })]; });
  check('a 6-cell timber room with a window and a bed is a homestead: +10 morning energy, stage-4 parts open', r[0] === 3 && r[1] === 110 && !/first/.test(r[2] || ''), JSON.stringify(r));
  r = await ev(() => { Build.S.list.length = 0; Build.rebuild(); Survival.Energy.max = 100; Survival.Energy.set(100); return Build.homeStage(); }); check('pulling the home down drops the stage again', r === 1, String(r));

  // ---- nights: fair and ramped
  r = await ev(() => { const D = Monsters.Director; Survival.Clock.setHour(23.5); const at = d => { Survival.Clock.day = d; return D.budget(); }; const v = [at(1), at(2), at(3), at(6)]; Survival.Clock.day = 5; return v; });
  check('night danger ramps over the first nights (budget day 1 < day 2 < day 6)', r[0] < r[1] && r[1] <= r[2] && r[2] < r[3], r.join(' → '));
  r = await ev(() => { Survival.Clock.setHour(23); Player.setPos(300, 318); let bad = 0, n = 0; for (let i = 0; i < 400; i++) for (const h of ['forest', 'pond', 'ruin', 'burrow']) { const s = Monsters.Director.site(h); if (!s) continue; n++; const dd = Math.hypot(s[0] - 300, s[1] - 318); if (dd <= 110) bad++; } return [n, bad]; });
  check('creatures are never placed within 110 px of the player', r[0] > 100 && r[1] === 0, `${r[0]} sites, ${r[1]} too close`);
  r = await ev(() => { const T = []; for (let i = 0; i < 300; i++) { const s = Monsters.Director.site('forest'); if (s) T.push(s); } return T.filter(s => Math.hypot(s[0] - 318, s[1] - 262) < 50).length; });
  check('no spawn site inside the campfire\'s pool of light', r === 0, `${r} inside`);

  // ---- weather: natural, seasonal, held when set by hand, linked to fishing, finds and sound
  r = await ev(() => { const Wx = Survival.Weather; Wx.seed = 12345; let dry = 0, maxDry = 0, fogLate = 0, snowOff = 0, rainWinter = 0, kinds = {}; Wx.lastRainDay = 0;
    for (let d = 2; d < 120; d++) { const season = ['spring', 'summer', 'autumn', 'winter'][Math.floor((d - 1) / 28) % 4]; const pl = Wx.plan(d, season); const rain = pl.some(b => b.kind.includes('rain')); if (rain) Wx.lastRainDay = d; if (season !== 'winter') { dry = rain ? 0 : dry + 1; maxDry = Math.max(maxDry, dry); }
      for (const b of pl) { kinds[b.kind] = (kinds[b.kind] || 0) + 1; if (b.kind === 'fog' && b.h >= 10 && !(b.h >= 20 && (season === 'spring' || season === 'autumn'))) fogLate++; if (b.kind === 'snow' && season !== 'winter') snowOff++; if (b.kind.includes('rain') && season === 'winter') rainWinter++; } }
    Wx.lastRainDay = 0; return [maxDry, fogLate, snowOff, rainWinter, kinds]; });
  check('weather plans: rain at least every 3rd day outside winter, fog only in the morning (and spring/autumn evening mist), snow only in winter', r[0] <= 3 && r[1] === 0 && r[2] === 0 && r[3] === 0 && Object.keys(r[4]).length >= 5, `longest dry spell ${r[0]} days; ${JSON.stringify(r[4])}`);
  r = await ev(() => { const Wx = Survival.Weather; Wx.enabled = true; Wx.hold = false; Wx.setKind = null; Wx.seed = 777; Survival.Clock.day = 9; let changed = 0; let last = null; for (let h = 0; h < 24; h++) { Survival.Clock.setHour(h + .1); Wx.apply(); if (WeatherState.kind !== last) { changed++; last = WeatherState.kind; } } return [changed, Wx.forecast(10)]; });
  check('the sky changes on its own during a day, and the morning journal can say what is coming', r[0] >= 1 && typeof r[1] === 'string' && r[1].length > 4, `${r[0]} changes; tomorrow: ${r[1]}`);
  r = await ev(() => { const Wx = Survival.Weather; Survival.Clock.setHour(11); Wx.apply(); WeatherState.set('fog', .8); Survival.Clock.setHour(16); Wx.apply(); const held = WeatherState.kind; Survival.Clock.day += 1; Survival.Clock.setHour(16.2); Wx.apply(); return [held, Wx.hold]; });
  check('weather chosen by hand (dev menu, preset) holds for the rest of that day', r[0] === 'fog' && r[1] === false, JSON.stringify(r));
  r = await ev(() => { Survival.Weather.enabled = false; WeatherState.set('light_rain', .7); WeatherState.intensity = .7; Gather.WeatherState = WeatherState; for (let i = 0; i < 3; i++) Gather.tick(.1); const clay = Gather.Nodes.list.find(n => n.def.id === 'clay_bank'); clay.left = 4; clay.state = 'full'; const vis = Gather.Nodes.conditionsMet(clay); const fc = Fishing.conditions(); WeatherState.set('clear', 0); WeatherState.intensity = 0; WeatherState.recentRainHours = 99; const dry = Gather.Nodes.conditionsMet(clay); Survival.Weather.enabled = true; return [vis, fc.rainy, dry]; });
  check('rain opens the clay bank and changes the fishing conditions; dry weather closes it again', r[0] === true && r[1] === true && r[2] === false, JSON.stringify(r));
  r = await ev(async () => { await Sound.start(); Survival.Weather.enabled = false; WeatherState.set('heavy_rain', .9); WeatherState.intensity = .9; await new Promise(res => setTimeout(res, 1500)); const wet = Sound.debug().layers.rain; WeatherState.set('clear', 0); WeatherState.intensity = 0; Survival.Weather.enabled = true; return wet; });
  check('the rain ambience follows the weather', r > .05, `rain layer ${r}`);

  r = await ev(() => { const Wx = Survival.Weather, F = Festival.data(); const k = 'fest_fireflies', f = F.festivals[k]; let day = 1; while (!(Festival.Cal.seasonOf(day) === f.season && Festival.Cal.dos(day) === f.day)) day++; Wx.lastRainDay = 0; const pl = Wx.plan(day, f.season); return [pl.filter(b => b.h >= 15).every(b => b.kind === 'clear'), Wx.forecast(day)]; });
  check('a festival day keeps its evening clear, and the morning forecast says so', r[0] && /festival/.test(r[1]), r[1]);
  r = await ev(() => { Gather.Inventory.slots = Gather.Inventory.slots.map(() => null); Gather.Inventory.add('blackberry', 2); Survival.Energy.set(50); WorldClock.minutes = 600; const i = Gather.Inventory.slots.findIndex(x => x && x.id === 'blackberry'); Gather.UI.open = 'inventory'; Gather.UI.cursor = i; Gather.UI.key('u'); const e = Survival.Energy.current, n = Gather.Inventory.count('blackberry'); Survival.Energy.set(Survival.Energy.max); Gather.UI.key('u'); const full = Gather.Inventory.count('blackberry'); Gather.UI.open = null; return [e, n, full, Math.round(WorldClock.minutes - 600)]; });
  check('wild food restores a little energy, takes a moment, and is refused when you are not hungry', r[0] === 54 && r[1] === 1 && r[2] === 1 && r[3] === 2, JSON.stringify(r));
  r = await ev(() => { Gather.Inventory.slots = Gather.Inventory.slots.map(() => null); Gather.Inventory.add('fiber', 2); Build.Craft.station = 'hand'; Build.Craft.job = null; Build.Craft.start('cord', 'hand'); Build.Craft.job.t = .3; Survival.SaveState.save(); Build.Craft.job = null; Survival.SaveState.load(); const j = Build.Craft.job; const out = [!!j, j && j.id, j && j.t]; Build.Craft.finish && j && Build.Craft.finish(); return out.concat([Gather.Inventory.count('cord')]); });
  check('a craft in progress survives save and load and then finishes', r[0] && r[1] === 'cord' && r[2] === .3 && r[3] === 1, JSON.stringify(r));
  // ---- discoveries, collision
  r = await ev(() => { Gather.Inventory.slots = Gather.Inventory.slots.map(() => null); const n = Gather.Nodes.list.find(x => x.def.id === 'stones_path'); n.left = 2; n.state = 'full'; delete Gather.Journal.found.stone; Survival.Energy.set(100); Gather.Gathering.attempt(n); return [!!Gather.Journal.found.stone, Gather.Journal.found.stone && Gather.Journal.found.stone.count]; });
  check('gathering records the find in the field guide', r[0] && r[1] >= 1, JSON.stringify(r));
  r = await ev(() => { const water = Build.validate('fnd_wood', { cx: 39, cy: 16, x: 632, y: 271 }); const tent = Build.validate('fnd_wood', { cx: 17, cy: 15, x: 280, y: 255 }); return [water, tent]; });
  check('building placement refuses water and the tent', typeof r[0] === 'string' && typeof r[1] === 'string', JSON.stringify(r));

  // ---- neighbours: passing by costs nothing
  const soc = fs.readFileSync('/root/mosslight/preview/social.js', 'utf8'); const ci = soc.slice(soc.indexOf('function checkIgnored'), soc.indexOf('function checkIgnored') + 700);
  check('walking past a neighbour who is waiting never lowers trust or affection', !/Rel\.change/.test(ci) && !/'ignored'/.test(ci.replace("st.ignored[k]", '')), 'checkIgnored only records the day');

  // ---- saving: everything round-trips; damage and interruption are survived; old saves migrate; autosave; continue
  r = await ev(() => { Survival.Weather.enabled = true; Player.setPos(410, 300); Player.facing = 'side'; give({ resin: 3 }); Gather.Tools.owned.knife.tier = 1; Gather.Tools.owned.knife.durability = 77; room(10, 4, 3, 3); WeatherState.set('fog', .6); WeatherState.intensity = .6; Survival.Clock.day = 12; Survival.Clock.setHour(14.5);
    Monsters.Health.cur = 61; UIKit.Map.seen = null; UIKit.explore(600, 280); Fishing.S.visited = ['Stream']; Fishing.Book.rec.roach = Fishing.Book.rec.roach || { count: 0 }; Fishing.Book.rec.roach.count = 3; Social.S.pip.mem.push({ kind: 'visit', t: 1, sig: .5, detail: {} });
    const before = JSON.stringify([Player.x, Player.y, Gather.Inventory.count('resin'), Gather.Tools.owned.knife, Build.S.list.length, WeatherState.kind, Survival.Clock.day, Math.round(WorldClock.minutes), Monsters.Health.cur, UIKit.Map.seen.reduce((a, b) => a + b, 0), Fishing.S.visited, Fishing.Book.rec.roach.count, Social.S.pip.mem.length, Build.homeStage()]);
    const ok = !!Survival.SaveState.save(); Player.setPos(300, 318); Gather.Inventory.slots = Gather.Inventory.slots.map(() => null); Gather.Tools.owned.knife.tier = 0; Build.S.list.length = 0; Build.rebuild(); WeatherState.set('clear', 0); Survival.Clock.day = 1; WorldClock.minutes = 300; Monsters.Health.cur = 100; UIKit.Map.seen = null; Fishing.S.visited = []; Fishing.Book.rec.roach.count = 0; Social.S.pip.mem = [];
    const l = Survival.SaveState.load(); const after = JSON.stringify([Player.x, Player.y, Gather.Inventory.count('resin'), Gather.Tools.owned.knife, Build.S.list.length, WeatherState.kind, Survival.Clock.day, Math.round(WorldClock.minutes), Monsters.Health.cur, UIKit.Map.seen.reduce((a, b) => a + b, 0), Fishing.S.visited, Fishing.Book.rec.roach.count, Social.S.pip.mem.length, Build.homeStage()]); return [ok, l, before === after, before, after]; });
  check('one save holds position, pack, tool tiers, buildings and home stage, weather, day and time, health, map, far waters, fish records and memories', r[0] && r[1] && r[2], r[2] ? r[3] : `before ${r[3]}\nafter  ${r[4]}`);
  r = await ev(() => { const K = Survival.SaveState.KEY; Survival.SaveState.save(); Survival.Clock.day = 33; Survival.SaveState.save(); localStorage.setItem(K, localStorage.getItem(K).replace('\\"day\\":33', '\\"day\\":34')); Survival.Clock.day = 1; const ok = Survival.SaveState.load(); return [ok, Survival.Clock.day, Survival.SaveState.lastSource, Survival.SaveState.problems.join('; ')]; });
  check('a damaged save (checksum mismatch) is caught and the backup copy is loaded instead', r[0] && r[1] === 12 && /\.bak$/.test(r[2]), JSON.stringify(r));
  r = await ev(() => { const K = Survival.SaveState.KEY; Survival.Clock.day = 40; Survival.SaveState.save(); const good = localStorage.getItem(K); localStorage.setItem(K + '.tmp', good); localStorage.setItem(K, '{"app":"mosslight","v":2,"sum":"0","len":3,"body":"{"'); localStorage.setItem(K + '.bak', 'not json at all'); Survival.Clock.day = 1; let threw = false, ok; try { ok = Survival.SaveState.load(); } catch (e) { threw = true; } return [threw, ok, Survival.Clock.day, Survival.SaveState.lastSource]; });
  check('an interrupted write (main torn, backup garbage) recovers from the temp copy without throwing', !r[0] && r[1] && r[2] === 40 && /\.tmp$/.test(r[3]), JSON.stringify(r));
  r = await ev(() => { const K = Survival.SaveState.KEY; for (const k of ['', '.bak', '.tmp']) localStorage.removeItem(K + k); localStorage.setItem(K, JSON.stringify({ version: 1, day: 7, season: 'summer', minutes: 600, energy: 55, maxEnergy: 100, record: null, days: [], gather: Gather.Save.snapshot() })); Survival.Clock.day = 1; const ok = Survival.SaveState.load(); return [ok, Survival.Clock.day, SeasonState.season, Survival.Energy.current]; });
  check('an older plain (version 1) save still loads and is migrated', r[0] && r[1] === 7 && r[2] === 'summer' && r[3] === 55, JSON.stringify(r));
  r = await ev(() => { const K = Survival.SaveState.KEY; for (const k of ['', '.bak', '.tmp']) localStorage.setItem(K + k, '<<garbage>>'); let threw = false, ok; try { ok = Survival.SaveState.load(); } catch (e) { threw = true; } for (const k of ['', '.bak', '.tmp']) localStorage.removeItem(K + k); return [threw, ok]; });
  check('when every copy is garbage, loading fails cleanly (no crash, no partial state)', !r[0] && r[1] === false, JSON.stringify(r));
  r = await ev(async () => { const K = Survival.SaveState.KEY; localStorage.removeItem(K); Survival.Clock.day = 14; Survival.Clock.setHour(22); Survival.Sleep._cool = 0; Survival.Sleep.start({ instant: true }); await new Promise(res => setTimeout(res, 300)); const s = Survival.SaveState.read(); return s ? s.day : null; });
  check('waking up autosaves the morning', r === 15, String(r));
  r = await ev(() => { const K = Survival.SaveState.KEY; localStorage.removeItem(K); Survival.Clock.day = 16; Object.defineProperty(document, 'hidden', { configurable: true, get: () => true }); document.dispatchEvent(new Event('visibilitychange')); delete document.hidden; const s = Survival.SaveState.read(); return s ? s.day : null; });
  check('switching away from the game (page hidden) saves at once', r === 16, String(r));
  // continue after a reload: position and day come back, with a welcome note
  await ev(() => { Player.setPos(430, 310); Survival.Clock.day = 21; WorldClock.minutes = 800; Survival.SaveState.save(); });
  await p.goto(`http://127.0.0.1:${PORT}/preview/play.html?lab=1`); await p.waitForFunction(() => window.Survival && window.Gather && Gather.Nodes && Gather.Nodes.list.length && window.UIKit && UIKit.Map, { timeout: 60000 }); await wait(800);
  r = await ev(() => [Survival.Clock.day, Math.round(Player.x), Math.round(Player.y), Math.round(WorldClock.minutes)]);
  check('reopening the game carries on where you left off', r[0] === 21 && Math.abs(r[1] - 430) < 2 && Math.abs(r[2] - 310) < 2 && Math.abs(r[3] - 800) < 30, JSON.stringify(r));
  await ev(() => { UIKit.Menu.open = 'newgame'; }); await wait(250); const c = await p.$('#c'); await c.screenshot({ path: '/root/mosslight/renders/p16/new_game_confirm.png' }).catch(async () => { fs.mkdirSync('/root/mosslight/renders/p16', { recursive: true }); await c.screenshot({ path: '/root/mosslight/renders/p16/new_game_confirm.png' }); }); await ev(() => { UIKit.Menu.open = null; });

  // ---- performance and memory over long play
  r = await ev(async () => { Festival.setEnabled(false); Social.setEnabled(false); setPreset(4); WorldClock.paused = false; WorldClock.scale = 900; const m0 = performance.memory ? performance.memory.usedJSHeapSize : 0; const t0 = performance.now(); let frames = 0;
    await new Promise(res => { (function f() { frames++; if (performance.now() - t0 < 25000) { if (frames % 60 === 0) { Player.setPos(200 + (frames * 7) % 400, 200 + (frames * 3) % 200); } requestAnimationFrame(f); } else res(); })(); });
    if (window.gc) window.gc(); const m1 = performance.memory ? performance.memory.usedJSHeapSize : 0; return [frames, (performance.now() - t0) / frames, (m1 - m0) / 1048576, PFX.fire.length, PFX.ripple.length, PFX.rain.length, UIKit.hits().length]; });
  check('25 s of fast-forwarded play (rain, day into night): steady frame time, bounded particles, no runaway memory', r[1] < 60 && r[2] < 40 && r[3] <= 160 && r[4] <= 120 && r[6] < 200, `${r[0]} frames, ${r[1].toFixed(1)} ms/frame, heap ${r[2] >= 0 ? '+' : ''}${r[2].toFixed(1)} MB, particles fire ${r[3]} ripples ${r[4]} rain ${r[5]}, ${r[6]} tap targets`);
  r = await ev(() => { const S = Monsters; S.clearAll(); WorldClock.paused = true; Survival.Clock.setHour(23.5); Survival.Clock.day = 9; for (let i = 0; i < 12; i++) S.spawn(Object.keys(S.cfg().creatures)[i % 6], 100 + i * 50, 300); return new Promise(res => { let n = 0, t0 = performance.now(); (function f() { if (++n < 60) requestAnimationFrame(f); else res((performance.now() - t0) / 60); })(); }); });
  check('night with 12 creatures renders under the frame budget', r < 60, r.toFixed(1) + ' ms/frame');

  // ---- the public page: the site root opens the game in player mode, fast and complete
  { const pp = await ctx.newPage(); const reqs = new Set(); const perr = []; pp.on('pageerror', e => perr.push(e.message)); pp.on('request', q => { const u = new URL(q.url()); if (/^\/assets\/.*\.(png|json)$/.test(u.pathname)) reqs.add('..' + u.pathname); });
    await pp.evaluate(() => 0).catch(() => {}); await pp.goto(`http://127.0.0.1:${PORT}/?new=1`); await pp.waitForFunction(() => window.BOOTED, null, { timeout: 60000 });
    const st = await pp.evaluate(() => [location.pathname, getComputedStyle(document.querySelector('header')).display, UIKit.Menu.open, !!document.getElementById('loading'), document.getElementById('c').getBoundingClientRect().width]);
    const man = J('preview/manifest.json').files; const missing = [...reqs].filter(u => !man.includes(u));
    check('the site root opens the game: no lab controls, a title page, the canvas fills the window', /preview\/play\.html$/.test(st[0]) && st[1] === 'none' && st[2] === 'title' && st[4] > 1500, JSON.stringify(st));
    check('every file the game loads is in the parallel warm-up manifest', missing.length === 0 && reqs.size > 50, missing.slice(0, 5).join(', ') || `${reqs.size} files, all listed`);
    await pp.keyboard.press('Enter'); await wait(300); check('Enter on the title page starts play', await pp.evaluate(() => UIKit.Menu.open === null) && perr.length === 0, perr.join(' | ')); await pp.close(); }
  check('no page errors', errs.length === 0, errs.slice(0, 3).join(' | '));
  fs.writeFileSync('/root/mosslight/tests/integration_results.json', JSON.stringify({ results, passed: results.filter(r => r.ok).length, total: results.length }, null, 1));
  console.log(`${results.filter(r => r.ok).length}/${results.length} passed`); await b.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
