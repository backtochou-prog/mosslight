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
      if (c.count) lines.push(names.map(id => `${c.activities[id]}× ${(CFG.activities[id] || {}).label || id}`.toLowerCase()).join(', ') + '.');
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
        Energy.set(full ? Energy.max : Math.min(Energy.max, Math.max(Energy.current, CFG.sleep.short_night_restore)));
        Energy._walkAcc = 0;
        Record.start(Clock.day, season);
        this.lastSummary = Record.summary(rec); this.summaryT = 7.0; emit('wake', Clock.day, rec);
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
    KEY: 'mosslight.save',
    snapshot() { return { version: CFG.version, day: Clock.day, season: W.SeasonState.season, minutes: W.WorldClock.minutes, energy: Energy.current, maxEnergy: Energy.max, sleeping: false, record: Record.cur, days: Record.days }; },
    save() { const s = this.snapshot(); try { localStorage.setItem(this.KEY, JSON.stringify(s)); } catch (_) {} return s; },
    load(s) { s = s || JSON.parse(localStorage.getItem(this.KEY) || 'null'); if (!s) return false;
      Clock.day = s.day; W.SeasonState.season = s.season; W.WorldClock.minutes = s.minutes; Energy.max = s.maxEnergy; Energy.set(s.energy);
      Record.cur = s.record || Record.cur; Record.days = s.days || []; Sleep.sleeping = false; Sleep.fade = 0;
      Clock.lastHour = Math.floor(s.minutes / 60); Clock.lastPhase = Clock.phase();   // no duplicate day/phase events on load
      emit('load', s); return true; },
  };

  // ---------------- HUD (native resolution, cozy: parchment text on a soft dark card; energy as a segmented bar)
  const HUD = {
    col: { card: 'rgba(24,30,28,0.72)', rim: 'rgba(222,220,180,0.45)', text: '#eedcb0', dim: 'rgba(238,220,176,0.6)', energetic: '#8cc452', tired: '#c8b85a', exhausted: '#d08a46', critical: '#c0392b', zero: '#6a5a4c' },
    draw(g, vw, vh, safe, T) {
      const x0 = 8 + safe, y0 = 8 + safe;
      const h = Clock.hour(); const ph = Clock.phase();
      const t = `${W.WorldClock.label()}  ·  day ${Clock.day}  ·  ${W.SeasonState.season}`;
      g.font = '9px ui-monospace, monospace'; g.textAlign = 'left';
      const tw = Math.max(118, g.measureText(t).width + 30);
      g.fillStyle = this.col.card; g.fillRect(x0, y0, tw, 30); g.strokeStyle = this.col.rim; g.lineWidth = 1; g.strokeRect(x0 + 0.5, y0 + 0.5, tw - 1, 29);
      // sun / moon arc: a dot travelling an arc from dawn to night
      const sc = Clock.schedule(); const dayLen = (sc.early_night - sc.dawn); const u = Math.max(0, Math.min(1, (h - sc.dawn) / dayLen)); const night = Clock.isNight() || ph === 'dawn_transition';
      const ax = x0 + 12, ay = y0 + 20, ar = 8;
      g.strokeStyle = 'rgba(222,220,180,0.25)'; g.beginPath(); g.arc(ax, ay, ar, Math.PI, 0); g.stroke();
      const a = Math.PI + u * Math.PI; const dx = ax + Math.cos(a) * ar, dy = ay + Math.sin(a) * ar;
      g.fillStyle = night ? '#b9cce8' : (ph === 'sunset' || ph === 'dawn' ? '#f0b24a' : '#ffd98a'); g.beginPath(); g.arc(night ? ax : dx, night ? ay - 6 : dy, 2.5, 0, 7); g.fill();
      if (night) { g.fillStyle = this.col.card; g.beginPath(); g.arc(ax + 1.5, ay - 7, 2.2, 0, 7); g.fill(); }
      g.fillStyle = this.col.text; g.fillText(t, x0 + 26, y0 + 11);
      // energy bar: 10 segments coloured by state; pulses softly when critical
      const bx = x0 + 26, by = y0 + 17, bw = tw - 34, bh = 6; const frac = Energy.current / Energy.max;
      g.fillStyle = 'rgba(0,0,0,0.35)'; g.fillRect(bx, by, bw, bh);
      const c = this.col[Energy.state] || this.col.zero; const pulse = Energy.state === 'critical' ? 0.75 + 0.25 * Math.sin(T * 3) : 1;
      g.globalAlpha = pulse; g.fillStyle = c; const segs = 10, gap = 1, sw = (bw - gap * (segs - 1)) / segs;
      for (let i = 0; i < segs; i++) { const f = Math.max(0, Math.min(1, frac * segs - i)); if (f > 0) g.fillRect(Math.round(bx + i * (sw + gap)), by, Math.max(1, Math.round(sw * f)), bh); }
      g.globalAlpha = 1; g.fillStyle = this.col.dim; g.font = '8px ui-monospace, monospace'; g.fillText(`${Math.round(Energy.current)}`, bx + bw + 3, by + 6);
      // critical: a soft vignette, no flashes
      if (Energy.state === 'critical' || Energy.state === 'zero') { const gr = g.createRadialGradient(vw / 2, vh / 2, vh * 0.45, vw / 2, vh / 2, vh * 0.85); gr.addColorStop(0, 'rgba(10,8,12,0)'); gr.addColorStop(1, 'rgba(10,8,12,0.35)'); g.fillStyle = gr; g.fillRect(0, 0, vw, vh); }
      // sleep fade + journal card
      if (Sleep.fade > 0) { g.fillStyle = `rgba(6,8,10,${Sleep.fade})`; g.fillRect(0, 0, vw, vh); if (Sleep.fade > 0.95) { g.fillStyle = this.col.dim; g.font = '10px ui-monospace, monospace'; g.textAlign = 'center'; g.fillText('…', vw / 2, vh / 2); } }
      if (Sleep.summaryT > 0 && Sleep.lastSummary && !Sleep.sleeping) {
        const alpha = Math.min(1, Sleep.summaryT); g.globalAlpha = alpha; g.font = '9px ui-monospace, monospace'; g.textAlign = 'left';
        const words = Sleep.lastSummary.split(' '); const lines = []; let cur = ''; const maxW = Math.min(vw - 40, 300);
        for (const w of words) { const test = cur ? cur + ' ' + w : w; if (g.measureText(test).width > maxW - 16) { lines.push(cur); cur = w; } else cur = test; } if (cur) lines.push(cur);
        const cw = maxW, ch = 16 + lines.length * 12, cx = Math.round(vw / 2 - cw / 2), cy = y0 + 40;
        g.fillStyle = 'rgba(40,34,26,0.9)'; g.fillRect(cx, cy, cw, ch); g.strokeStyle = this.col.rim; g.strokeRect(cx + 0.5, cy + 0.5, cw - 1, ch - 1);
        g.fillStyle = this.col.text; lines.forEach((l, i) => g.fillText(l, cx + 8, cy + 12 + i * 12)); g.globalAlpha = 1; }
    },
  };

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
    Record.start(Clock.day, W.SeasonState.season); Clock.lastPhase = Clock.phase();
    const origTick = W.WorldClock.tick.bind(W.WorldClock);
    W.WorldClock.tick = function (dtReal) { const prev = this.minutes; origTick(dtReal); if (!this.paused) { const d = (this.minutes - prev + 1440) % 1440; Record.minutes(d); Clock.afterTick(prev); } };
  }
  function tick(dt, gameMinutes, moving) { Sleep.tick(dt); Activities.tick(dt); if (!Sleep.sleeping) { Energy.tickMovement(gameMinutes, moving); if (moving) Record.moving(gameMinutes); } }
  return { init, tick, on, Clock, Energy, Activities, Record, Sleep, SaveState, HUD, Dev, cfg: () => CFG };
})();
