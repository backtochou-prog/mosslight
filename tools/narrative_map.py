"""When each authored exchange may be played. The words come from DIALOGUE_LIBRARY.md (see narrative.py); this file only
says under which real game conditions a line is allowed, so nothing is shown before its trust or discovery condition and
no line claims a past that did not happen.

Pools
  talk   an exchange the character opens with when the player chooses "Talk" (and as the first words of a visit)
  topic  an exchange that starts with the player's words; the player picks it from "Say something" (its label is that line)
  beat   a story moment offered as its own button ("Sit with Nera a while"); declining uses the library's choice response
  meet   the first meeting
  gift   a reaction to one specific kind of gift (items=...)
  none   no matching feature exists in the game yet (listed in docs/NARRATIVE_INTEGRATION.md)
Conditions (`w`) use the social engine's own condition words, plus: hour=[a,b), player_low, hounds (stalker/howler near),
seen / req tokens:  seen:<id>  disc:<flag>  gave:<item>  flag:<name>  world:<name>
"""
def R(p=None, w=None, req=None, once=False, items=None, label=None, sets=None, weight=1.0, note=None):
    d = dict(w=w or {}, req=req or [], once=once, weight=weight)
    if p: d['p'] = p
    if items: d['items'] = items
    if label: d['label'] = label
    if sets: d['sets'] = sets
    if note: d['note'] = note
    return d

MORNING = dict(hour=[5, 10]); DAY = dict(hour=[9, 17]); EVENING = dict(hour=[17, 22]); NIGHT = dict(period=['night', 'deep']); DUSKNIGHT = dict(period=['dusk', 'night'])
RAIN = dict(weather=['rain']); WINTER = dict(season=['winter'])
FRIEND = dict(bond='friendly'); CLOSE = dict(bond='close'); FAM = dict(bond='acquainted')
LOW = dict(player_low=True)
NOFEAT = lambda why: R('none', note=why)

RULES = {
 # ---------------------------------------------------------------- Nera (engine id: ebb)
 'ebb': {
  1: R(w=MORNING), 2: R(w=DAY), 3: R(w=EVENING), 4: R(w=RAIN), 5: R(w=WINTER), 6: R(weight=.7),
  7: R(w=LOW), 8: R(w=FAM), 9: R(w=FRIEND, once=True), 10: R(w=FRIEND), 11: R(w=CLOSE, once=True), 12: R(w=FRIEND, once=True),
  13: R('meet'),
  14: R('talk', w=FAM, req=['flag:jar_asked', 'gave:clean_glass'], once=True, weight=4),
  15: R('beat', w=FRIEND, once=True, label='Watch the water with Nera'),
  16: R('beat', w=CLOSE, req=['seen:ebb.15'], once=True, label='Stay with Nera while she says something', sets=['flag:confessed']),
  17: R('topic', req=['disc:intake'], once=True),
  18: R('talk', w=dict(at=['inflow']), req=['seen:ebb.16'], once=True, weight=5),
  19: R('gift', items=['glass_pane', 'glass_shard', 'spore_jar']),
  20: NOFEAT('no perfume exists in the game'),
  21: NOFEAT('the Low Archive does not exist in the game yet'),
  22: R(w=DUSKNIGHT), 23: R(w=NIGHT), 24: R(w=dict(monsters_near=1), weight=5), 25: R(w=dict(festival='fest_fireflies'), weight=5),
 },
 # ---------------------------------------------------------------- Pip
 'pip': {
  1: R(w=MORNING), 2: R(w=DAY), 3: R(w=EVENING), 4: R(w=RAIN), 5: R(w=WINTER), 6: R(weight=.7),
  7: R(w=LOW), 8: R(w=FAM), 9: R(w=FRIEND, once=True), 10: R(w=FRIEND), 11: R(w=CLOSE, once=True), 12: R(w=FRIEND, once=True),
  13: R('meet'),
  14: R('talk', w=FAM, req=['gave:eggshell'], once=True, weight=4),
  15: R('beat', w=FRIEND, once=True, label='Read Pip\'s field notes'),
  16: R('beat', w=CLOSE, req=['seen:pip.15'], once=True, label='Sit with Pip', sets=['flag:page_read']),
  17: NOFEAT('the Weather Station does not exist in the game yet'),
  18: NOFEAT('the Glass Orchard does not exist in the game yet'),
  19: R('gift', items=['blackberry', 'rowan_berry']),
  20: R('gift', items=['burdock_root', 'emberroot']),
  21: R('talk', req=['world:root_door_opened'], once=True, weight=5),
  22: R(w=DUSKNIGHT), 23: R(w=NIGHT), 24: R(w=dict(monsters_near=1), weight=5), 25: R(w=dict(festival='fest_forgotten'), weight=5),
 },
 # ---------------------------------------------------------------- Sella (engine id: wick)
 'wick': {
  1: R(w=MORNING), 2: R(w=DAY), 3: R(w=EVENING), 4: R(w=RAIN), 5: R(w=dict(season=['winter'], hour=[16, 24])), 6: R(weight=.7),
  7: R(w=LOW), 8: R(w=FAM), 9: R(w=FRIEND, once=True), 10: R(w=FRIEND), 11: R(w=CLOSE, req=['flag:told_light'], once=True), 12: R(w=FRIEND, once=True),
  13: R('meet'),
  14: R('talk', w=FAM, req=['flag:light_low'], once=True, weight=4),
  15: R('beat', w=FRIEND, once=True, label='Sit with Sella by the low lamp'),
  16: R('beat', w=CLOSE, req=['seen:wick.15'], once=True, label='Sit with Sella a while longer', sets=['flag:wick_kept']),
  17: R('beat', w=CLOSE, req=['seen:wick.16', 'flag:wind_lamp_built'], once=True, label='Try the wind lamp with Sella', sets=['world:wind_lamp']),
  18: R('topic', req=['disc:lights'], once=True),
  19: R('gift', items=['hinge', 'nails', 'hook_iron']),
  20: R('gift', items=['quartz', 'amethyst', 'moonstone', 'starshard']),
  21: NOFEAT('the Weather Station does not exist in the game yet'),
  22: R(w=DUSKNIGHT), 23: R(w=NIGHT), 24: R(w=dict(monsters_near=1), weight=5), 25: R(w=dict(festival='fest_fireflies'), weight=5),
 },
 # ---------------------------------------------------------------- Orun (engine id: burl)
 'burl': {
  1: R(w=MORNING), 2: R(w=DAY), 3: R(w=EVENING), 4: R(w=RAIN), 5: R(w=WINTER), 6: R(weight=.7),
  7: R(w=LOW), 8: R(w=FAM), 9: R(w=FRIEND, once=True), 10: R(w=FRIEND, req=['seen:burl.15', 'disc:root_door'], once=True), 11: R(w=CLOSE, once=True), 12: R(w=FRIEND, once=True),
  13: R('meet'),
  14: R('topic', w=FAM, label='Ask about the paths', once=True),
  15: R('beat', w=FRIEND, once=True, label='Sit under Orun\'s branches'),
  16: R('beat', w=CLOSE, req=['seen:burl.15', 'disc:root_door'], once=True, label='Stand with Orun while they decide', sets=['flag:stood_at_door']),
  17: R('beat', w=CLOSE, req=['seen:burl.16', 'flag:group_agreed'], once=True, label='Open the old door together', sets=['world:root_door_opened']),
  18: R('topic', req=['disc:old_mark', 'met:tessel'], once=True),
  19: R('gift', items=['rot_fiber', 'moss']),
  20: NOFEAT('no bell can be found or crafted in the game'),
  21: NOFEAT('the Glass Orchard does not exist in the game yet'),
  22: R(w=DUSKNIGHT), 23: R(w=NIGHT), 24: R(w=dict(wind=.6), weight=5), 25: R(w=dict(festival='fest_forgotten'), weight=5),
 },
 # ---------------------------------------------------------------- Morrow (engine id: tessel)
 'tessel': {
  1: R(w=MORNING), 2: R(w=DAY), 3: R(w=EVENING), 4: R(w=RAIN), 5: R(w=WINTER), 6: R(weight=.7),
  7: R(w=LOW), 8: R(w=FAM), 9: R(w=FRIEND, once=True), 10: R(w=FRIEND), 11: R(w=dict(bond='close', talk_days=5), once=True), 12: R(w=FRIEND, once=True),
  13: R('meet'),
  14: R('talk', w=dict(bond='acquainted', on_ridge=True, low_visits=2), once=True, weight=4),
  15: R('topic', w=FRIEND, once=True),
  16: R('beat', w=CLOSE, req=['seen:tessel.15'], once=True, label='Stand with Morrow while it talks'),
  17: R('beat', w=CLOSE, req=['seen:tessel.16'], once=True, label='Sit beside Morrow for the shutdown test', sets=['flag:shutdown_test']),
  18: R('talk', req=['world:root_door_opened'], once=True, weight=5),
  19: R('gift', items=['bolt', 'nails', 'hinge']),
  20: R('gift', items=['cloth']),
  21: NOFEAT('the Weather Station does not exist in the game yet'),
  22: R(w=DUSKNIGHT), 23: R(w=NIGHT), 24: R(w=dict(hounds=1), weight=6), 25: R(w=dict(festival='fest_fireflies'), weight=5),
 },
 # ---------------------------------------------------------------- Luma (engine id: lull)
 'lull': {
  1: R(w=MORNING), 2: R(w=DAY), 3: R(w=EVENING), 4: R(w=RAIN), 5: R(w=WINTER), 6: R(weight=.7),
  7: R(w=LOW), 8: R(w=FAM), 9: R(w=FRIEND, once=True), 10: R(w=FRIEND, req=['seen:lull.8|seen:lull.14|seen:lull.1'], once=True), 11: R(w=CLOSE, once=True), 12: R(w=FRIEND, once=True),
  13: R('meet'),
  14: R('talk', w=FAM, once=True, weight=4),
  15: R('talk', w=FRIEND, once=True, weight=3),
  16: R('beat', w=CLOSE, once=True, label='Sit with Luma while they wake', sets=['flag:dream_shared']),
  17: NOFEAT('the Low Archive does not exist in the game yet'),
  18: R('talk', req=['disc:second_dawn'], once=True, weight=5),
  19: NOFEAT('no pears exist in the game yet'),
  20: NOFEAT('no bell can be found or crafted in the game'),
  21: NOFEAT('the Glass Orchard does not exist in the game yet'),
  22: R(w=DUSKNIGHT), 23: R(w=dict(period=['night', 'deep'], season=['spring', 'summer', 'autumn'])), 24: R(w=dict(hounds=1), weight=6), 25: R(w=dict(festival='fest_forgotten'), weight=5),
 },
}

# Overheard exchanges (DIALOGUE_LIBRARY "Cross-character conversations"). Each needs both speakers present at once near
# the player; `at` lists anchors where either speaker may be; the player lingers, nothing happens to or because of them.
CROSS = {
 1: dict(who=['pip', 'ebb'], at=['pond_bank', 'dock_end'], w=dict(hour=[15, 18])),
 2: dict(who=['wick', 'tessel'], at=['lantern'], w=dict(hour=[19.5, 20.5])),
 3: dict(who=['burl', 'lull'], at=['burl_home', 'oak_shelter'], w=dict(hour=[17, 19.5])),
 4: dict(who=['pip', 'tessel'], at=['meadow', 'sign'], w=dict(hour=[13, 15])),
 5: dict(who=['ebb', 'wick'], at=['dock_end', 'pond_bank'], w=dict(after_rain=True, hour=[15, 19])),
 6: dict(who=['pip', 'tessel', 'burl', 'lull', 'ebb'], at=['camp_fire'], w=dict(festival='fest_forgotten', hour=[18, 23]), any_place=True),
}

# New schedule entries (each character keeps all of their existing routine) so the overheard scenes can happen.
SCHEDULE_ADD = {
 'tessel': [dict(frm=19, to=20.5, at='lantern', act='learning to trim a wick', when=dict(weather=['clear']))],
 'wick': [dict(when=dict(after_rain=True), frm=15, to=19, at='pond_bank', act='setting an unlit wick on the bank')],
 'lull': [dict(frm=17, to=19.5, at='oak_shelter', act='dozing against the broad roots', when=dict(weather=['fog']))],
 'ebb': [dict(when=dict(milestone='close', weather=['clear']), frm=6.5, to=8.5, at='inflow', act='tasting the river where it enters the pond')],
}

# Library exchanges that open with the player's words are offered as choices; the label is that line. These keep the
# library's own wording for the label, shortened only if it is too long for a button.

# World pages (WORLD_NARRATIVE.md) and how the player comes to know them. Nothing is revealed all at once: a folklore page
# opens when a character the player has spoken with tells that story in a written exchange; a place opens by standing in it
# (an anchor) or by an exchange that takes place there. 'show' = whose Stories page keeps the note. Pages with no way in yet
# (no feature for them) stay out of the game and are listed in docs/NARRATIVE_INTEGRATION.md.
WORLD_NOTES = [
  dict(kind='folklore', title='The Listening Turn', src=['pip.23'], show=['pip']),
  dict(kind='folklore', title='The Borrowed Shore', src=['pip.5'], show=['pip', 'wick']),
  dict(kind='folklore', title='The Lantern Walk', src=['ebb.25', 'wick.25', 'tessel.25', 'wick.18'], show=['ebb', 'wick', 'tessel']),
  dict(kind='folklore', title='The Root Rooms', src=['burl.23', 'ebb.23', 'burl.18', 'tessel.18'], show=['burl', 'ebb', 'tessel']),
  dict(kind='folklore', title='The Second Dawn', src=['lull.18'], show=['lull']),
  dict(kind='folklore', title='The Empty Bowl', src=['pip.25', 'burl.25', 'lull.25'], show=['pip', 'burl', 'lull']),
  dict(kind='place', title='Pondside Camp', disc=['camp_fire'], show=['ebb']),
  dict(kind='place', title='The Pond', disc=['pond_bank'], show=['ebb']),
  dict(kind='place', title='Lantern Row', disc=['lantern'], show=['wick']),
  dict(kind='place', title='The Root Rooms', src=['burl.18', 'tessel.18'], world=['root_door_opened'], show=['burl', 'tessel']),
]
# Folklore with no connected way in yet: The House That Keeps Weather (Weather Station), The Bellwether (no creature in game).
# Places: The Weather Station, The Glass Orchard, The Low Archive.

# "Notice" lines: what a neighbour says about what is true of the player right now (the fish in their hands, the lantern they carry,
# trees cut today, how tired they look). They are written in the library's voices, say nothing about the past, and are offered
# before the ambient talk when one fits, so a conversation answers the player rather than the clock.
NOTICE = {
 'ebb': [('n_catch', 'A {ctx.lastFish}. Tell me the depth and the hour. Every fish you show me makes the pond a little less lonely to keep.', dict(caught_today=True)),
         ('n_cut', 'Trees came down today. Take from the dry side. The roots are holding the bank, and the bank is holding my attention.', dict(cut_today=True)),
         ('n_low', 'You are running on fumes. Sit before you decide you are fine. Fine is a verdict, and you have not heard the evidence.', dict(player_low=True)),
         ('n_rain', 'The rain came through the north channel clean. I checked twice. Then I checked the checking.', dict(after_rain=True)),
         ('n_fog', 'Fog on the water. Everything is being told in a whisper. Stay on the bank and listen.', dict(weather=['fog'])),
         ('n_lantern', 'Your lantern on the water makes a second lantern. I have watched this pond alone a long time. Tonight it has company.', dict(lantern=True, period=['dusk', 'night']))],
 'pip': [('p_catch', 'Is that a {ctx.lastFish}? Do not tell me. I will guess. Pond-flavored. Am I close.', dict(caught_today=True)),
         ('p_berry', 'You have blackberries. I can smell them from here. I am standing nearby with my whole face.', dict(has='blackberry')),
         ('p_cut', 'A tree came down today. I felt it in my feet. Were there nests. Tell me there were no nests.', dict(cut_today=True)),
         ('p_low', 'You look like a wet sock. A brave one. Sit by the fire and I will find you something crunchy.', dict(player_low=True)),
         ('p_lantern', 'Your lantern makes everything look like it is holding its breath. I like it. I also do not blink near it.', dict(lantern=True)),
         ('p_rain', 'Everything smells unwrapped. Mushrooms are going to arrive. I can feel it in my hat.', dict(after_rain=True))],
 'wick': [('w_lantern', 'Your lantern is lit. Would you like it brighter, or would you like the dark to come a little closer?', dict(lantern=True)),
          ('w_lights', 'You keep several lights now. Shall I walk them with you, or would you rather count them alone?', dict(lights=4)),
          ('w_low', 'You are very tired. We can sit, or we can walk slowly. Either is allowed.', dict(player_low=True)),
          ('w_fog', 'Fog. The rail lights will be out. We can watch from here, or closer. Closer is not required.', dict(weather=['fog']))],
 'burl': [('b_cut', 'Someone is cutting. I feel it through my feet. I will not make a speech. I have made it, and the trees were not impressed.', dict(cut_today=True)),
          ('b_rain', 'Rain. Good. The ground drinks in the order it likes. Left to right.', dict(after_rain=True)),
          ('b_low', 'You are tired. Sit with your back to something that has stood longer than you. I qualify.', dict(player_low=True)),
          ('b_fog', 'Fog. Everything leans closer to listen. Even me. Especially me.', dict(weather=['fog'])),
          ('b_catch', 'A {ctx.lastFish}. The pond is generous. Do not let it hear you say so.', dict(caught_today=True))],
 'tessel': [('t_catch', 'Observation: you have acquired a {ctx.lastFish}. I could estimate its mass. I would prefer that you tell me how it felt.', dict(caught_today=True)),
            ('t_low', 'Your pace has decreased. I recommend rest. You wear no coat, so I recommend one. This is how I say I am worried about you.', dict(player_low=True)),
            ('t_rain', 'Rain. Pressure down, humidity up, my left wheel gently offended. I have classified this as weather being weather.', dict(weather=['light_rain', 'heavy_rain'])),
            ('t_lantern', 'Your lantern is operating at a pleasing brightness. I would like to be that reliably warm. I am working on it.', dict(lantern=True)),
            ('t_cut', 'Trees: fewer today. I record it without judgment. I record it with a small amount of judgment.', dict(cut_today=True))],
 'lull': [('l_fog', 'The fog has come to sit with us. I like that it does not ask anything.', dict(weather=['fog'])),
          ('l_rain', 'The ground is dreaming of being wet. I can hear it. It is a good dream.', dict(after_rain=True)),
          ('l_low', 'You are very tired. You can lean on the warm side of me. I am mostly warm side.', dict(player_low=True)),
          ('l_lantern', 'Your lantern is a very small sun that has agreed to stay. I am grateful to it.', dict(lantern=True)),
          ('l_catch', 'A {ctx.lastFish}. It came up out of the dark to meet you. That was brave of both of you.', dict(caught_today=True))],
}
