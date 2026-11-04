// MOSSlight social simulation: inhabitants with routines, memories, moods, multi-dimensional relationships, advice,
// gifts, promises and personal storylines. Data: assets/social/cast.json (tools/social_data.py). This file names no
// character. It works entirely offline; a future language-model voice may only be plugged in through Provider below,
// and anything it proposes is checked against stored memories before a character may say it.
window.Social = (() => {
  let D = null, W = null, A = null, IDX = null, AW = 0, PIDX = null, PORT = null, T = 0; const CH = {}; const S = {}; const L = {};
  const listeners = {}; const on = (e, cb) => (listeners[e] = listeners[e] || []).push(cb); const emit = (e, ...a) => (listeners[e] || []).forEach(cb => cb(...a));
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  // short sentences go to the kit's notes; discoveries, promises and storylines to its toasts (the build module's floating text is the fallback)
  const notice = (msg, secs) => { if (!msg) return; if (window.UIKit && UIKit.note) UIKit.note(msg, secs); else W.Build.FX.say(msg, secs); };
  const toast = o => { const k = window.UIKit; if (!k || !k.toast) return; const fit = s_ => { s_ = String(s_ || ''); if (k.measure(s_) <= 136) return s_; while (s_.length > 1 && k.measure(s_ + '…') > 136) s_ = s_.slice(0, -1); return s_.replace(/[\s,.;:]+$/, '') + '…'; }; k.toast({ ...o, title: fit(o.title), sub: o.sub ? fit(o.sub) : o.sub }); };
  const P = () => W.Player; const day = () => W.Survival.Clock.day; const hour = () => W.WorldClock.hour(); const now = () => day() * 24 + hour();
  const PH = { dawn: 'dawn', dawn_transition: 'dawn', day: 'day', sunset: 'dusk', early_night: 'night', deep_night: 'deep' };
  const period = () => PH[W.Survival.Clock.phase()] || 'day';
  const weather = () => { const w = W.WeatherState; if (w.intensity < .15) return 'clear'; return w.kind === 'light_rain' || w.kind === 'heavy_rain' ? 'rain' : w.kind; };
  const itemName = id => (W.Gather.DB.get(id) || { name: id }).name; const itemCat = id => (W.Gather.DB.get(id) || {}).category;
  const hash = s => { let h = 2166136261; for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619); return ((h >>> 0) % 100000) / 100000; };
  const agoText = h => { const d = Math.floor(h / 24); if (h < 6) return 'earlier today'; if (d < 1) return 'yesterday'; if (d < 2) return 'yesterday'; if (d < 7) return `${d} days ago`; if (d < 14) return 'last week'; return `${Math.round(d / 7)} weeks ago`; };
  const anchor = (c, a) => a ? (D.water[a] && CH[c].movement === 'swim' ? D.water[a] : D.anchors[a] || D.water[a]) : null;

  // ================================================================= persistent state per character
  function qstate(c, q) { const st = S[c]; return st.qs[q.id] = st.qs[q.id] || { stage: -1, ready: false, data: {}, done: false }; }
  function chapters(c) { const ch = CH[c]; const out = []; if (ch.quest) out.push(ch.quest); const q2 = ch.quest2; if (q2 && ch.quest) { const c1 = S[c].qs[ch.quest.id]; if (c1 && c1.done) { const v = q2.variants ? q2.variants[c1.choice] || q2.variants.default : q2; if (v) out.push(v); } } return out; }
  function activeQ(c) { for (const q of chapters(c)) { const s_ = qstate(c, q); if (!s_.done) return q; } return null; }
  function fresh(id) { const r = {}; for (const d of D.dims) r[d] = 0; return alias(id, { met: false, metT: null, lastTalk: null, talkDays: [], chatsToday: 0, chatDay: -1, rel: r, rlog: [], mood: { state: CH[id].baseline, i: .3, cause: 'its usual self', src: 'base', t: 0 }, mem: [], memN: 0, flags: {}, facts: {}, known: [], said: [], quest: null, qs: {}, milestones: {}, promises: [], advice: {}, gifts: [], keepsakes: [], seen: {}, ignored: {}, tells: {} }); }
  function alias(c, st) { const q = CH[c].quest; if (q) { st.qs = st.qs || {}; if (st.quest && !st.qs[q.id]) st.qs[q.id] = st.quest; st.qs[q.id] = st.qs[q.id] || { stage: -1, ready: false, data: {}, done: false }; st.quest = st.qs[q.id]; } st.milestones = st.milestones || {}; return st; }

  // ================================================================= MEMORY: meaningful events only, prioritised, bounded
  const CAP = 40; const CAT = { met: 'social', visit: 'social', gift_loved: 'social', gift_liked: 'social', gift_neutral: 'social', gift_disliked: 'negative', gift_repeat: 'social', showed: 'shared', told: 'personal', fact_learned: 'personal', fact_mentioned: 'personal', advice: 'social', advice_outcome: 'social', promise_made: 'social', promise_kept: 'helpful', promise_broken: 'negative', quest_help: 'helpful', quest_choice: 'social', shared_catch: 'shared', protected: 'helpful', witnessed: 'shared', took: 'negative', against_wish: 'negative', ignored: 'negative', trees_cut: 'negative', lied: 'negative', discovery: 'shared' };
  const Memory = {
    add(c, kind, f = {}) { const st = S[c], K = D.memory_kinds[kind] || { sig: .4, sign: 0 }; const mul = (CH[c].memory || {})[kind] || 1;
      if (f.consolidate) { const ex = st.mem.find(m => m.kind === kind && (!f.key || m.key === f.key)); if (ex) { ex.count = (ex.count || 1) + 1; ex.t = now(); ex.day = day(); ex.sig = Math.min(1, ex.sig + .05); Object.assign(ex, f.detail || {}); return ex; } }
      const m = { id: `${c}:${++st.memN}`, c, kind, cat: CAT[kind] || 'social', t: now(), day: day(), sig: clamp((f.sig ?? K.sig) * mul, .05, 1), sign: f.sign ?? K.sign, key: f.key || null, value: f.value ?? null, tags: f.tags || [], ref: f.ref || null, count: 1, recalled: 0, lastRecall: null, ...(f.detail || {}) };
      st.mem.push(m); this.trim(c); emit('memory', c, m); return m; },
    score(m) { const age = (now() - m.t) / 24; return m.sig * (.55 + .45 * Math.exp(-age / 40)) - Math.min(.2, m.recalled * .04); },
    trim(c) { const st = S[c]; while (st.mem.length > CAP) { const cand = st.mem.filter(m => m.sig < .8 && !['quest_help', 'quest_choice', 'promise_kept', 'promise_broken', 'protected', 'lied'].includes(m.kind)); if (!cand.length) break; cand.sort((a, b) => this.score(a) - this.score(b)); st.mem.splice(st.mem.indexOf(cand[0]), 1); } },
    find(c, q = {}) { const types = q.type ? [].concat(q.type) : null; return S[c].mem.filter(m => (!types || types.includes(m.kind)) && (!q.key || m.key === q.key) && (q.value === undefined || m.value === q.value) && (!q.tags || q.tags.every(t => m.tags.includes(t))) && (q.min_age === undefined || (now() - m.t) / 24 >= q.min_age) && (q.recent === undefined || (now() - m.t) / 24 <= q.recent) && (q.sig === undefined || m.sig >= q.sig)).sort((a, b) => this.score(b) - this.score(a)); },
    important(c, n = 5) { return [...S[c].mem].filter(m => m.kind !== 'visit').sort((a, b) => this.score(b) - this.score(a)).slice(0, n); } };

  // ================================================================= RELATIONSHIP: six dimensions, each change carries its reason
  const Rel = {
    change(c, deltas, reason) { const st = S[c]; const out = {}; for (const [d, v] of Object.entries(deltas || {})) { if (!v) continue; let dv = v; if (d === 'familiarity' && reason === 'talked') { const used = st.flags['fam_' + day()] || 0; dv = Math.max(0, Math.min(v, 3 - used)); st.flags['fam_' + day()] = used + dv; } if (!dv) continue; const lo = ['trust', 'affection'].includes(d) ? -50 : 0; st.rel[d] = clamp(st.rel[d] + dv, lo, 100); out[d] = dv; } if (Object.keys(out).length) { st.rlog.push({ day: day(), d: out, why: reason }); if (st.rlog.length > 30) st.rlog.shift(); emit('rel', c, out, reason); } return out; },
    bond(c) { const w = CH[c].weights, r = S[c].rel; let s = 0, n = 0; for (const d of D.dims) { s += (w[d] || 1) * r[d]; n += (w[d] || 1); } return s / n; },
    tier(c) { const b = this.bond(c); let t = D.tiers[0][1]; for (const [v, nm] of D.tiers) if (b >= v) t = nm; return t; },
    tierIdx: nm => D.tiers.findIndex(t => t[1] === nm) };

  // ================================================================= MOOD: caused, lasting, recovering
  const Mood = {
    set(c, state, i, cause, src = 'event') { const m = S[c].mood; if (src === 'climate' && m.src === 'event' && m.i > .35) return; S[c].mood = { state, i: clamp(i, 0, 1), cause, src, t: now() }; emit('mood', c, S[c].mood); },
    hourly(c) { const m = S[c].mood; if (m.src === 'event') { m.i -= .06; if (m.i > .2) return; } const ctx = context(c); const r = (CH[c].climate || []).find(r => when(c, r.when, ctx)); if (r) { if (m.state !== r.mood || m.src !== 'climate') this.set(c, r.mood, .5, r.cause, 'climate'); } else this.base(c, ctx); },
    base(c, ctx) { const st = S[c]; const lonely = st.met && (CH[c].traits.warmth || 0) > .7 && Rel.bond(c) >= 12 && ctx.absent >= 4; if (lonely) this.set(c, 'lonely', .5, `you have not come by in ${ctx.absent} days`, 'climate'); else if (st.mood.src !== 'event' || st.mood.i <= .2) S[c].mood = { state: CH[c].baseline, i: .3, cause: 'its usual self', src: 'base', t: now() }; },
    expr(c) { return D.moods[S[c].mood.state] || 'calm'; } };

  // ================================================================= CONTEXT and conditions
  const stats = { cutToday: {}, lastFish: null, lastFishDay: -1, kills: 0, firstWeather: {} };
  function context(c) { const st = S[c], l = L[c] || {}, p = P(); const e = l.entry || {};
    const lastT = st.lastTalk == null ? null : st.lastTalk; const absent = lastT == null ? 0 : Math.floor((now() - lastT) / 24);
    return { period: period(), hour: hour(), player_low: playerLow(), on_ridge: p.y < 200, low_visits: st.flags.low_n || 0, hounds: W.Monsters.list.filter(m => (m.type === 'stalker' || m.type === 'howler') && l.x !== undefined && Math.hypot(m.x - l.x, m.y - l.y) < 220).length, season: W.SeasonState.season, weather: weather(), mood: st.mood.state, at: e.at, act: e.act, asleep: !!e.asleep, drowsy: !!e.drowsy, absent, met: st.met, met_days: st.metT == null ? -1 : (now() - st.metT) / 24, bond: Rel.tier(c), rel: st.rel,
      lantern: !!W.Monsters.Health.lantern, fished: W.Fishing.Book.stats.caught, caught_today: stats.lastFishDay === day(), lastFish: stats.lastFish, cut_today: (stats.cutToday[day()] || 0) > 0, monsters_seen: W.Monsters.Stats ? Object.values(W.Monsters.Stats.kills || {}).reduce((a, b) => a + b, 0) + (W.Monsters.list.length ? 1 : 0) : 0,
      monsters_near: W.Monsters.list.filter(m => l.x !== undefined && Math.hypot(m.x - l.x, m.y - l.y) < 200).length, lights: (W.Build.lights ? W.Build.lights().length : 0) + 2, day: day(), wind: W.WeatherState.wind || 0, after_rain: (W.WeatherState.recentRainHours ?? 99) < 10,
      pond_pressure: (W.Fishing.S.stock || {}).pond || 0, festival: window.Festival && window.Festival.active ? window.Festival.active() : null, festival_soon: soonFest(), milestone: st.milestones, trees_cut_recent: Object.entries(stats.cutToday).filter(([d]) => day() - d <= 3).reduce((a, [, v]) => a + v, 0) };
  }
  // how the player is doing: tired or hurt (comfort is only offered when it is true)
  function playerLow() { const E = W.Survival.Energy, H = W.Monsters.Health; return E.current < E.max * .4 || H.cur < H.max * .5; }
  function soonFest() { if (!window.Festival || !window.Festival.data()) return null; for (const f of Object.keys(window.Festival.data().festivals)) { const k = window.Festival.Cal.daysUntil(f); if (k >= 1 && k <= 3) return f; } return null; }
  function when(c, w, ctx) { if (!w) return true; ctx = ctx || context(c); const st = S[c];
    for (const [k, v] of Object.entries(w)) { switch (k) {
      case 'period': case 'season': case 'weather': case 'mood': case 'at': if (!v.includes(ctx[k])) return false; break;
      case 'met': if (ctx.met !== v) return false; break;
      case 'met_days': if (!ctx.met || ctx.met_days < v) return false; break;
      case 'absent': if (ctx.absent < v) return false; break;
      case 'bond': if (Rel.tierIdx(ctx.bond) < Rel.tierIdx(v)) return false; break;
      case 'trust': case 'familiarity': case 'affection': case 'respect': case 'reliability': case 'shared': if (st.rel[k] < v) return false; break;
      case 'hour': if (!(ctx.hour >= v[0] && ctx.hour < v[1])) return false; break;
      case 'player_low': if (ctx.player_low !== v) return false; break;
      case 'hounds': if (ctx.hounds < v) return false; break;
      case 'on_ridge': if (ctx.on_ridge !== v) return false; break;
      case 'low_visits': if (ctx.low_visits < v) return false; break;
      case 'talk_days': if (st.talkDays.length < v) return false; break;
      case 'lantern': if (ctx.lantern !== v) return false; break;
      case 'fished': if (ctx.fished < v) return false; break;
      case 'caught_today': if (ctx.caught_today !== v) return false; break;
      case 'cut_today': if (ctx.cut_today !== v) return false; break;
      case 'monsters_seen': if (ctx.monsters_seen < v) return false; break;
      case 'monsters_near': if (ctx.monsters_near < v) return false; break;
      case 'lights': if (ctx.lights < v) return false; break;
      case 'has': if (!W.Gather.Inventory.count(v)) return false; break;
      case 'day_mod': if (ctx.day % v !== 0) return false; break;
      case 'wind': if (ctx.wind < v) return false; break;
      case 'after_rain': if (ctx.after_rain !== v) return false; break;
      case 'pond_pressure': if (ctx.pond_pressure < v) return false; break;
      case 'trees_cut_recent': if (ctx.trees_cut_recent < v) return false; break;
      case 'met_char': if (!S[v] || !S[v].met) return false; break;
      case 'quest': { const [q, sid] = v.split(':'); const qq = CH[c].quest; if (!qq || qq.id !== q || st.quest.stage < 0 || qq.stages[st.quest.stage].id !== sid) return false; break; }
      case 'drowsy': if (ctx.drowsy !== v) return false; break;
      case 'festival': if (ctx.festival !== v) return false; break;
      case 'festival_soon': if (ctx.festival_soon !== v) return false; break;
      case 'milestone': if (!st.milestones[v]) return false; break;
      case 'no_milestone': if (st.milestones[v]) return false; break;
      case 'ch1': { const q = CH[c].quest; const s1 = q && st.qs[q.id]; if (!s1 || !s1.done || (v !== true && s1.choice !== v && !(Array.isArray(v) && v.includes(s1.choice)))) return false; break; }
      case 'gone': if (!!st.flags.gone !== v) return false; break;
      case 'showing': if (!ctx.showing) return false; break;
      default: break; } }
    return true; }

  // ================================================================= LINE SELECTION: context-scored, memory-bound, never repeating soon
  const Provider = { name: 'authored', compose(c, pool, ctx) { return pick(c, pool, ctx); } };
  let provider = Provider; const convoLog = [];
  function bindMemory(c, q) { const ms = Memory.find(c, q); return ms.find(m => m.lastRecall == null || now() - m.lastRecall > 20) || null; }
  function pick(c, pool, ctx, win = 6) { const st = S[c]; let best = null, bs = -1e9, bm = null;
    for (const l of pool) { if (!when(c, l.when, ctx)) continue; let m = null; if (l.mem) { m = bindMemory(c, l.mem); if (!m) continue; }
      const recentIdx = st.said.lastIndexOf(l.id); if (recentIdx >= 0 && st.said.length - recentIdx <= win) continue;
      const spec = Object.keys(l.when || {}).length; const s = (l.w || 1) + spec * .6 + (m ? 2 + m.sig : 0) + hash(`${day()}|${c}|${st.said.length}|${l.id}`) * .9;
      if (s > bs) { bs = s; best = l; bm = m; } }
    if (!best && win > 1) return pick(c, pool, ctx, 1);   // a quiet character may repeat itself, but never twice running
    return best ? { line: best, mem: bm } : null; }
  function vars(c, mem, extra = {}) { const v = { absent: context(c).absent, weather: weather(), ...extra }; if (mem) { v.mem = { ...mem, itemName: mem.item ? itemName(mem.item) : mem.itemName, ago: agoText(now() - mem.t), agoHours: Math.round(now() - mem.t), detailText: mem.detailText || mem.value || '', count: mem.count }; } const aq = activeQ(c); const q = (aq ? qstate(c, aq) : S[c].quest).data; v.quest = { fish: (q.fish || []).map(itemName).join(', '), partsList: Object.entries(q.delivered || {}).map(([k, n]) => `${itemName(k)}${n > 1 ? ' x' + n : ''}`).join(', ') || 'none yet', fragments: (q.frags || []).map(f => f.text).join('; ') }; v.ctx = { lastFish: stats.lastFish ? itemName(stats.lastFish) : '' }; return v; }
  function fill(t, v) { return t.replace(/\{([a-zA-Z_.]+)\}/g, (_, k) => { let o = v; for (const p of k.split('.')) o = o == null ? '' : o[p]; return o == null ? '' : String(o); }); }
  // A proposal from any provider must cite only memories that exist, belong to this character and predate the line.
  function validate(c, prop) { if (!prop || !prop.line) return false; if (prop.mem) { const m = S[c].mem.find(x => x.id === prop.mem.id); if (!m || m.c !== c || m.t > now()) return false; } if (prop.line.mem && !prop.mem) return false; if (/\{mem\./.test(prop.line.text) && !prop.mem) return false; return true; }
  function say(c, pool, extra = {}) { const ctx = { ...context(c), ...extra.ctx }; let prop = provider.compose(c, pool, ctx); if (provider !== Provider && !validate(c, prop)) prop = Provider.compose(c, pool, ctx); if (!prop) return null;
    const { line, mem } = prop; const st = S[c]; st.said.push(line.id); if (st.said.length > 24) st.said.shift(); if (mem) { mem.recalled++; mem.lastRecall = now(); }
    convoLog.push({ t: now(), c, line: line.id, mem: mem ? mem.id : null, memT: mem ? mem.t : null }); if (convoLog.length > 400) convoLog.shift();
    if (line.fact && !st.facts[line.fact]) { st.facts[line.fact] = { learned: now() }; }
    if (line.learn && !st.known.includes(line.learn)) st.known.push(line.learn);
    if (line.sets) st.flags[line.sets] = true; if (line.reveals && window.Festival && window.Festival.Cal) window.Festival.Cal.discover(line.reveals, 'told by ' + CH[c].name);
    return { text: fill(line.text, vars(c, mem, extra.vars || {})), expr: line.expr, pics: line.pics, id: line.id, mem: mem ? mem.id : null }; }

  // ================================================================= AUTHORED EXCHANGES (docs/narrative/DIALOGUE_LIBRARY.md)
  // Each exchange is a short, written conversation (turns by the character and by the player). The player starts every one of them:
  // "Talk" lets the character open with something that fits the moment, "Say something" lists exchanges that begin with the
  // player's own words, and story moments are offered as their own button that can always be declined.
  const exList = c => CH[c].ex || [];
  const seenEx = (c, id) => !!(S[c] && S[c].flags['seen:' + id]);
  const GAVE = { clean_glass: ['glass_pane', 'glass_shard', 'spore_jar'] };
  function groupAgreed(c) { let n = 0; for (const o in CH) if (o !== c && S[o].met && Rel.tierIdx(Rel.tier(o)) >= 1) n++; return n >= 3; }
  function tokenOk(c, tok) { const i = tok.indexOf(':'), kind = tok.slice(0, i), arg = tok.slice(i + 1), st = S[c];
    switch (kind) {
      case 'seen': { const oc = Object.keys(CH).find(k => arg.startsWith(k + '.')) || c; return seenEx(oc, arg); }
      case 'disc': return !!((S._disc || {})[arg]);
      case 'world': return !!((S._world || {})[arg]);
      case 'met': return !!(S[arg] && S[arg].met);
      case 'gave': { const ids = GAVE[arg] || [arg]; return st.gifts.some(g => ids.includes(g.id)); }
      case 'flag': return arg === 'group_agreed' ? groupAgreed(c) : !!st.flags[arg];
      default: return true; } }
  function reqOk(c, e) { return (e.req || []).every(t => t.split('|').some(a => tokenOk(c, a))); }
  function exOk(c, e, ctx) { if (e.once && seenEx(c, e.id)) return false; if (!when(c, e.w, ctx)) return false; return reqOk(c, e); }
  function exScore(c, e) { return (e.weight || 1) + Object.keys(e.w || {}).length * .6 + (e.req || []).length * .3 + (e.once ? 1.2 : 0) + hash(`${day()}|${c}|${S[c].said.length}|${e.id}`) * .9; }
  function pickEx(c, pools, ctx, o = {}) { const st = S[c]; let best = null, bs = -1e9;
    for (const e of exList(c)) { if (!pools.includes(e.p)) continue; if (!exOk(c, e, ctx)) continue; if (o.specific && !Object.keys(e.w || {}).length && !e.once) continue;
      const ri = st.said.lastIndexOf(e.id); if (ri >= 0 && st.said.length - ri <= 10) continue; const sc = exScore(c, e); if (sc > bs) { bs = sc; best = e; } }
    return best; }
  function applySets(c, e) { for (const t of e.sets || []) { const i = t.indexOf(':'), k = t.slice(0, i), a = t.slice(i + 1); if (k === 'flag') S[c].flags[a] = day(); else if (k === 'world') { S._world = S._world || {}; S._world[a] = true; } } }
  const BEAT_FX = { beat: { trust: 3, affection: 2, shared: 3 }, topic: { familiarity: 1, affection: 1 }, talk: { familiarity: 1 }, meet: {}, gift: {} };
  // play an exchange into the conversation; story beats are marked so the page can treat them as a distinct moment
  function pushEx(c, e, o = {}) { const st = S[c]; st.flags['seen:' + e.id] = day(); st.said.push(e.id); if (st.said.length > 24) st.said.shift(); convoLog.push({ t: now(), c, line: e.id, mem: null, memT: null }); if (convoLog.length > 400) convoLog.shift();
    const emph = e.p === 'beat' || !!o.emph;
    e.turns.forEach(([who, text], i) => push(c, { text: fill(text, vars(c, null)), who: who === 'p' ? 'player' : 'npc', emph, exid: e.id, first: i === 0 }));
    applySets(c, e); const fx = BEAT_FX[e.p]; if (fx && Object.keys(fx).length) Rel.change(c, fx, `a conversation: ${e.tag}`);
    if (e.p === 'beat' && e.tag) Memory.add(c, 'shared_time', { detail: { detailText: e.tag.toLowerCase() }, tags: ['beat'] });
    emit('exchange', c, e.id); }
  function topicLabel(e) { if (e.label) return e.label; const t = (e.turns.find(x => x[0] === 'p') || ['p', e.tag])[1]; return t; }

  // ================================================================= ROUTINES and movement
  function entryFor(c) { if (S[c].flags.gone) return { at: null, act: 'gone' }; if (S[c].flags.away_until && day() < S[c].flags.away_until) return { at: null, act: 'away in the north woods' }; const ctx = context(c); const h = hour(); for (const e of CH[c].schedule) { if (!when(c, e.when, ctx)) continue; const inH = e.frm <= e.to ? (h >= e.frm && h < e.to) : (h >= e.frm || h < e.to); if (inH) return e; } return { at: null, act: 'elsewhere' }; }
  const grid = {}; const CS = 8;
  function freeAt(x, y, fw = 8, fh = 4) { const col = W.DATA.col, w = 768; for (let yy = Math.round(y - fh / 2); yy <= y + fh / 2; yy += 2) for (let xx = Math.round(x - fw / 2); xx <= x + fw / 2; xx += 2) { if (xx < 0 || yy < 0 || xx >= 768 || yy >= 480 || col[yy * w + xx]) return false; } return true; }
  function field(tx, ty) { const key = `${tx | 0},${ty | 0}`; if (grid[key] && T - grid[key].t < 6) return grid[key]; const cols = 768 / CS, rows = 480 / CS; const f = new Int16Array(cols * rows).fill(-1); const q = []; const s = (tx / CS | 0) + (ty / CS | 0) * cols; f[s] = 0; q.push(s);
    for (let i = 0; i < q.length; i++) { const k = q[i], cx = k % cols, cy = k / cols | 0; for (const [a, b] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) { const nx = cx + a, ny = cy + b; if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue; const n = nx + ny * cols; if (f[n] >= 0 || !freeAt(nx * CS + 4, ny * CS + 4)) continue; f[n] = f[k] + 1; q.push(n); } }
    return grid[key] = { f, cols, rows, t: T }; }
  function stepToward(c, tx, ty, dt) { const l = L[c], ch = CH[c], sp = ch.speed * dt; const d = Math.hypot(tx - l.x, ty - l.y); if (d < 2) { l.moving = false; return true; } l.moving = true;
    if (ch.movement === 'float' || ch.movement === 'swim') { const k = Math.min(1, sp / d); l.x += (tx - l.x) * k; l.y += (ty - l.y) * k; l.flip = tx < l.x; return false; }
    const F = field(tx, ty); const cx = l.x / CS | 0, cy = l.y / CS | 0; let best = F.f[cx + cy * F.cols], nxt = null; if (best < 0) best = 1e9;
    for (const [a, b] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [-1, 1], [1, -1], [-1, -1]]) { const nx = cx + a, ny = cy + b; if (nx < 0 || ny < 0 || nx >= F.cols || ny >= F.rows) continue; const v = F.f[nx + ny * F.cols]; if (v >= 0 && v < best && (a === 0 || b === 0 || (F.f[cx + a + cy * F.cols] >= 0 && F.f[cx + (cy + b) * F.cols] >= 0))) { best = v; nxt = [nx * CS + 4, ny * CS + 4]; } }
    const [gx, gy] = (best < 2 || !nxt) ? [tx, ty] : nxt; const dd = Math.hypot(gx - l.x, gy - l.y) || 1; const vx = (gx - l.x) / dd * sp, vy = (gy - l.y) / dd * sp;
    if (Math.abs(vx) > .01) l.flip = vx < 0; let moved = false; if (freeAt(l.x + vx, l.y)) { l.x += vx; moved = true; } if (freeAt(l.x, l.y + vy)) { l.y += vy; moved = true; }
    if (!moved) { l.stuck = (l.stuck || 0) + dt; if (l.stuck > 3) { l.x = tx; l.y = ty; l.stuck = 0; } } else l.stuck = 0; l.anim += dt * 6; return false; }
  function place(c, snap) { const l = L[c], e = entryFor(c); const prevAt = l.entry && l.entry.at; l.entry = e; const ch = CH[c];
    if (!e.at) { l.present = false; return; } let at = e.at; if (e.wander) { if (!l.wanderAt || !e.wander.includes(l.wanderAt) || (T - (l.wanderT || 0) > 25)) { l.wanderAt = e.wander[Math.floor(hash(`${c}${Math.floor(T / 25)}`) * e.wander.length)]; l.wanderT = T; } at = l.wanderAt; }
    const [x, y] = anchor(c, at); l.tx = x; l.ty = y; if (!l.present || snap || l.x === undefined) { l.x = x; l.y = y; } l.present = true; }
  // ================================================================= EVENTS that become memories
  function near(c, r) { const l = L[c]; return l && l.present && !(l.entry || {}).hidden && Math.hypot(l.x - P().x, l.y - P().y) < r; }
  function onCatch(Lf) { if (W.Fishing.S.vista) return; const f = Lf.f; stats.lastFish = f.id; stats.lastFishDay = day();
    for (const c in CH) { if (!S[c].met || !near(c, 110) || (L[c].entry || {}).asleep) continue; if (['common'].includes(f.rarity) && !Lf.isNew) continue; Memory.add(c, 'shared_catch', { tags: [f.rarity], detail: { item: f.id } }); Rel.change(c, { shared: 3, familiarity: 1 }, `you caught a ${f.name} together`); if ((CH[c].traits.curiosity || 0) > .7) Mood.set(c, 'excited', .7, `watching you land a ${f.name}`); }
    for (const c in CH) { const q = activeQ(c), st = S[c]; if (!q) continue; const qs = qstate(c, q); if (qs.stage < 0 || qs.ready) continue; const ob = q.stages[qs.stage].objective;
      if (ob.type === 'catch_distinct' && W.Fishing.S.habitat === ob.habitat) { const set = qs.data.fish = qs.data.fish || []; if (!set.includes(f.id)) set.push(f.id); if (set.length >= ob.n) markReady(c, `${CH[c].name} will want to hear about the fish.`); }
      if (ob.type === 'fish_snag' && W.Fishing.S.habitat === ob.habitat && (!ob.period || ob.period.includes(period())) && !W.Gather.Inventory.count(ob.item)) { const n = (qs.data.tries = (qs.data.tries || 0) + 1); if (n >= (ob.after || 2)) { W.Gather.Inventory.add(ob.item, 1); W.Gather.Journal.record(ob.item, null); notice(ob.found, 6); Memory.add(c, 'discovery', { detail: { detailText: ob.found, item: ob.item }, tags: [q.id] }); markReady(c); } } }
    if (S._fishWith) for (const c in S._fishWith) if (now() - S._fishWith[c] < 2 && near(c, 160)) { Memory.add(c, 'shared_catch', { tags: ['together', f.rarity], detail: { item: f.id } }); Rel.change(c, { shared: 2 }, `you fished together and caught a ${f.name}`); } }
  function onGathered(n, got) { const d = n.def;
    if (d.kind === 'tree_marker') { stats.cutToday[day()] = (stats.cutToday[day()] || 0) + 1; for (const c in CH) { const st = S[c]; if (!(CH[c].memory || {}).trees_cut || !st.met) continue; Memory.add(c, 'trees_cut', { consolidate: true, detail: { lastTree: d.id } }); Rel.change(c, { respect: -2 }, 'you cut a tree'); const claim = st.tells.axe; if (claim && claim !== 'honest' && !st.flags.lied_axe) { st.flags.lied_axe = true; const t = st.mem.find(m => m.kind === 'told' && m.key === 'axe'); Memory.add(c, 'lied', { detail: { detailText: t ? t.value : 'would not cut trees' } }); Rel.change(c, { trust: -10 }, 'you said one thing about axes and did another'); Mood.set(c, 'suspicious', .9, 'you lied about the axe'); } else Mood.set(c, 'sad', .5, 'it heard a tree come down'); } }
    for (const c in CH) { const st = S[c]; if ((CH[c].owns || []).includes(d.id) && st.flags.told_patch) { Memory.add(c, 'took', { detail: { node: d.id } }); Rel.change(c, { trust: -4, affection: -3 }, `you took from ${CH[c].name}'s patch`); Mood.set(c, 'sad', .6, 'someone took its mushrooms'); } } }
  function checkKills() { const k = Object.values(W.Monsters.Stats.kills || {}).reduce((a, b) => a + b, 0); if (k > stats.kills) { for (const c in CH) if (S[c].met && near(c, 130) && ['night', 'deep'].includes(period())) { Memory.add(c, 'protected', { detail: { detailText: 'something from the dark' } }); Rel.change(c, { trust: 6, respect: 3, shared: 3 }, 'you drove something off near it'); Mood.set(c, 'grateful', .8, 'you protected it'); } } stats.kills = k; }
  function checkWitness() { const wk = weather(), s = W.SeasonState.season; const key = `${s}:${wk}:${day() > 0 ? Math.floor(day() / 28) : 0}`; if (!['fog', 'snow'].includes(wk) || stats.firstWeather[key]) return; let any = false; for (const c in CH) if (S[c].met && near(c, 130)) { any = true; Memory.add(c, 'witnessed', { detail: { detailText: wk === 'snow' ? 'the first snow' : 'the fog come in' }, tags: [wk] }); Rel.change(c, { shared: 3 }, `you watched the ${wk === 'snow' ? 'first snow' : 'fog'} together`); } if (any) stats.firstWeather[key] = true; }

  // ================================================================= PROMISES and QUEST objectives
  function promise(c, p) { const pr = { id: `${c}:p${S[c].promises.length + 1}`, what: p.what, due: now() + p.days * 24, check: p.check || null, status: 'open', made: now(), concern: p.concern || null, quest: p.quest || null, visits: [] }; S[c].promises.push(pr); Memory.add(c, 'promise_made', { detail: { detailText: p.what }, ref: pr.id }); return pr; }
  function keep(c, pr) { pr.status = 'kept'; Memory.add(c, 'promise_kept', { detail: { detailText: pr.what }, ref: pr.id }); Rel.change(c, { reliability: 8, trust: 4 }, `you kept your word: ${pr.what}`); Mood.set(c, 'grateful', .8, `you kept your promise`); }
  function breakP(c, pr) { pr.status = 'broken'; Memory.add(c, 'promise_broken', { detail: { detailText: pr.what }, ref: pr.id }); Rel.change(c, { reliability: -10, trust: -5 }, `you did not ${pr.what}`); Mood.set(c, (CH[c].traits.pride || 0) > .5 ? 'frustrated' : 'sad', .7, `you did not ${pr.what}`); }
  function lightNear(a, r) { const [x, y] = D.anchors[a]; return (W.Build.lights ? W.Build.lights() : []).some(l => Math.hypot(l.x - x, l.y - y) < r); }
  function checkPromises() { for (const c in CH) for (const pr of S[c].promises) { if (pr.status !== 'open') continue; const k = pr.check || {};
      if (k.be_at) { const [x, y] = D.anchors[k.be_at] || D.water[k.be_at]; if (Math.hypot(P().x - x, P().y - y) < 40 && (!k.period || k.period.includes(period()))) keep(c, pr); }
      if (k.light_near && lightNear(k.light_near, k.radius || 48)) keep(c, pr);
      if (k.visit_days) { if (near(c, 60) && !pr.visits.includes(day())) pr.visits.push(day()); if (pr.visits.length >= k.visit_days) keep(c, pr); }
      if (pr.status === 'open' && now() > pr.due) breakP(c, pr); } }
  function markReady(c, msg) { const q = activeQ(c); if (!q) return; const qs = qstate(c, q); if (qs.ready) return; qs.ready = true; if (msg) notice(msg, 4); if (S[c].met) toast({ kicker: 'Storyline', title: q.title, sub: `Go and tell ${CH[c].name}`, glyph: 'book' }); }
  function checkObjectives() { for (const c in CH) { const q = activeQ(c), st = S[c]; if (!q) continue; const qs = qstate(c, q); st.quest_ = qs; if (qs.stage < 0 || qs.ready) continue; const ob = q.stages[qs.stage].objective; const p = P();
      if (ob.type === 'be_at') { const [x, y] = D.anchors[ob.at] || D.water[ob.at]; if (Math.hypot(p.x - x, p.y - y) < ob.radius && (!ob.period || ob.period.includes(period())) && (!ob.lantern || W.Monsters.Health.lantern) && (!ob.after_rain || context(c).after_rain)) { notice(ob.found, 6); Memory.add(c, 'discovery', { detail: { detailText: ob.found }, ref: q.id, tags: [q.id] }); markReady(c); } }
      if (ob.type === 'visit_all') { const v = st.quest.data.visited = st.quest.data.visited || []; for (const a of ob.at) { const [x, y] = D.anchors[a]; if (!v.includes(a) && Math.hypot(p.x - x, p.y - y) < ob.radius && (!ob.period || ob.period.includes(period()))) { v.push(a); notice(ob.found, 4); } } if (v.length >= ob.at.length) markReady(c, `${CH[c].name} will want to know.`); }
      if (ob.type === 'escort') { const l = L[c]; const [x, y] = D.anchors[ob.at]; if (!l.follow) continue; if (Math.hypot(l.x - p.x, l.y - p.y) > (ob.lose || 220)) { l.follow = false; qs.data.lost = true; Memory.add(c, 'left_behind', { detail: { detailText: ob.lost_text }, tags: [q.id] }); Rel.change(c, { trust: -6, affection: -3 }, 'you went on ahead and left it behind'); Mood.set(c, 'sad', .7, 'it was left behind'); notice(ob.lost_text, 5); qs.ready = true; continue; }
        if (Math.hypot(p.x - x, p.y - y) < 40 && Math.hypot(l.x - x, l.y - y) < 60 && (!ob.period || ob.period.includes(period()))) { l.follow = false; notice(ob.found, 6); Memory.add(c, 'witnessed', { detail: { detailText: ob.shared }, tags: [q.id] }); Rel.change(c, { shared: 6 }, ob.shared); markReady(c); } }
      if (ob.type === 'signal') { const [x, y] = D.anchors[ob.at]; const here = Math.hypot(p.x - x, p.y - y) < (ob.radius || 40) && (!ob.period || ob.period.includes(period())); const lan = !!W.Monsters.Health.lantern; qs.data.sig = qs.data.sig || []; if (here && lan !== qs.data.last) { qs.data.sig.push(T); qs.data.last = lan; qs.data.sig = qs.data.sig.filter(t => T - t < 8); if (qs.data.sig.length >= ob.toggles) { notice(ob.found, 6); Memory.add(c, 'witnessed', { detail: { detailText: ob.shared }, tags: [q.id] }); markReady(c); } } if (!here) qs.data.last = lan; }
      if (ob.type === 'visit_days') { const vd = qs.data.days = qs.data.days || []; if (near(c, 70) && !vd.includes(day())) vd.push(day()); if (vd.length >= ob.n) markReady(c, ob.found); }
      if (ob.type === 'festival_with') { if (window.Festival.active() === ob.festival && near(c, 90)) markReady(c); } } }
  function checkIgnored() { for (const c in CH) { const st = S[c]; const aq = activeQ(c); const pending = (aq && qstate(c, aq).stage >= 0 && st.flags.offered_quest) || Object.values(st.advice).some(a => a.state === 'offered'); if (!pending || !near(c, 70) || st.lastTalk != null && day() - Math.floor(st.lastTalk / 24) === 0) continue; const k = `d${day()}`; if (st.ignored[k]) continue; st.ignored[k] = true; } }   // no penalty: passing by is always fine (Prompt 14/16 rule); the request simply waits

  // ================================================================= MILESTONES: earned by behaviour and shared history, never by numbers alone
  function milestones(c) { const st = S[c], ctx = context(c); const got = []; for (const m of D.milestones) { if (st.milestones[m.id]) continue; if (!when(c, m.when, ctx)) continue; const n = m.needs || {};
      if (n.memories && !Memory.find(c, { type: n.memories }).length) continue; if (n.shared && st.mem.filter(x => x.cat === 'shared').length < n.shared) continue; if (n.chapter && !(CH[c].quest && (st.qs[CH[c].quest.id] || {}).done)) continue;
      st.milestones[m.id] = { day: day() }; Memory.add(c, 'milestone', { key: m.id, detail: { detailText: m.label }, sig: .75 }); st.flags.newMilestone = m.id; got.push(m.id); emit('milestone', c, m.id); } return got; }
  // ================================================================= ACTIVITIES: offered only inside a conversation you started; declining costs nothing
  function activities(c, list, ctx) { const st = S[c], ch = CH[c], l = L[c]; if (st.flags[c + '_cold']) return; S._fishWith = S._fishWith || {}; for (const a of ch.activities || []) { if (!st.milestones[a.milestone]) continue; if (a.when && !when(c, a.when, ctx)) continue;
      if (a.near && Math.hypot(l.x - D.anchors[a.near][0], l.y - D.anchors[a.near][1]) > (a.radius || 80)) continue; if (a.water && !W.Fishing.nearest(P().x, P().y)) continue;
      const last = st.flags['act_' + a.id]; if (a.every && last != null && day() - last < a.every) continue; if (a.id === 'walk' && l.follow) { list.push({ label: a.stop, fn: () => { l.follow = false; push(c, { text: a.stop_line, expr: 'calm' }); hub(c); } }); continue; }
      list.push({ label: a.label, fn: () => doActivity(c, a) }); } }
  function doActivity(c, a) { const st = S[c], l = L[c]; st.flags['act_' + a.id] = day(); emit('activity', c, a.id);
    if (a.kind === 'fireside') { W.Survival.Activities.performCustom('fireside', { label: 'Sit', heavy: false, energy: 0, minutes: 30, anim: null }, 'social'); W.Survival.Energy.set(Math.min(W.Survival.Energy.max, W.Survival.Energy.current + 6)); const ln = say(c, ch_lines(c, 'fireside')) || { text: a.line }; push(c, ln); Memory.add(c, 'shared_time', { key: 'fireside', consolidate: true, detail: { detailText: 'an evening by the fire' }, tags: ['fireside'] }); Rel.change(c, { shared: 3, affection: 2 }, 'you sat by the fire together'); }
    if (a.kind === 'fish') { S._fishWith[c] = now(); const f = hintFish(c); push(c, { text: f ? fillHint(a.line, f) : a.none, expr: 'calm' }); Memory.add(c, 'shared_time', { key: 'fishing', consolidate: true, detail: { detailText: 'fishing side by side' }, tags: ['fishing'] }); Rel.change(c, { shared: 2, familiarity: 1 }, 'you fished together'); }
    if (a.kind === 'found') { const id = a.items[(st.flags.foundN = (st.flags.foundN || 0) + 1) % a.items.length]; const got = W.Gather.Inventory.add(id, 1); if (got) { W.Gather.Journal.record(id, null); W.Gather.FX.pop(P().x, P().y - 22, [[id, 1]]); } push(c, { text: fill(a.line, { item: (W.Gather.DB.get(id) || { name: id }).name }), expr: 'glad' }); Memory.add(c, 'exchange', { detail: { item: id }, tags: ['exchange'] }); Rel.change(c, { trust: 2, affection: 1 }, 'it shared something it found'); }
    if (a.kind === 'walk') { l.follow = true; push(c, { text: a.line, expr: 'glad' }); UI.conv.choices = []; UI.conv.closing = true; Memory.add(c, 'shared_time', { key: 'walk', consolidate: true, detail: { detailText: 'a walk together' }, tags: ['walk'] }); Rel.change(c, { shared: 2 }, 'you walked together'); return; }
    if (a.kind === 'line') { const ln = say(c, ch_lines(c, a.pool)) || { text: a.line }; push(c, ln); Rel.change(c, { shared: 1 }, a.label.toLowerCase()); }
    hub(c); }
  const ch_lines = (c, pool) => (CH[c].pools || {})[pool] || [];
  function hintFish(c) { const F = W.Fishing; if (!F.data) return null; const cond = F.conditions(); const notCaught = F.data().fish.filter(f => f.habitat === 'pond' && !F.Book.rec[f.id] && !f.event); if (!notCaught.length) return null; return notCaught[Math.floor(hash(`${c}${day()}`) * notCaught.length)]; }
  function fillHint(t, f) { return fill(t, { fish: f.name, clue: f.clue, bait: f.bait[0].replace('_', ' '), when: f.periods.join(' or ') }); }
  function festivalTick() { const f = window.Festival && window.Festival.active && window.Festival.active(); if (f) { S._festSeen = S._festSeen || {}; for (const c in CH) if (S[c].met && near(c, 120)) S._festSeen[c] = f; S._festLast = f; return; }
    if (S._festLast && S._festSeen) { const ff = S._festLast, y = window.Festival.Cal.year(day()); for (const [c, fv] of Object.entries(S._festSeen)) { if (fv !== ff) continue; const talked = S[c].mem.some(m => m.kind === 'festival' && m.key === ff && m.year === y); if (!talked) Memory.add(c, 'saw_at_festival', { key: ff, detail: { detailText: window.Festival.data().festivals[ff].title, year: y }, sig: .3 }); } S._festSeen = {}; } S._festLast = null; }
  // ================================================================= CONVERSATION
  const UI = { conv: null, journal: false, jc: 0, jpage: 0, buttons: [] };
  function begin(c) { const st = S[c], e = (L[c] || {}).entry || {}; W.Build.FX.say('', 0.01);
    UI.conv = { c, queue: [], choices: [], sel: 0, shown: 0, t: 0, open: 0 };
    if (e.asleep || (e.hidden && !e.asleep)) { push(c, say(c, CH[c].asleep) || { text: '...', expr: 'calm' }); UI.conv.choices = [{ label: 'Leave quietly', fn: end }]; if (e.asleep) UI.conv.choices.unshift({ label: 'Leave a gift', fn: () => itemPicker(c, 'gift') }); return; }
    const first = !st.met; const ctx0 = context(c); if (P().y >= 250) st.flags.low_n = Math.min(9, (st.flags.low_n || 0) + 1);
    // chosen before meeting is recorded, so a first meeting gets the first-meeting exchange; later visits open with something that fits the moment, or with what the character is doing
    const opener = first ? exList(c).find(x => x.p === 'meet') || null : pickEx(c, ['talk'], ctx0, { specific: true });
    const noticed = opener || first ? null : say(c, CH[c].notice || []);   /* a line about what is true of the player right now opens the talk when one fits */
    const greet = opener ? null : noticed || (CH[c].greet && CH[c].greet.length ? say(c, CH[c].greet) : null);
    if (first) { st.met = true; st.metT = now(); Memory.add(c, 'met', { detail: { detailText: e.act } }); Rel.change(c, { familiarity: 3 }, 'you met'); emit('met', c); }
    else { Memory.add(c, 'visit', { consolidate: true }); }
    if (opener) pushEx(c, opener); else if (greet) push(c, greet); else push(c, { narr: true, text: `${CH[c].name} is ${e.act || 'here'}.`, expr: 'calm' });
    const fu = followups(c); if (fu) push(c, fu);
    const lastDay = st.lastTalk == null ? null : Math.floor(st.lastTalk / 24); st.lastTalk = now(); if (!st.talkDays.includes(day())) { st.talkDays.push(day()); if (st.talkDays.length > 60) st.talkDays.shift(); Rel.change(c, { familiarity: 2 }, 'talked'); }
    for (const pr of st.promises) if (pr.status === 'open' && pr.check && pr.check.visit_days && !pr.visits.includes(day())) { pr.visits.push(day()); if (pr.visits.length >= pr.check.visit_days) keep(c, pr); }
    const fest = window.Festival && window.Festival.active && window.Festival.active(); if (fest && !first) { const y = window.Festival.Cal.year(day()); if (!st.mem.some(m => m.kind === 'festival' && m.key === fest && m.year === y)) { Memory.add(c, 'festival', { key: fest, detail: { detailText: window.Festival.data().festivals[fest].title, year: y }, tags: [fest] }); Rel.change(c, { shared: 3, affection: 1 }, `you spent the ${window.Festival.data().festivals[fest].title} together`); const fl = say(c, (CH[c].pools || {}).festival || []); if (fl) push(c, fl); } }
    const ms = milestones(c); if (st.flags.newMilestone) { const ml = (CH[c].milestone_lines || {})[st.flags.newMilestone]; if (ml) push(c, { text: ml, expr: 'glad', id: 'milestone:' + st.flags.newMilestone }); st.flags.newMilestone = null; }
    hub(c); }
  function push(c, line) { if (!line) return; UI.conv.queue.push({ ...line, c }); }
  function end() { UI.conv = null; }
  function followups(c) { const st = S[c]; for (const [cid, a] of Object.entries(st.advice)) { if (a.state !== 'given' || now() < a.due) continue; const con = CH[c].concerns.find(k => k.id === cid); if (!con) continue;
      const pr = st.promises.find(p => p.concern === cid); if (a.used === 'practical' && pr && pr.status === 'open') continue;
      let [res, text] = con.followup.outcomes[a.used] || ['mixed', '']; if (res === 'promise') { const kept = pr && pr.status === 'kept'; const parts = text.split('|'); text = kept ? parts[0] : parts[1]; res = kept ? 'good' : 'bad'; }
      if (a.used !== a.stance) text = (CH[c].gesture || CH[c].pictures ? '' : 'I decided otherwise. ') + text;
      a.state = 'done'; a.result = res; const m = Memory.add(c, 'advice_outcome', { detail: { adviceShort: a.short, outcomeText: text, result: res, followed: a.used === a.stance }, ref: cid, tags: [cid, res] });
      if (a.used === a.stance) Rel.change(c, res === 'good' ? { trust: 5, respect: 2 } : res === 'bad' ? { trust: -3 } : { respect: 1 }, `your advice about ${con.id.replace(/_/g, ' ')} turned out ${res}`);
      Mood.set(c, res === 'good' ? (a.used === a.stance ? 'grateful' : 'happy') : res === 'bad' ? 'sad' : 'relaxed', .6, `how ${con.id.replace(/_/g, ' ')} turned out`);
      m.recalled = 1; m.lastRecall = now(); return { text, expr: res === 'good' ? 'glad' : res === 'bad' ? 'troubled' : 'calm', id: 'followup:' + cid, mem: m.id }; }
    return null; }
  // Talk: a memory the character really has comes first; otherwise an authored exchange that fits the moment
  function talkNow(c) { const st = S[c], ch = CH[c], ctx = context(c); const rp = pick(c, ch.recall || [], ctx);
    if (rp && rp.mem) { const l = say(c, ch.recall); push(c, l); if (l) Rel.change(c, { familiarity: 1, affection: l.mem ? 1 : 0 }, 'talked'); return; }
    if ((day() + st.said.length) % 3 !== 0) { const l = say(c, ch.notice || []); if (l) { push(c, l); Rel.change(c, { familiarity: 1 }, 'talked'); return; } }   /* what is true of the player right now comes first, most of the time */
    const e = pickEx(c, ['talk'], ctx); if (e) return pushEx(c, e);
    const l = say(c, [...(ch.recall || []), ...(ch.chat || [])]); push(c, l || { narr: true, text: `${ch.name} is quiet for a moment, and that is fine.`, expr: 'calm' }); if (l) Rel.change(c, { familiarity: 1, affection: l.mem ? 1 : 0 }, 'talked'); }
  function topicList(c, ctx) { const st = S[c]; return exList(c).filter(e => e.p === 'topic' && exOk(c, e, ctx) && !(st.said.lastIndexOf(e.id) >= 0 && st.said.length - st.said.lastIndexOf(e.id) <= 12)).map(e => [exScore(c, e), e]).sort((a, b) => b[0] - a[0]).slice(0, 3).map(x => x[1]); }
  function topicMenu(c, list) { const st = S[c], cv = UI.conv; cv.choices = list.map(e => ({ label: topicLabel(e), fn: () => { st.chatsToday++; pushEx(c, e); hub(c); } })).concat([{ label: 'Never mind', fn: () => hub(c) }]); cv.sel = 0; }
  // a story moment is its own button, and it can always be put off: no penalty, the character keeps it for later
  function beatFor(c, ctx) { const inv = W.Gather.Inventory; return exList(c).filter(e => e.p === 'beat' && exOk(c, e, ctx) && (!e.needs || Object.entries(e.needs).every(([id, n]) => inv.count(id) >= n))).sort((a, b) => a.n - b.n)[0] || null; }
  function beatConfirm(c, e) { const cv = UI.conv, ch = CH[c];
    cv.choices = [{ label: e.stay || 'Stay', fn: () => { if (e.needs) for (const [id, n] of Object.entries(e.needs)) { const inv = W.Gather.Inventory; let left = n; for (let i = inv.slots.length - 1; i >= 0 && left > 0; i--) if (inv.slots[i] && inv.slots[i].id === id) left -= inv.remove(i, left) || 0; } pushEx(c, e, { emph: !e.soft }); if (e.minutes) W.Survival.Clock.advance(e.minutes); hub(c); } },
                  { label: 'Not now', fn: () => { push(c, { text: (D.choices || {})[c] || 'Of course.', expr: 'calm' }); hub(c); } }]; cv.sel = 0; }
  function farewell(c) { const ch = CH[c], st = S[c]; const arr = ch.farewell; if (arr && arr.length) return { text: arr[Math.floor(hash(`${c}bye${day()}${st.said.length}`) * arr.length)], expr: 'calm' };
    return { text: ch.gesture ? '*Its light dips once.*' : ch.pictures ? '*It shows you a small wave.*' : (Rel.tierIdx(Rel.tier(c)) >= 2 ? 'Come back soon.' : '...'), expr: 'calm' }; }
  function hub(c) { const st = S[c], ch = CH[c], cv = UI.conv; const ch_ = []; const ctx = context(c);
    if (st.chatDay !== day()) { st.chatDay = day(); st.chatsToday = 0; }
    if (st.chatsToday < 3) { ch_.push({ label: ch.gesture ? 'Watch it' : ch.pictures ? 'Look at its pictures' : 'Talk', fn: () => { st.chatsToday++; talkNow(c); hub(c); } });
      const tl = topicList(c, ctx); if (tl.length) ch_.push({ label: 'Say something', fn: () => topicMenu(c, tl) }); }
    const bt = beatFor(c, ctx); if (bt) ch_.push({ label: bt.label, fn: () => beatConfirm(c, bt) });
    const q = activeQ(c); if (q) { const qs = qstate(c, q), s = qs.stage; if (s < 0 && when(c, q.stages[0].when, ctx) && when(c, q.requires, ctx)) ch_.push({ label: q.offer || (ch.gesture || ch.pictures ? 'What is troubling it?' : 'Ask if it needs a hand'), fn: () => questStart(c) }); else if (s >= 0) { const stg = q.stages[s]; if (qs.ready || stg.objective.type === 'choice') ch_.push({ label: `${q.title}${qs.ready ? ': tell it' : ''}`, fn: () => questTalk(c) }); if (stg.objective.type === 'deliver') ch_.push({ label: `${q.title}: hand over ${stg.objective.label || 'parts'}`, fn: () => deliver(c) }); if (stg.objective.type === 'escort' && !L[c].follow && !qs.data.lost) ch_.push({ label: stg.objective.go || "Let's go", fn: () => { L[c].follow = true; push(c, { text: stg.objective.start || 'Lead the way.', expr: 'glad' }); cv.choices = []; cv.closing = true; } }); } }
    activities(c, ch_, ctx);
    for (const con of ch.concerns || []) { const a = st.advice[con.id]; if ((!a || a.state === 'offered') && when(c, con.when, ctx)) { ch_.push({ label: ch.gesture || ch.pictures ? 'It seems unsettled' : 'It seems to have something on its mind', fn: () => advise(c, con) }); break; } }
    for (const t of ch.tells || []) { if (!st.tells[t.id] && when(c, t.when, ctx)) { ch_.push({ label: ch.gesture ? 'It is asking you something' : 'It wants to ask you something', fn: () => tell(c, t) }); break; } }
    for (const f of ch.facts || []) { const k = st.facts[f.id]; if (k && !k.mentioned && now() - k.learned >= 18 && when(c, f.when, ctx)) { ch_.push({ label: f.mention, fn: () => mention(c, f) }); break; } }
    if (ch.shows && W.Gather.Inventory.slots.some(s => s && ch.shows.cats.includes(itemCat(s.id)))) ch_.push({ label: ch.shows.label, fn: () => itemPicker(c, 'show') });
    ch_.push({ label: 'Give something', fn: () => itemPicker(c, 'gift') }); ch_.push({ label: 'Goodbye', fn: () => { push(c, farewell(c)); cv.choices = []; cv.closing = true; } });
    cv.choices = ch_; cv.sel = 0; }
  function questStart(c) { const st = S[c], q = activeQ(c), stg = q.stages[0], qs = qstate(c, q); qs.stage = 0; qs.started = now(); qs.data = {}; st.flags.offered_quest = true; toast({ kicker: 'New storyline', title: q.title, sub: `with ${CH[c].name}`, glyph: 'book' }); push(c, { text: fill(stg.talk, vars(c, null)), expr: 'troubled' }); if (stg.objective.promise || stg.promise) promise(c, { ...(stg.promise || {}), what: (stg.promise || {}).what || q.title, days: (stg.promise || {}).days || 6, quest: q.id, check: { quest_stage: 0 } }); Rel.change(c, { trust: 2 }, `it told you about ${q.title.toLowerCase()}`); UI.conv.choices = [{ label: stg.accept || "I'll see what I can do.", fn: () => { Memory.add(c, 'promise_made', { detail: { detailText: q.title }, ref: q.id, tags: [q.id] }); hub(c); } }]; }
  function questTalk(c) { const st = S[c], q = activeQ(c), qs = qstate(c, q); const s = qs.stage, stg = q.stages[s];
    if (stg.objective.type === 'choice') return choice(c, stg);
    if (!qs.ready) { push(c, { text: stg.journal, expr: 'calm' }); return hub(c); }
    qs.ready = false; if (qs.data.lost && stg.objective.on_lost) { const o = stg.objective.on_lost; Memory.add(c, 'quest_choice', { detail: { detailText: o.detail, outcomeText: o.line, choice: 'lost', result: 'bad' }, ref: q.id, tags: [q.id] }); qs.done = true; qs.choice = 'lost'; qs.doneT = now(); push(c, { text: o.line, expr: 'troubled' }); return hub(c); } Memory.add(c, 'quest_help', { detail: { detailText: stg.journal }, ref: q.id, tags: [q.id, stg.id] }); Rel.change(c, { trust: 4, shared: 2 }, `you helped with ${q.title.toLowerCase()}`);
    qs.stage = s + 1; const nx = q.stages[s + 1]; push(c, { text: fill(nx.talk, vars(c, null)), expr: 'calm' }); if (nx.objective.type === 'choice') choice(c, nx); else hub(c); }
  function choice(c, stg) { const ob = stg.objective; const inv = W.Gather.Inventory;
    UI.conv.choices = ob.options.map(o => { let ok = true, why = ''; if (o.needs) for (const [k, n] of Object.entries(o.needs)) if (inv.count(k) < n) { ok = false; why = `needs ${n} ${itemName(k)}`; } if (o.needs_met && !(S[o.needs_met] || {}).met) { ok = false; why = `you have not met ${CH[o.needs_met].name}`; } if (o.needs_light && !lightNear(o.needs_light, 48)) { ok = false; why = 'needs a light set there first'; }
      return { label: o.text + (ok ? '' : ` (${why})`), disabled: !ok, fn: () => resolve(c, stg, o) }; }).concat([{ label: 'Not yet.', fn: () => hub(c) }]); }
  function resolve(c, stg, o) { const st = S[c], q = activeQ(c), qs = qstate(c, q), inv = W.Gather.Inventory;
    if (o.needs) for (const [k, n] of Object.entries(o.needs)) { let left = n; for (let i = 0; i < inv.slots.length && left; i++) { const s = inv.slots[i]; if (s && s.id === k) left -= inv.remove(i, Math.min(left, s.qty)); } }
    let line = o.line; if (o.line_by_trust) line = o.line_by_trust[st.rel.trust >= 20 ? 'high' : 'low'];
    Memory.add(c, 'quest_choice', { detail: { detailText: o.detail || o.text.toLowerCase().replace(/\.$/, ''), outcomeText: line.replace(/^\.\.\./, '').split(' ... ').slice(-1)[0], choice: o.id, result: o.result }, ref: q.id, tags: [q.id, ...(o.tags || [])] });
    Rel.change(c, o.rel || {}, `your choice: ${o.text.toLowerCase()}`); if (o.followup_flag) st.flags[o.followup_flag] = true;
    for (const [oc, x] of Object.entries(o.cross || {})) if (S[oc]) { Memory.add(oc, x.type, { detail: { detailText: x.detail }, tags: ['morel'] }); Rel.change(oc, x.rel || {}, `it heard that you ${x.detail}`); }
    qs.choice = o.id; qs.done = true; qs.doneT = now(); if (q === CH[c].quest) st.flags.secret = true; else st.flags['secret_' + q.id] = true; if (o.sets) for (const f of [].concat(o.sets)) st.flags[f] = true; if (o.gone) st.flags.gone = true; if (o.away) st.flags.away_until = day() + o.away; if (o.keepsake && !st.keepsakes.includes(o.keepsake)) st.keepsakes.push(o.keepsake); if (o.world) S._world = Object.assign(S._world || {}, o.world);
    Mood.set(c, o.result === 'good' ? 'grateful' : 'relaxed', .7, `how ${q.title} ended`); push(c, { text: line, expr: o.result === 'good' ? 'glad' : 'calm' }); push(c, { text: (o.complete || q.complete), expr: o.result === 'bad' ? 'troubled' : 'glad' }); emit('quest_done', c, o.id); if (o.gone) { UI.conv.choices = [{ label: 'Goodbye', fn: end }]; return; } hub(c); }
  function deliver(c) { const st = S[c], q = activeQ(c), qs = qstate(c, q), ob = q.stages[qs.stage].objective, inv = W.Gather.Inventory; const dl = qs.data.delivered = qs.data.delivered || {}; const got = [];
    for (const [k, n] of Object.entries(ob.items)) { const need = n - (dl[k] || 0); if (need <= 0) continue; let left = Math.min(need, inv.count(k)); for (let i = 0; i < inv.slots.length && left > 0; i++) { const s = inv.slots[i]; if (s && s.id === k) { const r = inv.remove(i, Math.min(left, s.qty)); left -= r; dl[k] = (dl[k] || 0) + r; got.push(itemName(k)); } } }
    if (got.length) { Memory.add(c, 'quest_help', { detail: { detailText: got.join(', ') }, tags: ['parts', q.id] }); Rel.change(c, { reliability: 2 }, 'you brought parts'); }
    const done = Object.entries(ob.items).every(([k, n]) => (dl[k] || 0) >= n);
    push(c, { text: got.length ? (done ? (ob.done_text || 'All parts received. Assembling.') : `Received: ${got.join(', ')}. Still needed: ${Object.entries(ob.items).filter(([k, n]) => (dl[k] || 0) < n).map(([k, n]) => `${itemName(k)} (${n - (dl[k] || 0)})`).join(', ')}.`) : 'You have none of the parts. That is acceptable. It is also not helpful.', expr: got.length ? 'glad' : 'calm' });
    if (done) { for (const pr of st.promises) if (pr.status === 'open' && pr.quest === q.id) keep(c, pr); qs.ready = true; return questTalk(c); } hub(c); }
  function advise(c, con) { const st = S[c], a = st.advice[con.id] = st.advice[con.id] || { state: 'offered', asked: false }; push(c, { text: con.intro, expr: 'troubled', pics: con.pics }); adviceChoices(c, con); }
  function adviceChoices(c, con) { const a = S[c].advice[con.id]; const opts = Object.entries(con.options).map(([stance, text]) => ({ label: text, fn: () => giveAdvice(c, con, stance, text) })); if (!a.asked) opts.unshift({ label: con.ask, fn: () => { a.asked = true; push(c, { text: con.reveal, expr: 'troubled' }); Rel.change(c, { familiarity: 2, affection: 1 }, 'you asked before advising'); Memory.add(c, 'told', { key: 'asked_' + con.id, detail: { detailText: con.reveal }, sig: .5 }); adviceChoices(c, con); } }); opts.push({ label: 'I don\'t know.', fn: () => { push(c, { text: CH[c].gesture || CH[c].pictures ? '*It accepts that, and drifts back to its own thoughts.*' : 'Nor do I. That is why I asked.', expr: 'calm' }); hub(c); } }); UI.conv.choices = opts; }
  function adviceScore(c, con, stance) { const t = CH[c].traits, st = S[c]; const base = { encourage: .3 + t.curiosity * .5 - t.caution * .4, reassure: .2 + t.caution * .5 - t.curiosity * .2, compromise: .35 + t.practicality * .2 + t.caution * .15, practical: .2 + t.practicality * .6 }[stance];
    let s = base + (con.lean === stance ? .3 : 0) - (con.resists === stance ? .35 : 0); const m = st.mood.state; if (['worried', 'sad', 'lonely'].includes(m)) s += stance === 'reassure' ? .2 : stance === 'encourage' ? -.15 : 0; if (['excited', 'curious'].includes(m)) s += stance === 'encourage' ? .15 : 0; if (m === 'suspicious') s -= .15;
    if (st.rel.trust < 8) s -= .15; else if (st.rel.trust > 40) s += .1; if (st.advice[con.id] && st.advice[con.id].asked) s += .08;
    const prev = Memory.find(c, { type: 'advice_outcome' })[0]; if (prev) s += prev.result === 'good' && prev.followed ? .1 : prev.result === 'bad' && prev.followed ? -.15 : 0; return s; }
  function giveAdvice(c, con, stance, text) { const st = S[c], a = st.advice[con.id]; const s = adviceScore(c, con, stance); const reaction = s >= .72 ? 'accept' : s >= .5 ? 'consider' : 'reject';
    const used = reaction === 'accept' || (reaction === 'consider' && s >= .6) ? stance : con.lean; Object.assign(a, { state: 'given', stance, used, reaction, short: text.replace(/\.$/, '').replace(/^I'll /, 'let you ').replace(/^(.)/, m => m.toLowerCase()), score: +s.toFixed(2), t: now(), due: now() + con.followup.days * 24 });
    Memory.add(c, 'advice', { detail: { adviceShort: a.short, reaction, stance }, ref: con.id, tags: [con.id, stance, reaction] });
    Rel.change(c, reaction === 'accept' ? { respect: 3, trust: 2 } : reaction === 'consider' ? { respect: 1, familiarity: 1 } : { familiarity: 1 }, `your advice: ${a.short}`);
    if (con.promise && con.promise.stance === stance) promise(c, { ...con.promise, concern: con.id });
    Mood.set(c, reaction === 'accept' ? 'relaxed' : reaction === 'reject' ? (CH[c].traits.pride > .6 ? 'frustrated' : 'relaxed') : 'curious', .5, 'thinking over your advice');
    push(c, { text: con.reactions[reaction][0], expr: reaction === 'accept' ? 'glad' : reaction === 'reject' ? 'troubled' : 'calm' }); emit('advice', c, con.id, stance, reaction); hub(c); }
  function tell(c, t) { push(c, { text: t.ask, expr: 'calm' }); UI.conv.choices = t.options.filter(o => !o.needs_found || W.Gather.Journal.found[o.needs_found]).map(o => ({ label: o.text, fn: () => { S[c].tells[t.id] = o.claim || o.value || 'said'; if (o.value) Memory.add(c, 'told', { key: t.id, value: o.value, detail: { detailText: o.value } }); Rel.change(c, o.rel || {}, `you told it something about yourself`); if (o.learn && !S[c].known.includes(o.learn)) S[c].known.push(o.learn); push(c, { text: CH[c].gesture ? '*It dips its light: it will remember.*' : CH[c].pictures ? '*It keeps the picture.*' : 'Hm. I will keep that.', expr: 'calm' }); hub(c); } })); }
  function mention(c, f) { const k = S[c].facts[f.id]; k.mentioned = now(); Memory.add(c, 'fact_mentioned', { key: f.id, detail: { detailText: f.mention } }); Rel.change(c, { affection: 5, respect: 2 }, 'you remembered something it told you'); Mood.set(c, 'happy', .75, 'you remembered'); push(c, { text: f.react, expr: 'glad' }); hub(c); }
  function itemPicker(c, mode) { const inv = W.Gather.Inventory; const ch = CH[c]; const seen = new Set(); const opts = [];
    inv.slots.forEach((s, i) => { if (!s || seen.has(s.id)) return; if (mode === 'show' && !ch.shows.cats.includes(itemCat(s.id))) return; if (['tackle', 'bait'].includes(itemCat(s.id)) && mode === 'gift') {} seen.add(s.id); opts.push({ label: itemName(s.id) + (s.qty > 1 ? ` x${W.Gather.Inventory.count(s.id)}` : ''), icon: s.id, fn: () => mode === 'gift' ? gift(c, s.id) : show(c, s.id) }); });
    UI.conv.choices = opts.slice(0, 7).concat([{ label: 'Never mind', fn: () => hub(c) }]); UI.conv.sel = 0; }
  function pref(c, id) { const g = CH[c].gifts, cat = 'cat:' + itemCat(id); const has = l => l.includes(id) || l.includes(cat); return has(g.loves) ? 'loved' : has(g.dislikes) ? 'disliked' : has(g.likes) ? 'liked' : 'neutral'; }
  function gift(c, id) { const st = S[c], ch = CH[c], inv = W.Gather.Inventory; const i = inv.slots.findIndex(s => s && s.id === id); if (i < 0) return hub(c); inv.remove(i, 1);
    const e = (L[c] || {}).entry || {}; if (e.asleep) { st.gifts.push({ id, day: day(), kind: 'sleepy' }); Memory.add(c, 'gift_neutral', { detail: { item: id }, sig: .3 }); push(c, { text: fill(ch.gift_lines.sleepy[0], { item: itemName(id) }), expr: 'calm' }); UI.conv.choices = [{ label: 'Leave quietly', fn: end }]; return; }
    const kind = pref(c, id); const prior = Memory.find(c, { type: ['gift_loved', 'gift_liked', 'gift_neutral', 'gift_disliked', 'gift_repeat'] }).filter(m => m.item === id && now() - m.t < 24 * 7); const today = st.gifts.filter(g => g.day === day()).length;
    let lk = kind, mem = null; if (prior.length && kind !== 'disliked') { lk = 'repeat'; mem = prior[0]; }
    const lines = ch.gift_lines[lk] || ch.gift_lines.neutral; const text = fill(lines[Math.floor(hash(`${c}${id}${day()}`) * lines.length)], { item: itemName(id), mem: mem ? { ago: agoText(now() - mem.t) } : {} });
    if (mem) { mem.recalled++; mem.lastRecall = now(); convoLog.push({ t: now(), c, line: 'gift_repeat', mem: mem.id, memT: mem.t }); }
    const sad = ['sad', 'worried', 'lonely'].includes(st.mood.state); const mult = today ? .25 : 1;
    const eff = { loved: { affection: 6, trust: 1 }, liked: { affection: 3 }, neutral: { affection: 1 }, disliked: { affection: -4, respect: -1 }, repeat: { affection: 1 } }[lk];
    const scaled = {}; for (const [k, v] of Object.entries(eff)) scaled[k] = Math.round(v * (v > 0 ? mult * (sad && lk === 'loved' ? 1.5 : 1) : 1));
    Rel.change(c, scaled, lk === 'repeat' ? `another ${itemName(id)}` : `you gave it ${itemName(id)} (${kind})`);
    Memory.add(c, lk === 'repeat' ? 'gift_repeat' : 'gift_' + kind, { detail: { item: id }, tags: [kind] });
    if (kind === 'loved' && lk !== 'repeat') { Mood.set(c, sad ? 'grateful' : 'happy', .7, `you gave it ${itemName(id)}`); if (st.keepsakes.length < 3 && !st.keepsakes.includes(id)) st.keepsakes.push(id); } else if (kind === 'disliked') Mood.set(c, 'frustrated', .4, `you gave it ${itemName(id)}`);
    st.gifts.push({ id, day: day(), kind: lk }); if (st.gifts.length > 40) st.gifts.shift();
    for (const pr of st.promises) if (pr.status === 'open' && pr.check && pr.check.give === id) keep(c, pr);
    if (!st.known.includes('gift:' + id)) st.known.push('gift:' + id);
    const ge = lk !== 'repeat' ? exList(c).find(x => x.p === 'gift' && (x.items || []).includes(id) && !seenEx(c, x.id)) : null;
    if (ge) pushEx(c, ge); else push(c, { text, expr: kind === 'disliked' ? 'troubled' : kind === 'neutral' ? 'calm' : 'glad' }); hub(c); }
  function show(c, id) { const st = S[c], ch = CH[c]; const f = W.Fishing.data && W.Fishing.data().fish.find(x => x.id === id); const before = Memory.find(c, { type: 'showed' }); const same = before.find(m => m.item === id);
    const rare = f ? ['rare', 'very_rare', 'exceptional', 'legendary'].includes(f.rarity) : ['rare', 'very_rare'].includes((W.Gather.DB.get(id) || {}).rarity);
    let out = null; if (!same && before.length) out = say(c, ch.recall.filter(l => l.id.endsWith('show_again')), { ctx: { showing: true } });
    const frag = ch.fragments && ch.fragments[id];
    if (!out) { const set = ch.show_lines[same ? 'seen' : rare ? 'rare' : 'new']; out = { text: fill(set[0], { item: itemName(id), when: f ? f.periods.join(' or ') : '' }), expr: same ? 'calm' : 'glad' }; }
    push(c, out); if (frag && !same) { push(c, { text: `*A new picture: ${frag}.*`, pics: [id], expr: 'glad' }); const aq = activeQ(c); const q = aq ? qstate(c, aq) : st.quest; const fr = q.data.frags = q.data.frags || []; if (!fr.find(x => x.id === id)) fr.push({ id, text: frag }); if (aq && q.stage >= 0 && aq.stages[q.stage].objective.type === 'fragments' && fr.length >= aq.stages[q.stage].objective.n) markReady(c); }
    if (!same) { Memory.add(c, 'showed', { detail: { item: id, fragment: frag || '' }, tags: [rare ? 'rare' : 'common'].concat(frag ? ['fragment'] : []), sig: rare ? .7 : .5 }); Rel.change(c, { shared: rare ? 4 : 2, familiarity: 1 }, `you showed it ${itemName(id)}`); if (rare) Mood.set(c, 'excited', .6, `seeing a ${itemName(id)}`); }
    hub(c); }

  // ================================================================= TICK
  let acc = 0, accH = -1, lastNow = null;
  let enabled = true;
  /* ---- Overheard scenes and Vale notes. A scene plays only if the player has been standing near the speakers for a few seconds;
     the speakers never turn to the player, walk over, or block anything. Each plays once and can be dismissed with a tap. */
  const wd = () => S._world || (S._world = {});
  const OH = { cur: null, near: 0, last: -99 };
  function sceneReady(sc) { const ids = sc.who; if (!ids.every(c => S[c] && S[c].met && L[c] && L[c].present && !(L[c].entry || {}).hidden)) return false;
    if (!sc.any_place && !ids.every(c => sc.at.includes((L[c].entry || {}).at))) return false;
    if (!ids.every(c => near(c, 110))) return false; const ctx = context(ids[0]); return when(ids[0], sc.w || {}, ctx); }
  function crossTick(dt) { const w = wd(); w.cross = w.cross || {};
    if (UI.conv || UI.journal) { OH.cur = null; OH.near = 0; return; }
    if (OH.cur) { const o = OH.cur; o.t += dt; if (!o.sc.who.every(c => near(c, 160))) { OH.cur = null; return; } if (o.t >= o.dur) { o.i++; o.t = 0; if (o.i >= o.sc.turns.length) { OH.cur = null; OH.last = T; return; } o.dur = lineSecs(o.sc.turns[o.i][1]); } return; }
    if (T - OH.last < 20) return;
    const sc = (D.cross || []).find(x => !w.cross[x.n] && sceneReady(x)); if (!sc) { OH.near = 0; return; }
    OH.near += dt; if (OH.near < 3) return; OH.near = 0; w.cross[sc.n] = day(); OH.cur = { sc, i: 0, t: 0, dur: lineSecs(sc.turns[0][1]) }; }
  const lineSecs = t => Math.min(7, 2.2 + t.length * .055);
  const noteMet = () => Object.keys(CH).some(c => S[c].met);
  function worldTick() { const w = wd(); w.notes = w.notes || {}; const p = P();
    for (const n of D.world_notes || []) { if (w.notes[n.id]) continue;
      let ok = (n.src || []).some(id => { const c = id.split('.')[0]; return S[c] && S[c].met && seenEx(c, id); }) || (n.world || []).some(f => w[f]);
      if (!ok && noteMet()) ok = (n.disc || []).some(a => { const q = D.anchors[a]; return q && Math.hypot(p.x - q[0], p.y - q[1]) < 70; });
      if (ok) { w.notes[n.id] = day(); toast({ kicker: n.kind === 'place' ? 'A place, written down' : 'A story, written down', title: n.title, sub: 'Neighbours, Stories', glyph: 'book' }); } } }
  function tick(dt) { if (!D || !enabled) return; T += dt; const n = now(); const jump = lastNow != null && Math.abs(n - lastNow) > .5; lastNow = n; acc += dt;
    if (acc > .5 || jump) { for (const c in CH) place(c, jump); acc = 0; checkPromises(); checkObjectives(); checkKills(); checkWitness(); checkIgnored(); for (const c in CH) sight(c); }
    const h = Math.floor(n); if (h !== accH) { accH = h; for (const c in CH) { Mood.hourly(c); milestones(c); } }
    if (acc === 0) { festivalTick(); worldTick(); }
    crossTick(dt);
    if (UI.conv) { UI.conv.t += dt; UI.conv.open = Math.min(1, UI.conv.open + dt * 7); const l = L[UI.conv.c]; if (Math.hypot(l.x - P().x, l.y - P().y) > CH[UI.conv.c].talk_radius + 26) { UI.conv = null; S._walkedAway = (S._walkedAway || 0) + 1; } }
    const p = P();
    for (const c in CH) { const l = L[c]; if (!l.present) continue; const st = S[c]; const d = Math.hypot(l.x - p.x, l.y - p.y);
      if (l.follow) { if (d > 22) stepToward(c, p.x - 14, p.y + 4, dt * 1.4); else l.moving = false; l.anim += dt * (l.moving ? 6 : 2); continue; }
      const talking = UI.conv && UI.conv.c === c; if (CH[c].movement !== 'rooted' && l.tx !== undefined && !talking) stepToward(c, l.tx, l.ty, dt);
      if (!l.moving && d < 64 && st.met) l.flip = p.x < l.x;                       // it notices you: turns to look, nothing more
      if (st.met && d < 70 && !l.noticed) { l.noticed = true; const ms = st.milestones; l.emote = { t: 2.4, kind: ms.close ? 'heart' : ms.familiar ? 'dot' : 'look' }; } else if (d > 120) l.noticed = false;
      if (l.emote) { l.emote.t -= dt; if (l.emote.t <= 0) l.emote = null; }
      l.anim += dt * (l.moving ? 6 : 2); } }
  function sight(c) { const l = L[c], st = S[c]; if (!l.present || (l.entry || {}).hidden) return; const p = P(); const d = Math.hypot(l.x - p.x, l.y - p.y); if (d > 150) return; const k = `${period()}@${(l.entry || {}).at}`; st.seen[k] = (st.seen[k] || 0) + 1; if (!st.flags.spotted) { st.flags.spotted = day(); emit('spotted', c); } }
  function nearest(px, py) { if (!D || UI.conv || !enabled) return null; let best = null, bd = 1e9; for (const c in CH) { const l = L[c]; if (!l.present) continue; const e = l.entry || {}; const r = CH[c].talk_radius; const d = Math.hypot(l.x - px, l.y - py); if (d < r && d < bd) { bd = d; best = c; } } if (!best) return null; const c = best, st = S[c], e = L[c].entry || {};
    const label = e.hidden || e.asleep ? (e.hidden ? 'Listen at the hollow log' : `${st.met ? CH[c].name : 'Something'} is asleep`) : st.met ? (CH[c].gesture ? `Greet ${CH[c].name}` : `Talk to ${CH[c].name}`) : 'Approach quietly'; return { id: 'soc:' + c, label, x: L[c].x, y: L[c].y, r: CH[c].talk_radius, buildAct: () => begin(c) }; }
  function busy() { return !!UI.conv || UI.journal; }
  function blocking() { return !!UI.journal; }

  // ================================================================= INPUT
  function key(k) { if (!D) return false; if (UI.journal) { if (k === 'h' || k === 'escape') UI.journal = false; else if (k === 'x') UI.details = !UI.details; else if (k === 'e') UI.jpage = (UI.jpage + 1) % 3; else if (k === 'q') UI.jpage = (UI.jpage + 2) % 3; else if (k === 'arrowup' || k === 'w') UI.jc = Math.max(0, UI.jc - 1); else if (k === 'arrowdown' || k === 's') UI.jc = Math.min(Object.keys(CH).length - 1, UI.jc + 1); else if (k === 'arrowright' || k === 'd') UI.jpage = (UI.jpage + 1) % 3; else if (k === 'arrowleft' || k === 'a') UI.jpage = (UI.jpage + 2) % 3; else if (k === 'pagedown') { JT.pg++; JT.t0 = window.UIKit ? UIKit.now() : 0; } else if (k === 'pageup') { JT.pg = Math.max(0, JT.pg - 1); JT.t0 = window.UIKit ? UIKit.now() : 0; } return true; }
    const cv = UI.conv; if (cv) { if (['w', 'a', 's', 'd', 'arrowleft', 'arrowright'].includes(k)) return false;   // walking is never blocked: walk away to leave
      const cur = cv.queue[0]; if (cur) { if (['e', 'enter', ' '].includes(k)) advance(); else if (k === 'escape') end(); else return false; return true; }
      if (cv.closing) { end(); return true; } const n = cv.choices.length; if (k === 'arrowup') cv.sel = (cv.sel + n - 1) % n; else if (k === 'arrowdown') cv.sel = (cv.sel + 1) % n; else if (['e', 'enter', ' '].includes(k)) choose(cv.sel); else if (/^[1-9]$/.test(k)) choose(+k - 1); else if (k === 'escape') end(); else return false; return true; }
    if (k === 'h' && !W.Gather.UI.open && !W.Build.UI.busy() && !W.Monsters.Journal.open && !W.Fishing.busy() && !W.Fishing.Book.open) { UI.journal = true; return true; } return false; }
  function advance() { const cv = UI.conv; if (!cv) return; const cur = cv.queue[0]; if (!cur) return end(); const full = cur.text.length; if (cv.shown < full) { cv.shown = full; return; } cv.queue.shift(); cv.shown = 0; cv.t = 0; if (!cv.queue.length && cv.closing) end(); }
  function choose(i) { const cv = UI.conv; const o = cv.choices[i]; if (!o || o.disabled) return; cv.choices = []; o.fn(); }
  function pointer(x, y, down) { if (!D || !down) return false; const b = UI.buttons.find(b => x >= b.x && x < b.x + b.w && y >= b.y && y < b.y + b.h); if (b) { b.fn(); return true; } return !!UI.journal; }

  // ================================================================= DRAW: sprites in the world, then the conversation and the journal
  function spriteFor(c) { const l = L[c], ch = CH[c], e = l.entry || {}, fr = ch.frames; let f; if (e.state === 'submerged' && fr.submerged !== undefined) f = fr.submerged; else if (e.asleep && fr.asleep !== undefined) f = fr.asleep; else if (e.drowsy && fr.drowsy !== undefined) f = fr.drowsy; else if (ch.id === 'lull' && UI.conv && UI.conv.c === c && fr.awake !== undefined) f = fr.awake; else { const seq = l.moving && fr.walk ? fr.walk : fr.idle; f = seq[Math.floor(l.anim) % seq.length]; } return A.index[`${ch.sprite}_${f}`]; }
  function blit(cx, c) { const l = L[c]; if (!l.present || (l.entry || {}).hidden) return; const s = spriteFor(c); if (!s) return; const { d, W: FW, H: FH, tab, dayTab, dep, LW, LI, LIGHTS, lightAmount, flick } = cx; const ch = CH[c]; const by = Math.round(l.y); const fl = ch.movement === 'float' ? Math.round(Math.sin(T * 1.6 + c.length) * 1.5) - (ch.id === 'wick' ? 2 : 6) : 0;
    const x0 = Math.round(l.x) - (l.flip ? s.w - 1 - s.ox : s.ox), y0 = by - s.oy + fl; const ghost = ch.id === 'lull' ? .7 : 1;
    if (ch.movement === 'walk' || ch.movement === 'rooted') { const rx = Math.max(4, s.w * .34); for (let yy = -2; yy <= 2; yy++) for (let xx = -Math.ceil(rx); xx <= rx; xx++) { if ((xx / rx) ** 2 + (yy / 2.2) ** 2 > 1) continue; const px = Math.round(l.x) + xx, py = by + yy; if (px < 0 || py < 0 || px >= FW || py >= FH || dep[py * FW + px]) continue; const o = (py * FW + px) * 4; d[o] *= .76; d[o + 1] *= .76; d[o + 2] *= .76; } }
    for (let yy = 0; yy < s.h; yy++) { const py = y0 + yy; if (py < 0 || py >= FH) continue; for (let xx = 0; xx < s.w; xx++) { const pi = IDX[(s.y + yy) * AW + s.x + (l.flip ? s.w - 1 - xx : xx)]; if (!pi) continue; const px = x0 + xx; if (px < 0 || px >= FW) continue; if (ghost < 1 && ((px * 3 + py * 5 + (T * 6 | 0)) % 10) >= ghost * 10) continue; const i = py * FW + px; if (dep[i] > by && ch.movement !== 'swim') continue;
        let r, g, b; if (cx.spriteRGB) { [r, g, b] = cx.spriteRGB(pi, i); const o = i * 4; d[o] = r; d[o + 1] = g; d[o + 2] = b; continue; } const t = tab[pi]; r = t[0]; g = t[1]; b = t[2]; const lw = LW[i]; if (lw > 0 && lightAmount > 0 && LIGHTS[LI[i]].kind !== 'firefly') { const w = lw * lightAmount * flick[LI[i]], dc = dayTab[pi], Lt = LIGHTS[LI[i]]; r += (dc[0] * Lt.color[0] + 18 - r) * w; g += (dc[1] * Lt.color[1] + 18 - g) * w; b += (dc[2] * Lt.color[2] + 18 - b) * w; } const o = i * 4; d[o] = r; d[o + 1] = g; d[o + 2] = b; } } }
  // speech marks above heads are drawn in the world layer (view scale, after the world, before the UI): crisp, never UI-scaled
  function emoteDraw(g, c, ox, oy) { const l = L[c], e = l.emote; if (!e || !l.present || (l.entry || {}).hidden) return; const s = spriteFor(c); if (!s) return; const ch = CH[c];
    const fl = ch.movement === 'float' ? -(ch.id === 'wick' ? 2 : 6) : 0; const calm = window.UIKit && UIKit.S.reduceMotion; const rise = !calm && e.t > 2 ? Math.round((2.4 - e.t) * 5) - 2 : 0;
    const x = Math.round(l.x) - ox, tip = Math.round(l.y) - s.oy + fl - 4 - oy + rise; const bw = 11, bh = 9, bx = x - 5, by = tip - bh - 1; if (bx < -12 || by < -12) return;
    g.save(); g.globalAlpha = Math.max(0, Math.min(1, e.t)) * .95;
    g.fillStyle = 'rgba(24,14,6,.32)'; g.fillRect(bx + 1, by + 2, bw, bh); g.fillStyle = '#5a3820'; g.fillRect(bx - 1, by, bw + 2, bh); g.fillRect(bx, by - 1, bw, bh + 2); g.fillRect(x, by + bh + 1, 1, 1);   // leather rim, rounded corners, a one-pixel tail
    g.fillStyle = '#f6ecd2'; g.fillRect(bx, by, bw, bh); g.fillRect(x, by + bh, 1, 1);
    if (e.kind === 'heart') { g.fillStyle = '#a8341c'; for (const [a, b, w] of [[-2, 2, 2], [1, 2, 2], [-3, 3, 7], [-3, 4, 7], [-2, 5, 5], [-1, 6, 3], [0, 7, 1]]) g.fillRect(x + a, by + b - 1, w, 1); }
    else if (e.kind === 'dot') { g.fillStyle = '#3a2a1a'; for (const a of [-3, 0, 3]) g.fillRect(x + a, by + 4, 1, 2); }
    else { g.fillStyle = '#3a2a1a'; g.fillRect(x, by + 2, 1, 3); g.fillRect(x, by + 6, 1, 1); }
    g.restore(); }
  function keepsakes(g, tab, ox, oy) { if ((S._world || {}).dock_fish) W.Gather.UI.drawIcon(g, 'carved_fish', 590 - ox, 258 - oy, .5, tab); for (const c in CH) { const ks = S[c].keepsakes; if (!ks.length) continue; const home = { ebb: 'pond_bank', pip: 'hollow_log', wick: 'lantern', burl: 'burl_home', tessel: 'ruin_floor', lull: 'lone_rowan' }[c] || 'camp_fire'; const [x, y] = D.anchors[home] || [0, 0]; ks.forEach((id, i) => W.Gather.UI.drawIcon(g, id, x - ox + 14 + i * 9, y - oy - 4, .5, tab)); } }
  let VIEW_H = 0, US_ = 1;
  const R = { items(cx, front) { if (!D || !enabled) return; for (const c of Object.keys(CH).sort((a, b) => (L[a].y || 0) - (L[b].y || 0))) { if (!L[c].present) continue; if ((Math.round(L[c].y) > cx.pyBase) === front) blit(cx, c); } },
    drawWorld(g, vw, vh, tab) { VIEW_H = vh; if (!D) return; const ox = W.Camera.ix(), oy = W.Camera.iy(); keepsakes(g, tab, ox, oy); if (!enabled) return; for (const c in CH) emoteDraw(g, c, ox, oy); },
    overlay(g, vw, vh, safe, tab) { UI.buttons = []; if (!D) return; const k = window.UIKit; if (!k) return; US_ = VIEW_H ? k.scale(VIEW_H) : 1; tapHook();
      if (UI.journal) journal(g, vw, vh, tab); else { k.openT('folk', false); JT.key = ''; }
      if (UI.conv && !UI.journal) dialogue(g, vw, vh, safe, tab); else k.openT('talk', false);
      if (OH.cur && !UI.conv && !UI.journal) overheard(g, vw, vh, safe); } };
  function overheard(g, vw, vh, safe) { const k = window.UIKit, C = k.C, o = OH.cur, [who, text] = o.sc.turns[o.i]; const w = Math.min(vw - 16, 290), ls = k.lines(text, w - 16), h = 20 + ls.length * 10, x = Math.round(vw / 2 - w / 2), y = Math.round(vh - (safe || 0) - h - 14);
    g.save(); g.globalAlpha = Math.min(1, o.t * 4, (o.dur - o.t) * 4 + .3); k.tag(g, x, y, w, h, {}); k.text(g, who, x + 8, y + 11, { color: C.rust, bold: true }); ls.forEach((l, i) => k.text(g, l, x + 8, y + 22 + i * 10, { color: C.ink }));
    g.restore(); rec(x, y, w, h, () => { OH.cur = null; OH.last = T; }); }
  function portrait(c, e) { const key = `${CH[c].portrait}_${e}`; PORT.cache = PORT.cache || {}; if (PORT.cache[key]) return PORT.cache[key]; const o = PORT.index[key] || PORT.index[`${CH[c].portrait}_calm`]; const cv = document.createElement('canvas'); cv.width = cv.height = 48; const gg = cv.getContext('2d'), im = gg.createImageData(48, 48); const pw = PORT.size * 3;
    for (let y = 0; y < 48; y++) for (let x = 0; x < 48; x++) { const i = PIDX[(o[1] + y) * pw + o[0] + x]; const q = (y * 48 + x) * 4; const p = PORT.palette[i] || [0, 0, 0]; im.data[q] = p[0]; im.data[q + 1] = p[1]; im.data[q + 2] = p[2]; im.data[q + 3] = i ? 255 : 0; } gg.putImageData(im, 0, 0); return PORT.cache[key] = cv; }
  // ================================================================= UI helpers: every control is a kit tap target; UI.buttons mirrors them in view pixels
  const TAP = { x: -1, y: -1 };
  function tapHook() { const k = window.UIKit; if (!k || k.__socialTap) return; const p0 = k.pointer; k.pointer = function (x, y) { TAP.x = x; TAP.y = y; return p0.apply(this, arguments); }; k.__socialTap = true; }   // remembers where a tap landed, so one target can serve a column of rows
  const rec = (x, y, w, h, fn) => UI.buttons.push({ x: Math.round(x * US_), y: Math.round(y * US_), w: Math.round(w * US_), h: Math.round(h * US_), fn });
  function rowsHit(x, y, w, rh, n, fn, label) { if (n <= 0) return; window.UIKit.hit(x, y, w, rh * n, () => fn(Math.max(0, Math.min(n - 1, Math.floor((TAP.y - y) / rh)))), label); }
  function hoverRow(x, y, w, rh, n) { const P_ = window.UIKit.Ptr; if (!P_.over || P_.x < x || P_.x >= x + w || P_.y < y || P_.y >= y + rh * n) return -1; return Math.floor((P_.y - y) / rh); }
  const fitText = (s, w, face = 1) => { const k = window.UIKit; s = String(s || ''); if (k.measure(s, face) <= w) return s; while (s.length > 1 && k.measure(s + '…', face) > w) s = s.slice(0, -1); return s.replace(/[\s,.;:]+$/, '') + '…'; };
  function frame(g, x, y, s, img, sc = 1) { const C = window.UIKit.C; x = Math.round(x); y = Math.round(y); const o = s * sc + 4; g.fillStyle = C.shadow; g.fillRect(x + 2, y + 3, o, o); g.fillStyle = C.leather; g.fillRect(x, y, o, o); g.fillStyle = C.leather2; g.fillRect(x, y, o, 1); g.fillStyle = '#e9dcb6'; g.fillRect(x + 1, y + 1, o - 2, o - 2); g.fillStyle = 'rgba(90,60,30,.12)'; g.fillRect(x + 2, y + o - 8, o - 4, 6);
    if (img) { g.imageSmoothingEnabled = false; g.drawImage(img, x + 2, y + 2, s * sc, s * sc); } return o; }
  function faceCrop(g, c, x, y, s, met) { const C = window.UIKit.C; g.fillStyle = '#e9dcb6'; g.fillRect(x, y, s, s); if (!met) { window.UIKit.text(g, '?', x + s / 2, y + Math.round(s / 2) + 4, { align: 'center', color: C.faint, bold: true }); return; } const sx = Math.round(24 - s / 2), sy = clamp(Math.round(29 - s / 2), 0, 48 - s); g.imageSmoothingEnabled = false; g.drawImage(portrait(c, 'calm'), sx, sy, s, s, x, y, s, s); }
  function unknownPlate(g, x, y, s) { const k = window.UIKit, C = k.C; const o = frame(g, x, y, s, null); k.text(g, '?', x + o / 2, y + Math.round(o / 2) + 4, { align: 'center', color: C.faint, face: s >= 60 ? 2 : 1 }); return o; }

  // ================================================================= the conversation: one paper page at the foot of the screen
  function dialogue(g, vw, vh, safe, tab) { const k = window.UIKit, C = k.C, cv = UI.conv, c = cv.c, ch = CH[c], st = S[c]; const touch = k.touch(), hints = !touch && k.S.hints;
    const cur = cv.queue[0]; if (cur) cv.last = cur; const n = cur ? 0 : cv.choices.length;
    const pw = Math.min(vw - 16, 500), x = Math.round(vw / 2 - pw / 2), tx = x + 76, tw = pw - 76 - 14, LH = 11, room = vh - safe - 36;
    const quiet = !!(ch.gesture || ch.pictures);         // light, gesture and pictures are described rather than spoken
    let body = [], ctxL = [], rh = touch ? 19 : 14, cols = 1, top0 = 0, ph;
    if (cur) { body = k.lines(cur.text, tw); ph = 40 + (cur.pics ? 24 : 0) + (body.length - 1) * LH + 16; }
    else if (n) { if (cv.last) ctxL = k.lines(cv.last.text, tw); const need = (ctx, rows, r) => (ctx.length ? 38 + ctx.length * LH : 31) + rows * r + 9;
      const cap = Math.min(room, Math.max(120, Math.round(vh * .62))); const all = ctxL; const tries = [[all, 1], [all, 2], [[], 1], [[], 2]].filter(([, k2]) => k2 === 1 || (tw >= 280 && n > 3)); const ok = tries.find(([cl, k2]) => need(cl, Math.ceil(n / k2), rh) <= cap) || tries[tries.length - 1]; ctxL = ok[0]; cols = ok[1];
      const rpc = Math.ceil(n / cols); if (need(ctxL, rpc, rh) > room) rh = Math.max(13, Math.floor((room - need([], 0, 0)) / rpc)); ph = need(ctxL, rpc, rh); }
    else { if (cv.last) body = k.lines(cv.last.text, tw); ph = 40 + Math.max(0, body.length - 1) * LH + 16; }
    ph = Math.max(68, Math.min(room, ph)); const y = Math.round(vh - ph - 8 - safe);
    const isP = !!(cur && cur.who === 'player'), emph = !!(cur && cur.emph); if (emph) { g.fillStyle = 'rgba(16,10,4,.2)'; g.fillRect(0, 0, vw, vh); }          // a story moment: the world dims a little
    g.save(); k.enter(g, 'talk', true, x, y, pw, ph);
    if (cur || !n) { k.hit(x, y, pw, ph, cur ? advance : end, cur ? 'line' : 'close'); rec(x, y, pw, ph, cur ? advance : end); }   // the whole page turns the line
    k.paper(g, x, y, pw, ph, { close: () => end() });
    // the speaker, framed; it lifts a little when a new line begins
    const e = (cur && cur.expr) || Mood.expr(c); const bob = !k.S.reduceMotion && cur && cv.t < .14 && !isP ? -1 : 0; if (emph) { g.fillStyle = C.rust; g.fillRect(x + Math.round(pw / 2) - 14, y + 3, 28, 1); } g.save(); if (isP) g.globalAlpha = .5; frame(g, x + 10, y + 10 + bob, 48, portrait(c, e)); g.restore();
    const name = isP ? 'You' : st.met ? ch.name : '???'; k.text(g, name, tx, y + 23, { face: 2 }); const nw = k.measure(name, 2); g.fillStyle = C.ink2; g.fillRect(tx, y + 26, nw, 1); g.fillRect(tx + nw + 3, y + 26, 2, 1);
    const subRoom = x + pw - 30 - (tx + nw + 10); let sub = isP ? '' : st.met ? `${ch.epithet} · ${st.mood.state}` : ch.species; if (k.measure(sub) > subRoom && st.met) sub = ch.epithet; if (k.measure(sub) <= subRoom) k.text(g, sub, tx + nw + 10, y + 23, { color: C.faint });
    if (cur) { let by = y + 40; if (cur.pics) { cur.pics.forEach((id, i) => { k.slot(g, tx + i * 24, y + 31, 20); W.Gather.UI.drawIcon(g, id, tx + 2 + i * 24, y + 33, 1, tab); }); by += 24; }
      cv.shown = Math.min(cur.text.length, (cv.shown || 0) + (k.S.reduceMotion ? 1e9 : cur.emph ? 1.0 : 1.6)); let left = Math.floor(cv.shown);
      body.forEach((l, i) => { if (left <= 0) return; k.text(g, l.slice(0, left), tx, by + i * LH, { color: isP ? C.rust : (quiet || cur.narr) ? C.ink2 : C.ink }); left -= l.length + 1; });
      if (cv.shown >= cur.text.length) k.text(g, touch ? 'tap to go on ▸' : hints ? 'E  ▸' : '▸', x + pw - 12, y + ph - 9, { align: 'right', color: C.faint }); }
    else if (n) { let yy = y + 40; let top = y + 31; if (ctxL.length) { ctxL.forEach(l => { k.text(g, l, tx, yy, { color: C.faint }); yy += LH; }); g.fillStyle = 'rgba(58,42,26,.22)'; g.fillRect(tx, yy - 6, Math.min(tw, 120), 1); top = yy - 2; }
      const rpc = Math.ceil(n / cols), gap = cols > 1 ? 10 : 0, cw = Math.floor((tw - gap * (cols - 1)) / cols);
      for (let col = 0; col < cols; col++) { const cx = tx + col * (cw + gap) - 4, cnt = Math.min(rpc, n - col * rpc); const hv = hoverRow(cx, top, cw, rh, cnt); if (hv >= 0 && (k.Ptr.x !== cv.px || k.Ptr.y !== cv.py)) { cv.sel = col * rpc + hv; } 
        for (let j = 0; j < cnt; j++) { const i = col * rpc + j, o = cv.choices[i], ry = top + j * rh, sel = !touch && i === cv.sel, mid = ry + Math.round(rh / 2) + 3;
          if (touch) { g.fillStyle = 'rgba(255,250,235,.4)'; g.fillRect(cx, ry + 1, cw, rh - 3); g.fillStyle = 'rgba(90,60,30,.16)'; g.fillRect(cx, ry + rh - 2, cw, 1); if (!o.disabled) k.text(g, '▸', cx + cw - 4, mid, { align: 'right', color: C.faint }); }
          if (sel) { g.fillStyle = 'rgba(138,58,26,.08)'; g.fillRect(cx, ry, cw, rh - 1); k.text(g, '▸', cx + 2, mid, { color: C.rust }); } else if (hints && i < 9) k.text(g, String(i + 1), cx + 2, mid, { color: C.faint });
          let lx = cx + (touch ? 4 : 11); if (o.icon) { W.Gather.UI.drawIcon(g, o.icon, lx, ry + Math.round((rh - 12) / 2), .75, tab); lx += 15; }
          const label = fitText(o.label, cx + cw - 4 - lx); k.text(g, label, lx, mid, { color: o.disabled ? C.faint : sel ? C.ink : C.ink2 }); if (sel) { g.fillStyle = C.rust; g.fillRect(lx, mid + 2, k.measure(label), 1); }
          if (j < cnt - 1 && !touch) { g.fillStyle = 'rgba(58,42,26,.12)'; g.fillRect(cx + 4, ry + rh - 1, cw - 8, 1); }
          rec(cx, ry, cw, rh, () => { cv.sel = i; choose(i); }); }
        rowsHit(cx, top, cw, rh, cnt, j => { cv.sel = col * rpc + j; choose(col * rpc + j); }, 'choice'); }
      cv.px = k.Ptr.x; cv.py = k.Ptr.y; }
    else { body.forEach((l, i) => k.text(g, l, tx, y + 40 + i * LH, { color: C.faint })); k.text(g, touch ? 'tap to close' : hints ? 'E  close' : '', x + pw - 12, y + ph - 9, { align: 'right', color: C.faint }); }
    g.restore(); }
  const DIARY = { met: m => `met ${m.cn}${m.detailText ? ', ' + m.detailText : ''}`, gift_loved: m => `gave ${m.cn} a ${itemName(m.item)}. It loved it`, gift_liked: m => `gave ${m.cn} a ${itemName(m.item)}`, gift_disliked: m => `gave ${m.cn} a ${itemName(m.item)}. A mistake`, gift_repeat: m => `gave ${m.cn} another ${itemName(m.item)}`, gift_neutral: m => `left ${m.cn} a ${itemName(m.item)}`, showed: m => `showed ${m.cn} a ${itemName(m.item)}`, told: m => m.key && m.key.startsWith('asked_') ? `asked ${m.cn} what was wrong` : `told ${m.cn} ${m.key === 'why_here' ? 'I came here ' : m.key === 'favourite' ? 'I love ' : m.key === 'function' ? 'my function is ' : ''}${m.detailText}`, fact_mentioned: m => `remembered something ${m.cn} told me`, advice: m => `told ${m.cn} to ${m.adviceShort}. It ${m.reaction === 'accept' ? 'agreed' : m.reaction === 'reject' ? 'disagreed' : 'said it would think'}`, advice_outcome: m => `${m.cn}: ${m.result === 'good' ? 'it went well' : m.result === 'bad' ? 'it went badly' : 'it went neither way'}`, promise_made: m => `promised ${m.cn}: ${m.detailText}`, promise_kept: m => `kept my promise to ${m.cn}`, promise_broken: m => `broke my promise to ${m.cn}`, quest_help: m => `helped ${m.cn}: ${m.detailText}`, quest_choice: m => `decided with ${m.cn}: ${m.detailText}`, shared_catch: m => `caught a ${itemName(m.item)} with ${m.cn} watching`, protected: m => `drove something off near ${m.cn}`, witnessed: m => `watched ${m.detailText} with ${m.cn}`, took: m => `took mushrooms from ${m.cn}'s patch`, against_wish: m => `${m.cn} heard that I ${m.detailText}`, ignored: m => `walked past ${m.cn} again`, trees_cut: m => `cut ${m.count} tree${m.count > 1 ? 's' : ''}; ${m.cn} knows`, lied: m => `${m.cn} caught me out about the axe`, discovery: m => `found what ${m.cn} sent me to find`, milestone: m => `${m.cn}: ${m.detailText.toLowerCase()}`, festival: m => `spent the ${m.detailText} with ${m.cn}`, saw_at_festival: m => `saw ${m.cn} at the ${m.detailText}`, shared_time: m => `${m.detailText} with ${m.cn}${m.count > 1 ? ' (' + m.count + ' times)' : ''}`, exchange: m => `${m.cn} gave me a ${itemName(m.item)} it found`, left_behind: m => `went too fast and left ${m.cn} behind` };
  function stage(c) { const ms = S[c].milestones; let l = 'just met'; for (const m of D.milestones) if (ms[m.id]) l = m.short; return S[c].flags.gone ? 'gone' : l; }
  function standing(c) { const r = S[c].rel, n = CH[c].name; const q = (v, a) => v >= 60 ? a[3] : v >= 30 ? a[2] : v >= 10 ? a[1] : a[0];
    return [q(r.trust, [`${n} does not trust you yet.`, `${n} trusts you a little.`, `${n} trusts you.`, `${n} trusts you completely.`]) + (r.trust < 0 ? ' Something you did is still in the way.' : ''), q(r.familiarity, ['You are still a stranger here.', 'It knows your face.', 'It knows your habits.', 'It knows you well.']), q(r.respect, ['', 'It respects how you go about things.', 'It respects you.', 'It looks up to you, in its way.']), q(r.reliability, ['', 'You have kept your word so far.', 'It counts on you.', 'Your word is as good as done.']), q(r.shared, ['', 'You have a few moments together.', 'You have shared a good deal.', 'You have a whole history together.'])].filter(Boolean).join(' '); }
  // ================================================================= the Neighbours journal: list on the left page, the chosen neighbour on the right
  const JT = { key: '', pg: 0, t0: -9, top: 0 };
  const memN = m => +String(m.id).split(':')[1] || 0; const lastMemory = c => [...S[c].mem].filter(m => m.kind !== 'visit' && DIARY[m.kind]).sort((a, b) => b.t - a.t || memN(b) - memN(a))[0];
  const diaryText = (c, m) => `Day ${m.day}: ${DIARY[m.kind]({ ...m, cn: CH[c].name })}.`;
  const dueText = pr => { const h = pr.due - now(); if (h <= 0) return 'due now'; const d = Math.round(h / 24); return d < 1 ? 'due today' : d === 1 ? 'due tomorrow' : `due in ${d} days`; };
  const ready = c => { const q = activeQ(c); return !!(q && qstate(c, q).ready && qstate(c, q).stage >= 0); };
  function journalRows(c, w, narrow) { const k = window.UIKit, C = k.C, st = S[c], ch = CH[c], rows = [], LH = 11;
    const para = (s, o = {}) => { if (!s) return; const ind = o.indent || 0; k.lines(s, w - ind).forEach((l, i) => rows.push({ h: LH, draw: (g, x, y) => { if (i === 0 && o.bullet) k.text(g, o.bullet, x, y + 8, { color: o.bc || C.ink2 }); k.text(g, l, x + ind, y + 8, { color: o.color || C.ink, bold: o.bold }); } })); };
    const head = s => { rows.push({ h: 5, draw: () => {} }); rows.push({ h: 12, head: true, draw: (g, x, y) => { k.text(g, s, x, y + 8, { color: C.ink }); g.fillStyle = 'rgba(58,42,26,.25)'; g.fillRect(x + k.measure(s) + 6, y + 5, Math.max(0, w - k.measure(s) - 6), 1); } }); };
    const gap = h => rows.push({ h, draw: () => {} });
    if (!st.met) { if (st.flags.spotted) { para('Not yet met. Only seen from a distance.', { color: C.ink2, bold: true }); gap(4); para(ch.description); const ks = Object.entries(st.seen).sort((a, b) => b[1] - a[1]).slice(0, 3); if (ks.length) { head('Where it was seen'); for (const [kk] of ks) para(`${kk.split('@')[0]}, near the ${(kk.split('@')[1] || '').replace(/_/g, ' ')}`, { bullet: '·', indent: 8 }); } }
      else { para('Nothing written here yet.', { color: C.ink2 }); gap(4); para('This page fills in once you have seen this neighbour about the clearing.', { color: C.faint }); } return rows; }
    if (narrow && UI.jpage === 0) rows.push({ h: 60, draw: (g, x, y) => { frame(g, x, y, 48, portrait(c, Mood.expr(c))); const tx = x + 60, tw = w - 60; k.text(g, ch.name, tx, y + 14, { face: 2 }); k.text(g, fitText(`${ch.species}, ${ch.epithet.toLowerCase()}`, tw), tx, y + 28, { color: C.ink2 }); k.text(g, fitText(`Feels ${st.mood.state}: ${st.mood.cause}`, tw), tx, y + 39, { color: C.ink }); k.text(g, fitText(`Speaks in ${ch.communication}`, tw), tx, y + 50, { color: C.faint }); } });
    if (UI.jpage === 0) { para(ch.appearance + ' ' + (st.rel.familiarity >= 20 ? ch.background : ch.description));
      const ints = ch.interests.filter(([kk]) => st.known.includes(kk)).map(([, t]) => t); const gl = st.known.filter(kk => kk.startsWith('gift:')).map(kk => itemName(kk.slice(5)));
      head('Cares about'); if (ints.length) ints.forEach(t => para(t, { bullet: '·', indent: 8 })); else para('Not sure yet.', { color: C.faint }); if (gl.length) para(`Gifts tried: ${gl.join(', ')}.`, { color: C.ink2 });
      head('Habits'); const seen = Object.entries(st.seen).sort((a, b) => b[1] - a[1]).slice(0, 4).map(([kk]) => `${kk.split('@')[0]} near the ${(kk.split('@')[1] || '?').replace(/_/g, ' ')}`); if (st.rel.familiarity >= 40) para(ch.habits); else if (seen.length) seen.forEach(t => para(t, { bullet: '·', indent: 8 })); else para('Not sure yet.', { color: C.faint });
      head(UI.details ? 'In numbers' : 'How things stand');
      if (UI.details) { const half = Math.floor((w - 8) / 2); for (let i = 0; i < D.dims.length; i += 2) { const pair = D.dims.slice(i, i + 2); rows.push({ h: 12, draw: (g, x, y) => pair.forEach((d, j) => { const bx = x + j * (half + 8), v = st.rel[d]; k.text(g, `${d} ${Math.round(v)}`, bx, y + 8, { color: C.ink2 }); const bw = Math.max(20, half - 70); k.bar(g, bx + half - bw, y + 4, bw, 3, Math.min(1, Math.abs(v) / 100), { color: v < 0 ? C.rust : C.moss }); }) }); }
        for (const r of st.rlog.slice(-3).reverse()) para(`${Object.entries(r.d).map(([kk, v]) => `${v > 0 ? '+' : ''}${v} ${kk}`).join(', ')}: ${r.why}`, { color: C.faint }); }
      else { para(standing(c)); const r = st.rlog[st.rlog.length - 1]; if (r) { gap(3); para(`Lately: ${r.why}.`, { color: C.ink2 }); } }
      for (const q of chapters(c)) { const qs = st.qs[q.id]; if (!qs || qs.stage < 0) continue; head('Storyline'); para(q.title + (qs.done ? ' (finished)' : ''), { bold: true }); para(qs.done ? (q === ch.quest ? (st.flags.secret ? ch.secret : q.complete) : (qs.choice === 'lost' ? 'It ended badly.' : q.complete)) : q.stages[qs.stage].journal, { color: C.ink }); if (!qs.done && qs.ready) para(`Ready: go and tell ${ch.name}.`, { color: C.moss }); } }
    else if (UI.jpage === 1) { const ms = Memory.important(c, 12).sort((a, b) => a.t - b.t || memN(a) - memN(b)).filter(m => DIARY[m.kind]); if (!ms.length) para('Nothing remembered yet.', { color: C.faint });
      for (const m of ms) para(diaryText(c, m), { bullet: m.sign < 0 ? '✗' : m.sign > 0 ? '●' : '○', bc: m.sign < 0 ? C.rust : m.sign > 0 ? C.moss : C.faint, indent: 9, color: m.sign < 0 ? C.ink2 : C.ink });
      const pr = st.promises.filter(p => p.status === 'open'); if (pr.length) { head('Promised'); for (const p of pr) para(`${p.what} (${dueText(p)})`, { bullet: '·', indent: 8 }); } }
    else if (UI.jpage === 3) { const ti = Rel.tierIdx(Rel.tier(c));
      /* the bible, opened one page at a time: what is written here is only what this friendship has earned */
      const rel = ch.story && ch.story.Relationships; if (rel && ti >= 2) { head('Among the neighbours'); para(rel); }
      const wf = ch.story && ch.story['Wants, fears, contradictions']; if (wf && ti >= 3) { head('Wants and fears'); para(wf); }
      if (seenEx(c, c + '.16') && ch.secret) { head('Kept quiet'); para(ch.secret); }
      const notes = (D.world_notes || []).filter(n => (n.show || []).includes(c) && (wd().notes || {})[n.id]);
      if (notes.length) { head('Vale notes'); for (const n of notes) { para(n.title, { bold: true }); for (const t of n.text) para(t, { color: C.ink2 }); gap(3); } }
      else { head('Vale notes'); para('Nothing written down yet. Notes appear as you walk the Vale and as neighbours tell you things.', { color: C.faint }); } }
    else { let any = false; const add = (b, bc, t, col) => { any = true; para(t, { bullet: b, bc, indent: 9, color: col }); };
      for (const m of D.milestones) if (st.milestones[m.id]) add('★', C.gold, `Day ${st.milestones[m.id].day}: ${m.label}.`);
      for (const q of chapters(c)) { const qs = st.qs[q.id]; if (!qs || qs.stage < 0) continue; add('●', C.ink2, `${q.title}: ${qs.done ? (qs.choice === 'lost' ? 'it ended badly' : 'finished') : q.stages[qs.stage].journal}`); }
      for (const m of st.mem.filter(m => ['quest_choice', 'advice'].includes(m.kind))) add('▸', C.rust, `Decided: ${m.kind === 'advice' ? 'told it to ' + m.adviceShort : m.detailText}.`);
      for (const m of st.mem.filter(m => m.kind === 'festival' || m.kind === 'saw_at_festival')) add('♥', C.rust, `${m.kind === 'festival' ? 'Shared' : 'Saw it at'} ${m.detailText}, year ${m.year}.`);
      const acts = (ch.activities || []).filter(a => st.milestones[a.milestone]); if (acts.length) { head('You can'); for (const a of acts) add('✓', C.moss, a.label + '.'); }
      if (!any) para('Nothing shared yet.', { color: C.faint }); }
    return rows; }
  function paginate(rows, h) { const pages = [[]]; let used = 0; rows.forEach((r, i) => { const next = rows[i + 1]; const need = r.head && next ? r.h + next.h : r.h; if (used + need > h && pages[pages.length - 1].length) { pages.push([]); used = 0; if (!r.head && r.h <= 5) return; } pages[pages.length - 1].push(r); used += r.h; }); return pages; }
  function sideColumn(g, c, x, y, w, bot) { const k = window.UIKit, C = k.C, st = S[c], ch = CH[c]; let yy = y; const big = w >= 104 && bot - y >= 250;
    const line = (s, o = {}) => { for (const l of k.lines(s, w)) { if (yy > bot) return; k.text(g, l, x, yy, o); yy += 10; } };
    const lab = s => { if (yy + 14 > bot) { yy = bot + 1; return; } yy += 5; k.text(g, s, x, yy, { color: C.faint }); yy += 11; };
    const ps = big ? 96 : 48; const o = st.met ? frame(g, x + Math.round((w - ps - 4) / 2), yy, 48, portrait(c, Mood.expr(c)), big ? 2 : 1) : unknownPlate(g, x + Math.round((w - ps - 4) / 2), yy, ps); yy += o + 18;
    if (!st.met) { k.text(g, st.flags.spotted ? 'Someone, seen' : 'Not yet met', x + w / 2, yy, { align: 'center', color: C.ink2 }); return; }
    k.text(g, fitText(ch.name, w, 2), x, yy, { face: 2 }); yy += 11; line(ch.epithet, { color: C.ink2 });
    lab('Mood'); line(`Feels ${st.mood.state}: ${st.mood.cause}.`);
    lab('Standing'); line(`${Rel.tier(c)[0].toUpperCase() + Rel.tier(c).slice(1)}.${st.milestones.met ? ` Met on day ${st.milestones.met.day}.` : ''}`);
    const m = lastMemory(c); if (m) { lab('Last remembered'); line(diaryText(c, m)); }
    const pr = st.promises.filter(p => p.status === 'open'); if (pr.length) { lab('Promised'); for (const p of pr.slice(0, 3)) line(`${p.what}, ${dueText(p)}.`); }
    if (ready(c)) { lab('Waiting'); line(`${ch.name} would like to hear how it went.`, { color: C.moss }); } }
  function journal(g, vw, vh, tab) { const k = window.UIKit, C = k.C, ids = Object.keys(CH), n = ids.length; UI.jc = clamp(UI.jc, 0, n - 1); const touch = k.touch(), hints = !touch && k.S.hints;
    const bw = Math.min(vw - 8, 660), bh = Math.min(vh - 24, 372), x = Math.round(vw / 2 - bw / 2), y = Math.max(20, Math.round((vh - bh) / 2) + 6), lw = Math.round(clamp(bw * .3, 122, 176));
    g.save(); k.enter(g, 'folk', true, x, y, bw, bh); const met = ids.filter(c => S[c].met).length; const tW = k.measure('Neighbours', 2) + 26; const sub = tW + k.measure(`${met} of ${n} met`) < lw ? `${met} of ${n} met` : tW + k.measure(`${met}/${n}`) < lw ? `${met}/${n}` : '';
    k.paper(g, x, y, bw, bh, { title: 'Neighbours', sub, spread: lw / bw, close: () => { UI.journal = false; } }); rec(x + bw - 26, y + 4, 22, 22, () => { UI.journal = false; });
    // left page: one ruled row per neighbour, tap to open its page
    const hintL = []; if (hints) for (const h of ['W S  neighbour', 'Q E  page', 'X  numbers', 'H  close']) { const t = hintL.length ? hintL[hintL.length - 1] + '   ' + h : h; if (hintL.length && k.measure(t) <= lw - 22) hintL[hintL.length - 1] = t; else hintL.push(h); } const ly = y + 34, lb = y + bh - 10 - hintL.length * 10;
    let rh = clamp(Math.floor((lb - ly) / n), 24, 58), fit = Math.min(n, Math.floor((lb - ly) / rh)); if (fit < n) { rh = 24; fit = Math.max(1, Math.floor((lb - ly - 16) / rh)); }
    if (UI.jc < JT.top) JT.top = UI.jc; if (UI.jc >= JT.top + fit) JT.top = UI.jc - fit + 1; JT.top = clamp(JT.top, 0, n - fit); const rx = x + 10, rw = lw - 18; const hv = hoverRow(rx, ly, rw, rh, fit);
    for (let j = 0; j < fit; j++) { const i = JT.top + j, c = ids[i], st = S[c], ry = ly + j * rh, sel = i === UI.jc; if (j === hv && !sel) { g.fillStyle = 'rgba(255,250,235,.35)'; g.fillRect(rx, ry, rw, rh - 2); }
      const th = rh >= 56 ? 48 : rh >= 30 ? 24 : 20, tyy = ry + Math.round((rh - 2 - th) / 2); if (th === 48) { if (st.met) frame(g, rx + 1, tyy - 2, 48, portrait(c, 'calm')); else unknownPlate(g, rx + 1, tyy - 2, 48); } else { k.slot(g, rx + 2, tyy - 1, th + 2); faceCrop(g, c, rx + 3, tyy, th, st.met); }
      const nx = rx + th + (th === 48 ? 14 : 10), mid = ry + Math.round(rh / 2); const nm = st.met ? CH[c].name : st.flags.spotted ? 'Someone, seen' : '???'; const two = rh >= 28; const ny = two ? mid - 1 : mid + 3;
      k.text(g, fitText(nm, rx + rw - nx - 8), nx, ny, { color: st.met ? (sel ? C.ink : C.ink2) : C.faint, bold: sel && st.met }); if (sel) { g.fillStyle = C.rust; g.fillRect(nx, ny + 2, k.measure(fitText(nm, rx + rw - nx - 8)) + 1, 1); }
      if (two) k.text(g, fitText(st.met ? (ready(c) ? 'has news for you' : stage(c)) : st.flags.spotted ? 'not yet met' : '', rx + rw - nx - 4), nx, mid + 10, { color: st.met && ready(c) ? C.moss : C.faint });
      if (st.met && ready(c)) { g.fillStyle = C.moss; g.fillRect(rx + rw - 7, mid - 2, 3, 3); }
      g.fillStyle = 'rgba(58,42,26,.18)'; g.fillRect(rx, ry + rh - 1, rw, 1);
      if (sel) { g.fillStyle = C.rust; for (const [a, b, dx, dy] of [[rx, ry, 1, 1], [rx + rw - 1, ry, -1, 1], [rx, ry + rh - 2, 1, -1], [rx + rw - 1, ry + rh - 2, -1, -1]]) { g.fillRect(a, b, dx * 4, 1); g.fillRect(a, b, 1, dy * 4); } }
      rec(rx, ry, rw, rh, () => { UI.jc = i; }); }
    rowsHit(rx, ly, rw, rh, fit, j => { UI.jc = JT.top + j; }, 'row');
    if (fit < n) { const by = ly + fit * rh + 3; k.button(g, rx, by, 30, 12, '↑', JT.top > 0 ? () => { JT.top--; UI.jc = Math.min(UI.jc, JT.top + fit - 1); } : null, { disabled: JT.top <= 0 }); k.button(g, rx + 34, by, 30, 12, '↓', JT.top + fit < n ? () => { JT.top++; UI.jc = Math.max(UI.jc, JT.top); } : null, { disabled: JT.top + fit >= n }); }
    hintL.forEach((l, i) => k.text(g, l, x + 12, y + bh - 9 - (hintL.length - 1 - i) * 10, { color: C.faint }));
    // right page
    const c = ids[UI.jc], st = S[c]; const px = x + lw + 12, pwid = bw - lw - 24, bot = y + bh - 10; const wide = pwid >= 400, sideW = wide ? Math.min(150, Math.round(pwid * .3)) : 0, cw = wide ? pwid - sideW - 14 : pwid;
    let cy = y + 12;
    if (st.met) { const tabs = ['Who', 'Remembered', 'Together', 'Stories']; let tx = px; tabs.forEach((t, i) => { const tw = k.measure(t) + 14, on = i === UI.jpage; g.fillStyle = on ? C.paper : C.paper2; g.fillRect(tx, cy, tw, 14); g.strokeStyle = on ? C.ink2 : 'rgba(58,42,26,.3)'; g.strokeRect(tx + .5, cy + .5, tw - 1, 13); if (on) { g.fillStyle = C.rust; g.fillRect(tx + 1, cy + 1, tw - 2, 1); } k.text(g, t, tx + 7, cy + 10, { color: on ? C.ink : C.faint }); k.hit(tx, cy, tw, 14, () => { UI.jpage = i; }, 'tab'); rec(tx, cy, tw, 14, () => { UI.jpage = i; }); tx += tw + 3; });
      if (UI.jpage === 0) { const lbl = 'Numbers', dw = k.measure(lbl) + 14, dx = Math.min(x + bw - 30 - dw, px + pwid - dw - 18); if (dx > tx + 4) { k.button(g, dx, cy, dw, 14, lbl, () => { UI.details = !UI.details; }, { primary: UI.details }); rec(dx, cy, dw, 14, () => { UI.details = !UI.details; }); } }
      cy += 20; g.fillStyle = 'rgba(58,42,26,.3)'; g.fillRect(px, cy, pwid - 20, 1); cy += 6; } else cy += 4;
    if (wide) { g.fillStyle = 'rgba(58,42,26,.18)'; g.fillRect(px + cw + 6, cy + 2, 1, bot - cy - 6); sideColumn(g, c, px + cw + 14, cy + 2, sideW, bot); }
    const key = `${UI.jc}|${UI.jpage}|${UI.details}|${cw}`; if (key !== JT.key) { if (JT.key && JT.key.split('|').slice(0, 2).join() !== key.split('|').slice(0, 2).join()) JT.t0 = k.now(); JT.key = key; JT.pg = 0; }
    const rows = journalRows(c, cw, !wide); const pages = paginate(rows, bot - cy - 16); JT.pg = clamp(JT.pg, 0, pages.length - 1); let yy = cy; for (const r of pages[JT.pg]) { r.draw(g, px, yy); yy += r.h; }
    if (!wide && st.met && UI.jpage > 0 && pages.length === 1 && bot - 16 - yy >= 70) { const ch = CH[c], by = bot - 54, tx = px + 62, tw = cw - 62; k.divider(g, px, by - 8, cw - 20);   // a narrow page keeps its spare foot for the neighbour at a glance
      frame(g, px, by, 48, portrait(c, Mood.expr(c))); k.text(g, ch.name, tx, by + 9, { bold: true }); k.text(g, fitText(`Feels ${st.mood.state}: ${st.mood.cause}`, tw), tx, by + 21); k.text(g, fitText(`Standing: ${Rel.tier(c)}`, tw), tx, by + 32, { color: C.ink2 });
      const pr = st.promises.find(p_ => p_.status === 'open'), m = lastMemory(c); const last = UI.jpage === 2 && m ? `Last remembered: ${DIARY[m.kind]({ ...m, cn: ch.name })}` : pr ? `Promised: ${pr.what}, ${dueText(pr)}` : ''; if (last) k.text(g, fitText(last, tw), tx, by + 43, { color: C.ink2 }); }
    if (pages.length > 1) { const by = bot - 12, bx = px + cw - 96; k.text(g, `page ${JT.pg + 1} of ${pages.length}`, bx - 6, by + 9, { align: 'right', color: C.faint }); k.button(g, bx, by, 44, 13, '↑ back', JT.pg > 0 ? () => { JT.pg--; JT.t0 = k.now(); } : null, { disabled: JT.pg <= 0 }); k.button(g, bx + 48, by, 44, 13, 'more ↓', JT.pg < pages.length - 1 ? () => { JT.pg++; JT.t0 = k.now(); } : null, { disabled: JT.pg >= pages.length - 1 }); if (hints) k.text(g, 'PgUp PgDn', px, by + 9, { color: C.faint }); }
    // a quick page-turn sweep when the page changes (skipped with reduced motion)
    const pt = (k.now() - JT.t0) / .28; if (pt < 1 && !k.S.reduceMotion) { const sx = Math.round(px + pwid * (1 - pt)); g.fillStyle = 'rgba(255,248,226,.55)'; g.fillRect(sx, y + 4, 3, bh - 8); g.fillStyle = 'rgba(90,60,30,.16)'; g.fillRect(sx + 3, y + 4, 6, bh - 8); }
    g.restore(); }

  // ================================================================= SAVE: meaningful history only; positions come from the schedule on load
  const Save = { snapshot() { const out = {}; for (const c in CH) { const s = S[c]; out[c] = { ...s, said: s.said.slice(-12), ignored: Object.fromEntries(Object.entries(s.ignored).slice(-6)) }; } return { version: 1, chars: out, world: S._world || {}, stats: { cutToday: stats.cutToday, kills: stats.kills, firstWeather: stats.firstWeather } }; },
    restore(sv) { UI.conv = null; UI.journal = false; for (const c in CH) S[c] = fresh(c); if (sv && sv.chars) for (const c in sv.chars) if (CH[c]) S[c] = alias(c, Object.assign(fresh(c), JSON.parse(JSON.stringify(sv.chars[c])))); if (sv && sv.stats) Object.assign(stats, sv.stats); S._world = (sv && sv.world) || {}; for (const c in CH) { L[c] = { anim: 0, present: false }; place(c, true); } lastNow = now(); } };
  function announce() { on('met', c => toast({ kicker: 'Met a neighbour', title: CH[c].name, sub: CH[c].epithet, glyph: 'hand' }));
    on('milestone', (c, id) => { if (id === 'met') return; const m = D.milestones.find(x => x.id === id); if (m) toast({ kicker: CH[c].name, title: m.short[0].toUpperCase() + m.short.slice(1), sub: m.label, glyph: 'heart', sting: 'milestone' }); });
    on('quest_done', c => { const q = chapters(c).filter(q_ => (S[c].qs[q_.id] || {}).done).pop(); if (q) toast({ kicker: 'Storyline finished', title: q.title, sub: `with ${CH[c].name}`, glyph: 'book', sting: 'discovery' }); });
    on('memory', (c, m) => { const n = CH[c].name;
      if (m.kind === 'promise_made') toast({ kicker: 'Promise made', title: n, sub: m.detailText, glyph: 'hand' });
      else if (m.kind === 'promise_kept') toast({ kicker: 'Promise kept', title: n, sub: m.detailText, glyph: 'hand' });
      else if (m.kind === 'promise_broken') notice(`You did not keep your word to ${n}: ${m.detailText}.`, 4);
      else if (m.kind === 'quest_help' && m.ref) { const q = chapters(c).find(q_ => q_.id === m.ref); if (q) toast({ kicker: 'Storyline', title: q.title, sub: 'A new page in Neighbours', glyph: 'book' }); } }); }
  function preStamp(cast, col) { for (const c of Object.values(cast.characters)) if (c.solid) { const [x, y] = cast.anchors[c.schedule.find(e => e.at).at]; for (let yy = y - 6; yy <= y + 1; yy++) for (let xx = x - 15; xx <= x + 15; xx++) col[yy * 768 + xx] = 1; } }
  function init(data, world) { D = data.cast; W = world; A = data.atlas; AW = A.width; IDX = data.idx; PORT = data.portraits; PIDX = data.pidx; for (const [id, c] of Object.entries(D.characters)) CH[id] = c; for (const c in CH) { S[c] = fresh(c); L[c] = { anim: Math.random() * 4, present: false }; }
    announce(); W.Fishing.on('catch', onCatch); W.Gather.on('gathered', onGathered); for (const c in CH) place(c, true); lastNow = now();
    const SS = W.Survival.SaveState, sn = SS.snapshot.bind(SS), ld = SS.load.bind(SS); SS.snapshot = () => Object.assign(sn(), { social: Save.snapshot() }); SS.load = s => { s = s || SS.read(); const ok = ld(s); if (ok) SS.guard('neighbours', () => Save.restore(s.social)); return ok; }; }
  return { ex: { list: exList, ok: (c, e) => exOk(c, e, context(c)), push: pushEx, seen: seenEx, overheard: () => OH.cur, unlockNotes: worldTick }, world: () => S._world || {}, blocking, chapters, activeQ, qstate, setEnabled: v => { enabled = v; if (!v) { UI.conv = null; UI.journal = false; } }, init, tick, key, pointer, nearest, busy, begin, preStamp, on, render: R, Save, Memory, Rel, Mood, S, L, CH: () => CH, context, when, say, validate, setProvider: p => { provider = p || Provider; }, Provider, log: convoLog, UI, choose, advance, end, adviceScore, factsFor: c => ({ id: c, name: CH[c].name, traits: CH[c].traits, communication: CH[c].communication, mood: S[c].mood, relationship: S[c].rel, memories: Memory.important(c, 8).map(m => ({ id: m.id, kind: m.kind, day: m.day, item: m.item, detail: m.detailText || m.adviceShort || '' })) }),
    audit() { const bad = []; for (const e of convoLog) if (e.mem) { const m = S[e.c].mem.find(x => x.id === e.mem); if (!m && e.memT == null) bad.push(e); if (e.memT != null && e.memT > e.t) bad.push(e); } return bad; } };
})();
