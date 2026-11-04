// MOSSlight procedural audio. WebAudio only: every sound is synthesised from oscillators and filtered noise.
// One engine per AudioContext (the live one, or an OfflineAudioContext for tests): buses, ambience layers,
// one-shot recipes, UI sounds, creature calls, stings, and a generative score built from authored motifs.
// Public API: window.Sound = { init, start, tick, play, ui, creature, sting, settings, setVolume, setMuted, setMusicMuted, save, mood, debug }.
window.Sound = (() => {
  'use strict';
  const KEY = 'mosslight.audio';
  const DEFAULTS = { master: 0.8, music: 0.55, ambient: 0.7, sfx: 0.8, ui: 0.5, creatures: 0.8, muted: false, musicMuted: false, reduceRepetition: false };
  const BUSES = ['music', 'ambient', 'sfx', 'ui', 'creatures'];
  const PHASES = ['dawn', 'dawn_transition', 'day', 'sunset', 'early_night', 'deep_night'];
  const SEASONS = ['spring', 'summer', 'autumn', 'winter'];
  const WEATHER = ['clear', 'light_rain', 'heavy_rain', 'fog', 'snow', 'wind'];
  const THREAT_STATES = ['pursue', 'stalk', 'attack'];
  const LOOKAHEAD = 0.5, TICK_MS = 100, MOOD_HOLD = 20, DANGER_CALM = 8;
  const clamp = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v);
  const num = (v, d) => (typeof v === 'number' && isFinite(v) ? v : d);
  const mtof = m => 440 * Math.pow(2, (m - 69) / 12);
  const safe = (f, d) => { try { const v = f(); return v === undefined || v === null ? d : v; } catch (e) { return d; } };
  const prox = (d, r, k = 1.6) => (!(d < r) ? 0 : Math.pow(1 - Math.max(0, d) / r, k));
  function mulberry(seed) { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; }
  function phaseOf(h) { return h < 5 ? 'deep_night' : h < 6.5 ? 'dawn' : h < 7.5 ? 'dawn_transition' : h < 18 ? 'day' : h < 20 ? 'sunset' : h < 23 ? 'early_night' : 'deep_night'; }

  // ======================================================================= WORLD SENSING (every field optional)
  function sense(w) {
    w = w || {};
    const hour = num(safe(() => w.WorldClock.hour(), 12), 12);
    let phase = safe(() => w.Survival.Clock.phase(), null); if (!PHASES.includes(phase)) phase = phaseOf(((hour % 24) + 24) % 24);
    let season = safe(() => w.SeasonState.season, 'spring'); if (!SEASONS.includes(season)) season = 'spring';
    const WS = w.WeatherState || {}; let kind = WEATHER.includes(WS.kind) ? WS.kind : 'clear';
    const intensity = clamp(num(WS.intensity, kind === 'clear' ? 0 : 0.6));
    const wind = clamp(num(WS.wind, { clear: 0.2, light_rain: 0.3, heavy_rain: 0.55, fog: 0.08, snow: 0.3, wind: 0.8 }[kind]));
    const P = w.Player || {}; const px = num(P.x, 0), py = num(P.y, 0);
    const dist = fn => { const v = safe(() => (typeof w[fn] === 'function' ? w[fn](px, py) : Infinity), Infinity); return typeof v === 'number' && !isNaN(v) ? v : Infinity; };
    const trees = clamp(num(safe(() => w.treeDensity(px, py), 0.3), 0.3));
    const sheltered = !!safe(() => w.shelter(), false);
    const fishing = !!safe(() => w.Fishing.busy(), false);
    let festival = safe(() => w.Festival.active(), null); if (typeof festival !== 'string') festival = null;
    let threatD = Infinity;
    const ls = safe(() => (Array.isArray(w.Monsters.list) ? w.Monsters.list : typeof w.Monsters.list === 'function' ? w.Monsters.list() : []), []);
    if (Array.isArray(ls)) for (const m of ls) { if (!m || !THREAT_STATES.includes(m.state)) continue; const d = Math.hypot(num(m.x, 1e9) - px, num(m.y, 1e9) - py); if (d < threatD) threatD = d; }
    return { hour, phase, season, kind, intensity, wind, px, py, waterD: dist('waterDist'), fireD: dist('fireDist'), tentD: dist('tentDist'), trees, sheltered, fishing, festival, threatD };
  }
  function wantMood(s) {
    if (s.threatD < 140) return 'danger';
    if (s.festival && MOODS[s.festival]) return s.festival;
    if (s.fishing) return 'fishing';
    const night = s.phase === 'early_night' || s.phase === 'deep_night' || (s.phase === 'sunset' && s.hour >= 19.5);
    if (night && (s.sheltered || s.fireD < 70 || s.tentD < 36)) return 'shelter';
    if (s.season === 'winter') return 'winter';
    return { dawn: 'morning', dawn_transition: 'morning', day: 'day', sunset: 'sunset', early_night: 'night', deep_night: 'night' }[s.phase] || 'day';
  }

  // ======================================================================= AUTHORED SCORE
  // Melodies are [scale degree, beats] (R = rest), degrees index the mood's mode (wrapping by octave).
  // Progressions are chord roots in scale degrees, one per bar. Bass patterns are [degree offset from chord root, beat, beats].
  const MODES = { ionian: [0, 2, 4, 5, 7, 9, 11], dorian: [0, 2, 3, 5, 7, 9, 10], phrygian: [0, 1, 3, 5, 7, 8, 10], lydian: [0, 2, 4, 6, 7, 9, 11], mixolydian: [0, 2, 4, 5, 7, 9, 10], aeolian: [0, 2, 3, 5, 7, 8, 10], pent: [0, 2, 4, 7, 9] };
  const R = null;
  const MOODS = {
    morning: { root: 62, mode: 'ionian', bpm: 72, meter: 4, rest: [1, 3], silence: [6, 12], gain: 1,
      prog: [[0, 4, 5, 3], [0, 3, 0, 4], [5, 3, 0, 4]],
      mel: [[[4, 1], [5, .5], [4, .5], [2, 2], [R, 1], [1, 1], [2, 1], [4, 1], [7, 3], [R, 1], [6, 1], [4, 1], [5, 2]],
            [[2, 1.5], [4, .5], [7, 2], [R, 2], [6, 1], [5, 1], [4, 2], [2, 1], [1, 1], [0, 4]],
            [[R, 1], [7, 1], [9, 1], [8, 1], [7, 2], [4, 2], [R, 2], [5, 1], [4, 1], [2, 1], [1, 1], [2, 2]]],
      lead: { inst: 'piano', oct: 0, vel: .16 }, chord: { inst: 'pad', style: 'hold', oct: -1, vel: .045 }, bass: { inst: 'softbass', oct: -2, vel: .11, pat: [[0, 0, 3]] },
      sparkle: { inst: 'bell', oct: 1, vel: .05, p: .25 }, restPad: true },
    day: { root: 67, mode: 'ionian', bpm: 88, meter: 4, rest: [1, 2], silence: [5, 10], gain: 1,
      prog: [[0, 3, 4, 0], [5, 3, 1, 4], [0, 5, 3, 4]],
      mel: [[[0, .5], [1, .5], [2, 1], [4, 1], [2, .5], [4, .5], [5, 2], [R, 1], [4, .5], [5, .5], [7, 1], [5, 1], [4, 1], [2, 2], [R, 2]],
            [[4, 1], [4, .5], [5, .5], [4, 1], [2, 1], [0, 2], [R, 2], [1, 1], [2, 1], [4, 1], [1, 1], [2, 4]],
            [[7, 1.5], [6, .5], [4, 1], [5, 1], [4, 2], [2, 2], [R, 1], [0, .5], [1, .5], [2, 1], [4, 1], [1, 4]]],
      lead: { inst: 'pluck', oct: 0, vel: .17 }, chord: { inst: 'piano', style: 'arp', oct: -1, vel: .06 }, bass: { inst: 'softbass', oct: -2, vel: .11, pat: [[0, 0, 1.5], [4, 2, 1.5]] } },
    sunset: { root: 57, mode: 'aeolian', bpm: 66, meter: 4, rest: [2, 3], silence: [8, 14], gain: 1,
      prog: [[0, 5, 2, 6], [3, 0, 4, 4], [5, 3, 0, 6]],
      mel: [[[4, 2], [3, 1], [2, 1], [1, 3], [R, 1], [2, 1], [3, 1], [4, 1], [6, 1], [4, 4]],
            [[7, 1], [6, 1], [4, 2], [R, 1], [3, 1], [2, 1], [3, 1], [4, 3], [2, 1], [0, 4]],
            [[2, 1.5], [1, .5], [0, 2], [R, 2], [4, 1.5], [3, .5], [2, 2], [1, 1], [-1, 1], [0, 4]]],
      lead: { inst: 'piano', oct: 1, vel: .15 }, chord: { inst: 'pad', style: 'hold', oct: 0, vel: .05 }, bass: { inst: 'softbass', oct: -1, vel: .1, pat: [[0, 0, 4]] }, restPad: true },
    night: { root: 54, mode: 'dorian', bpm: 56, meter: 3, rest: [2, 4], silence: [8, 16], gain: 1,
      prog: [[0, 3, 0, 4], [0, 6, 3, 0], [5, 3, 4, 0]],
      mel: [[[4, 1], [R, 1], [2, 1], [3, 2], [R, 1], [1, 1], [R, 2], [0, 3]],
            [[R, 1], [7, 1], [6, 1], [4, 3], [R, 2], [3, 1], [2, 3]],
            [[2, 1], [4, 1], [R, 1], [5, 1.5], [4, .5], [R, 4], [1, 3]]],
      lead: { inst: 'bell', oct: 2, vel: .1 }, chord: { inst: 'pad', style: 'hold', oct: 0, vel: .032 }, drone: { inst: 'drone', oct: -1, vel: .045 } },
    danger: { root: 50, mode: 'phrygian', bpm: 63, meter: 4, rest: [0, 1], silence: [3, 5], gain: 1,
      prog: [[0, 0, 0, 0], [0, 0, -1, 0]],
      mel: [[[R, 8], [1, 4], [R, 4]], [[R, 10], [4, 2], [3, 4]], [[R, 16]]],
      lead: { inst: 'bowed', oct: 1, vel: .06 }, bass: { inst: 'pluck', oct: -1, vel: .15, dark: true, pat: [[0, 0, 1], [1, 1, 1], [0, 2, 1], [-2, 3, 1]] },
      drone: { inst: 'drone', oct: -1, vel: .07 }, sparkle: { inst: 'bell', oct: 2, vel: .025, p: .12, deg: 1 } },
    shelter: { root: 53, mode: 'ionian', bpm: 60, meter: 3, rest: [1, 3], silence: [6, 12], gain: 1,
      prog: [[0, 3, 4, 0], [0, 5, 3, 4], [3, 4, 0, 0]],
      mel: [[[2, 1], [4, 1], [5, 1], [4, 2], [2, 1], [1, 2], [2, 1], [0, 3]],
            [[4, 1.5], [5, .5], [4, 1], [7, 3], [5, 1], [4, 1], [2, 1], [4, 3]],
            [[R, 1], [0, 1], [2, 1], [4, 2], [3, 1], [2, 1], [1, 1], [2, 1], [0, 3]]],
      lead: { inst: 'piano', oct: 1, vel: .15 }, chord: { inst: 'pad', style: 'hold', oct: 0, vel: .045 }, bass: { inst: 'softbass', oct: -1, vel: .1, pat: [[0, 0, 3]] }, restPad: true },
    fishing: { root: 60, mode: 'pent', bpm: 54, meter: 4, rest: [2, 4], silence: [6, 12], gain: 1,
      prog: [[0, 0, 0, 0], [0, 3, 0, 0]],
      mel: [[[2, 1], [3, 1], [4, 2], [R, 4], [3, 1], [2, 1], [1, 2], [R, 4]],
            [[5, 2], [4, 1], [3, 1], [R, 3], [2, 1], [1, 2], [0, 2], [R, 4]],
            [[R, 2], [1, 1], [2, 1], [3, 4], [R, 2], [4, 1], [2, 3], [R, 2]]],
      lead: { inst: 'pluck', oct: 0, vel: .15 }, drone: { inst: 'drone', oct: -2, vel: .04 }, sparkle: { inst: 'bell', oct: 1, vel: .04, p: .3 } },
    winter: { root: 64, mode: 'aeolian', bpm: 50, meter: 4, rest: [3, 5], silence: [10, 18], gain: 1,
      prog: [[0, 5, 3, 6], [0, 3, 5, 4]],
      mel: [[[4, 2], [R, 1], [3, 1], [2, 3], [R, 1], [0, 2], [R, 2], [1, 4]],
            [[R, 2], [7, 2], [6, 1], [4, 3], [R, 4], [2, 4]],
            [[2, 1], [4, 1], [7, 4], [R, 2], [6, 2], [4, 4], [R, 2]]],
      lead: { inst: 'bell', oct: 1, vel: .1 }, chord: { inst: 'pad', style: 'hold', oct: -1, vel: .03 } },
    fest_awakening: { root: 65, mode: 'lydian', bpm: 80, meter: 4, rest: [1, 2], silence: [4, 8], gain: 1,
      prog: [[0, 1, 0, 4], [0, 1, 5, 4], [3, 1, 0, 0]],
      mel: [[[0, 1], [1, 1], [3, 1.5], [4, .5], [4, 2], [R, 1], [3, 1], [1, 1], [2, 1], [4, 4], [R, 2]],
            [[4, 1], [5, 1], [7, 2], [6, 1], [4, 1], [3, 2], [R, 1], [4, 1], [1, 2], [0, 4]],
            [[7, .5], [8, .5], [7, 1], [4, 2], [R, 1], [5, 1], [3, 1], [4, 1], [R, 1], [1, 1], [2, 1], [0, 5]]],
      lead: { inst: 'flute', oct: 0, vel: .11 }, chord: { inst: 'pluck', style: 'arp', oct: -1, vel: .07 }, bass: { inst: 'softbass', oct: -2, vel: .1, pat: [[0, 0, 2], [4, 2, 2]] }, sparkle: { inst: 'bell', oct: 1, vel: .04, p: .2 } },
    fest_fireflies: { root: 69, mode: 'pent', bpm: 100, meter: 4, rest: [1, 2], silence: [4, 8], gain: 1,
      prog: [[0, 3, 1, 4], [0, 1, 3, 0]],
      mel: [[[0, .5], [2, .5], [4, .5], [5, .5], [4, 1], [2, 1], [3, .5], [4, .5], [5, 1], [7, 2], [R, 1], [5, .5], [4, .5], [2, 1], [3, 1], [1, 1], [0, 2]],
            [[4, 1], [4, .5], [5, .5], [7, 1], [5, 1], [4, 2], [R, 1], [2, .5], [3, .5], [4, 1], [2, 1], [0, 3], [R, 2]],
            [[7, .5], [5, .5], [4, .5], [2, .5], [4, 1], [R, 1], [5, .5], [4, .5], [2, .5], [1, .5], [2, 1], [R, 1], [0, .5], [1, .5], [2, 1], [4, 2], [R, 4]]],
      lead: { inst: 'bell', oct: 0, vel: .11 }, chord: { inst: 'pluck', style: 'arp', oct: -1, vel: .06 }, bass: { inst: 'softbass', oct: -2, vel: .1, pat: [[0, 0, 1], [2, 2, 1]] }, sparkle: { inst: 'bell', oct: 1, vel: .035, p: .5 } },
    fest_forgotten: { root: 50, mode: 'dorian', bpm: 58, meter: 4, rest: [1, 3], silence: [6, 10], gain: 1,
      prog: [[0, 3, 0, 6], [0, 2, 3, 0]],
      mel: [[[0, 2], [2, 1], [3, 1], [4, 4], [R, 2], [3, 1], [2, 1], [1, 4]],
            [[4, 2], [5, 2], [4, 1], [2, 1], [3, 2], [R, 2], [2, 2], [0, 4]],
            [[R, 2], [6, 2], [5, 1], [4, 1], [2, 4], [R, 2], [1, 4]]],
      lead: { inst: 'bowed', oct: 1, vel: .09 }, chord: { inst: 'pad', style: 'hold', oct: 0, vel: .035 }, drone: { inst: 'drone', oct: -1, vel: .05 } },
    fest_silent_tide: { root: 58, mode: 'mixolydian', bpm: 48, meter: 4, rest: [2, 3], silence: [8, 14], gain: 1,
      prog: [[0, 6, 3, 0], [0, 4, 6, 0]],
      mel: [[[4, 3], [R, 1], [2, 2], [1, 2], [0, 4], [R, 4]],
            [[R, 2], [6, 2], [4, 2], [R, 2], [5, 3], [4, 1], [2, 4]],
            [[2, 1], [4, 1], [6, 2], [R, 4], [4, 2], [3, 2], [R, 4]]],
      lead: { inst: 'glass', oct: 1, vel: .1 }, chord: { inst: 'pad', style: 'hold', oct: 0, vel: .032 }, drone: { inst: 'drone', oct: -1, vel: .04 }, sparkle: { inst: 'glass', oct: 2, vel: .03, p: .2 } }
  };
  const degMidi = (M, deg, oct) => { const sc = MODES[M.mode], L = sc.length, o = Math.floor(deg / L); return M.root + 12 * (oct + o) + sc[deg - o * L]; };

  // ======================================================================= ENGINE
  function createEngine(ctx, opt) {
    const E = { ctx, world: opt.world || {}, settings: opt.settings, voices: 0, T: 0, mood: null, moodSince: -1e9, lastThreat: -1e9, cand: null, candT: 0,
      forced: null, mv: [], useMusic: opt.music !== false, useAmb: opt.ambience !== false, last: {}, rep: {}, timers: {}, primed: !opt.prime, ambAcc: 1, lv: {}, s: null };
    const rnd = opt.seed != null ? mulberry(opt.seed) : Math.random;
    const rr = (a, b) => a + (b - a) * rnd(), pick = a => a[Math.floor(rnd() * a.length)];
    const now = () => ctx.currentTime;
    const RR = () => !!(E.settings && E.settings.reduceRepetition);
    // ---- node helpers
    const G = (v = 0, dest) => { const g = ctx.createGain(); g.gain.value = v; if (dest) g.connect(dest); return g; };
    const F = (type, f, q, dest) => { const b = ctx.createBiquadFilter(); b.type = type; b.frequency.value = f; if (q !== undefined) b.Q.value = q; if (dest) b.connect(dest); return b; };
    const Pn = (p, dest) => { if (!ctx.createStereoPanner) return dest; const n = ctx.createStereoPanner(); n.pan.value = clamp(p, -1, 1); n.connect(dest); return n; };
    function track(src, t, stop, count) { src.start(t); src.stop(stop); if (count) { E.voices++; src.onended = () => { E.voices = Math.max(0, E.voices - 1); }; } return src; }
    function noiseBuf(kind) { const sr = ctx.sampleRate, n = Math.floor(sr * 3), b = ctx.createBuffer(2, n, sr);
      for (let ch = 0; ch < 2; ch++) { const d = b.getChannelData(ch); let b0 = 0, b1 = 0, b2 = 0, last = 0;
        for (let i = 0; i < n; i++) { const w = rnd() * 2 - 1;
          if (kind === 'white') d[i] = w;
          else if (kind === 'pink') { b0 = .99765 * b0 + w * .099046; b1 = .963 * b1 + w * .2965164; b2 = .57 * b2 + w * 1.0526913; d[i] = (b0 + b1 + b2 + w * .1848) * .16; }
          else { last = (last + .02 * w) / 1.02; d[i] = last * 3.5; } }
        const drift = d[n - 1] - d[0]; for (let i = 0; i < n; i++) d[i] -= drift * i / (n - 1); }   // seamless loop
      return b; }
    const NB = { white: noiseBuf('white'), pink: noiseBuf('pink'), brown: noiseBuf('brown') };
    function loopSrc(kind, dest) { const s = ctx.createBufferSource(); s.buffer = NB[kind]; s.loop = true; s.connect(dest); s.start(now(), rnd() * 2.5); return s; }
    // ---- envelope helpers
    function perc(p, t, a, dur, peak) { p.setValueAtTime(0, t); p.linearRampToValueAtTime(peak, t + a); p.setTargetAtTime(0, t + a, Math.max(.002, (dur - a) / 4)); return t + dur + (dur - a) / 2 + .02; }
    // nz: filtered noise burst. o: {dur, f, f2, q, type, g, a, src}
    function nz(dest, t, o) { const dur = o.dur || .1, s = ctx.createBufferSource(); s.buffer = NB[o.src || 'white']; if (dur > 2.5) s.loop = true;
      const f = F(o.type || 'bandpass', o.f || 1000, o.q === undefined ? 1 : o.q); f.frequency.setValueAtTime(o.f || 1000, t); if (o.f2) f.frequency.exponentialRampToValueAtTime(Math.max(20, o.f2), t + dur);
      const g = G(0); s.connect(f); f.connect(g); g.connect(dest); const end = perc(g.gain, t, o.a || .002, dur, o.g === undefined ? .3 : o.g);
      s.start(t, rnd() * 2); s.stop(end); return g; }
    // tn: pitched transient. o: {f, f2, glide, type, dur, g, a, lp}
    function tn(dest, t, o) { const dur = o.dur || .1, s = ctx.createOscillator(); s.type = o.type || 'sine'; s.frequency.setValueAtTime(Math.max(1, o.f), t);
      if (o.f2) s.frequency.exponentialRampToValueAtTime(Math.max(1, o.f2), t + (o.glide || dur));
      const g = G(0); let head = s; if (o.lp) { const f = F('lowpass', o.lp, .7); s.connect(f); head = f; } head.connect(g); g.connect(dest);
      const end = perc(g.gain, t, o.a || .003, dur, o.g === undefined ? .3 : o.g); track(s, t, end, o.count); return g; }
    function bell(dest, t, f, g, decay = 1.4) { [[1, 1, decay], [2.76, .28, decay * .35], [5.4, .08, decay * .15]].forEach(([r, a, d], i) => {
        const o = ctx.createOscillator(); o.frequency.value = f * r; const e = G(0, dest); e.gain.setValueAtTime(0, t); e.gain.linearRampToValueAtTime(g * a, t + .003); e.gain.setTargetAtTime(0, t + .003, d / 3); o.connect(e); track(o, t, t + d * 2 + .1, i === 0); }); }
    function shimmer(dest, t, g, dur = 2.2) { const lfo = ctx.createOscillator(); lfo.frequency.value = 6.5; const lg = G(g * .5); lfo.connect(lg);
      [2349, 2794, 3520].forEach(f => { const o = ctx.createOscillator(); o.frequency.value = f * rr(.997, 1.003); const e = G(0, dest); e.gain.setValueAtTime(0, t); e.gain.linearRampToValueAtTime(g, t + .3); e.gain.setTargetAtTime(0, t + .35, dur / 4); lg.connect(e.gain); o.connect(e); track(o, t, t + dur * 1.6, false); });
      track(lfo, t, t + dur * 1.6, false); }

    // ---- buses
    const limiter = ctx.createDynamicsCompressor(); limiter.threshold.value = -8; limiter.knee.value = 4; limiter.ratio.value = 10; limiter.attack.value = .003; limiter.release.value = .2; limiter.connect(ctx.destination);
    const master = G(0, limiter); const bus = {}; for (const b of BUSES) bus[b] = G(0, master);
    const duck = G(1, bus.music), musicMix = G(1, duck), stingBus = G(1, bus.music);
    const uiIn = F('lowpass', 5200, .5, bus.ui);
    function applySettings(instant) { const st = E.settings, t = now(); const set = (p, v) => (instant ? p.setValueAtTime(v, t) : p.setTargetAtTime(v, t, .06));
      set(master.gain, st.muted ? 0 : clamp(num(st.master, .8))); for (const b of BUSES) set(bus[b].gain, b === 'music' && st.musicMuted ? 0 : clamp(num(st[b], DEFAULTS[b]))); }
    applySettings(true);

    // ---- distance + pan for point one-shots
    function spatial(dest, o, vol, maxD = 480, ref = 100) { let g = vol, pan = num(o.pan, 0), cut = 0; const P = E.world.Player;
      if (o && typeof o.x === 'number' && P && typeof P.x === 'number') { const dx = o.x - P.x, dy = num(o.y, P.y) - num(P.y, 0), d = Math.hypot(dx, dy);
        if (d >= maxD) return null; g *= (1 / (1 + Math.pow(d / ref, 2))) * (1 - d / maxD); pan = clamp(dx / 170, -.85, .85); cut = d > 120 ? Math.max(1400, 16000 - (d - 120) * 40) : 0; }
      if (g < .002) return null; let head = dest; if (cut) head = F('lowpass', cut, .5, dest); const p = Pn(pan, head); const gn = G(g, p); return gn; }

    // =================================================================== AMBIENCE
    const A = {}; let amb = null;
    if (E.useAmb) {
      const outdoor = G(1), outLP = F('lowpass', 18000, .5, bus.ambient); outdoor.connect(outLP);
      const lay = (name, dest) => (A[name] = G(0, dest));
      // wind: pink noise bandpass + a brown low body; gusts on a sub-gain
      lay('wind', outdoor); const gust = G(.7, A.wind); const windBP = F('bandpass', 500, .6, gust); loopSrc('pink', windBP); const windLow = F('lowpass', 220, .5, G(.5, gust)); loopSrc('brown', windLow);
      lay('leaves', outdoor);
      lay('whistle', outdoor); const whBP = F('bandpass', 1300, 28, G(4, A.whistle)); loopSrc('white', whBP);
      lay('birds', outdoor);
      // insects: two cricket pulse trains (AM sine carriers) + a cicada-like AM bandpassed noise
      lay('insects', outdoor); const crickG = G(1, A.insects), cicG = G(0, A.insects);
      [0, 1].forEach(k => { const car = ctx.createOscillator(); car.frequency.value = 4400 + k * 370; const g1 = G(.5), g2 = G(.5, Pn(k ? .5 : -.5, crickG)); car.connect(g1); g1.connect(g2);
        const pulse = ctx.createOscillator(); pulse.frequency.value = 27 + k * 4; pulse.connect(G(.5)).connect(g1.gain);
        const gate = ctx.createOscillator(); gate.type = 'square'; gate.frequency.value = 1.1 + k * .37; gate.connect(F('lowpass', 22, .5)).connect(G(.5)).connect(g2.gain);
        [car, pulse, gate].forEach(o => o.start(now())); });
      { const cb = F('bandpass', 5600, 5); const am = G(.5, cicG); cb.connect(am); loopSrc('white', cb); const l = ctx.createOscillator(); l.frequency.value = 10.5; l.connect(G(.5)).connect(am.gain); l.start(now()); }
      lay('night', outdoor); loopSrc('brown', F('lowpass', 140, .5, A.night));
      lay('owls', outdoor); lay('frogs', outdoor);
      lay('water', outdoor); const lap = G(.35, A.water); loopSrc('pink', F('lowpass', 650, .6, lap)); loopSrc('white', F('bandpass', 1800, 2, G(.12, lap)));
      lay('rain', bus.ambient); const rainLP = F('lowpass', 7500, .5, A.rain); const rainIn = G(1, rainLP); loopSrc('white', F('highpass', 900, .5, G(.5, rainIn)));
      lay('canvas', bus.ambient); lay('thunder', outdoor);
      lay('fire', bus.ambient); loopSrc('brown', F('bandpass', 300, .7, G(.55, A.fire))); const crackG = G(1, A.fire);
      amb = { outdoor, outLP, gust, windBP, whBP, crickG, cicG, lap, rainLP, rainIn, crackG };
    }
    function setP(p, v, tau = 1) { if (E.primed) p.setTargetAtTime(v, now(), tau); else p.setValueAtTime(v, now()); }
    const LV = {}; // last layer targets, for debug
    function ambUpdate(s) { if (!amb) return;
      const raining = s.kind === 'light_rain' || s.kind === 'heavy_rain', dusk = s.phase === 'sunset' || s.phase === 'early_night', night = s.phase === 'early_night' || s.phase === 'deep_night', w = s.wind;
      const T = (name, v, tau = 1) => { LV[name] = v; setP(A[name].gain, v, tau); };
      setP(amb.outLP.frequency, s.sheltered ? 900 : s.kind === 'snow' ? 4500 : s.kind === 'fog' ? 9000 : 18000, .8); setP(amb.outdoor.gain, s.sheltered ? .55 : s.kind === 'snow' ? .8 : 1, .8);
      T('wind', .035 + .3 * Math.pow(w, 1.6), 1.2); setP(amb.windBP.frequency, 260 + 900 * w, 1.5);
      T('leaves', s.season === 'winter' ? .25 : .6);
      T('whistle', s.season === 'winter' ? .012 + .05 * w * w : 0, 1.5);
      const birdsOk = ['dawn', 'dawn_transition', 'day'].includes(s.phase) && !raining && s.kind !== 'snow' && w < .8;
      E.birdLvl = birdsOk ? (s.season === 'winter' ? .35 : 1) * (s.kind === 'fog' ? .6 : 1) : 0; T('birds', E.birdLvl * .9);
      const sF = { summer: 1, spring: .45, autumn: .5, winter: 0 }[s.season], tF = dusk ? 1 : s.phase === 'deep_night' ? (s.season === 'summer' ? .65 : .25) : 0;
      const rF = s.kind === 'heavy_rain' ? 0 : s.kind === 'light_rain' ? .3 : 1; T('insects', sF * tF * rF * (1 - .6 * w) * .05, 1.5);
      setP(amb.cicG.gain, s.season === 'summer' && dusk ? .6 : 0, 1.5);
      T('night', s.phase === 'deep_night' ? .07 : s.phase === 'early_night' ? .035 : 0, 2);
      T('owls', night && s.season !== 'summer' || s.phase === 'deep_night' ? .9 : 0);
      E.frogLvl = (s.season === 'spring' || s.season === 'summer') && (night || dusk) ? prox(s.waterD, 150, 1) : 0; T('frogs', E.frogLvl * .9);
      T('water', prox(s.waterD, 160, 1.5) * (s.season === 'winter' ? .25 : .55), 1.2);
      T('rain', raining ? (s.kind === 'heavy_rain' ? .55 : .3) * (.4 + .6 * s.intensity) : 0, 1.5); setP(amb.rainLP.frequency, s.sheltered ? 700 : 7500, .6);
      E.canvasLvl = raining ? prox(s.tentD, 45, 1) * s.intensity : 0; T('canvas', E.canvasLvl ? .25 + .5 * E.canvasLvl : 0);
      T('thunder', s.kind === 'heavy_rain' ? .9 : 0, .5);
      E.fireLvl = prox(s.fireD, 130, 1.6); T('fire', E.fireLvl * .5, .8);
    }
    // ---- ambient events
    function rustle(t, g) { const p = Pn(rr(-.8, .8), A.leaves), n = 4 + Math.floor(rnd() * 7); for (let i = 0; i < n; i++) nz(p, t + rr(0, .9), { f: rr(2500, 6000), q: .9, dur: rr(.02, .07), g: g * rr(.15, .45), a: .006 }); }
    function bird(t, sp) { const p = Pn(rr(-.75, .75), A.birds), g = rr(.3, .9);
      if (sp === 0) { let f = rr(2600, 3200), tt = t; const n = 3 + Math.floor(rnd() * 4); for (let i = 0; i < n; i++) { tn(p, tt, { f, f2: f * rr(1.12, 1.3), glide: .06, dur: rr(.07, .13), g: g * .07, a: .01, count: i === 0 }); tt += rr(.11, .19); f *= rr(.88, 1.02); } }
      else if (sp === 1) { const f = rr(3000, 3500), reps = rnd() < .5 ? 2 : 1; for (let r = 0; r < reps; r++) { const tt = t + r * .95; tn(p, tt, { f, f2: f * 1.03, dur: .22, g: g * .06, a: .03 }); tn(p, tt + .3, { f: f * .8, f2: f * .75, dur: .3, g: g * .05, a: .03 }); } }
      else { const n = 8 + Math.floor(rnd() * 7); let f = rr(4000, 4600); for (let i = 0; i < n; i++) { tn(p, t + i * .055, { f, f2: f * 1.15, dur: .035, g: g * .04 * (1 - i / n * .5), a: .004 }); f *= 1.008; } } }
    function owl(t) { const p = Pn(rr(-.6, .6), A.owls), g = rr(.05, .09), f = rr(360, 400);
      tn(p, t, { f, f2: f * .97, dur: .38, g, a: .07 }); tn(p, t + .65, { f: f * .87, f2: f * .83, dur: .7, g: g * .9, a: .08 }); if (rnd() < .35) tn(p, t + 1.6, { f: f * .87, f2: f * .84, dur: .6, g: g * .7, a: .08 }); }
    function frog(t) { const p = Pn(rr(-.7, .7), A.frogs), n = 6 + Math.floor(rnd() * 5), rate = rr(12, 16), f = rr(100, 160), bp = rr(500, 900);
      const b = F('bandpass', bp, 5, G(rr(.4, .9), p)); for (let i = 0; i < n; i++) tn(b, t + i / rate, { type: 'sawtooth', f, f2: f * .92, dur: .03, g: .5, a: .004 }); }
    function thunder(t) { const s = ctx.createBufferSource(); s.buffer = NB.brown; s.loop = true; const lp = F('lowpass', rr(90, 160), .7), g = G(0, A.thunder); s.connect(lp); lp.connect(g);
      const pk = rr(.5, .9), p = g.gain; p.setValueAtTime(0, t); p.linearRampToValueAtTime(pk * .6, t + rr(.3, .7)); p.setTargetAtTime(pk * .3, t + .8, .3); p.linearRampToValueAtTime(pk, t + rr(1.3, 1.8)); p.setTargetAtTime(0, t + 2, rr(1, 1.6)); s.start(t, rnd() * 2); s.stop(t + 9); }
    function drop(t) { tn(Pn(rr(-.9, .9), amb.rainIn), t, { f: rr(1800, 5000), f2: 1500, dur: .018, g: rr(.02, .07), a: .001 }); }
    function tap(t) { nz(Pn(rr(-.5, .5), A.canvas), t, { f: rr(400, 900), q: 2, dur: .025, g: rr(.15, .4) }); }
    function crackle(t) { if (rnd() < .2) nz(amb.crackG, t, { f: rr(600, 1400), q: 1.5, dur: .02, g: .45 }); else nz(amb.crackG, t, { type: 'highpass', f: rr(1500, 4000), q: .7, dur: rr(.003, .012), g: rr(.2, 1) }); }
    function count(rate, dt) { const x = rate * dt; let n = Math.floor(x); if (rnd() < x - n) n++; return n; }
    function ambEvents(s, dt) { if (!amb) return; const t0 = now() + .03, Ti = E.timers, tnow = now();
      const many = (rate, fn) => { const n = Math.min(40, count(rate, dt)); for (let i = 0; i < n; i++) fn(t0 + rnd() * dt); };
      many(s.trees * (.12 + 1.1 * s.wind) * (s.season === 'winter' ? .3 : 1), t => rustle(t, .6 + .4 * s.wind));
      if (E.birdLvl > 0 && tnow > (Ti.bird || 0)) { const rate = (s.phase === 'day' ? .14 : .32) * (.4 + s.trees) * (s.season === 'winter' ? .4 : 1) * (RR() ? .8 : 1);
        if (rnd() < rate * dt) { bird(t0, pick([0, 0, 1, 1, 2])); Ti.bird = tnow + rr(1.5, 3); } }
      if (LV.owls > 0 && s.phase === 'deep_night' && tnow > (Ti.owl || 0) && rnd() < dt / 40) { owl(t0); Ti.owl = tnow + rr(15, 30); }
      if (E.frogLvl > 0 && tnow > (Ti.frog || 0) && rnd() < .3 * E.frogLvl * dt * 4) { frog(t0); Ti.frog = tnow + rr(1.5, 5); }
      if (s.kind === 'heavy_rain') { if (Ti.thunder === undefined) Ti.thunder = tnow + rr(12, 35); if (tnow > Ti.thunder) { thunder(t0); Ti.thunder = tnow + rr(30, 80); } } else Ti.thunder = undefined;
      if (LV.rain > 0) many(14 * s.intensity, drop);
      if (E.canvasLvl > 0) many(28 * E.canvasLvl, tap);
      if (E.fireLvl > .01) many((1.5 + 7 * E.fireLvl), crackle);
      if (tnow > (Ti.lap || 0)) { amb.lap.gain.setTargetAtTime(rr(.5, .9), t0, .25); amb.lap.gain.setTargetAtTime(rr(.15, .3), t0 + rr(.5, .9), .5); Ti.lap = tnow + rr(1.6, 3.5); }
      if (tnow > (Ti.gust || 0)) { amb.gust.gain.setTargetAtTime(.45 + rnd() * .45 * (1 + s.wind), t0, 1.2); Ti.gust = tnow + rr(2, 6); }
      if (tnow > (Ti.wh || 0)) { amb.whBP.frequency.setTargetAtTime(rr(950, 1600), t0, 1.5); Ti.wh = tnow + rr(2, 5); } }

    // =================================================================== MUSIC INSTRUMENTS (dest, t, midi, dur, vel)
    const INST = {
      piano(d, t, m, dur, v) { const f = mtof(m), c = ctx.createOscillator(), mod = ctx.createOscillator(); c.frequency.value = f; mod.frequency.value = f;
        const mg = G(0); mg.gain.setValueAtTime(f * (.5 + 1.6 * v / .16 * .6), t); mg.gain.setTargetAtTime(f * .2, t, .12); mod.connect(mg); mg.connect(c.frequency);
        const lp = F('lowpass', 3000, .6); lp.frequency.setValueAtTime(3200, t); lp.frequency.setTargetAtTime(1300, t, .3); const a = G(0, d); c.connect(lp); lp.connect(a);
        const tau = clamp(1.6 - (m - 60) * .03, .6, 2.4); a.gain.setValueAtTime(0, t); a.gain.linearRampToValueAtTime(v, t + .006); a.gain.setTargetAtTime(0, t + .006, tau); a.gain.setTargetAtTime(0, t + dur + .05, .35);
        track(c, t, t + dur + 2.2, true); track(mod, t, t + dur + 2.2, false); },
      pad(d, t, m, dur, v) { const f = mtof(m), lp = F('lowpass', 850, .3), a = G(0, d); lp.connect(a); const at = Math.min(1.5, dur / 3);
        a.gain.setValueAtTime(0, t); a.gain.linearRampToValueAtTime(v, t + at); a.gain.setValueAtTime(v, t + dur); a.gain.setTargetAtTime(0, t + dur, .8);
        [-7, 7].forEach((c, i) => { const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = f; o.detune.value = c; o.connect(lp); track(o, t, t + dur + 4, i === 0); }); },
      pluck(d, t, m, dur, v, dark) { const f = mtof(m), lp = F('lowpass', 2800, 1), a = G(0, d); lp.frequency.setValueAtTime(dark ? 1400 : 3000, t); lp.frequency.setTargetAtTime(dark ? 260 : 420, t, .08); lp.connect(a);
        a.gain.setValueAtTime(0, t); a.gain.linearRampToValueAtTime(v, t + .003); a.gain.setTargetAtTime(0, t + .003, dark ? .45 : .35);
        const o1 = ctx.createOscillator(); o1.type = 'sawtooth'; o1.frequency.value = f; const o2 = ctx.createOscillator(); o2.type = 'triangle'; o2.frequency.value = f * 1.002; o1.connect(G(.5, lp)); o2.connect(lp);
        track(o1, t, t + 2.6, true); track(o2, t, t + 2.6, false); },
      bell(d, t, m, dur, v) { bell(d, t, mtof(m), v, 1.6); },
      softbass(d, t, m, dur, v) { const o = ctx.createOscillator(); o.type = 'triangle'; o.frequency.value = mtof(m); const lp = F('lowpass', 500, .5), a = G(0, d); o.connect(lp); lp.connect(a);
        a.gain.setValueAtTime(0, t); a.gain.linearRampToValueAtTime(v, t + .02); a.gain.setTargetAtTime(v * .55, t + .02, .3); a.gain.setTargetAtTime(0, t + dur, .15); track(o, t, t + dur + 1, true); },
      drone(d, t, m, dur, v) { const f = mtof(m), a = G(0, d); a.gain.setValueAtTime(0, t); a.gain.linearRampToValueAtTime(v, t + 2); a.gain.setValueAtTime(v, t + Math.max(2, dur)); a.gain.setTargetAtTime(0, t + Math.max(2, dur), 1.2);
        const trem = ctx.createOscillator(); trem.frequency.value = .17; trem.connect(G(v * .25)).connect(a.gain);
        [[1, 1], [1.5, .45], [2, .2]].forEach(([r, g], i) => { const o = ctx.createOscillator(); o.frequency.value = f * r; o.detune.value = rr(-3, 3); o.connect(G(g, a)); track(o, t, t + dur + 7, i === 0); }); track(trem, t, t + dur + 7, false); },
      flute(d, t, m, dur, v) { const f = mtof(m), o = ctx.createOscillator(); o.frequency.value = f; const vib = ctx.createOscillator(); vib.frequency.value = 5; const vg = G(0); vg.gain.setValueAtTime(0, t); vg.gain.linearRampToValueAtTime(f * .006, t + .4); vib.connect(vg); vg.connect(o.frequency);
        const a = G(0, d); a.gain.setValueAtTime(0, t); a.gain.linearRampToValueAtTime(v, t + .07); a.gain.setValueAtTime(v * .9, t + dur); a.gain.setTargetAtTime(0, t + dur, .12); o.connect(a);
        const br = nz(a, t, { f: f * 2, q: 3, dur: Math.max(.15, dur), g: .12, a: .05 }); track(o, t, t + dur + 1, true); track(vib, t, t + dur + 1, false); },
      bowed(d, t, m, dur, v) { const f = mtof(m), lp = F('lowpass', 1300, .5), a = G(0, d); lp.connect(a); a.gain.setValueAtTime(0, t); a.gain.linearRampToValueAtTime(v, t + .4); a.gain.setValueAtTime(v, t + dur); a.gain.setTargetAtTime(0, t + dur, .4);
        const vib = ctx.createOscillator(); vib.frequency.value = 4.6; const vg = G(f * .004); vib.connect(vg);
        [-5, 5].forEach((c, i) => { const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.value = f; o.detune.value = c; vg.connect(o.frequency); o.connect(G(.5, lp)); track(o, t, t + dur + 3, i === 0); }); track(vib, t, t + dur + 3, false); },
      glass(d, t, m, dur, v) { const f = mtof(m), c = ctx.createOscillator(), mod = ctx.createOscillator(); c.frequency.value = f; mod.frequency.value = f * 3.5; const mg = G(0); mg.gain.setValueAtTime(f * .9, t); mg.gain.setTargetAtTime(f * .1, t, .5); mod.connect(mg); mg.connect(c.frequency);
        const a = G(0, d); c.connect(a); a.gain.setValueAtTime(0, t); a.gain.linearRampToValueAtTime(v, t + .015); a.gain.setTargetAtTime(0, t + .015, 1.6); track(c, t, t + 7, true); track(mod, t, t + 7, false); }
    };

    // =================================================================== MOOD VOICES + LOOKAHEAD SCHEDULER
    function levelAt(v, t) { if (t <= v.f0) return v.from; if (t >= v.f0 + v.fd) return v.to; const x = (t - v.f0) / v.fd, k = Math.floor(x * 8), a = k / 8, b = (k + 1) / 8, cv = y => (v.to > v.from ? v.from + (v.to - v.from) * Math.sin(y * Math.PI / 2) : v.to + (v.from - v.to) * Math.cos(y * Math.PI / 2)); return cv(a) + (cv(b) - cv(a)) * (x - a) / (b - a); }
    function fade(v, to, dur) { const t = now() + .01, cur = levelAt(v, t), p = v.out.gain; p.cancelScheduledValues(t); p.setValueAtTime(cur, t); v.from = cur; v.to = to; v.f0 = t; v.fd = dur;
      for (let k = 1; k <= 8; k++) p.linearRampToValueAtTime(levelAt(v, t + dur * k / 8), t + dur * k / 8); }
    function newVoice(name, xf) { const M = MOODS[name]; const v = { name, M, out: G(0, musicMix), q: [], cursor: now() + .1, sect: 'phrase', n: 0, lastMel: -1, lastProg: -1, from: 0, to: 0, f0: 0, fd: 0, dead: false, deadT: 0 };
      if (xf > 0) fade(v, M.gain, xf); else { v.out.gain.value = M.gain; v.from = v.to = M.gain; } return v; }
    function switchMood(name, xf) { if (!E.useMusic) { E.mood = name; E.moodSince = E.T; return; } xf = xf === undefined ? (name === 'danger' ? 4 : 6) : xf;
      for (const v of E.mv) if (!v.dead && v.to > 0) { fade(v, 0, xf); v.deadT = now() + xf + .05; }
      E.mv.push(newVoice(name, E.mood === null && !E.primedMusic ? (opt.prime ? 0 : 2.5) : xf)); E.mood = name; E.moodSince = E.T; }
    function ev(v, t, fn) { v.q.push({ t, fn }); }
    const human = () => (rnd() - .5) * .02, hv = x => x * (.85 + rnd() * .3);
    function planPhrase(v) { const M = v.M, beat = 60 / M.bpm, bar = beat * M.meter, t0 = v.cursor, bars = 4;
      let pi = Math.floor(rnd() * M.prog.length); if (pi === v.lastProg && M.prog.length > 1) pi = (pi + 1) % M.prog.length; v.lastProg = pi; const prog = M.prog[pi];
      let mi = Math.floor(rnd() * M.mel.length); if (mi === v.lastMel && M.mel.length > 1) mi = (mi + 1 + Math.floor(rnd() * (M.mel.length - 1))) % M.mel.length; v.lastMel = mi;
      for (let b = 0; b < bars; b++) { const tb = t0 + b * bar, root = prog[b % prog.length], tones = [root, root + 2, root + 4];
        if (M.chord) { const C = M.chord; if (C.style === 'hold') tones.forEach(dg => ev(v, tb, () => INST[C.inst](v.out, tb, degMidi(M, dg, C.oct), bar + .25, C.vel)));
          else { const pat = M.meter === 3 ? [0, 1, 2] : [0, 1, 2, 1]; pat.forEach((ix, k) => { const tt = tb + k * beat + human(); ev(v, tt, () => INST[C.inst](v.out, tt, degMidi(M, tones[ix], C.oct), beat * 1.5, hv(C.vel))); }); } }
        if (M.bass) { const B = M.bass; B.pat.forEach(([off, bt, bd]) => { const tt = tb + bt * beat; ev(v, tt, () => INST[B.inst](v.out, tt, degMidi(M, root + off, B.oct), bd * beat, hv(B.vel), B.dark)); }); }
        if (M.sparkle && rnd() < M.sparkle.p) { const S = M.sparkle, tt = tb + Math.floor(rnd() * M.meter) * beat + human(), dg = S.deg !== undefined ? S.deg : pick(tones); ev(v, tt, () => INST[S.inst](v.out, tt, degMidi(M, dg, S.oct), beat, hv(S.vel))); } }
      if (M.drone) { const D = M.drone; ev(v, t0, () => INST[D.inst](v.out, t0, degMidi(M, 0, D.oct), bars * bar, D.vel)); }
      let tt = t0; const mel = M.mel[mi], vary = RR() || rnd() < .25;
      mel.forEach(([dg, bt], k) => { if (dg !== null && !(vary && k > 0 && k < mel.length - 1 && rnd() < .15)) { const t = tt + human(), dur = bt * beat; ev(v, t, () => INST[M.lead.inst](v.out, t, degMidi(M, dg, M.lead.oct), dur, hv(M.lead.vel))); v.lastDeg = dg; } tt += bt * beat; });
      v.cursor = t0 + bars * bar; }
    function planRest(v) { const M = v.M, beat = 60 / M.bpm, bar = beat * M.meter, t0 = v.cursor; let bars = M.rest[0] + Math.floor(rnd() * (M.rest[1] - M.rest[0] + 1)); if (RR()) bars++;
      let len = bars * bar; v.n++; if (v.n % 3 === 0 && rnd() < .7) len += rr(M.silence[0], M.silence[1]) * (RR() ? 1.3 : 1);
      if (len > 0 && M.restPad && M.chord && rnd() < .5) ev(v, t0, () => INST.pad(v.out, t0, degMidi(M, 0, M.chord.oct), Math.min(len, bar * 2), M.chord.vel * .6));
      if (len > 0 && M.drone && rnd() < .6) ev(v, t0 - .5, () => INST[M.drone.inst](v.out, t0 - .5, degMidi(M, 0, M.drone.oct), Math.min(len, bar * 2), M.drone.vel * .8));
      if (len > bar && v.lastDeg !== undefined && rnd() < .35) { const t = t0 + bar + Math.floor(rnd() * M.meter) * beat; ev(v, t, () => INST[M.lead.inst](v.out, t, degMidi(M, v.lastDeg, M.lead.oct), beat * 2, M.lead.vel * .6)); }
      v.cursor = t0 + len; }
    function pump() { if (!E.useMusic) return; const tnow = now(), hz = tnow + LOOKAHEAD;
      for (const v of E.mv) { if (v.dead) continue; if (v.deadT && tnow > v.deadT) { v.dead = true; v.q = []; continue; }
        while (v.cursor < tnow + 2) { if (v.sect === 'phrase') { planPhrase(v); v.sect = 'rest'; } else { planRest(v); v.sect = 'phrase'; } }
        if (v.q.length) { const keep = []; for (const e of v.q) { if (e.t < hz) { if (e.t > tnow - .05) { try { e.fn(); } catch (x) { } } } else keep.push(e); } v.q = keep; } }
      E.mv = E.mv.filter(v => !(v.dead && tnow > v.deadT + 9 && (v.out.disconnect(), true))); }

    // =================================================================== TICK
    function tick(dt) { dt = clamp(num(dt, 0), 0, .5); E.T += dt; const s = E.s = sense(E.world);
      let want = E.forced || wantMood(s); if (s.threatD < 140) E.lastThreat = E.T;
      if (E.mood === null) switchMood(want);
      else if (want !== E.mood) {
        if (want === 'danger') switchMood(want);
        else if (E.mood === 'danger') { if (E.T - E.lastThreat > DANGER_CALM) switchMood(want); }
        else { if (E.cand !== want) { E.cand = want; E.candT = E.T; } if (E.forced || (E.T - E.moodSince >= MOOD_HOLD && E.T - E.candT >= 2)) switchMood(want); } }
      else E.cand = null;
      E.ambAcc += dt; if (E.ambAcc >= .25 || !E.primed) { E.ambAcc = 0; ambUpdate(s); E.primed = true; }
      ambEvents(s, dt); }

    // =================================================================== SFX RECIPES (d = destination, t = time, p = pitch multiplier)
    const SFX = {
      wood_gather(d, t, p) { tn(d, t, { f: 180 * p, f2: 120 * p, type: 'triangle', dur: .12, g: .5, count: true }); nz(d, t, { f: 900 * p, q: 3, dur: .06, g: .35 }); tn(d, t + .09, { f: 200 * p, f2: 140 * p, type: 'triangle', dur: .09, g: .3 }); nz(d, t + .1, { f: 3500, q: .8, dur: .12, g: .08, a: .02 }); },
      wood_chop(d, t, p) { nz(d, t, { f: 1400 * p, q: 1.5, dur: .045, g: .7 }); tn(d, t, { f: 140 * p, f2: 70 * p, dur: .18, g: .6, count: true }); nz(d, t + .01, { type: 'highpass', f: 3000, dur: .03, g: .18 }); },
      stone_gather(d, t, p) { nz(d, t, { f: 2500 * p, q: 8, dur: .03, g: .5 }); nz(d, t + .07, { f: 2900 * p, q: 8, dur: .025, g: .35 }); nz(d, t, { type: 'lowpass', f: 1500, dur: .16, g: .15, a: .01 }); tn(d, t, { f: 220 * p, f2: 160 * p, dur: .06, g: .2, count: true }); },
      stone_pick(d, t, p) { nz(d, t, { f: 3200 * p, q: 12, dur: .05, g: .55 }); tn(d, t, { f: 2300 * p, dur: .08, g: .1, count: true }); tn(d, t, { f: 150 * p, f2: 110 * p, dur: .1, g: .3 }); },
      plant_gather(d, t, p) { nz(d, t, { f: 2500 * p, f2: 1200 * p, q: 1, dur: .25, g: .3, a: .03 }); tn(d, t + .02, { f: 800 * p, type: 'triangle', dur: .03, g: .12, count: true }); },
      leaf_rustle(d, t, p) { for (let i = 0; i < 5; i++) nz(d, t + i * rr(.04, .08), { type: 'highpass', f: 3000 * p, q: .7, dur: rr(.03, .07), g: rr(.08, .2), a: .008 }); tn(d, t, { f: 1, dur: .01, g: 0, count: true }); },
      berry_pop(d, t, p) { tn(d, t, { f: 600 * p, f2: 1100 * p, dur: .07, g: .35, count: true }); nz(d, t, { f: 2000 * p, q: 4, dur: .02, g: .2 }); },
      rare_gather(d, t, p) { SFX.plant_gather(d, t, p); bell(d, t + .05, mtof(88) * p, .08); bell(d, t + .2, mtof(95) * p, .06); shimmer(d, t + .1, .008, 1.5); },
      metal_gather(d, t, p) { [[1850, .14, .35], [2960, .08, .25], [4210, .05, .18]].forEach(([f, g, dd], i) => tn(d, t, { f: f * p, dur: dd, g, count: i === 0 })); nz(d, t, { f: 5000, q: 10, dur: .02, g: .25 }); },
      water_splash(d, t, p) { nz(d, t, { f: 1200 * p, f2: 500 * p, q: .8, dur: .4, g: .45, a: .005, src: 'white' }); for (let i = 0; i < 4; i++) tn(d, t + rr(.05, .35), { f: rr(600, 900) * p, f2: rr(1100, 1600) * p, dur: .04, g: .06, count: i === 0 }); },
      cast(d, t, p) { nz(d, t, { f: 600 * p, f2: 2400 * p, q: 2, dur: .35, a: .15, g: .25 }); for (let i = 0; i < 5; i++) nz(d, t + .1 + i * .045, { f: 3800, q: 6, dur: .008, g: .1 }); tn(d, t, { f: 1, dur: .01, g: 0, count: true }); },
      float_plop(d, t, p) { tn(d, t, { f: 300 * p, f2: 700 * p, dur: .08, g: .35, count: true }); nz(d, t, { type: 'lowpass', f: 800, dur: .12, g: .18 }); },
      nibble(d, t, p) { tn(d, t, { f: 900 * p, f2: 600 * p, dur: .04, g: .12, count: true }); nz(d, t, { f: 1500, q: 3, dur: .02, g: .06 }); },
      bite(d, t, p) { tn(d, t, { f: 250 * p, f2: 550 * p, dur: .1, g: .45, count: true }); nz(d, t, { f: 900 * p, q: 1, dur: .25, g: .3 }); },
      reel(d, t, p) { for (let i = 0; i < 8; i++) nz(d, t + i * .05, { f: 3500 * p, q: 6, dur: .008, g: .28 }); tn(d, t, { f: 1, dur: .01, g: 0, count: true }); },
      catch(d, t, p) { SFX.water_splash(d, t, p); tn(d, t + .15, { f: 660 * p, dur: .35, g: .07, a: .01 }); tn(d, t + .27, { f: 880 * p, dur: .45, g: .06, a: .01 }); },
      lose_fish(d, t, p) { nz(d, t, { type: 'highpass', f: 4000, dur: .03, g: .35 }); tn(d, t + .02, { f: 500 * p, f2: 250 * p, dur: .3, g: .12, type: 'triangle', count: true }); },
      pickup(d, t, p) { tn(d, t, { f: 520 * p, f2: 780 * p, dur: .09, g: .2, count: true }); nz(d, t, { f: 2400, q: 3, dur: .015, g: .08 }); },
      craft_tap(d, t, p) { tn(d, t, { f: 420 * p, type: 'triangle', dur: .06, g: .35, count: true }); nz(d, t, { f: 1800 * p, q: 2, dur: .02, g: .25 }); },
      craft_done(d, t, p) { [0, .12, .24].forEach(k => SFX.craft_tap(d, t + k, p * (1 + k * .2))); bell(d, t + .36, mtof(84) * p, .07); },
      build_knock(d, t, p) { tn(d, t, { f: 160 * p, f2: 110 * p, type: 'triangle', dur: .12, g: .55, count: true }); nz(d, t, { f: 700 * p, q: 2, dur: .05, g: .45 }); tn(d, t + .11, { f: 150 * p, f2: 105 * p, type: 'triangle', dur: .08, g: .12 }); },
      place(d, t, p) { tn(d, t, { f: 110 * p, f2: 70 * p, dur: .15, g: .45, count: true }); nz(d, t, { type: 'lowpass', f: 600, dur: .08, g: .25 }); },
      remove(d, t, p) { nz(d, t, { f: 400 * p, f2: 1200 * p, q: 1, dur: .2, a: .12, g: .2 }); tn(d, t + .1, { f: 180 * p, f2: 260 * p, dur: .12, g: .25, count: true }); },
      eat(d, t, p) { [0, .13, .26].forEach((k, i) => nz(d, t + k + rr(0, .02), { f: rr(1500, 2200) * p, q: 1.5, dur: .05, g: rr(.2, .32) })); tn(d, t, { f: 1, dur: .01, g: 0, count: true }); },
      hurt(d, t, p) { tn(d, t, { f: 140 * p, f2: 60 * p, dur: .2, g: .55, count: true }); nz(d, t, { type: 'lowpass', f: 500, dur: .1, g: .3 }); tn(d, t + .02, { f: 330 * p, f2: 220 * p, type: 'triangle', dur: .25, g: .1 }); },
      footstep_grass(d, t, p) { nz(d, t, { f: 2200 * p, q: .9, dur: .09, g: .16, a: .012 }); nz(d, t, { type: 'lowpass', f: 400, dur: .05, g: .1 }); tn(d, t, { f: 1, dur: .01, g: 0, count: true }); },
      footstep_dirt(d, t, p) { nz(d, t, { type: 'lowpass', f: 700 * p, dur: .07, g: .22 }); tn(d, t, { f: 90 * p, f2: 60 * p, dur: .05, g: .18, count: true }); },
      footstep_wood(d, t, p) { tn(d, t, { f: 220 * p, f2: 180 * p, type: 'triangle', dur: .07, g: .28, count: true }); nz(d, t, { f: 900 * p, q: 3, dur: .04, g: .22 }); },
      footstep_snow(d, t, p) { for (let i = 0; i < 4; i++) nz(d, t + i * rr(.02, .035), { f: 3000 * p, q: .7, dur: rr(.04, .07), a: .01, g: rr(.08, .15) }); tn(d, t, { f: 1, dur: .01, g: 0, count: true }); },
      door(d, t, p) { const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.setValueAtTime(140 * p, t); o.frequency.linearRampToValueAtTime(190 * p, t + .35); const b = F('bandpass', 900, 4), g = G(0, d); o.connect(b); b.connect(g); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(.12, t + .1); g.gain.linearRampToValueAtTime(0, t + .38); track(o, t, t + .4, true); tn(d, t + .38, { f: 110 * p, f2: 70 * p, dur: .15, g: .4 }); nz(d, t + .38, { type: 'lowpass', f: 600, dur: .06, g: .2 }); },
      sleep(d, t, p) { [69, 65, 62].forEach((m, i) => INST.piano(d, t + i * .45, m, .6, .08)); },
      wake(d, t, p) { [62, 65, 69].forEach((m, i) => INST.piano(d, t + i * .3, m, .5, .08)); },
      page(d, t, p) { UIR.page_turn(d, t, p); },
      swing(d, t, p) { nz(d, t, { f: 500 * p, f2: 1800 * p, q: 1.5, dur: .22, a: .1, g: .3 }); tn(d, t, { f: 1, dur: .01, g: 0, count: true }); },
      hit(d, t, p) { nz(d, t, { type: 'lowpass', f: 1200, dur: .06, g: .5 }); tn(d, t, { f: 160 * p, f2: 80 * p, dur: .12, g: .5, count: true }); }
    };
    const SFX_CD = { footstep_grass: .12, footstep_dirt: .12, footstep_wood: .12, footstep_snow: .12, reel: .35, eat: .4, door: .3, sleep: 1.5, wake: 1.5, cast: .3, catch: .5, craft_done: .4, rare_gather: .3, page: .12 };
    const UIR = {
      open(d, t, p) { tn(d, t, { f: 180 * p, f2: 120 * p, type: 'triangle', dur: .12, g: .22, count: true }); nz(d, t + .02, { f: 1800 * p, f2: 3200 * p, q: .8, dur: .18, g: .1, a: .04 }); },
      close(d, t, p) { nz(d, t, { f: 3000 * p, f2: 1500 * p, q: .8, dur: .14, g: .08, a: .02 }); tn(d, t + .08, { f: 150 * p, f2: 100 * p, type: 'triangle', dur: .1, g: .22, count: true }); },
      page_turn(d, t, p) { nz(d, t, { f: 1200 * p, f2: 4200 * p, q: .7, dur: .22, g: .11, a: .08 }); nz(d, t + .16, { f: 2600 * p, f2: 1400 * p, q: .8, dur: .12, g: .06 }); tn(d, t, { f: 1, dur: .01, g: 0, count: true }); },
      hover(d, t, p) { tn(d, t, { f: 1400 * p, dur: .025, g: .025, count: true }); },
      select(d, t, p) { tn(d, t, { f: 520 * p, f2: 500 * p, type: 'triangle', dur: .06, g: .14, count: true }); nz(d, t, { f: 2200, q: 3, dur: .015, g: .05 }); },
      confirm(d, t, p) { tn(d, t, { f: mtof(67) * p, type: 'triangle', dur: .25, g: .09, a: .004, count: true }); tn(d, t + .09, { f: mtof(72) * p, type: 'triangle', dur: .35, g: .08, a: .004 }); },
      cancel(d, t, p) { tn(d, t, { f: mtof(72) * p, type: 'triangle', dur: .14, g: .07, count: true }); tn(d, t + .08, { f: mtof(67) * p, type: 'triangle', dur: .22, g: .065 }); },
      error(d, t, p) { tn(d, t, { f: 160 * p, f2: 120 * p, type: 'triangle', dur: .08, g: .2, count: true }); tn(d, t + .12, { f: 150 * p, f2: 110 * p, type: 'triangle', dur: .1, g: .18 }); nz(d, t, { type: 'lowpass', f: 600, dur: .05, g: .08 }); },
      tab(d, t, p) { tn(d, t, { f: 900 * p, type: 'triangle', dur: .03, g: .07, count: true }); nz(d, t, { f: 3000, q: 2, dur: .012, g: .04 }); },
      slider(d, t, p, o) { tn(d, t, { f: (600 + 600 * clamp(num(o.value, .5))) * p, type: 'triangle', dur: .02, g: .045, count: true }); },
      toast(d, t, p) { bell(d, t, mtof(79) * p, .05, 1.2); },
      toast_rare(d, t, p) { bell(d, t, mtof(76) * p, .05, 1.2); bell(d, t + .12, mtof(83) * p, .045, 1.4); shimmer(d, t + .1, .005, 1.6); }
    };
    const UI_CD = { hover: .05, slider: .04, tab: .06 };
    const CRE = {
      howl(d, t, p) { const o = ctx.createOscillator(); o.type = 'sawtooth'; o.frequency.setValueAtTime(200 * p, t); o.frequency.linearRampToValueAtTime(290 * p, t + .6); o.frequency.exponentialRampToValueAtTime(95 * p, t + 2.2);
        const vib = ctx.createOscillator(); vib.frequency.value = 5; vib.connect(G(6)).connect(o.frequency); const lp = F('lowpass', 900, .7), g = G(0, d); o.connect(lp); lp.connect(g);
        g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(.16, t + .4); g.gain.setTargetAtTime(0, t + 1.6, .25); track(o, t, t + 2.6, true); track(vib, t, t + 2.6, false); nz(d, t, { f: 600, q: 1, dur: 2, a: .4, g: .04 }); },
      call(d, t, p) { const o = ctx.createOscillator(); o.type = 'triangle'; o.frequency.setValueAtTime(300 * p, t); o.frequency.exponentialRampToValueAtTime(180 * p, t + 1.2); const vib = ctx.createOscillator(); vib.frequency.value = 6; vib.connect(G(4)).connect(o.frequency);
        const g = G(0, d); o.connect(g); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(.09, t + .15); g.gain.setTargetAtTime(0, t + .9, .12); track(o, t, t + 1.5, true); track(vib, t, t + 1.5, false); },
      tick(d, t, p) { nz(d, t, { f: 1800 * p, q: 6, dur: .02, g: .35 }); nz(d, t + .07, { f: 1500 * p, q: 6, dur: .015, g: .2 }); tn(d, t, { f: 1, dur: .01, g: 0, count: true }); },
      groan(d, t, p) { tn(d, t, { type: 'sawtooth', f: 90 * p, f2: 60 * p, dur: .7, a: .12, g: .16, lp: 400, count: true }); },
      rumble(d, t, p) { tn(d, t, { type: 'triangle', f: 60 * p, f2: 35 * p, dur: 1, a: .15, g: .3, count: true }); nz(d, t, { type: 'lowpass', f: 120, src: 'brown', dur: 1, a: .2, g: .4 }); },
      thud(d, t, p) { tn(d, t, { f: 120 * p, f2: 45 * p, dur: .2, g: .5, count: true }); nz(d, t, { type: 'lowpass', f: 400, dur: .06, g: .3 }); },
      swing: (d, t, p) => SFX.swing(d, t, p), hit: (d, t, p) => SFX.hit(d, t, p), hurt: (d, t, p) => SFX.hurt(d, t, p),
      chime(d, t, p) { bell(d, t, 1320 * p, .07, 1.4); bell(d, t + .05, 1980 * p, .04, 1.2); }
    };
    function oneShot(table, cds, defCd, name, o, dest, maxD, ref) { const r = table[name]; if (!r) return false; o = o || {}; const tnow = now(), key = dest === uiIn ? 'ui:' + name : name;
      const cd = (cds[name] !== undefined ? cds[name] : defCd) * (RR() ? 1.5 : 1), last = E.last[key] === undefined ? -9 : E.last[key]; if (tnow - last < cd) return false;
      const rep = E.rep[key] = tnow - last < .6 ? (E.rep[key] || 0) + 1 : 0; E.last[key] = tnow; const spread = RR() ? .12 : .07;
      const p = num(o.pitch, 1) * (1 + (rnd() - .5) * spread * 2) * (rep ? 1 + ((rep % 3) - 1) * .03 : 1), vol = num(o.vol, 1) * rr(.88, 1.06) * Math.pow(.88, Math.min(rep, 4));
      const d = spatial(dest, o, vol, maxD, ref); if (!d) return false; try { r(d, tnow + .005, p, o); } catch (e) { return false; } return true; }
    const STINGS = {
      discovery(d, t) { INST.piano(d, t, 67, .6, .14); INST.piano(d, t + .28, 74, 1.2, .13); return 1.8; },
      rare(d, t) { [74, 78, 81].forEach((m, i) => { bell(d, t + i * .22, mtof(m), .07, 1.8); INST.piano(d, t + i * .22, m - 12, .8, .06); }); shimmer(d, t + .4, .006, 2.5); return 2.6; },
      recipe(d, t) { bell(d, t, mtof(76), .07, 1.6); return 1.4; },
      milestone(d, t) { [60, 64, 67, 72].forEach((m, i) => INST.piano(d, t + i * .16, m, 1.2, .1)); [48, 55, 64].forEach(m => INST.pad(d, t, m, 2.5, .03)); return 3; },
      festival(d, t) { [53, 60].forEach(m => INST.drone(d, t, m, 2.5, .04)); [77, 81, 84].forEach((m, i) => bell(d, t + .3 + i * .3, mtof(m), .06, 1.8)); return 3.2; }
    };
    function sting(kind) { const r = STINGS[kind]; if (!r) return false; const tnow = now(), key = 'sting:' + kind; if (tnow - (E.last[key] === undefined ? -9 : E.last[key]) < 1.5) return false; E.last[key] = tnow;
      const t = tnow + .02, len = r(stingBus, t); const p = duck.gain; p.cancelScheduledValues(t); p.setValueAtTime(p.value, t); p.linearRampToValueAtTime(.35, t + .3); p.setValueAtTime(.35, t + len); p.linearRampToValueAtTime(1, t + len + 1.5); return true; }
    E.api = {
      tick, pump, applySettings, sting, sense: () => E.s,
      play: (n, o) => oneShot(SFX, SFX_CD, .07, n, o, bus.sfx, 480, 100),
      ui: (n, o) => oneShot(UIR, UI_CD, .08, n, Object.assign({}, o || {}, { x: undefined }), uiIn),
      creature: (k, x, y) => oneShot(CRE, {}, .1, k, { x, y }, ['hurt', 'swing', 'hit'].includes(k) ? bus.sfx : bus.creatures, 420, 110),
      forceMood(m, xf) { if (!MOODS[m]) return false; E.forced = m; if (m !== E.mood) switchMood(m, xf); return true; },
      clearForce() { E.forced = null; },
      debug() { const layers = {}; for (const k in A) layers[k] = +A[k].gain.value.toFixed(4); return { mood: E.mood, layers, voices: E.voices, moodVoices: E.mv.filter(v => !v.dead).map(v => ({ name: v.name, level: +levelAt(v, now()).toFixed(3), to: v.to })), ctxState: ctx.state }; },
      E
    };
    return E.api;
  }

  // ======================================================================= PUBLIC WRAPPER
  let world = {}, ctx = null, eng = null, timer = null, visBound = false;
  function load() { const o = Object.assign({}, DEFAULTS); try { const s = JSON.parse(localStorage.getItem(KEY) || '{}') || {}; for (const k in DEFAULTS) { if (typeof s[k] === typeof DEFAULTS[k]) o[k] = typeof s[k] === 'number' ? clamp(s[k]) : s[k]; } } catch (e) { } return o; }
  const settings = load();
  const Sound = {
    settings, MOODS: Object.keys(MOODS),
    init(w) { world = w || {}; Object.assign(settings, load()); if (eng) { eng.E.world = world; eng.applySettings(); } return Sound; },
    start() { const AC = window.AudioContext || window.webkitAudioContext; if (!AC) return Promise.resolve(false);
      if (!ctx) { try { ctx = new AC({ latencyHint: 'interactive' }); } catch (e) { return Promise.resolve(false); } eng = createEngine(ctx, { world, settings }); eng.tick(0); eng.pump(); timer = setInterval(() => { try { eng.pump(); } catch (e) { } }, TICK_MS); }
      if (!visBound && typeof document !== 'undefined') { visBound = true; document.addEventListener('visibilitychange', () => { if (!ctx) return; if (document.hidden) ctx.suspend().catch(() => { }); else ctx.resume().catch(() => { }); }); }
      if (ctx.state === 'suspended' && !(typeof document !== 'undefined' && document.hidden)) return ctx.resume().then(() => true, () => false);
      return Promise.resolve(true); },
    tick(dt) { if (eng) { try { eng.tick(dt); } catch (e) { } } },
    play(name, opts) { return eng ? eng.play(name, opts) : false; },
    ui(name, opts) { return eng ? eng.ui(name, opts) : false; },
    creature(kind, x, y) { return eng ? eng.creature(kind, x, y) : false; },
    sting(kind) { return eng ? eng.sting(kind) : false; },
    setVolume(b, v) { if (!BUSES.includes(b) && b !== 'master') return false; settings[b] = clamp(num(+v, DEFAULTS[b])); if (eng) eng.applySettings(); Sound.save(); return true; },
    setMusicMuted(m) { settings.musicMuted = !!m; if (eng) eng.applySettings(); Sound.save(); return settings.musicMuted; },
    setMuted(m) { settings.muted = !!m; if (eng) eng.applySettings(); Sound.save(); return settings.muted; },
    save() { try { localStorage.setItem(KEY, JSON.stringify(settings)); } catch (e) { } },
    mood() { return eng ? eng.E.mood : wantMood(sense(world)); },
    debug() { if (!eng) return { mood: Sound.mood(), layers: {}, voices: 0, ctxState: 'none' }; return eng.debug(); },
    // ---- test hooks (not used by the game)
    _wantMood: w => wantMood(sense(w)), _engine: () => eng,
    // spec: { seconds, sampleRate, seed, world, music, ambience, settings, prime, onStep(t, engine) } → Promise<AudioBuffer>
    _renderOffline(spec) { const sr = spec.sampleRate || 44100, secs = spec.seconds || 8; const OAC = window.OfflineAudioContext || window.webkitOfflineAudioContext;
      const octx = new OAC(2, Math.ceil(secs * sr), sr); const st = Object.assign({}, DEFAULTS, spec.settings || {});
      const e = createEngine(octx, { world: spec.world || {}, settings: st, seed: spec.seed == null ? 1 : spec.seed, music: spec.music, ambience: spec.ambience, prime: spec.prime !== false });
      const step = .1; e.tick(0); e.pump();
      for (let i = 1; i * step < secs - .05; i++) { const t = i * step; octx.suspend(t).then(() => { try { if (spec.onStep) spec.onStep(t, e); e.tick(step); e.pump(); } catch (x) { console.error(x); } octx.resume(); }); }
      return octx.startRendering().then(buf => { spec.engine = e; return buf; }); }
  };
  return Sound;
})();
