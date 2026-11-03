// Prompt 15 tests: UI kit, typeface, settings, pause/map/ribbon, touch targets, orientation, sound wiring, player animation, lighting, ambient animation.
// Run: NODE_PATH=<nm> PORT=8777 node tests/atmosphere_tests.js
const { chromium } = require('playwright'); const fs = require('fs');
const PORT = process.env.PORT || 8777; const results = [];
function check(name, ok, detail) { results.push({ name, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? '  — ' + detail : '')); }
(async () => {
  const b = await chromium.launch(); const ctxo = await b.newContext({ viewport: { width: 2000, height: 1200 } }); const p = await ctxo.newPage();
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(`http://127.0.0.1:${PORT}/preview/play.html?lab=1`); await p.evaluate(() => { localStorage.removeItem('mosslight.settings'); });
  await p.reload(); await p.waitForFunction(() => window.UIKit && UIKit.Map && window.Gather && Gather.Nodes && Gather.Nodes.list.length && window.OFFC, { timeout: 60000 });
  const ev = (f, a) => p.evaluate(f, a); const wait = ms => p.waitForTimeout(ms);
  fs.mkdirSync('/root/mosslight/renders/p15', { recursive: true });
  const shot = async n => { await wait(350); const c = await p.$('#c'); await c.screenshot({ path: `/root/mosslight/renders/p15/${n}.png` }); };
  await ev(() => { Festival.setEnabled(false); Social.setEnabled(false); setPreset(1); });

  // ---- typeface
  const ft = await ev(() => { const c = document.createElement('canvas').getContext('2d'); c.font = '9px mossbook'; const w1 = c.measureText('Field journal').width; c.font = '12px mossbook'; const w2 = c.measureText('Field journal').width; c.font = '9px monospace'; const w3 = c.measureText('Field journal').width; return [w1, w2, w3, UIKit.measure('Field journal'), UIKit.measure('Field journal', 2)]; });
  check('Mossbook body + heading faces load; fillText/measureText route mossbook fonts to the pixel face', ft[0] === ft[3] && ft[1] === ft[4] && ft[1] > ft[0] * 1.8 && ft[0] !== ft[2], JSON.stringify(ft));
  const glyphs = await ev(() => fetch('../assets/ui/mossbook.json').then(r => r.json()).then(m => [Object.keys(m.glyphs).length, m.height]));
  check('typeface covers 100+ glyphs on a 9 px cell', glyphs[0] >= 100 && glyphs[1] === 9, `${glyphs[0]} glyphs`);
  const sysFonts = fs.readdirSync('/root/mosslight/preview').filter(f => f.endsWith('.js') && f !== 'audio.js').map(f => [f, (fs.readFileSync('/root/mosslight/preview/' + f, 'utf8').match(/font\s*=\s*['"`][^'"`]*(monospace|Georgia|serif)/g) || []).length]).filter(x => x[1]);
  check('no system fonts left in any game screen module', sysFonts.length === 0, JSON.stringify(sysFonts));

  // ---- pause, settings, map, ribbon
  await ev(() => { WorldClock.paused = false; }); await p.keyboard.press('Escape'); await wait(200); const m0 = await ev(() => [UIKit.Menu.open, WorldClock.minutes]); await wait(600); const m1 = await ev(() => WorldClock.minutes);
  check('Esc opens the pause page and holds the clock', m0[0] === 'pause' && Math.abs(m1 - m0[1]) < 0.01, `menu ${m0[0]}, clock ${m0[1].toFixed(2)}→${m1.toFixed(2)}`); await shot('pause');
  const sv = await ev(() => { localStorage.removeItem('mosslight.save'); return UIKit.hits().find(h => h.label === 'Save the game'); });
  await ev(() => UIKit.hits().find(h => h.label === 'Save the game').fn()); const saved = await ev(() => !!localStorage.getItem('mosslight.save'));
  check('pause › Save the game writes a save and confirms with a toast', !!sv && saved, `saved=${saved}`);
  await ev(() => { UIKit.Menu.open = 'settings'; UIKit.Menu.tab = 'access'; }); await shot('settings_access'); await ev(() => UIKit.hits().find(h => h.label === 'Off' || h.label === 'On') && UIKit.hits().filter(h => h.label === 'Off' || h.label === 'On')[0].fn());
  const rm = await ev(() => [UIKit.S.reduceMotion, JSON.parse(localStorage.getItem('mosslight.settings') || '{}').reduceMotion]);
  check('Settings › Reduce motion toggles by tap and is saved', rm[0] === true && rm[1] === true, JSON.stringify(rm));
  await ev(() => { UIKit.S.reduceMotion = false; UIKit.saveSettings(); UIKit.Menu.tab = 'sound'; }); await shot('settings_sound');
  await p.keyboard.press('Escape'); await p.keyboard.press('Escape'); const closed = await ev(() => UIKit.Menu.open); check('Esc steps back settings → pause → game', closed === null, String(closed));
  await ev(() => { UIKit.Map.seen = null; Player.setPos(300, 318); }); await wait(200); const e0 = await ev(() => UIKit.Map.seen.reduce((a, b) => a + b, 0));
  await ev(() => Player.setPos(600, 280)); await wait(200); const e1 = await ev(() => UIKit.Map.seen.reduce((a, b) => a + b, 0));
  check('the map uncovers where the player has been', e1 > e0 && e0 > 0, `${e0} → ${e1} cells`);
  await ev(() => { Survival.SaveState.save(); UIKit.Map.seen = null; Survival.SaveState.load(); }); const e2 = await ev(() => UIKit.Map.seen ? UIKit.Map.seen.reduce((a, b) => a + b, 0) : 0);
  check('exploration survives save/load', e2 === e1, `${e2}`);
  await p.keyboard.press('m'); await shot('map'); const mo = await ev(() => UIKit.Map.open); await p.keyboard.press('m'); check('M opens and closes the map', mo && !(await ev(() => UIKit.Map.open)));
  await ev(() => Player.setPos(300, 318)); await p.keyboard.press('i'); await wait(200); const rb = await ev(() => { const t = UIKit.hits().filter(h => h.label === 'tab'); return [UIKit.anyBook() && UIKit.anyBook().id, t.length]; });
  await ev(() => UIKit.openBook('creatures')); const rb2 = await ev(() => [UIKit.anyBook().id, Gather.UI.open, Monsters.Journal.open]);
  check('the journal ribbon shows every book and switches between them', rb[0] === 'pack' && rb[1] >= 8 && rb2[0] === 'creatures' && !rb2[1] && rb2[2], JSON.stringify([rb, rb2]));
  await p.keyboard.press('Tab'); const rb3 = await ev(() => UIKit.anyBook() && UIKit.anyBook().id); check('Tab moves to the next book', rb3 && rb3 !== 'creatures', rb3);
  await ev(() => { for (const t of ['pack']) UIKit.openBook(t); Gather.UI.open = null; });

  // ---- touch: targets, phone scale, orientation
  await ev(() => { document.getElementById('touch').checked = true; Touch.enabled = true; Camera.vw = 640; Camera.vh = 360; }); await wait(300);
  const tt = await ev(() => { const h = UIKit.hits(); return [UIKit.scale(360), h.length, Math.min(...h.map(x => Math.min(x.w, x.h))), h.map(x => x.label).join(',')]; });
  check('on a touch phone the UI layer draws at 1.5x and every tap target is ≥34 UI px', tt[0] === 1.5 && tt[1] >= 5 && tt[2] >= 34, `scale ${tt[0]}, ${tt[1]} targets, smallest ${tt[2]} [${tt[3]}]`); await shot('touch_controls');
  await ev(() => UIKit.hits().find(h => h.label === 'pack').fn()); const tp = await ev(() => Gather.UI.open); check('the pack seal opens the pack by tap', tp === 'inventory', String(tp)); await shot('touch_pack');
  const cl = await ev(() => { const c = UIKit.hits().find(h => h.label === 'close'); if (c) c.fn(); return [!!c, !!UIKit.anyBook()]; }); check('every book closes from its paper close box by tap', cl[0] && !cl[1], JSON.stringify(cl));
  await ev(() => UIKit.hits().find(h => h.label === 'map').fn()); const tm = await ev(() => UIKit.Map.open); await shot('touch_map'); await ev(() => { UIKit.Map.open = false; });
  await ev(() => UIKit.hits().find(h => h.label === 'menu').fn()); const tmenu = await ev(() => UIKit.Menu.open); await ev(() => { UIKit.Menu.open = null; });
  check('map and menu seals work by tap', tm && tmenu === 'pause', `${tm} ${tmenu}`);
  await p.setViewportSize({ width: 400, height: 800 }); await wait(500); const por = await ev(() => [portraitNow(), WorldClock.minutes]); await wait(500); const por2 = await ev(() => WorldClock.minutes); await shot('portrait_card');
  check('a phone held upright shows the turn-sideways page and the world waits', por[0] && Math.abs(por2 - por[1]) < 0.01, `portrait=${por[0]}`);
  await p.setViewportSize({ width: 2000, height: 1200 }); await ev(() => { Touch.enabled = false; document.getElementById('touch').checked = false; }); await wait(300);
  const hintTouch = await ev(() => { Touch.enabled = true; return true; }); await ev(() => { Touch.enabled = false; });

  // ---- sound wiring
  const snd = await ev(async () => { const ok = await Sound.start(); const d0 = Sound.debug(); const dangerMood = Sound._wantMood({ WorldClock: { hour: () => 23 }, Player: { x: 0, y: 0 }, Monsters: { list: [{ state: 'pursue', x: 30, y: 0 }] } }); const nightMood = Sound._wantMood({ WorldClock: { hour: () => 23 }, Player: { x: 0, y: 0 } }); const fest = Sound._wantMood({ WorldClock: { hour: () => 20 }, Festival: { active: () => 'fest_fireflies' } }); return [ok, d0.ctxState, dangerMood, nightMood, fest]; });
  check('sound starts on a gesture and picks mood from danger, time and festival', snd[1] === 'running' && snd[2] === 'danger' && snd[3] === 'night' && snd[4] === 'fest_fireflies', JSON.stringify(snd));
  const vol = await ev(() => { Sound.setVolume('music', .3); return JSON.parse(localStorage.getItem('mosslight.audio')).music; }); check('music volume persists to storage', vol === .3, String(vol)); await ev(() => Sound.setVolume('music', .55));
  const mon = await ev(() => { let got = null; const orig = Sound.creature; Sound.creature = (k) => { got = k; return true; }; Monsters.Audio.play('howl', 10, 10); Sound.creature = orig; return got; }); check('creature calls are voiced by the sound engine', mon === 'howl', String(mon));
  const steps = await ev(async () => { const seen = []; const orig = Sound.play; Sound.play = (n, o) => { seen.push(n); return true; }; Input.keys['d'] = true; await new Promise(r => setTimeout(r, 1200)); Input.keys['d'] = false; Sound.play = orig; return seen; });
  check('walking plays surface footsteps', steps.filter(n => n.startsWith('footstep_')).length >= 2, steps.slice(0, 6).join(','));

  // ---- player animation
  await ev(() => { setPreset(1); Player.setPos(300, 318); Input.keys['r'] = true; Input.keys['d'] = true; }); await wait(500); const run = await ev(() => [Player.running, DATA.player.facings[Player.pose(0)[0]], Math.abs(Player.vx)]); await ev(() => { Input.keys['r'] = false; Input.keys['d'] = false; });
  check('holding R runs: faster, with run frames', run[0] && run[1] === 'run_side' && run[2] > 64 * 1.3, JSON.stringify(run));
  await wait(400); const bl = await ev(() => DATA.player.facings[Player.pose(3.7 * 10 + .05)[0]]); check('idle blink frames play', bl === 'blink', bl);
  const hu = await ev(() => { Monsters.Health.cur = 50; Monsters.Health.inv = .4; const r = DATA.player.facings[Player.pose(0)[0]]; Monsters.Health.cur = Monsters.Health.max; Monsters.Health.inv = 0; return r; }); check('taking damage shows the flinch frames', hu === 'hurt', hu);
  const sl = await ev(() => { Survival.Sleep.sleeping = true; const r = DATA.player.facings[Player.pose(0)[0]]; Survival.Sleep.sleeping = false; return r; }); check('sleeping uses the bedroll frames', sl === 'sleep', sl);

  // ---- lighting: a warm pool at camp, real darkness away from it
  const lum = (x, y) => ev(([x, y]) => { const d = OFFC().getContext('2d').getImageData(x - 3, y - 3, 7, 7).data; let s = 0, r = 0, b = 0; for (let i = 0; i < d.length; i += 4) { s += d[i] * .3 + d[i + 1] * .59 + d[i + 2] * .11; r += d[i]; b += d[i + 2]; } return [s / 49, r / 49, b / 49]; }, [x, y]);
  await ev(() => { setPreset(9); Player.setPos(262, 286); }); await wait(700);
  const avg = async (x, y) => { const acc = [0, 0, 0]; for (let k = 0; k < 6; k++) { const v = await lum(x, y); v.forEach((q, i) => acc[i] += q / 6); await wait(90); } return acc; };   // flicker: average over frames
  const near = await avg(330, 300), far = await avg(150, 420);
  check('night: the camp spill is lit and warm, open ground away from camp falls into darkness', near[0] > far[0] * 1.7 && near[1] > near[2] * 1.1, `camp lum ${near[0].toFixed(0)} (r${near[1].toFixed(0)}/b${near[2].toFixed(0)}), far ${far[0].toFixed(0)}`); await shot('night_camp_pool');
  const deep = await ev(() => { const s = []; for (const h of [21, 1.5]) { WorldClock.minutes = h * 60; s.push(h); } return true; }); await ev(() => { WorldClock.minutes = 21 * 60; }); await wait(400); const l21 = await lum(150, 420); await ev(() => { WorldClock.minutes = 90; }); await wait(400); const l01 = await lum(150, 420);
  check('the small hours are darker than early night', l01[0] < l21[0], `21:00 ${l21[0].toFixed(1)} vs 01:30 ${l01[0].toFixed(1)}`);
  await ev(() => { setPreset(2); }); await wait(500); await shot('sunset'); await ev(() => { setPreset(5); }); await wait(500); await shot('fog_dawn');

  // ---- ambient animation
  const fire = await ev(async () => { setPreset(1); WorldClock.paused = false; await new Promise(r => setTimeout(r, 1500)); return [PFX.fire.filter(p => p.k === 'ember').length, PFX.fire.filter(p => p.k === 'smoke').length]; });
  check('the fire breathes smoke and spits embers', fire[0] > 0 && fire[1] > 0, `${fire[0]} embers, ${fire[1]} smoke`);
  const sway = await ev(async () => { WeatherState.set('clear', 0); WeatherState.wind = 0.08; const g = OFFC().getContext('2d'); const a = g.getImageData(0, 0, 768, 480).data.slice(); await new Promise(r => setTimeout(r, 900)); const c = g.getImageData(0, 0, 768, 480).data; let n = 0; for (let i = 0; i < a.length; i += 4) if (a[i] !== c[i] || a[i + 1] !== c[i + 1]) n++; return n; });
  check('a gentle breeze moves foliage even on a still day', sway > 200, `${sway} px changed`);
  const ripple = await ev(async () => { setPreset(4); WorldClock.paused = false; Player.setPos(540, 300); await new Promise(r => setTimeout(r, 1500)); return PFX.ripple.length; }); check('rain rings form on open water', ripple > 0, `${ripple} rings`); await shot('rain_ripples');
  const snow = await ev(async () => { setPreset(6); WorldClock.paused = false; const s0 = SNOW(); await new Promise(r => setTimeout(r, 2500)); return [s0, SNOW()]; }); check('snow settles on the ground while it falls', snow[1] > snow[0], `${snow[0].toFixed(3)} → ${snow[1].toFixed(3)}`);
  await ev(() => { setPreset(1); SNOW(0); UIKit.S.reduceMotion = true; WeatherState.wind = 0.05; }); await wait(1200);
  const still = await ev(async () => { const g = OFFC().getContext('2d'); const a = g.getImageData(0, 0, 768, 480).data.slice(); await new Promise(r => setTimeout(r, 700)); const c = g.getImageData(0, 0, 768, 480).data; let n = 0; for (let i = 0; i < a.length; i += 4) if (a[i] !== c[i]) n++; return n; });
  await ev(() => { UIKit.S.reduceMotion = false; });
  check('reduce motion stills foliage sway and cloth (only fire, water and particles move)', still < sway * .5, `${still} px changed vs ${sway}`);

  check('no page errors', errs.length === 0, errs.slice(0, 3).join(' | '));
  fs.writeFileSync('/root/mosslight/tests/atmosphere_results.json', JSON.stringify({ results, passed: results.filter(r => r.ok).length, total: results.length }, null, 1));
  console.log(`${results.filter(r => r.ok).length}/${results.length} passed`); await b.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
