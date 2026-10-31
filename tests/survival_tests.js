// Survival clock tests. Run: python3 preview/serve.py 8769 &  NODE_PATH=<nm> PORT=8769 node tests/survival_tests.js
const { chromium } = require('playwright'); const fs = require('fs');
const PORT = process.env.PORT || 8769; const results = [];
function check(name, ok, detail) { results.push({ name, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? '  — ' + detail : '')); }
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 2000, height: 1200 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(`http://127.0.0.1:${PORT}/preview/play.html?dev=1`);
  await p.waitForFunction(() => window.Survival && window.Player && window.SIM && Survival.cfg(), { timeout: 30000 });
  const ev = (f, a) => p.evaluate(f, a);
  const shot = async (n) => { await p.waitForTimeout(300); const c = await p.$('#c'); await c.screenshot({ path: `/root/mosslight/renders/survival_${n}.png` }); };
  await ev(() => { setPreset(1); WorldClock.paused = true; SeasonState.season = 'spring'; Survival.Clock.setHour(9); Survival.Energy.set(100); });
  // 1. clock drives everything: advance 1h / 6h changes the palette table; day increments once at midnight
  const tabAt = () => ev(() => { const t = tableAt(SeasonState.season, WorldClock.hour()); return [WorldClock.hour(), t.table[10].join(','), t.darkness]; });
  const t0 = await tabAt(); await ev(() => Survival.Clock.advance(60)); const t1 = await tabAt(); await ev(() => Survival.Clock.advance(360)); const t2 = await tabAt();
  check('advance +1h / +6h moves the clock and the lighting table', Math.abs(t1[0] - t0[0] - 1) < 0.01 && Math.abs(t2[0] - t1[0] - 6) < 0.01 && t2[1] !== t0[1], `${t0[0]}→${t1[0]}→${t2[0]} h; darkness ${t0[2].toFixed(2)}→${t2[2].toFixed(2)}`);
  await ev(() => { Survival.Clock.day = 1; Survival.Clock.setHour(23.5); }); await ev(() => Survival.Clock.advance(60)); let d = await ev(() => [Survival.Clock.day, WorldClock.hour()]); check('day increments exactly once crossing midnight', d[0] === 2 && Math.abs(d[1] - 0.5) < 0.01, `day ${d[0]} at ${d[1].toFixed(2)} h`);
  await ev(() => Survival.Clock.advance(60)); d = await ev(() => Survival.Clock.day); check('no double increment after midnight', d === 2);
  // phases + seasonal shift
  const ph = async (h, s) => ev(([h, s]) => Survival.Clock.phase(h, s), [h, s]);
  check('spring phases: 06 dawn, 12 day, 18 sunset, 20 early night, 23 deep night, 05:30 dawn transition', (await ph(6.5, 'spring')) === 'dawn' && (await ph(12, 'spring')) === 'day' && (await ph(18, 'spring')) === 'sunset' && (await ph(20, 'spring')) === 'early_night' && (await ph(23, 'spring')) === 'deep_night' && (await ph(5.5, 'spring')) === 'dawn_transition');
  const scW = await ev(() => Survival.Clock.schedule('winter')), scS = await ev(() => Survival.Clock.schedule('summer'));
  check('schedule shifts per season (winter dawn later, summer night later)', scW.dawn > 7 && scS.early_night > 19.5 && scS.early_night > scW.early_night, `winter dawn ${scW.dawn.toFixed(1)}, summer early night ${scS.early_night.toFixed(1)}`);
  check('danger is 0 by day and 1 in deep night', (await ev(() => { Survival.Clock.setHour(12); return Survival.Clock.danger(); })) === 0 && (await ev(() => { Survival.Clock.setHour(23); return Survival.Clock.danger(); })) === 1);
  // 2. energy: activity costs from config, states, passive walking drain
  await ev(() => { Survival.Clock.setHour(10); Survival.Energy.set(100); });
  const cfg = await ev(() => Survival.cfg());
  let r = await ev(() => Survival.Activities.perform('gather_stones')); let e = await ev(() => [Survival.Energy.current, WorldClock.hour()]);
  check('gather stones costs configured energy and minutes', r.ok && e[0] === 100 - cfg.activities.gather_stones.energy && Math.abs(e[1] - (10 + cfg.activities.gather_stones.minutes / 60)) < 0.02, `energy ${e[0]}, clock ${e[1].toFixed(2)} h`);
  r = await ev(() => Survival.Activities.perform('cut_tree')); e = await ev(() => Survival.Energy.current); check('cut tree costs 8 energy', r.ok && e === 100 - 3 - 8, `energy ${e}`);
  const states = await ev(() => [80, 60, 30, 10, 0].map(v => Survival.Energy.stateFor(v))); check('states at 80/60/30/10/0', states.join(',') === 'energetic,tired,exhausted,critical,zero', states.join(','));
  await ev(() => { Survival.Energy.set(100); Survival.Energy._walkAcc = 0; }); await ev(() => { for (let i = 0; i < 120; i++) Survival.tick(1 / 60, 60 / 120, true); }); e = await ev(() => Survival.Energy.current);   // one game hour of walking
  check('walking drains ~1 energy per game hour', e === 99, `energy ${e} after 60 game minutes moving`);
  await ev(() => { Survival.Energy.set(100); for (let i = 0; i < 120; i++) Survival.tick(1 / 60, 60 / 120, false); }); e = await ev(() => Survival.Energy.current); check('standing still drains nothing', e === 100);
  // 3. exhaustion: heavy refused at critical and at zero, light allowed, movement still works at zero
  await ev(() => Survival.Energy.set(10)); r = await ev(() => Survival.Activities.perform('cut_tree')); check('heavy activity refused when critical', !r.ok, r.reason);
  r = await ev(() => Survival.Activities.perform('gather_branches')); check('light activity allowed when critical', r.ok);
  await ev(() => Survival.Energy.set(0)); r = await ev(() => Survival.Activities.perform('gather_branches')); check('activities with a cost refused at zero energy', !r.ok, r.reason);
  r = await ev(() => Survival.Activities.perform('inspect')); check('zero-cost inspect still allowed at zero energy', r.ok);
  await ev(() => Player.setPos(420, 300)); await ev(() => SIM.step([1, 0], 60)); const px = await ev(() => Player.x); check('player can still walk at zero energy', px > 440, `moved to x=${px.toFixed(0)}`);
  await ev(() => Survival.Energy.set(30)); r = await ev(() => Survival.Activities.perform('cut_tree')); check('heavy allowed when exhausted (config allow_heavy_when_exhausted) with reduced efficiency', r.ok && r.efficiency === 0.6, `efficiency ${r.efficiency}`);
  await shot('critical_energy');
  // 4. time vs energy independence: enough energy, no daylight → works, logged after dark
  await ev(() => { Survival.Energy.set(100); Survival.Clock.setHour(22.5); }); r = await ev(() => Survival.Activities.perform('fish_attempt')); const rec = await ev(() => Survival.Record.cur);
  check('night fishing allowed with energy and logged after dark', r.ok && r.night && rec.minutesAfterDark >= 10, `afterDark ${rec.minutesAfterDark} min`);
  // 5. sleep before midnight → next day's dawn once; after midnight → same calendar day's dawn once; double trigger guarded
  await ev(() => { Survival.Clock.day = 3; Survival.Clock.setHour(23); Survival.Energy.set(20); Survival.Record.start(3, 'spring'); });
  let ok1 = await ev(() => Survival.Sleep.start({ instant: true })); let w = await ev(() => [Survival.Clock.day, WorldClock.hour(), Survival.Energy.current, Survival.Sleep.lastSummary]);
  check('sleep at 23:00 day 3 → day 4 at dawn, energy full', ok1 && w[0] === 4 && Math.abs(w[1] - 6) < 0.01 && w[2] === 100, `day ${w[0]} ${w[1]} h energy ${w[2]}`);
  check('journal summary built only from recorded fields', typeof w[3] === 'string' && w[3].includes('Day 3') && !w[3].includes('undefined') && !w[3].includes('NaN'), w[3]);
  let ok2 = await ev(() => Survival.Sleep.start({ instant: true })); check('second sleep within cooldown is ignored', ok2 === false);
  await p.waitForTimeout(1700);
  await ev(() => { Survival.Clock.day = 5; Survival.Clock.setHour(1.5); Survival.Energy.set(40); }); await ev(() => Survival.Sleep.start({ instant: true })); w = await ev(() => [Survival.Clock.day, WorldClock.hour(), Survival.Energy.current]);
  check('sleep at 01:30 day 5 → dawn of day 5 (same calendar day), energy full (before 02:00)', w[0] === 5 && Math.abs(w[1] - 6) < 0.01 && w[2] === 100, `day ${w[0]} ${w[1]} h energy ${w[2]}`);
  await p.waitForTimeout(1700);
  await ev(() => { Survival.Clock.day = 6; Survival.Clock.setHour(3.5); Survival.Energy.set(40); }); await ev(() => Survival.Sleep.start({ instant: true })); w = await ev(() => [Survival.Clock.day, WorldClock.hour(), Survival.Energy.current]);
  check('sleep at 03:30 → short night, energy restored to 80 not 100', w[0] === 6 && w[2] === cfg.sleep.short_night_restore, `energy ${w[2]}`);
  await p.waitForTimeout(1700);
  // animated sleep via the tent interaction: fade out, apply, fade in; movement blocked while sleeping
  await ev(() => { Survival.Clock.day = 7; Survival.Clock.setHour(21); Player.setPos(272, 262); WorldClock.paused = false; Interaction.update(0.016); Input.actionPressed = true; Interaction.update(0.016); Input.actionPressed = false; Input._actionLatch = false; });
  await p.waitForTimeout(500); const mid = await ev(() => [Survival.Sleep.sleeping, Survival.Sleep.fade]); await shot('sleep_fade'); await p.waitForTimeout(2800); const after = await ev(() => [Survival.Sleep.sleeping, Survival.Clock.day, WorldClock.hour(), Survival.Sleep.fade]);
  check('tent interaction sleeps with a fade and wakes on day 8 at dawn', mid[0] && mid[1] > 0.2 && !after[0] && after[1] === 8 && after[2] < 6.3 && after[3] === 0, `mid fade ${mid[1].toFixed(2)}, after: day ${after[1]} ${after[2].toFixed(2)} h`);
  await shot('journal_morning');
  await ev(() => { WorldClock.paused = true; });
  // 6. phase events across sunset → night; season change shifts schedule
  const got = await ev(() => { const seen = []; Survival.on('phase', (ph) => seen.push(ph)); Survival.Clock.setHour(16.5); Survival.Clock.advance(360); return seen; });
  check('phase events fire crossing sunset → early night → deep night', got.includes('sunset') && got.includes('early_night') && got.includes('deep_night'), got.join('>'));
  await ev(() => { SeasonState.season = 'winter'; }); const pw = await ev(() => Survival.Clock.phase(7.0)); await ev(() => { SeasonState.season = 'spring'; }); check('changing season changes the phase at the same hour (07:00 winter is still dawn transition/dawn)', pw !== 'day', `winter 07:00 = ${pw}`);
  // 7. save / load at 03:00 and 15:00: restores day/time/energy, no duplicate day increment
  for (const h of [3, 15]) { await ev(h => { Survival.Clock.day = 9; Survival.Clock.setHour(h); Survival.Energy.set(42); Survival.SaveState.save(); Survival.Clock.day = 1; Survival.Clock.setHour(12); Survival.Energy.set(100); }, h);
    const s = await ev(() => { Survival.SaveState.load(); return [Survival.Clock.day, WorldClock.hour(), Survival.Energy.current]; }); await ev(() => Survival.Clock.advance(30)); const s2 = await ev(() => Survival.Clock.day);
    check(`save/load at ${String(h).padStart(2, '0')}:00 restores day 9, time, energy 42 without a duplicate reset`, s[0] === 9 && Math.abs(s[1] - h) < 0.01 && s[2] === 42 && s2 === 9, `loaded day ${s[0]} ${s[1]} h energy ${s[2]}; +30min → day ${s2}`); }
  // 8. HUD screenshots at 16:9 and 19.5:9 with safe inset, day / sunset / night
  await ev(() => { Survival.Energy.set(100); Player.setPos(300, 318); });
  for (const [n, h] of [['hud_day', 10], ['hud_sunset', 18.4], ['hud_night', 23]]) { await ev(h => Survival.Clock.setHour(h), h); await shot(n); }
  await ev(() => { Camera.vw = 780; Camera.vh = 360; Camera.safe = 24; Touch.enabled = true; Survival.Clock.setHour(10); }); await shot('hud_phone_safe'); await ev(() => { Camera.vw = 640; Camera.vh = 360; Camera.safe = 0; Touch.enabled = false; });
  check('no page errors', errs.length === 0, errs.join(' | '));
  fs.writeFileSync('/root/mosslight/tests/survival_results.json', JSON.stringify({ results, passed: results.filter(r => r.ok).length, total: results.length }, null, 1));
  console.log(`${results.filter(r => r.ok).length}/${results.length} passed`); await b.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
