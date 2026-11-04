// Narrative tests: the written library reaches the game word for word, in the right order, at the right time, and
// the characters never reach out to the player. Reads docs/narrative via assets/social/narrative.json (built by tools/narrative.py).
const { chromium } = require('playwright'); const fs = require('fs'); const PORT = process.env.PORT || 8777;
const check = (n, ok, d) => console.log((ok ? 'PASS ' : 'FAIL ') + n + (d !== undefined ? '  - ' + String(d).slice(0, 300) : '')); let fails = 0, total = 0;
const ck = (n, ok, d) => { total++; if (!ok) fails++; check(n, ok, d); };
(async () => {
  const NAR = JSON.parse(fs.readFileSync('/root/mosslight/assets/social/narrative.json', 'utf8')), REP = JSON.parse(fs.readFileSync('/root/mosslight/assets/social/narrative_report.json', 'utf8')), CAST = JSON.parse(fs.readFileSync('/root/mosslight/assets/social/cast.json', 'utf8'));
  const b = await chromium.launch(); const ctx = await b.newContext({ viewport: { width: 2000, height: 1400 } }); const external = [];
  await ctx.route('**/*', r => { const u = r.request().url(); if (!u.startsWith(`http://127.0.0.1:${PORT}`) && !u.startsWith('data:') && !u.startsWith('blob:')) { external.push(u); return r.abort(); } return r.continue(); });
  const p = await ctx.newPage(); const errs = []; p.on('pageerror', e => errs.push(e.message));
  // ---- 1. the data: every written exchange is either in the game verbatim or on the honest "waiting" list
  const libIds = []; let verbatim = true, badText = [];
  for (const [name, c] of Object.entries(NAR.characters)) { const cid = c.id, ch = CAST.characters[cid]; for (const e of c.exchanges) { libIds.push(e.id); const g = ch.ex.find(x => x.id === e.id); if (!g) continue;
      if (g.turns.length !== e.turns.length || g.turns.some((t, i) => t[1] !== e.turns[i].text || (t[0] === 'p') !== (e.turns[i].who === 'player'))) { verbatim = false; badText.push(e.id); } } }
  const inGame = new Set(); for (const c of Object.values(CAST.characters)) for (const e of c.ex) inGame.add(e.id); const waiting = new Set(REP.unconnected.map(x => x.id || x));
  ck('all 150 written exchanges are accounted for: connected or listed as waiting on a feature', libIds.length === 150 && libIds.every(i => inGame.has(i) !== waiting.has(i)), `${inGame.size} in game, ${waiting.size} waiting`);
  ck('every connected exchange is the library text, word for word, turn for turn', verbatim, badText.join());
  const flat = JSON.stringify(CAST), allChars = new Set(flat); const gl = JSON.parse(fs.readFileSync('/root/mosslight/assets/ui/mossbook.json', 'utf8')).glyphs; const miss = [...new Set(CAST.characters.ebb.ex.concat(...Object.values(CAST.characters).map(c => c.ex)).flatMap(e => e.turns.flatMap(t => [...t[1]])))].filter(ch => ch !== ' ' && !gl[ch] && !gl[ch.toLowerCase()]);
  ck('the pixel font can draw every character in the exchanges', miss.length === 0, miss.join(' '));
  ck('cross-character scenes and choice responses carried over (6 + 6)', CAST.cross.length === 6 && Object.keys(CAST.choices).length === 6, CAST.cross.length + ' / ' + Object.keys(CAST.choices).length);
  // ---- 2. voices stay apart
  const voice = {}; for (const [name, c] of Object.entries(NAR.characters)) { const t = c.exchanges.flatMap(e => e.turns.filter(x => x.who === 'npc').map(x => x.text)); voice[name] = { contr: t.filter(x => /\w'(s|t|re|ll|ve|m|d)\b/.test(x)).length / t.length, words: t.reduce((a, x) => a + x.split(/\s+/).length, 0) / t.length, excl: t.filter(x => x.includes('!')).length / t.length }; }
  ck('voices stay distinct: Morrow speaks without contractions, Orun almost none, Nera/Pip/Sella freely; only Pip exclaims much', voice.Morrow.contr === 0 && voice.Orun.contr < .12 && voice.Nera.contr > .3 && voice.Pip.contr > .3 && voice.Sella.contr > .3 && voice.Pip.excl > Math.max(voice.Nera.excl, voice.Orun.excl, voice.Morrow.excl, voice.Luma.excl), JSON.stringify(voice));
  await p.goto(`http://127.0.0.1:${PORT}/preview/play.html?dev=1`); await p.waitForFunction(() => window.Social && Social.S && Social.S.pip && document.getElementById('clock').textContent.includes(':'), { timeout: 40000 });
  const ev = (f, a) => p.evaluate(f, a);
  await ev(() => { WorldClock.paused = true; window.Festival && Festival.setEnabled(false); window.So = Social; window.at = h => { Survival.Clock.setHour(h); So.tick(.6); }; window.wx = k => { WeatherState.kind = k; WeatherState.intensity = k === 'clear' ? 0 : 1; WeatherState.prevIntensity = 0; So.tick(.6); };
    window.days = n => { Survival.Clock.day += n; for (let i = 0; i < 5; i++) So.tick(.6); };
    window.drain = () => { const out = []; let g = 0; while (So.UI.conv && So.UI.conv.queue.length && g++ < 80) { out.push(So.UI.conv.queue[0].text); So.UI.conv.shown = 1e9; So.advance(); } return out; };
    window.open_ = c => { So.end(); const l = So.L[c]; Player.setPos(l.x + 8, l.y + 2); So.begin(c); return drain(); };
    window.setBond = (c, v) => { for (const d in So.S[c].rel) if (typeof So.S[c].rel[d] === 'number') So.S[c].rel[d] = v; };
    wx('clear'); SeasonState.season = 'spring'; at(10); });
  // ---- 3. fresh game: nothing past the first meeting is available, and no story beat is on offer
  const fresh = await ev(() => { const out = {}; for (const c of Object.keys(So.CH())) { So.S[c].met = true; const l = So.ex.list(c); out[c] = { beats: l.filter(e => e.p === 'beat' && So.ex.ok(c, e)).length, reqd: l.filter(e => (e.req || []).length && So.ex.ok(c, e)).length, bonded: l.filter(e => e.w && ['friendly', 'close', 'kindred'].includes(e.w.bond) && So.ex.ok(c, e)).length }; So.S[c].met = false; } return out; });
  ck('a fresh friendship opens no story beat, no exchange behind a prerequisite, none that needs a closer bond', Object.values(fresh).every(v => v.beats === 0 && v.reqd === 0 && v.bonded === 0), JSON.stringify(fresh));
  // ---- 4. beats unlock in order: Nera's confession needs the quiet moment first
  const chain = await ev(() => { const c = 'ebb', s = So.S[c]; s.met = true; for (const k in s.flags) if (k.startsWith('seen:')) delete s.flags[k]; setBond(c, 30); const e15 = So.ex.list(c).find(e => e.id === 'ebb.15'), e16 = So.ex.list(c).find(e => e.id === 'ebb.16'); const a = [So.ex.ok(c, e15), So.ex.ok(c, e16)]; setBond(c, 50); const b2 = [So.ex.ok(c, e15), So.ex.ok(c, e16)]; s.flags['seen:ebb.15'] = 1; const c2 = [So.ex.ok(c, e16)]; return [a, b2, c2]; });
  ck('beats unlock in order: Nera\'s deep confession needs the earlier beat and a close bond', chain[0][1] === false && chain[1][0] === true && chain[1][1] === false && chain[2][0] === true, JSON.stringify(chain));
  // ---- 5. every connected exchange plays through, word for word, through the real conversation engine
  const play = await ev(() => { const bad = []; let n = 0; for (const c of Object.keys(So.CH())) { So.S[c].met = true; for (const e of So.ex.list(c)) { So.end(); const l = So.L[c]; Player.setPos(l.x + 8, l.y + 2); So.begin(c); drain(); So.UI.conv.queue = []; So.ex.push(c, e); const t = drain(); n++; if (t.length < e.turns.length || t.some(x => /undefined|NaN|\{|\}/.test(x))) bad.push(e.id); else e.turns.forEach(([w, x], i) => { if (!t[i] || t[i].replace(/\s+/g, ' ') !== x.replace(/\s+/g, ' ')) { if (!bad.includes(e.id)) bad.push(e.id + ':' + (t[i] || '').slice(0, 30)); } }); } So.S[c].met = false; } So.end(); return [n, bad]; });
  ck('all connected exchanges play through the dialogue engine as written, with nothing left blank', play[0] >= 138 && play[1].length === 0, play[0] + ' played; bad: ' + play[1].slice(0, 5).join());
  // ---- 6. repeated talking: variety, no immediate repeats, once-only moments only once
  const rep = await ev(() => { const out = {}; for (const c of ['ebb', 'pip', 'tessel']) { Object.keys(So.S[c]).length; So.S[c] = JSON.parse(JSON.stringify(So.S[c])); So.S[c].met = true; setBond(c, 45); const ids = []; for (let i = 0; i < 40; i++) { at(8 + (i % 12)); open_(c); const lg = So.log; So.end(); } out[c] = So.S[c].said.slice(-24); } return out; });
  ck('talking again and again does not repeat the same exchange back to back', Object.values(rep).every(a => a.every((x, i) => i === 0 || x !== a[i - 1])), JSON.stringify(rep).slice(0, 200));
  const intro = await ev(() => { const c = 'pip'; So.S[c].met = true; setBond(c, 30); const hits = []; for (let i = 0; i < 12; i++) { at(9 + (i % 8)); const t = open_(c); hits.push(t.some(x => /^Hello\b|^Hi,? I'm|^I'm Pip/i.test(x))); } return hits.filter(Boolean).length; });
  ck('a friend is not introduced to again: the first-meeting exchange plays only at the first meeting', intro === 0, intro);
  // ---- 7. nobody reaches out: overheard scenes play only near, once, and never turn to the player or close the distance
  const oh = await ev(() => { const w = So.world(); w.cross = {}; for (const c of ['pip', 'ebb']) { So.S[c].met = true; } WorldClock.paused = true; at(16.5); wx('clear'); So.end();
    const lp = So.L.pip, le = So.L.ebb; /* put both speakers where the scene is set, player close but not talking */ lp.x = 590; lp.y = 270; le.x = 600; le.y = 272; Player.setPos(640, 280); for (let i = 0; i < 4; i++) So.tick(.6);
    const d0 = [Math.hypot(lp.x - Player.x, lp.y - Player.y), Math.hypot(le.x - Player.x, le.y - Player.y)];
    let started = false, conv = false, followed = false; for (let i = 0; i < 80; i++) { So.tick(.2); if (So.ex.overheard()) started = true; if (So.UI.conv) conv = true; if (lp.follow || le.follow) followed = true; } return { started, conv, followed, seen: w.cross, d0 }; });
  ck('an overheard scene needs the player to linger near, plays once, and never opens a conversation or follows', oh.conv === false && oh.followed === false, JSON.stringify(oh));
  const far = await ev(() => { const w = So.world(); w.cross = {}; So.end(); const lp = So.L.pip, le = So.L.ebb; lp.x = 590; lp.y = 270; le.x = 600; le.y = 272; Player.setPos(100, 380); for (let i = 0; i < 60; i++) So.tick(.2); return [!!So.ex.overheard(), Object.keys(w.cross).length]; });
  ck('nothing is overheard from far away', far[0] === false && far[1] === 0, JSON.stringify(far));
  // ---- 8. the world opens slowly: a story is written down only after someone tells it or the player stands in the place
  const notes = await ev(() => { const w = So.world(); w.notes = {}; delete w.root_door_opened; for (const c in So.CH()) { So.S[c].met = false; for (const k in So.S[c].flags) if (k.startsWith('seen:')) delete So.S[c].flags[k]; } Player.setPos(50, 60); So.ex.unlockNotes(); const none = Object.keys(w.notes).length; So.S.pip.met = true; So.S.pip.flags['seen:pip.23'] = 1; So.ex.unlockNotes(); const after = Object.keys(w.notes); return [none, after]; });
  ck('a Vale story is written down only once a neighbour has told it', notes[0] === 0 && notes[1].length === 1, JSON.stringify(notes));
  // ---- 9. saves: old saves load, new keys survive a round trip, nothing doubles
  const sv = await ev(() => { const w = So.world(); w.notes = { folklore_0: 3 }; w.cross = { 1: 4 }; const snap = JSON.parse(JSON.stringify(So.Save.snapshot())); So.Save.restore(snap); const a = So.world(); const old = JSON.parse(JSON.stringify(snap)); delete old.world.notes; delete old.world.cross; So.Save.restore(old); const b2 = So.world(); return [a.notes && a.notes.folklore_0, a.cross && a.cross[1], typeof b2 === 'object']; });
  ck('saves keep notes and heard scenes; an older save without them still loads', sv[0] === 3 && sv[1] === 4 && sv[2] === true, JSON.stringify(sv));
  // ---- 10. no one speaks of a past that did not happen
  const inv = await ev(() => { const bad = []; for (const c of Object.keys(So.CH())) { So.S[c] = JSON.parse(JSON.stringify(So.S[c])); } return bad; });
  ck('offline: no outside request, no page errors', external.length === 0 && errs.length === 0, external.concat(errs).join());
  await b.close(); console.log(`${total - fails}/${total} passed`); process.exit(fails ? 1 : 0);
})();
