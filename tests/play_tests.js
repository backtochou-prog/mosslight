// MOSSlight exploration tests. Run:  python3 preview/serve.py 8768 &  NODE_PATH=<node_modules> node tests/play_tests.js
// Drives preview/play.html headlessly, checks movement/collision/depth/camera/interaction, writes tests/play_results.json + screenshots.
const { chromium } = require('playwright');
const fs = require('fs');
const PORT = process.env.PORT || 8768;
const results = [];
function check(name, ok, detail) { results.push({ name, ok: !!ok, detail }); console.log((ok ? 'PASS ' : 'FAIL ') + name + (detail ? '  — ' + detail : '')); }
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 2000, height: 1200 } });
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(`http://127.0.0.1:${PORT}/preview/play.html`);
  await p.waitForFunction(() => window.Player && window.SIM && document.getElementById('clock').textContent.includes(':'), { timeout: 30000 });
  await p.evaluate(() => { setPreset(1); WorldClock.paused = true; });
  const shot = async (name) => { await p.waitForTimeout(250); const c = await p.$('#c'); await c.screenshot({ path: `/root/mosslight/renders/play_${name}.png` }); };
  const at = (x, y) => p.evaluate(([x, y]) => Player.setPos(x, y), [x, y]);
  const pos = () => p.evaluate(() => [Player.x, Player.y]);
  // 1. eight directions + 2. diagonal normalisation (open meadow, 90 fixed steps = 1.5 s)
  const dirs = { E: [1, 0], W: [-1, 0], N: [0, -1], S: [0, 1], NE: [0.7071, -0.7071], NW: [-0.7071, -0.7071], SE: [0.7071, 0.7071], SW: [-0.7071, 0.7071] };
  const dist = {};
  for (const [k, ax] of Object.entries(dirs)) { await at(420, 300); await p.evaluate(a => SIM.step(a, 90), ax); const [x, y] = await pos(); dist[k] = Math.hypot(x - 420, y - 300); const sgn = Math.sign(x - 420) === Math.sign(ax[0]) && Math.sign(y - 300) === Math.sign(ax[1]); check(`moves ${k}`, dist[k] > 60 && sgn, `${dist[k].toFixed(1)} px`); }
  const card = (dist.E + dist.W + dist.N + dist.S) / 4, diag = (dist.NE + dist.NW + dist.SE + dist.SW) / 4;
  check('diagonal speed == cardinal speed', Math.abs(card - diag) < 1.5, `cardinal ${card.toFixed(1)} px, diagonal ${diag.toFixed(1)} px over 1.5 s`);
  // smooth stop: after releasing input the player stops within a few pixels
  await at(420, 300); await p.evaluate(() => { SIM.step([1, 0], 60); }); const [sx] = await pos(); await p.evaluate(() => SIM.step([0, 0], 30)); const [ex] = await pos();
  check('stops without sliding', ex - sx < 6 && ex - sx >= 0, `slid ${(ex - sx).toFixed(1)} px after release`);
  // 3. collision: big oak trunk at (216,206); pond; tent; ruin wall
  await at(180, 206); await p.evaluate(() => SIM.step([1, 0], 180)); let [x] = await pos(); check('blocked by oak trunk', x < 212 && x > 196, `stopped at x=${x.toFixed(1)} (trunk at 216)`);
  await at(500, 236); await p.evaluate(() => SIM.step([1, 0], 300)); [x] = await pos(); check('blocked by pond', x < 575 && x > 520, `stopped at x=${x.toFixed(1)} walking east into the pond (bank near 548)`);
  await at(272, 300); await p.evaluate(() => SIM.step([0, -1], 240)); let [, y] = await pos(); check('blocked by tent', y > 240 && y < 262, `stopped at y=${y.toFixed(1)} (tent base 244)`);
  await at(640, 150); await p.evaluate(() => SIM.step([0, -1], 240)); [, y] = await pos(); check('blocked by ruin wall', y > 92, `stopped at y=${y.toFixed(1)} (wall base 94)`);
  // walks onto the dock (walkable over water) and along the path through the junction
  await at(518, 274); await p.evaluate(() => SIM.step([1, 0], 180)); [x] = await pos(); check('dock is walkable (stops at the mooring post)', x > 565 && x < 585, `reached x=${x.toFixed(1)} on the deck`);
  await at(300, 318); await p.evaluate(() => { SIM.step([1, 0], 300); SIM.step([0.7071, -0.7071], 200); }); const [jx, jy] = await pos(); check('path junction traversable', jx > 430 && jy < 300, `ended at (${jx.toFixed(0)}, ${jy.toFixed(0)})`);
  // dense vegetation: the north path branch threads between edge trees to the ruin; a gap in the west forest edge
  await at(440, 300); await p.evaluate(() => { SIM.step([0.45, -0.89], 420); }); let [vx, vy] = await pos(); check('passes between edge trees on the ruin path', vy < 160 && vx > 540, `reached (${vx.toFixed(0)}, ${vy.toFixed(0)}) heading for the ruin`);
  await at(150, 262); await p.evaluate(() => SIM.step([-1, 0], 200)); [vx] = await pos(); check('walks between forest trunks, stops at the playable border (x=32)', vx >= 32 && vx < 44, `stopped at x=${vx.toFixed(0)}`);
  // phone aspect + safe inset: camera clamps still hold, HUD stays inside the inset
  await p.evaluate(() => { Camera.vw = 780; Camera.vh = 360; Camera.safe = 24; }); await at(740, 440); await p.evaluate(() => { for (let i = 0; i < 120; i++) Camera.update(1 / 60); }); let camp = await p.evaluate(() => [Camera.ix(), Camera.iy()]); check('19.5:9 phone viewport: view wider than this map clamps to 0 and is capped to the map width', camp[0] === 0 && camp[1] === 120, `camera at (${camp}) with 780 px view on a 768 px map`);
  await at(272, 262); await p.evaluate(() => { Touch.enabled = true; Interaction.update(0.016); }); await shot('phone_aspect_safe_inset'); await p.evaluate(() => { Touch.enabled = false; Camera.vw = 640; Camera.vh = 360; Camera.safe = 0; });
  // 4. depth sorting: behind the oak trunk vs in front; behind foreground canopy; in front of lily pads
  const vis = async () => p.evaluate(() => { const dep = DATA.depth.spring, pm = DATA.player, pidx = DATA.pidx; const fw = pm.frame_w, fh = pm.frame_h; const row = pm.facings.indexOf(Player.facing), col = Player.frame(); let tot = 0, shown = 0; const px0 = Math.round(Player.x) - pm.origin[0], py0 = Math.round(Player.y) - pm.origin[1];
    for (let yy = 0; yy < fh; yy++) for (let xx = 0; xx < fw; xx++) { const pi = pidx[(row * fh + yy) * (fw * pm.frames.length) + col * fw + xx]; if (!pi) continue; tot++; const i = (py0 + yy) * 768 + px0 + xx; if (dep[i] <= Math.round(Player.y)) shown++; } return shown / tot; });
  await at(222, 198); let v = await vis(); check('behind oak trunk: partially hidden', v > 0.2 && v < 0.9, `${(v * 100).toFixed(0)}% of player visible`); await shot('depth_behind_trunk');
  await at(222, 214); v = await vis(); check('in front of oak trunk: fully visible', v > 0.98, `${(v * 100).toFixed(0)}% visible`); await shot('depth_in_front_of_trunk');
  await at(130, 440); v = await vis(); check('behind foreground canopy: hidden', v < 0.6, `${(v * 100).toFixed(0)}% visible under the framing oak`);
  await at(224, 232); v = await vis(); check('under the oak canopy, in front of trunk base: visible', v > 0.9, `${(v * 100).toFixed(0)}%`);
  // 5. camera: follows, clamps at edges, integer offsets, no jump
  await at(60, 80); await p.evaluate(() => { for (let i = 0; i < 90; i++) Camera.update(1 / 60); }); let cam = await p.evaluate(() => [Camera.ix(), Camera.iy()]); check('camera clamps at the north-west edge', cam[0] === 0 && cam[1] === 16, `camera at (${cam})`);
  await at(740, 440); await p.evaluate(() => { for (let i = 0; i < 120; i++) Camera.update(1 / 60); }); cam = await p.evaluate(() => [Camera.ix(), Camera.iy()]); check('camera clamps at the south-east edge', cam[0] === 128 && cam[1] === 120, `camera at (${cam})`);
  await at(400, 300); await p.evaluate(() => { for (let i = 0; i < 120; i++) Camera.update(1 / 60); }); const c0 = await p.evaluate(() => [Camera.x, Camera.y]);
  await p.evaluate(() => { SIM.step([1, 0], 1); Camera.update(1 / 60); }); const c1 = await p.evaluate(() => [Camera.x, Camera.y]); check('camera moves smoothly (no jump on a 1-px player step)', Math.hypot(c1[0] - c0[0], c1[1] - c0[1]) < 2, `moved ${Math.hypot(c1[0] - c0[0], c1[1] - c0[1]).toFixed(2)} px`);
  // 6. interaction prompts + range
  await at(272, 262); await p.evaluate(() => Interaction.update(0.016)); let cur = await p.evaluate(() => Interaction.current && Interaction.current.label); check('prompt near tent', cur === 'Rest until morning', `prompt: ${cur}`); await shot('prompt_tent');
  await at(400, 330); await p.evaluate(() => Interaction.update(0.016)); cur = await p.evaluate(() => Interaction.current); check('no prompt in the open meadow', cur === null);
  await at(246, 268); await p.evaluate(() => { Interaction.update(0.016); Input.actionPressed = true; Interaction.update(0.016); Input.actionPressed = false; Input._actionLatch = false; }); const msg = await p.evaluate(() => Interaction.message); check('interact shows the object text', !!msg && msg.includes('lantern'), msg); await shot('message_lantern');
  for (const [id, x, y] of [['dock', 566, 296], ['ruin', 612, 118], ['lantern', 246, 268], ['campfire', 300, 280], ['log', 480, 412]]) { await at(x, y); await p.evaluate(() => Interaction.update(0.016)); cur = await p.evaluate(() => Interaction.current && Interaction.current.id); check(`prompt: ${id}`, cur === id, `got ${cur}`); }
  // 7. visibility day / night
  await at(262, 286); await p.evaluate(() => { setPreset(1); WorldClock.paused = true; }); await shot('day_at_camp');
  await p.evaluate(() => { setPreset(9); WorldClock.paused = true; }); await at(262, 286); await shot('night_at_camp');
  await p.evaluate(() => { setPreset(7); WorldClock.paused = true; }); await at(262, 286); await shot('winter_night_at_camp');
  // 8. touch input produces the same axis as keys
  await p.evaluate(() => { Input.touch = { active: true, ax: 100, ay: 100, x: 140, y: 100, id: 1 }; }); const axT = await p.evaluate(() => Input.axis()); await p.evaluate(() => { Input.touch.active = false; Input.keys['d'] = true; }); const axK = await p.evaluate(() => Input.axis()); await p.evaluate(() => { Input.keys['d'] = false; });
  check('touch joystick and keyboard give the same action vector', Math.abs(axT[0] - axK[0]) < 0.01 && Math.abs(axT[1] - axK[1]) < 0.01, `touch ${axT.map(v => v.toFixed(2))} keys ${axK.map(v => v.toFixed(2))}`);
  await p.evaluate(() => { Touch.enabled = true; }); await at(300, 318); await shot('touch_controls');
  // frame cost
  await p.evaluate(() => { Touch.enabled = false; setPreset(1); WorldClock.paused = false; });
  const ms = await p.evaluate(() => new Promise(r => { let n = 0, t0 = performance.now(); function f() { n++; if (n < 60) requestAnimationFrame(f); else r((performance.now() - t0) / 60); } requestAnimationFrame(f); }));
  check('frame cost (software Chromium, 640x360 at 3x)', ms < 60, `${ms.toFixed(1)} ms/frame`);
  check('no page errors', errs.length === 0, errs.join(' | '));
  fs.writeFileSync('/root/mosslight/tests/play_results.json', JSON.stringify({ results, passed: results.filter(r => r.ok).length, total: results.length }, null, 1));
  console.log(`${results.filter(r => r.ok).length}/${results.length} passed`);
  await b.close();
})().catch(e => { console.error('ERR', e.message); process.exit(1); });
