// MOSSlight survival clock: energy, exhaustion, activities, sleep, day record, HUD, save, dev tools.
// Uses the existing WorldClock as the ONLY time source (wraps its tick; never a second clock).
// Mirrors godot/survival/*.gd. Config: assets/survival/config.json.
window.Survival = (() => {
  let CFG = null, W = null;            // W = { WorldClock, SeasonState, Player, Interaction, DATA, keyframes }
  const listeners = {};
  const on = (ev, cb) => (listeners[ev] = listeners[ev] || []).push(cb);
  const emit = (ev, ...a) => (listeners[ev] || []).forEach(cb => cb(...a));

  // ---------------- Clock extensions: day counter, phases shifted per season, advance()
  const Clock = {
    day: 1, lastHour: -1, lastPhase: null,
    hour() { return W.WorldClock.hour(); },
    schedule(season) {
      // base schedule is authored for the reference season; other seasons slide dawn-side and night-side
      // hours by the difference in that season's dawn / night keyframe hours.
      const s = CFG.schedule, ref = W.keyframes[s.reference_season].hours, kf = W.keyframes[season || W.SeasonState.season].hours;
      const dDawn = kf[0] - ref[0], dNight = kf[5] - ref[5];
      return { dawn_transition: s.dawn_transition + dDawn, dawn: s.dawn + dDawn, day: s.day + dDawn, sunset: s.sunset + dNight, early_night: s.early_night + dNight, deep_night: s.deep_night + dNight };
    },
    phase(h = this.hour(), season) {
      const sc = this.schedule(season);
      if (h >= sc.deep_night || h < sc.dawn_transition) return 'deep_night';
      if (h < sc.dawn) return 'dawn_transition';
      if (h < sc.day) return 'dawn';
      if (h < sc.sunset) return 'day';
      if (h < sc.early_night) return 'sunset';
      return 'early_night';
    },
    danger() { return CFG.danger[this.phase()] || 0; },
    isNight() { return ['early_night', 'deep_night'].includes(this.phase()); },
    afterTick(prevMinutes) {
      const m = W.WorldClock.minutes;
      if (m < prevMinutes - 1) { this.day += 1; emit('day', this.day); Record.onMidnight(); }
      const h = Math.floor(m / 60); if (h !== this.lastHour) { this.lastHour = h; emit('hour', h); }
      const ph = this.phase(); if (ph !== this.lastPhase) { const prev = this.lastPhase; this.lastPhase = ph; emit('phase', ph, prev); }
    },
    advance(minutes) {            // same path as real time so lighting/weather/day rollover stay consistent
      const step = 15; let left = minutes;
      while (left > 0) { const d = Math.min(step, left); const prev = W.WorldClock.minutes; W.WorldClock.minutes = (W.WorldClock.minutes + d) % 1440; this.afterTick(prev); Record.minutes(d); left -= d; }
    },
    setHour(h) { const prev = W.WorldClock.minutes; W.WorldClock.minutes = ((h * 60) % 1440 + 1440) % 1440; this.lastHour = -1; this.afterTick(Math.min(prev, W.WorldClock.minutes)); },
  };

  // ---------------- Energy
  const Energy = {
    max: 100, current: 100, state: 'energetic', _walkAcc: 0,
    stateFor(v) { for (const [name, min] of CFG.energy.states) if (v >= min) return v <= 0 ? 'zero' : name; return 'zero'; },
    _update() { const s = this.stateFor(this.current); if (s !== this.state) { const prev = this.state; this.state = s; emit('energy_state', s, prev); } emit('energy', this.current); },
    spend(amount, reason) { const a = Math.min(this.current, amount); this.current -= a; Record.energy(a, reason); this._update(); return a; },
    restore(amount) { this.current = Math.min(this.max, this.current + amount); this._update(); },
    set(v) { this.current = Math.max(0, Math.min(this.max, v)); this._update(); },
    efficiency() { return CFG.energy.efficiency[this.state]; },
    canDo(act) { if (!act.heavy) return this.current > 0 || act.energy === 0; if (this.current <= 0) return false;
      if (this.state === 'critical' && !CFG.energy.allow_heavy_when_critical) return false;
      if (this.state === 'exhausted' && !CFG.energy.allow_heavy_when_exhausted) return false; return this.current >= act.energy * 0.5; },
    tickMovement(gameMinutes, moving) { if (!moving || !CFG.energy.walk_per_game_hour) return; this._walkAcc += gameMinutes / 60 * CFG.energy.walk_per_game_hour; if (this._walkAcc >= 0.999) { const n = Math.max(1, Math.floor(this._walkAcc + 0.001)); this._walkAcc -= n; this.spend(n, 'walking'); } },
  };

  // ---------------- Activities (registry from config; perform = check, spend, advance time, log, animate)
  const Activities = {
    queue: [], current: null,
    get(id) { return Object.assign({ id }, CFG.activities[id]); },
    perform(id, source) {
      const act = this.get(id); if (!act.label) return { ok: false, reason: 'unknown' };
      if (!Energy.canDo(act)) return { ok: false, reason: Energy.current <= 0 ? 'You are too exhausted for that. Rest first.' : 'You are too tired for heavy work right now.' };
      const night = Clock.isNight();
      Energy.spend(act.energy, id); Clock.advance(act.minutes);
      Record.activity(id, act, night);
      this.current = { id, anim: act.anim, t: 0, dur: Math.min(1.6, 0.4 + act.minutes / 30) };
      emit('activity', id, act, source); return { ok: true, act, night, efficiency: Energy.efficiency() };
    },
    performCustom(id, act, source) {      // same path as perform(), for costs defined outside the activity table (crafting, construction)
      if (!Energy.canDo(act)) return { ok: false, reason: Energy.current <= 0 ? 'You are too exhausted for that. Rest first.' : 'You are too tired for heavy work right now.' };
      const night = Clock.isNight();
      Energy.spend(act.energy, id); Clock.advance(act.minutes); Record.activity(id, Object.assign({ label: act.label || id }, act), night);
      if (act.anim) this.current = { id, anim: act.anim, t: 0, dur: Math.min(1.2, 0.4 + act.minutes / 60) };
      emit('activity', id, act, source); return { ok: true, act, night, efficiency: Energy.efficiency() };
    },
    enqueue(id, source) { this.queue.push({ id, source }); },       // prepared for future action queues
    tick(dt) { if (this.current) { this.current.t += dt; if (this.current.t >= this.current.dur) this.current = null; } },
  };

  // ---------------- Day record + journal
  const Record = {
    days: [], cur: null,
    start(day, season) { this.cur = { day, season, activities: {}, energySpent: 0, energyBy: {}, minutesAwake: 0, minutesAfterDark: 0, minutesMoving: 0, returnedBeforeDark: null, sleptAt: null, count: 0 }; },
    activity(id, act, night) { const c = this.cur; c.activities[id] = (c.activities[id] || 0) + 1; c.count += 1; if (night) c.minutesAfterDark += act.minutes; },
    energy(a, reason) { const c = this.cur; c.energySpent += a; c.energyBy[reason] = (c.energyBy[reason] || 0) + a; },
    minutes(m) { const c = this.cur; c.minutesAwake += m; if (Clock.isNight()) c.minutesAfterDark += m; },
    moving(m) { this.cur.minutesMoving += m; },
    onMidnight() { /* calendar day changes; the record closes only on sleep */ },
    close(sleptHour) { const c = this.cur; c.sleptAt = sleptHour; c.returnedBeforeDark = !Clock.isNight(); this.days.push(c); return c; },
    summary(c) {   // only from fields that hold data; reads as a journal line, never a dashboard
      const lines = [`Day ${c.day}, ${c.season}.`];
      const names = Object.keys(c.activities);
      if (c.count) lines.push(names.map(id => `${c.activities[id]}× ${(CFG.activities[id] || {}).label || id.replace(/^(craft|build):/, '').replace(/_/g, ' ')}`.toLowerCase()).join(', ') + '.');
      else lines.push('A quiet day of walking and looking.');
      const hAwake = Math.round(c.minutesAwake / 60);
      if (hAwake) lines.push(`About ${hAwake} hour${hAwake > 1 ? 's' : ''} outside` + (c.minutesAfterDark >= 30 ? `, ${Math.round(c.minutesAfterDark / 60 * 10) / 10} of them after dark.` : '.'));
      if (c.energySpent) lines.push(`Spent ${Math.round(c.energySpent)} energy.`);
      lines.push(c.returnedBeforeDark ? 'Home before dark.' : 'Back late, by lantern light.');
      return lines.join(' ');
    },
  };

  // ---------------- Sleep (reusable for future beds / houses)
  const Sleep = {
    sleeping: false, fade: 0, _cool: 0, lastSummary: null, summaryT: 0, _phase: null,
    canSleep() { return !this.sleeping && this._cool <= 0; },
    start(opts = {}) {
      if (!this.canSleep()) return false;
      this.sleeping = true; this._phase = 'out'; this._cool = CFG.sleep.cooldown_seconds; emit('sleep_start');
      this._apply = () => {
        const sleptHour = Clock.hour();
        const rec = Record.close(sleptHour);
        const season = W.SeasonState.season;
        const wake = Clock.schedule(season).dawn;                   // wake at this season's dawn
        // next morning exactly once, whether we sleep before or after midnight
        const m = W.WorldClock.minutes, wakeM = wake * 60;
        if (m >= wakeM) { W.WorldClock.minutes = wakeM; Clock.day += 1; emit('day', Clock.day); } else { W.WorldClock.minutes = wakeM; }
        Clock.lastHour = -1; Clock.lastPhase = null; Clock.afterTick(W.WorldClock.minutes);
        const full = (sleptHour >= CFG.sleep.full_restore_before_hour + 12 || sleptHour < CFG.sleep.full_restore_before_hour);   // before ~02:00 (incl. evening) = full night
        const B = window.Build && Build.homeBonus ? Build.homeBonus() : {}, home = !!(window.Build && Build.sheltered && Build.sheltered(W.Player.x, W.Player.y));   // your own room: always a full night, and a bed of your own adds to the morning
        Energy.max = CFG.energy.max + (home ? (B.maxEnergy || 0) : 0); const rested = full || (home && B.fullRest);
        Energy.set(rested ? Energy.max : Math.min(Energy.max, Math.max(Energy.current, CFG.sleep.short_night_restore)));
        Energy._walkAcc = 0;
        Record.start(Clock.day, season);
        Weather.apply(true); this.lastSummary = Record.summary(rec) + ` Today: ${Weather.forecast(Clock.day)}.`; this.summaryT = 7.0; emit('wake', Clock.day, rec);
      };
      if (opts.instant) { this._apply(); this.sleeping = false; this.fade = 0; this._phase = null; }
      return true;
    },
    tick(dt) {
      if (this._cool > 0) this._cool -= dt;
      if (this.summaryT > 0) this.summaryT -= dt;
      if (!this.sleeping) return;
      const spd = 1 / CFG.sleep.fade_seconds;
      if (this._phase === 'out') { this.fade = Math.min(1, this.fade + dt * spd); if (this.fade >= 1) { this._apply(); this._phase = 'hold'; this._hold = 0.6; } }
      else if (this._phase === 'hold') { this._hold -= dt; if (this._hold <= 0) this._phase = 'in'; }
      else if (this._phase === 'in') { this.fade = Math.max(0, this.fade - dt * spd); if (this.fade <= 0) { this.sleeping = false; this._phase = null; emit('sleep_end'); } }
    },
  };

  // ---------------- Save / restore (prepared for the future save system; one store, versioned)
  const SaveState = {
    KEY: 'mosslight.save', VERSION: 2, problems: [], lastSource: null, lastSaved: null,
    // v2 envelope: { app, v, sum, len, body }. The body is the game snapshot as JSON; sum is FNV-1a over the body, so a torn or edited save is caught.
    sum(str) { let h = 0x811c9dc5; for (let i = 0; i < str.length; i++) { h ^= str.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return h.toString(16); },
    snapshot() { const P = W.Player, WS = window.WeatherState || {}; return { version: this.VERSION, day: Clock.day, season: W.SeasonState.season, minutes: W.WorldClock.minutes, energy: Energy.current, maxEnergy: Energy.max, sleeping: false, record: Record.cur, days: Record.days,
      player: P ? { x: Math.round(P.x * 10) / 10, y: Math.round(P.y * 10) / 10, facing: P.facing, flip: !!P.flip } : null, weather: { kind: WS.kind || 'clear', intensity: WS.intensity || 0, target: WS.target || 0, wind: WS.wind || 0, plan: Weather.snapshot() } }; },
    // read the best save there is: the main slot, else the backup, else the half-written temp; older plain saves are migrated
    read() { this.problems = []; const tryKey = k => { const raw = (() => { try { return localStorage.getItem(k); } catch (_) { return null; } })(); if (!raw) return null; try { const o = JSON.parse(raw);
        if (o && o.app === 'mosslight' && typeof o.body === 'string') { if (o.body.length !== o.len || this.sum(o.body) !== o.sum) { this.problems.push(k + ': checksum mismatch'); return null; } return this.migrate(JSON.parse(o.body)); }
        if (o && typeof o === 'object' && o.day && o.minutes !== undefined) return this.migrate(o); this.problems.push(k + ': not a save'); return null; } catch (e) { this.problems.push(k + ': unreadable (' + e.message + ')'); return null; } };
      for (const k of [this.KEY, this.KEY + '.bak', this.KEY + '.tmp']) { const s = tryKey(k); if (s) { this.lastSource = k; return s; } } this.lastSource = null; return null; },
    migrate(s) { if (!s.version || s.version < 2) { s.version = 2; if (!s.player) s.player = null; if (!s.weather) s.weather = null; } return s; },
    exists() { return !!this.read(); },
    save() { const s = this.snapshot(); s.savedAt = Date.now(); let body; try { body = JSON.stringify(s); JSON.parse(body); } catch (e) { this.problems = ['could not serialise: ' + e.message]; return null; }
      const env = JSON.stringify({ app: 'mosslight', v: this.VERSION, sum: this.sum(body), len: body.length, body });
      try { localStorage.setItem(this.KEY + '.tmp', env); const prev = localStorage.getItem(this.KEY); if (prev && prev !== env) localStorage.setItem(this.KEY + '.bak', prev); localStorage.setItem(this.KEY, env); localStorage.removeItem(this.KEY + '.tmp'); }
      catch (e) { this.problems = ['storage refused the save (' + (e.name || e.message) + ')']; return null; }
      this.lastSaved = s.savedAt; emit('saved', s); return s; },
    guard(name, fn) { try { fn(); return true; } catch (e) { this.problems.push(name + ' could not be restored: ' + e.message); console.warn('[save]', name, e); return false; } },
    load(s) { s = s || this.read(); if (!s) return false;
      if (s.app === 'mosslight' && typeof s.body === 'string') { try { s = this.migrate(JSON.parse(s.body)); } catch (_) { return false; } }          // handed a raw envelope
      if (!isFinite(s.day) || !isFinite(s.minutes)) { this.problems.push('save has no day or time'); return false; }
      if (!['spring', 'summer', 'autumn', 'winter'].includes(s.season)) s.season = 'spring'; if (!isFinite(s.energy)) s.energy = CFG.energy.max;
      Clock.day = s.day; W.SeasonState.season = s.season; W.WorldClock.minutes = s.minutes; Energy.max = s.maxEnergy || CFG.energy.max; Energy.set(s.energy);
      Record.cur = s.record || Record.cur; Record.days = s.days || []; Sleep.sleeping = false; Sleep.fade = 0;
      Clock.lastHour = Math.floor(s.minutes / 60); Clock.lastPhase = Clock.phase();   // no duplicate day/phase events on load
      if (s.player && W.Player && W.Player.setPos && isFinite(s.player.x) && isFinite(s.player.y)) { W.Player.setPos(s.player.x, s.player.y); if (W.Player.blocked && W.Player.blocked(s.player.x, s.player.y) && W.DATA) { const sp = W.DATA.play.spawn; W.Player.setPos(sp[0], sp[1]); } W.Player.facing = s.player.facing || 'down'; W.Player.flip = !!s.player.flip; }
      if (s.weather && window.WeatherState) { const WS = window.WeatherState; WS.kind = s.weather.kind; WS.intensity = s.weather.intensity; WS.target = s.weather.target; WS.prevIntensity = 0; WS.wind = s.weather.wind || 0; Weather.restore(s.weather.plan); Weather.setKind = WS.kind; }
      emit('load', s); return true; },
  };

  // ---------------- HUD (native resolution, cozy: parchment text on a soft dark card; energy as a segmented bar)
  const HUD = {
    col: { energetic: '#4c6a28', tired: '#8a7a1a', exhausted: '#a8601a', critical: '#9a2e16', zero: '#6a5a4c' },
    lowT: 0, hp: null, hurtT: 0,
    // one journal slip, top-left: the day line, then energy and health rows; state is said in words as well as colour
    draw(g, vw, vh, safe, T) { const K = window.UIKit; if (!K) return; const C = K.C; const x0 = 6 + safe, y0 = 6 + safe;
      const h = Clock.hour(), ph = Clock.phase(), night = Clock.isNight() || ph === 'dawn_transition'; const M = window.Monsters, H = M && M.Health;
      const season = W.SeasonState.season, day = `Day ${Clock.day}`, time = W.WorldClock.label(); const seasonName = season[0].toUpperCase() + season.slice(1);
      const wk = (window.WeatherState || {}).kind || 'clear'; const wg = { light_rain: 'rain', heavy_rain: 'rain', snow: 'snow', fog: 'fog', wind: 'wind' }[wk];
      const tw = 132, th = H ? 29 : 18; const mood = { energetic: 'rested', tired: 'tired', exhausted: 'worn out', critical: 'spent', zero: 'empty' }[Energy.state];
      /* the date and time have their own slip, top right (clear of the menu button on a phone); vitals stay top left */
      const cw = 122, cx0 = vw - safe - cw - (K.touch() ? 40 : 6), cy0 = y0, ink = night ? '#3a4a7a' : C.gold;
      K.tag(g, cx0, cy0, cw, 29); K.glyph(g, night ? 'moon' : 'sun', cx0 + 4, cy0 + 3, ink); K.text(g, time, cx0 + 14, cy0 + 9, { bold: true }); K.text(g, `${day} · ${seasonName}`, cx0 + 14, cy0 + 21, { color: C.ink2 }); if (wg) K.glyph(g, wg, cx0 + cw - 12, cy0 + 3, C.water);
      const sc = Clock.schedule(); const u = Math.max(0, Math.min(1, (h - sc.dawn) / (sc.early_night - sc.dawn))); g.fillStyle = 'rgba(58,42,26,.25)'; g.fillRect(cx0 + 52, cy0 + 6, cw - 66, 1); g.fillStyle = ink; g.fillRect(cx0 + 52 + Math.round((cw - 68) * (night ? 1 : u)), cy0 + 4, 2, 5);
      K.tag(g, x0, y0, tw, th);
      /* music button under the clock: tap to mute or bring back the music (effects and ambience stay) */
      { const A = window.Sound; if (A && A.setMusicMuted) { const off = !!A.settings.musicMuted, bw = K.touch() ? 30 : 22, bh = K.touch() ? 24 : 18, bx = cx0 + cw - bw, by = cy0 + 33;
          K.tag(g, bx, by, bw, bh); K.glyph(g, 'note', bx + Math.round((bw - 5) / 2), by + Math.round((bh - 7) / 2), off ? C.faint : C.ink);
          if (off) { g.fillStyle = C.rust; for (let i = 0; i < 9; i++) g.fillRect(bx + Math.round((bw - 9) / 2) + i, by + Math.round((bh - 9) / 2) + 8 - i, 1, 1); }
          K.hit(bx, by, bw, bh, () => A.setMusicMuted(!A.settings.musicMuted), 'music'); } }
      const row = (yy, glyph, gcol, v, max, col, label, low) => { K.glyph(g, glyph, x0 + 4, yy - 1, gcol); K.bar(g, x0 + 14, yy + 1, 60, 4, v / max, { color: col, low }); K.text(g, String(Math.round(v)), x0 + 78, yy + 6, { color: C.ink }); K.text(g, label, x0 + 96, yy + 6, { color: C.ink2 }); };
      const frac = Energy.current / Energy.max; const pulse = (Energy.state === 'critical' || Energy.state === 'zero') && !K.S.reduceMotion ? (Math.sin(T * 3) > 0 ? 1 : .55) : 1;
      g.globalAlpha = pulse; row(y0 + 6, 'leaf', this.col[Energy.state] || C.ink2, Energy.current, Energy.max, this.col[Energy.state] || this.col.zero, mood, .4); g.globalAlpha = 1;
      if (H) { if (this.hp !== null && H.cur < this.hp) this.hurtT = .45; this.hp = H.cur; if (this.hurtT > 0) this.hurtT -= 1 / 60; const sh = this.hurtT > 0 && !K.S.reduceMotion ? Math.round(Math.sin(T * 60)) : 0; const hf = H.cur / H.max;
        g.save(); g.translate(sh, 0); row(y0 + 17, 'heart', '#9a2e16', H.cur, H.max, hf > .35 ? '#9a2e16' : '#c23a1a', hf > .7 ? 'well' : hf > .35 ? 'hurt' : 'badly hurt', .35); g.restore();
        let bx = x0 + tw + 4; const badge = (gl, lab) => { K.tag(g, bx, y0, 16, 14); K.glyph(g, gl, bx + 5, y0 + 3, C.ink); bx += 20; }; if (H.lantern) badge('lantern'); if (H.sneak) badge('sneak'); if (window.Build && Build.sheltered && Build.sheltered(W.Player.x, W.Player.y)) badge('shelter'); }
      // low energy: a calm reminder once per state change, never a flash
      if (Energy.state !== this._lastState) { if (this._lastState && (Energy.state === 'exhausted' || Energy.state === 'critical' || Energy.state === 'zero')) K.note(Energy.state === 'exhausted' ? 'You are worn out. Heavy work will be refused until you rest.' : 'You are running on nothing. Find the tent and sleep.', 4); this._lastState = Energy.state; }
      if (Energy.state === 'critical' || Energy.state === 'zero') { const gr = g.createRadialGradient(vw / 2, vh / 2, vh * 0.45, vw / 2, vh / 2, vh * 0.85); gr.addColorStop(0, 'rgba(10,8,12,0)'); gr.addColorStop(1, 'rgba(10,8,12,0.32)'); g.fillStyle = gr; g.fillRect(0, 0, vw, vh); }
      // sleep: the screen dims to night, then the morning page of the journal
      if (Sleep.fade > 0) { g.fillStyle = `rgba(8,6,4,${Sleep.fade})`; g.fillRect(0, 0, vw, vh); if (Sleep.fade > 0.95) { K.glyph(g, 'moon', vw / 2 - 3, vh / 2 - 12, '#c8b88a', 1); K.text(g, 'Sleeping', vw / 2, vh / 2 + 6, { align: 'center', color: '#c8b88a' }); } }
      if (Sleep.summaryT > 0 && Sleep.lastSummary && !Sleep.sleeping) { const alpha = Math.min(1, Sleep.summaryT); g.globalAlpha = alpha; const cw = Math.min(vw - 30, 280); const ls = K.lines(Sleep.lastSummary, cw - 24); const ch = 34 + ls.length * 10, cx = Math.round(vw / 2 - cw / 2), cy = y0 + th + 18;
        K.paper(g, cx, cy, cw, ch, { rule: false }); K.text(g, `Morning, day ${Clock.day}`, cx + 12, cy + 16, { face: 2 }); ls.forEach((l, i) => K.text(g, l, cx + 12, cy + 28 + i * 10)); g.globalAlpha = 1; }
    },
  };

  // ---------------- Weather: a plan for each day, so rain, fog and snow come and go on their own
  // Five blocks a day, each likely to keep the last one's sky; fog only in the morning; snow only in winter. Seeded, so a
  // loaded save sees the same skies. Outside winter there is rain at least every third day, so rain-only finds never stall.
  // Anything that sets the weather by hand (the dev menu, a preset, a test) holds it until the next morning.
  const Weather = { enabled: true, seed: 0, lastRainDay: 0, setKind: null, hold: false, holdDay: 0,
    BLOCKS: [0, 6, 10, 15, 20],
    ODDS: { spring: { clear: .47, light_rain: .28, heavy_rain: .07, fog: .12, wind: .06 }, summer: { clear: .64, light_rain: .14, heavy_rain: .1, fog: .04, wind: .08 },
      autumn: { clear: .36, light_rain: .26, heavy_rain: .12, fog: .16, wind: .1 }, winter: { clear: .42, snow: .4, fog: .1, wind: .08 } },
    rng(day, k) { let a = (this.seed * 2654435761 + day * 40503 + k * 9973) >>> 0; a ^= a << 13; a >>>= 0; a ^= a >> 17; a ^= a << 5; return ((a >>> 0) % 100000) / 100000; },
    plan(day, season) { season = season || W.SeasonState.season; const odds = this.ODDS[season] || this.ODDS.spring; const out = []; let prev = null;
      if (day <= 1) return this.BLOCKS.map(h => ({ h, kind: 'clear', i: 0 }));                       // a gentle first day
      this.BLOCKS.forEach((h, k) => { let kind;
        if (prev && this.rng(day, k * 7 + 1) < .62) kind = prev; else { let r = this.rng(day, k * 7 + 2), acc = 0; kind = 'clear'; for (const [w, p] of Object.entries(odds)) { acc += p; if (r < acc) { kind = w; break; } } }
        if (kind === 'fog' && h >= 10 && !(h >= 20 && (season === 'spring' || season === 'autumn'))) kind = 'clear'; /* morning fog, and evening mist over spring and autumn nights */ prev = kind; out.push({ h, kind, i: kind === 'clear' ? 0 : .45 + this.rng(day, k * 7 + 3) * .45 }); });
      const rainy = out.some(b => b.kind === 'light_rain' || b.kind === 'heavy_rain');
      const fest = this.festivalOn(day);
      if (season !== 'winter' && !rainy && day - this.lastRainDay >= 3) { if (fest) out[1] = { h: 6, kind: 'light_rain', i: .5 }; else out[3] = { h: 15, kind: 'light_rain', i: .55 }; }
      if (fest) for (const b of out) if (b.h >= 15) { b.kind = 'clear'; b.i = 0; }          // festivals were made for clear evenings: the sky keeps the date
      return out; },
    festivalOn(day) { try { const F = window.Festival; if (!F || !F.data || !F.data()) return null; const D = F.data(), C = F.Cal; for (const k in D.festivals) { const f = D.festivals[k]; if (C.seasonOf(day) === f.season && C.dos(day) === f.day) return k; } } catch (_) {} return null; },
    blockAt(hour, day) { const p = this.plan(day || Clock.day); let b = p[0]; for (const x of p) if (hour >= x.h) b = x; return b; },
    forecast(day) { const p = this.plan(day); const words = { clear: 'clear', light_rain: 'showers', heavy_rain: 'heavy rain', fog: 'morning fog', snow: 'snow', wind: 'wind' }; const parts = []; const when = ['night', 'early morning', 'late morning', 'afternoon', 'evening'];
      p.forEach((b, k) => { if (b.kind !== 'clear' && k > 0 && (k === 1 || p[k - 1].kind !== b.kind)) parts.push(`${words[b.kind]} in the ${when[k]}`); }); const f = this.festivalOn(day); const sky = parts.length ? parts.join(', then ') : 'clear skies all day'; return f ? sky + '; clear for the festival tonight' : sky; },
    apply(force) { const WS = window.WeatherState; if (!this.enabled || !WS) return;
      if (this.hold) { if (Clock.day === this.holdDay && !force) return; this.hold = false; }          // a hand-picked sky lasts the rest of that day
      else if (this.setKind && WS.kind !== this.setKind && !force) { this.hold = true; this.holdDay = Clock.day; return; }   // someone chose the weather by hand
      const b = this.blockAt(Clock.hour());
      if (WS.kind !== b.kind || Math.abs(WS.target - b.i) > .05) WS.set(b.kind, b.i); this.setKind = b.kind; if (b.kind === 'light_rain' || b.kind === 'heavy_rain') this.lastRainDay = Clock.day; },
    snapshot() { return { seed: this.seed, lastRainDay: this.lastRainDay, hold: this.hold, holdDay: this.holdDay, setKind: this.setKind }; },
    restore(o) { if (!o) return; Object.assign(this, { seed: o.seed || 0, lastRainDay: o.lastRainDay || 0, hold: !!o.hold, holdDay: o.holdDay || 0, setKind: o.setKind || null }); } };

  // ---------------- Dev tools (header buttons; only with ?dev=1 or the dev toggle)
  const Dev = {
    actions: {
      '+1h': () => Clock.advance(60), '+6h': () => Clock.advance(360), 'sunset': () => Clock.setHour(Clock.schedule().sunset), 'night': () => Clock.setHour(Clock.schedule().deep_night),
      'dawn': () => Clock.setHour(Clock.schedule().dawn_transition), 'energy 50': () => Energy.set(50), 'energy 10': () => Energy.set(10), 'drain': () => Energy.set(0), 'full': () => Energy.set(Energy.max),
      'sleep': () => Sleep.start(), 'save': () => SaveState.save(), 'load': () => SaveState.load(),
    },
    mount(container) { for (const k in this.actions) { const b = document.createElement('button'); b.textContent = k; b.onclick = this.actions[k]; container.appendChild(b); } },
  };

  function init(cfg, world) {
    CFG = cfg; W = world;
    Energy.max = CFG.energy.max; Energy.current = CFG.energy.start;
    Record.start(Clock.day, W.SeasonState.season); Clock.lastPhase = Clock.phase(); Weather.seed = (Math.random() * 1e9) >>> 0; on('hour', () => Weather.apply());
    const origTick = W.WorldClock.tick.bind(W.WorldClock);
    W.WorldClock.tick = function (dtReal) { const prev = this.minutes; origTick(dtReal); if (!this.paused) { const d = (this.minutes - prev + 1440) % 1440; Record.minutes(d); Clock.afterTick(prev); } };
  }
  function tick(dt, gameMinutes, moving) { Sleep.tick(dt); Activities.tick(dt); if (!Sleep.sleeping) { Energy.tickMovement(gameMinutes, moving); if (moving) Record.moving(gameMinutes); } }
  return { init, tick, on, Clock, Energy, Activities, Record, Sleep, SaveState, HUD, Dev, Weather, cfg: () => CFG };
})();
