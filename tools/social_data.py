"""The inhabitants of MOSSlight as data. The social engine (preview/social.js) names no character; everything a
character is, does, likes, worries about and says lives here. Lines that refer to the past must bind a memory
(`mem`), or the build refuses them: characters may not invent shared history."""
import json, os, re
DIMS = ['trust', 'familiarity', 'affection', 'respect', 'reliability', 'shared']
ANCHORS = dict(camp_fire=(340, 298), tent_mouth=(256, 266), hollow_log=(446, 374), lone_rowan=(404, 200), meadow=(388, 338), pond_bank=(604, 330), junction=(500, 252), sign=(470, 350),
               bridge=(654, 382), ruin_floor=(596, 146), ruin_arch=(616, 112), oak_shelter=(198, 252), burl_home=(170, 284), north_glade=(330, 160), outcrop=(296, 248), east_bank=(704, 380),
               river_east=(730, 232), lantern=(226, 290), birch_a=(130, 172), birch_b=(104, 210), birch_c=(186, 178))
WATER = dict(dock_end=(606, 282), pond_centre=(636, 262), willow_shallows=(700, 286), inflow=(728, 196), ice_hole=(612, 286))
MEMORY = {   # default significance and sign of each kind of event; characters weight them with their own `memory` multipliers
 'met': (.5, 1), 'visit': (.15, 1), 'gift_loved': (.7, 1), 'gift_liked': (.4, 1), 'gift_disliked': (.45, -1), 'gift_neutral': (.2, 1), 'gift_repeat': (.1, 0), 'showed': (.5, 1), 'told': (.55, 1),
 'fact_learned': (.3, 1), 'fact_mentioned': (.6, 1), 'advice': (.7, 0), 'advice_outcome': (.6, 0), 'promise_made': (.6, 1), 'promise_kept': (.75, 1), 'promise_broken': (.8, -1),
 'quest_help': (.85, 1), 'quest_choice': (.8, 0), 'shared_catch': (.65, 1), 'protected': (.9, 1), 'witnessed': (.6, 1), 'took': (.7, -1), 'against_wish': (.75, -1), 'ignored': (.6, -1),
 'trees_cut': (.5, -1), 'lied': (.85, -1), 'discovery': (.65, 1), 'milestone': (.75, 1), 'festival': (.65, 1), 'saw_at_festival': (.3, 1), 'shared_time': (.4, 1), 'exchange': (.45, 1), 'left_behind': (.85, -1)}
MOODS = dict(happy='glad', excited='glad', grateful='glad', curious='calm', relaxed='calm', worried='troubled', sad='troubled', frustrated='troubled', lonely='troubled', suspicious='troubled')
C = {}
def char(id, **k): C[id] = dict(id=id, **k)
def L(id, text, **k): return dict(id=id, text=text, **k)

# ============================================================== EBB, keeper of the pond
char('ebb', name='Ebb', species='Pond elder', epithet='Keeper of the pond', communication='speech, slow, in water images', sprite='ebb', frames=dict(idle=[0, 1, 2, 3], submerged=4), portrait='ebb', movement='swim', speed=9, solid=False, talk_radius=46,
  traits=dict(caution=.5, curiosity=.5, practicality=.4, pride=.3, warmth=.6), weights=dict(trust=1.2, familiarity=.8, affection=.8, respect=1, reliability=1, shared=1.3),
  memory=dict(showed=1.5, shared_catch=1.4, promise_broken=1.2),
  appearance='A broad, old, wet head rising from the pond, wearing a mask of grey driftwood. Duckweed fronds for gills; a lily growing on its crown.',
  description='Something has lived in the pond for longer than the ruin has been a ruin. It surfaces when it chooses, mostly at the edges of the day.',
  background='Ebb remembers the pond before the dock, and the dock before it went grey. It counts the fish the way others count days.',
  secret='Ebb once took bread from a child who sat on the dock every evening. It kept the child\'s carved fish for forty years, at the bottom of the pond.',
  interests=[('fish', 'Fish, and which ones come back'), ('weather', 'Rain, especially the first rain after a dry week'), ('old_world', 'The people who built the pipes'), ('quiet', 'Quiet water')],
  dislikes=[('noise', 'Splashing for no reason'), ('given_fish', 'Being handed its neighbours as gifts')],
  habits='Rises at the dock at dawn and dusk; dozes in the willow shallows through the day; reads the moon on clear nights; under the ice in winter except at noon.',
  schedule=[dict(when=dict(season=['winter']), frm=11, to=14, at='ice_hole', act='breathing at the ice hole'), dict(when=dict(season=['winter']), frm=0, to=24, at='pond_centre', act='asleep under the ice', state='submerged', asleep=True),
            dict(when=dict(weather=['rain']), frm=6, to=21, at='pond_centre', act='drinking the rain'),
            dict(frm=5, to=9, at='dock_end', act='watching the mist lift'), dict(frm=9, to=15, at='willow_shallows', act='dozing under the willow', state='submerged', asleep=True), dict(frm=15, to=20, at='dock_end', act='counting the evening rise'),
            dict(when=dict(weather=['clear']), frm=20, to=23, at='pond_centre', act='reading the moon on the water'), dict(frm=0, to=24, at='pond_centre', act='asleep in the deep', state='submerged', asleep=True)],
  climate=[dict(when=dict(weather=['rain']), mood='happy', cause='rain on the pond'), dict(when=dict(pond_pressure=.35), mood='worried', cause='the pond feels thin')],
  baseline='relaxed',
  gifts=dict(loves=['moonstone', 'nightlily', 'quartz', 'starshard'], likes=['stone', 'flint', 'lily', 'moss', 'insect_bait', 'worm'], dislikes=['cat:fish', 'scrap_metal', 'coal']),
  shows=dict(cats=['fish'], label='Show it a fish'),
  greet=[L('e_first', 'Hm. A new shape on my dock. The ripples said something was coming. They exaggerate.', when=dict(met=False), expr='calm'),
         L('e_g_dawn', 'Morning comes up out of the water here. Watch. ... There. That was it.', when=dict(period=['dawn'])),
         L('e_g_dusk', 'This is the hour the pond breathes out. Stand still and you can hear it.', when=dict(period=['dusk'])),
         L('e_g_rain', 'Rain! Every drop is a small visitor. I greet them all. It takes a while.', when=dict(weather=['rain']), expr='glad'),
         L('e_g_night', 'The moon is on the water. I am reading it. It mostly says the same thing, but slowly.', when=dict(period=['night', 'deep'])),
         L('e_g_winter', 'Ah. The ice lets me up for an hour. Talk fast. No. Talk slow. I have an hour.', when=dict(season=['winter'])),
         L('e_g_worried', 'There you are. Good. The water is thin today, and I do not like to be alone with that.', when=dict(mood=['worried']), expr='troubled'),
         L('e_g_absent', 'You were gone {absent} days. The pond noticed. I said nothing. The pond is a gossip.', when=dict(absent=4, bond='acquainted'), w=3),
         L('e_g_plain', 'Back again. The water remembers your footsteps. So do I.', when=dict(met=True, bond='acquainted')),
         L('e_g_0', 'Hm.', when=dict(met=True), w=.3)],
  chat=[L('e_c_rise', 'Watch the dock at dusk. The perch come up to taste the light going. Or they used to.', w=2),
        L('e_c_rain', 'The first rain after a dry week is the best one. The pond smells like the beginning of something.', fact='first_rain', w=2),
        L('e_c_weather', 'Fog tomorrow, maybe. The water is warmer than the air. The pond always knows first and tells no one.', when=dict(weather=['clear']), w=1),
        L('e_c_pipes', 'People built the pipes under the ruin. They sang while they worked. Badly. I liked it anyway.', when=dict(bond='friendly'), learn='old_world'),
        L('e_c_fishers', 'You fish here. Good. Fish that are never caught grow proud. Mind you put the small ones back.', when=dict(fished=1), learn='fish'),
        L('e_c_ice', 'Under the ice it is very quiet. I think about everything I have ever eaten. It is a short list, and a long time.', when=dict(season=['winter'])),
        L('e_c_summer', 'In summer the water gets lazy at the top. So do I. We understand each other.', when=dict(season=['summer'])),
        L('e_c_fog', 'Fog is just the pond trying to get up and walk around. It never gets far.', when=dict(weather=['fog'])),
        L('e_c_noise', 'You walk softly. Some things splash for no reason. I keep a list of those things.', learn='quiet', w=.7)],
  recall=[L('e_r_show_again', 'You found another one? I remember the {mem.itemName} you showed me, {mem.ago}. The water must be changing again.', mem=dict(type='showed', min_age=1), when=dict(showing=True), w=6),
          L('e_r_show', 'I still think about that {mem.itemName} you brought to the dock. {mem.ago}. I had not seen one in years.', mem=dict(type='showed', min_age=2, sig=.6), w=3),
          L('e_r_why', 'You told me you came here {mem.detailText}. I have thought about that. The pond has been both of those things for me.', mem=dict(type='told', key='why_here', min_age=2), w=3),
          L('e_r_catch', 'The day you pulled the {mem.itemName} out of my pond, right in front of me. I pretended not to watch. I watched.', mem=dict(type='shared_catch', min_age=1), w=4),
          L('e_r_gift', 'The {mem.itemName} you gave me is at the bottom of the pond now, where I keep the good things.', mem=dict(type='gift_loved', min_age=1), w=3),
          L('e_r_fact', 'You remembered what I said about the first rain. Nobody remembers what the pond says. It matters to me more than I expected.', mem=dict(type='fact_mentioned', min_age=1), w=2),
          L('e_r_promise_broken', 'You said you would look upstream. I waited at the inflow three nights. Then I stopped. That is all.', mem=dict(type='promise_broken', min_age=0), w=5, expr='troubled'),
          L('e_r_advice', 'You told me to {mem.adviceShort}. {mem.outcomeText}', mem=dict(type='advice_outcome', min_age=0), w=4)],
  asleep=[L('e_s1', 'Only two eyes above the water, and they are closed. A slow bubble rises.'), L('e_s2', 'The willow shadow moves over a long shape that does not move.')],
  tells=[dict(id='why_here', ask='Why did you come to this clearing? Walkers usually pass it.', when=dict(met_days=1),
              options=[dict(text='I was lost.', value='because you were lost', rel=dict(trust=2)), dict(text='I wanted somewhere quiet.', value='looking for somewhere quiet', rel=dict(affection=2), learn='quiet'), dict(text="I don't remember.", value='without remembering why', rel=dict(familiarity=2))])],
  facts=[dict(id='first_rain', learn_line='e_c_rain', mention='The first rain after a dry week. Like you said.', when=dict(weather=['rain']), react="You remembered that. I did not think anyone was listening. The pond is glad. So am I.")],
  gift_lines=dict(loved=['Oh. {item}. That goes at the bottom, with the good things. Thank you.', '{item}! The water will like this. I like this.'], liked=['{item}. Useful to a pond. Thank you.'], neutral=['{item}. I will find a place for it. Thank you for thinking of the pond.'],
                  disliked=['You bring me my neighbours. ... I know you meant well. Take it back.', 'That does not belong in a pond. Or near one.'], repeat=['Another {item}? You gave me one {mem.ago}. The pond is not a shop.'], sleepy=['It does not open its eyes. The gift sinks a little way and stops.']),
  show_lines=dict(new=['A {item}! Look at the colour on it. I had not seen one in years.', 'So the {item} still lives in this water. Good. Good.'], seen=['A {item}. Yes. They come up at {when} sometimes.'], rare=['That is a {item}. Do you know how few of those there are? I do. I count them.']),
  concerns=[dict(id='water_changing', when=dict(bond='acquainted', met_days=2), lean='compromise', resists='encourage',
      intro='The water is not what it was. Warmer at the edges, quieter in the middle. I have kept this pond the same way for longer than your kind kept calendars. Should an old thing change its ways, or hold still and let the water come back to it?',
      ask='What feels different, exactly?', reveal='The young perch do not come to the shallows. The eels left the inflow. Something upstream, I think. Something old.',
      options=dict(encourage='Change with it. Find out what the water wants now.', reassure="Hold still. You've seen worse, and it came back.", compromise='Watch it closely for a season, then decide.', practical="Let me find out what's changing. I'll look upstream."),
      promise=dict(stance='practical', what='look upstream at the inflow at night', days=4, check=dict(be_at='river_east', period=['night', 'deep'])),
      reactions=dict(accept=['That is what I would tell myself, if I listened. Thank you for saying it kindly.'], consider=['Perhaps. I will turn it over, like a stone.'], reject=['I tried that once, and it cost the pond more than I admit. I cannot do it twice.']),
      followup=dict(days=3, outcomes=dict(compromise=('good', 'I watched, as you said. The fish move upriver at dusk now, not dawn. Knowing that is half of keeping a pond.'), encourage=('mixed', 'I tried new ways. I waited in the inflow at night. It was cold, and I learned little. Still, I learned the cold.'),
                                            reassure=('bad', 'I held still. The water did not come back. Perhaps holding still was a kind of hiding.'), practical=('promise', 'You went upstream, like you said. The silt. The rust. Now I know what I am fighting.|You said you would look upstream. You did not. I looked myself. I am too slow for rivers.'))))],
  quest=dict(id='thinning', title='The Thinning', stages=[
      dict(id='ask', when=dict(familiarity=10), talk='The perch used to rise under the dock at dusk, seven or eight of them. Now two. I am old; maybe I count badly. Would you catch three different kinds from my pond and tell me? Not to keep. To know.', journal='Ebb wants to know which fish still live in the pond: three different kinds.', objective=dict(type='catch_distinct', habitat='pond', n=3), accept='I will look. Three kinds.'),
      dict(id='upstream', talk='Three kinds: {quest.fish}. So they are not gone. They are leaving. The inflow, then. Go and look at night, when the river talks louder. Take a light.', journal='Look at the river inflow at night, with a light.', objective=dict(type='be_at', at='river_east', radius=40, period=['night', 'deep'], lantern=True, found='In your lantern light the inflow runs cloudy: orange silt and flakes of rust, washing down from the old pipes under the ruin.')),
      dict(id='decide', talk='Rust from the old pipes. So that is it. What should be done? I am a pond. I cannot climb.', journal='Decide with Ebb what to do about the rust in the inflow.', objective=dict(type='choice', options=[
           dict(id='clear', text='I will clear the old culvert myself.', needs=dict(stone=3, plank=1), result='good', line='You did it with your own hands. The water will clear by the next rain. I will remember this, and the pond will remember it longer.', rel=dict(trust=6, respect=4, reliability=4)),
           dict(id='tessel', text='Tessel knows those pipes. Let me ask it.', needs_met='tessel', result='good', line='The metal one. It talks too much and counts the wrong things, and it understands pipes better than I do, which I resent. Ask it.', rel=dict(respect=3), followup_flag='tessel_pipes'),
           dict(id='wait', text='Let the river find its own way. It always has.', result='mixed', line='Perhaps. Rivers are patient. So am I. Fewer perch this year, then. More the year after, if the river is kind.', rel=dict(familiarity=2))]))],
      complete='The perch rose under the dock tonight. Five of them. I counted twice.', reward_secret=True)
)

# ============================================================== PIP, the little forager
char('pip', name='Pip', species='Burrling', epithet='The little forager', communication='quick speech, in fragments and tangents', sprite='pip', frames=dict(idle=[0, 2], walk=[0, 1, 2, 3]), portrait='pip', movement='walk', speed=30, solid=False, talk_radius=26,
  traits=dict(caution=.65, curiosity=.95, practicality=.3, pride=.2, warmth=.9), weights=dict(trust=.9, familiarity=1.3, affection=1.2, respect=.6, reliability=.9, shared=1.4),
  memory=dict(shared_catch=1.3, showed=1.2, discovery=1.4, took=1.3),
  appearance='A chestnut burr the size of a fist, on twig legs, under one enormous leaf it wears as a hat. A moss satchel full of finds.',
  description='Something small runs from cover to cover in the clearing, talking to itself, filling a satchel with anything that looks interesting.',
  background='Pip fell from a chestnut tree that no longer exists and has been collecting the world ever since, one small thing at a time.',
  secret="Pip's satchel holds one thing it never shows anyone: a brass button with a face on it. Pip thinks it is a very small person, asleep.",
  interests=[('mushrooms', 'Mushrooms, especially ones that glow'), ('flowers', 'Flowers, all of them'), ('shiny', 'Small interesting objects'), ('north', 'The north woods, which it has never seen')],
  dislikes=[('rain', 'Getting its hat wet'), ('loud', 'Sudden loud things'), ('metal', 'Cold metal')], owns=['mush_log'],
  habits='Up at dawn at the lone rowan, foraging by the hollow log in the morning, chasing beetles in the meadow at noon, watching dragonflies at the pond in the afternoon. Sleeps in the hollow log.',
  schedule=[dict(when=dict(weather=['rain']), frm=6, to=20, at='oak_shelter', act='sheltering under the big oak, wringing out its hat'),
            dict(when=dict(season=['winter']), frm=9, to=16, at='camp_fire', act='warming itself at your fire'), dict(when=dict(season=['winter']), frm=0, to=24, at='hollow_log', act='asleep in the hollow log', hidden=True, asleep=True),
            dict(frm=5.5, to=8, at='lone_rowan', act='collecting dew from the rowan'), dict(frm=8, to=12, at='hollow_log', act='turning over leaves'), dict(frm=12, to=15, at='meadow', act='chasing a beetle'),
            dict(frm=15, to=18, at='pond_bank', act='watching dragonflies'), dict(when=dict(familiarity=25), frm=18, to=20.5, at='camp_fire', act='warming its twig hands at your fire'), dict(frm=18, to=20.5, at='hollow_log', act='tidying its satchel'),
            dict(frm=0, to=24, at='hollow_log', act='asleep in the hollow log', hidden=True, asleep=True)],
  climate=[dict(when=dict(weather=['rain']), mood='sad', cause='its hat is soaked'), dict(when=dict(weather=['fog']), mood='worried', cause='the fog makes everything quiet'), dict(when=dict(season=['spring'], weather=['clear']), mood='excited', cause='spring, and everything growing')],
  baseline='curious',
  gifts=dict(loves=['mushroom_red', 'mushroom_brown', 'feather', 'bellflower', 'ghostcap', 'eggshell', 'glass_shard'], likes=['daisy', 'poppy', 'yarrow', 'seeds_wild', 'blackberry', 'rowan_berry', 'moss', 'fern_frond'], dislikes=['scrap_metal', 'bolt', 'iron_ingot', 'coal', 'nails']),
  shows=dict(cats=['natural', 'botanical', 'rare_find'], label='Show it something you found'),
  greet=[L('p_first', "Oh! Oh. Hello. Did you see the — no. Never mind. Hello! You're very big. That's fine. I'm Pip.", when=dict(met=False), expr='glad'),
         L('p_g_morning', 'Morning! The rowan had eleven dew drops. I drank nine. Nine is plenty.', when=dict(period=['dawn'])),
         L('p_g_rain', 'Everything is wet and my hat is wet and the hat is the whole point of the hat.', when=dict(weather=['rain']), expr='troubled'),
         L('p_g_fog', "It's so quiet in the fog. Too quiet. Can you talk? Just say things. Anything.", when=dict(weather=['fog']), expr='troubled'),
         L('p_g_fire', 'Your fire is the best fire. I have only seen one other fire. Yours is better.', when=dict(at=['camp_fire'])),
         L('p_g_lonely', "You were gone {absent} days! I counted. I'm not upset. I made a pile of leaves for every day. It's a big pile.", when=dict(absent=3, bond='acquainted'), w=3, expr='troubled'),
         L('p_g_excited', 'Spring spring spring! Everything is coming up at once and I can only look at one thing at a time!', when=dict(mood=['excited'])),
         L('p_g_plain', 'Hi! Hi. What did you find today? I found a beetle. It found me first, actually.', when=dict(met=True))],
  chat=[L('p_c_mush', "Mushrooms don't grow, they arrive. One morning, there they are. Like they walked in at night.", learn='mushrooms', w=2),
        L('p_c_north', "There's a moss in the north woods that glows blue. Everyone says. Nobody I know has been.", learn='north', w=1.5),
        L('p_c_hat', "This hat's name is Fennel. Don't tell anyone. Hats get embarrassed.", fact='hat_name', when=dict(bond='acquainted'), w=2),
        L('p_c_flowers', 'Daisies close at night. Bellflowers ring but too quiet to hear. I put my ear right up close.', learn='flowers', when=dict(season=['spring', 'summer'])),
        L('p_c_patch', 'The mushrooms by the hollow log are mine. Nobody owns mushrooms, so I just look after them very, very hard.', when=dict(met_days=1), sets='told_patch'),
        L('p_c_beetle', 'I chased a beetle for an hour. Then it chased me. Then we both sat down.', when=dict(period=['day'])),
        L('p_c_winter', "Winter is when the world is asleep and I'm not. It's lonely. Your fire helps.", when=dict(season=['winter'])),
        L('p_c_autumn', 'Autumn is the best because everything falls down to where I can reach it.', when=dict(season=['autumn'])),
        L('p_c_loud', 'Something big crashed in the trees last night. I hid in my log until my legs stopped wobbling.', when=dict(monsters_seen=1), learn='loud')],
  recall=[L('p_r_pref', 'You said you love {mem.detailText}! Did you do some today? You should. Every day. That is my advice.', mem=dict(type='told', key='favourite'), w=3),
          L('p_r_pref_fish', 'You said you love fishing — and you caught a {ctx.lastFish} today! I knew it. I knew it about you.', mem=dict(type='told', key='favourite', value='fishing'), when=dict(caught_today=True), w=6, expr='glad'),
          L('p_r_tip', 'I looked {mem.detailText} like you said. You were right! There were three of them! I ate one. Sorry. It was there.', mem=dict(type='told', key='tip', min_age=1), w=6, expr='glad'),
          L('p_r_shared', 'Remember when you caught that {mem.itemName} and I was right there? I tell everyone. The beetle has heard it nine times and it still looks proud of you.', mem=dict(type='shared_catch', min_age=1), w=4),
          L('p_r_gift', 'I still have the {mem.itemName} you gave me! It lives in my satchel. It has its own pocket.', mem=dict(type='gift_loved', min_age=1), w=3),
          L('p_r_took', "Somebody took the mushrooms by the hollow log. I saw you near them. I'm not angry. I only wanted to be asked.", mem=dict(type='took', min_age=0, recent=6), w=7, expr='troubled'),
          L('p_r_fact', 'You asked about Fennel! Nobody ever asks about Fennel. Fennel is fine. Fennel says hello.', mem=dict(type='fact_mentioned', min_age=1), w=2),
          L('p_r_promise', "You made me the jar! I keep it lit at night. My log looks like a little house now.", mem=dict(type='promise_kept', min_age=0), w=5, expr='glad'),
          L('p_r_promise_broken', "I waited for the lantern. I didn't go north, because I didn't want to go alone. I'm small, so I'm good at waiting. I would have liked company.", mem=dict(type='promise_broken', min_age=0), w=6, expr='troubled'),
          L('p_r_advice', 'You told me to {mem.adviceShort}. {mem.outcomeText}', mem=dict(type='advice_outcome', min_age=0), w=4)],
  asleep=[L('p_s1', 'From inside the hollow log: a very small snore, and a leaf going up and down.')],
  tells=[dict(id='favourite', ask='What do you like doing most? Tell me. I collect those too.', when=dict(met_days=0, bond='acquainted'),
              options=[dict(text='Fishing.', value='fishing', rel=dict(familiarity=2)), dict(text='Foraging, like you.', value='foraging', rel=dict(affection=3)), dict(text='Building things.', value='building', rel=dict(familiarity=2)),
                       dict(text='Exploring.', value='exploring', rel=dict(affection=2)), dict(text='Sitting by the fire.', value='sitting by the fire', rel=dict(affection=2))]),
         dict(id='tip', ask='Have you seen anything that glows at night? I am looking for something.', when=dict(quest='morel:ask'),
              options=[dict(text='Pale caps glow by the hollow log at night.', value='by the hollow log at night', needs_found='moondew', rel=dict(trust=2)), dict(text='There is a ghostly cap in the west woods after rain.', value='in the west woods after the rain', needs_found='ghostcap', rel=dict(trust=2)),
                       dict(text='Not yet. I will watch for it.', value=None, rel=dict(familiarity=1))])],
  facts=[dict(id='hat_name', learn_line='p_c_hat', mention='How is Fennel?', when=dict(met_days=1), react='You remembered Fennel! Nobody remembers Fennel. Fennel is so happy it is hiding under the brim.')],
  gift_lines=dict(loved=['For me? A {item}? For me! It is going in the satchel. It is going in the special pocket.', '{item}!! I had one once, for one minute, then I dropped it in the pond. Now I have one forever.'],
                  liked=['Ooh, {item}. Thank you! I will look at it a lot.'], neutral=['A {item}. Huh. I will find out what it is for. Everything is for something.'],
                  disliked=['Oh. It is cold. Cold things make my twigs ache. Thank you though. Can you keep it for me? Far away?'], repeat=['Another {item}! You gave me one {mem.ago}. I still have it. Now they can talk to each other.'], sleepy=['It is asleep. You leave the gift by the log. In the morning it will think the log made it.']),
  show_lines=dict(new=['Oh! What is that? A {item}! Can I hold it? I will not drop it. I might drop it.'], seen=['A {item}! I have seen those. Not as good as that one though.'], rare=["A {item}?! Where did you find it! I want to hear everything, and then I want to follow your footprints back to the place."]),
  concerns=[dict(id='north_woods', when=dict(bond='acquainted', met_days=1), lean='compromise', resists='reassure',
      intro="I want to go and see the north woods. The blue moss. But it's dark there, even in the day, and I'm... small. I'm very small.",
      ask='What scares you most about it?', reveal="The quiet. Here the pond talks all day. There, nothing talks. I'd be the only thing talking.",
      options=dict(encourage="Go. You'll always wonder if you don't.", reassure='Stay. The clearing needs you.', compromise='Go in daylight, and come back before dusk.', practical="I'll make you a light to carry first."),
      promise=dict(stance='practical', what='bring Pip a spore jar', days=4, check=dict(give='spore_jar')),
      reactions=dict(accept=["Yes. Yes! That's it. That's exactly it."], consider=['I will think about it while I chase something. I always think better running.'], reject=['I don\'t think I can. I am scared, and I want to see it, and I want to see it anyway.']),
      followup=dict(days=2, outcomes=dict(compromise=('good', "Daylight only, like you said! I found the blue moss! It doesn't glow in the day. I'm going back to see it glow."), encourage=('mixed', 'I went! I ran most of the way back. It was beautiful for one whole minute.'),
                                            reassure=('bad', "I stayed. It's fine. Everything's fine. I keep looking north though."), practical=('promise', 'Your jar lit the whole path! I saw it — the blue moss, glowing! I sat with it until I got sleepy.|I waited for the light. I did not go.'))))],
  quest=dict(id='morel', title='The Lantern Morel', stages=[
      dict(id='ask', when=dict(familiarity=8), talk='There is a mushroom. The lantern morel. It glows from inside, like it swallowed a firefly. The old stump says it comes up where something old fell down, the night after rain. I have looked for three autumns.', journal='Pip is looking for a lantern morel: it comes up where something old fell, the night after rain.', objective=dict(type='be_at', at='hollow_log', radius=30, period=['night', 'deep'], after_rain=True, found='Under the hollow log something glows faint orange from inside: a lantern morel, small as your thumb.')),
      dict(id='decide', talk='You found it? You found it! Where? What did you do with it?', journal='Tell Pip about the lantern morel.', objective=dict(type='choice', options=[
           dict(id='bring', text='Come and see it. It is under the hollow log.', result='good', line='It was right there under my own log the whole time! It glows like a tiny window. We sat with it. I will never forget sitting with it.', rel=dict(shared=6, affection=4), cross=dict(burl=dict(type='witnessed', detail='left the lantern morel to grow', rel=dict(respect=3)))),
           dict(id='pick', text='I picked it for you.', result='mixed', line="For me? Oh... oh, it's going dim. It wanted to stay in the ground, didn't it. I'll keep it anyway. I'll keep it until it's just a mushroom.", rel=dict(affection=2), cross=dict(burl=dict(type='against_wish', detail='picked the lantern morel', rel=dict(respect=-3)))),
           dict(id='leave', text='I left it to spread its spores. Next year there will be more.', result='mixed', line='More next year? ...That is a long time to wait. But more. You did a patient thing. I am not very patient. I will try.', rel=dict(respect=3, trust=2), cross=dict(burl=dict(type='witnessed', detail='let the lantern morel spread its spores', rel=dict(respect=4))))]))],
      complete='Whenever I see something glow now, I think: maybe.', reward_secret=True)
)

# ============================================================== WICK, the lantern keeper
char('wick', name='Wick', species='Lamp moth', epithet='The lantern keeper', communication='light and gesture; it does not speak', sprite='wick', frames=dict(idle=[0, 1, 2, 3]), portrait='wick', movement='float', speed=16, solid=False, talk_radius=30, gesture=True,
  traits=dict(caution=.85, curiosity=.4, practicality=.6, pride=.4, warmth=.5), weights=dict(trust=1.5, familiarity=.7, affection=.7, respect=1, reliability=1.2, shared=1.1),
  memory=dict(protected=1.6, promise_broken=1.3, witnessed=1.2),
  appearance='Tall and narrow, wrapped in its own folded wings like a dusty coat. Where a head would be, a paper lantern with a small steady flame.',
  description='On some nights a small light walks the clearing that is not a lantern anyone lit.',
  background='Wick visits every light in the clearing at night, one by one, like someone checking on sleeping children.',
  secret='Wick was a moth once. It flew into the last lamp still burning in the reservoir, the night the valley flooded, and came out as this.',
  interests=[('light', 'Light, every kind'), ('dusk_fire', 'The light of a fire just before it goes out'), ('safety', 'Keeping others away from dark places')], dislikes=[('coal', 'Coal: "dead light"'), ('dark_door', 'The door in the ruin')],
  habits='Only at night. Visits your lantern after dusk, keeps watch at the ruin arch, lights the crossing after midnight. Never in rain.',
  schedule=[dict(when=dict(weather=['rain']), frm=0, to=24, at=None, act='away from the rain'), dict(when=dict(weather=['fog']), frm=19.5, to=24, at='ruin_arch', act='keeping watch at the dark door'), dict(when=dict(weather=['fog']), frm=0, to=5.5, at='ruin_arch', act='keeping watch at the dark door'),
            dict(when=dict(season=['winter']), frm=19.5, to=24, at='camp_fire', act='warming its wings at your fire'), dict(frm=19.5, to=22, at='lantern', act='visiting your lantern'), dict(frm=22, to=24, at='ruin_arch', act='keeping watch at the dark door'),
            dict(frm=0, to=3, at='bridge', act='lighting the crossing'), dict(frm=3, to=5.5, at='ruin_arch', act='keeping watch at the dark door'), dict(frm=0, to=24, at=None, act='somewhere in the daylight, folded')],
  climate=[dict(when=dict(monsters_near=3), mood='worried', cause='too many unlit things about'), dict(when=dict(weather=['clear'], period=['night', 'deep']), mood='relaxed', cause='a clear night')],
  baseline='relaxed',
  gifts=dict(loves=['lantern_moth', 'glass_shard', 'nightglass', 'luminous_spores', 'resin', 'spore_jar'], likes=['moondew', 'starshard', 'quartz', 'feather'], dislikes=['coal', 'mud', 'cat:fish']),
  greet=[L('w_first', '*A small light stops at the edge of the dark and looks at you. The flame inside it leans toward you, then away.* (It is deciding whether you are dangerous.)', when=dict(met=False), expr='calm'),
         L('w_g_lantern', '*It bends close to your lantern, flame to flame, and its own light steadies.* (It approves of your lantern.)', when=dict(lantern=True)),
         L('w_g_dark', '*It holds its lantern up to your face, then points at your empty hand.* (You are walking at night without a light.)', when=dict(lantern=False, period=['night', 'deep']), expr='troubled'),
         L('w_g_worried', '*Its light flickers fast, three times, toward the trees.* (Something unlit is moving out there.)', when=dict(mood=['worried']), expr='troubled'),
         L('w_g_fire', '*It settles by the fire and opens its wings a little. You see they are patterned like dusty eyes.* (It is content.)', when=dict(at=['camp_fire'])),
         L('w_g_absent', '*It brightens, slowly, all the way. Then dims back to normal, as if embarrassed.* (It missed you. {absent} nights.)', when=dict(absent=3, bond='acquainted'), w=3, expr='glad'),
         L('w_g_plain', '*A slow pulse of light, the same rhythm as before.* (It recognises you.)', when=dict(met=True))],
  chat=[L('w_c_dusk', '*It points at your campfire, then makes its own flame very small and very red, then waits.* (It loves the light a fire gives just before it goes out.)', fact='dusk_fire', when=dict(bond='acquainted'), w=2),
        L('w_c_door', '*It turns toward the ruin and covers its lantern with a wing until there is no light at all.* (Do not go to the arch at night.)', learn='safety', w=1.5),
        L('w_c_stars', '*It holds its lantern up at the sky, then lowers it, as if comparing.* (The stars are lanterns too far away to check on.)', when=dict(weather=['clear'])),
        L('w_c_lamps', '*It visits each of your lights in turn, then comes back and dips once.* (All your lights are well.)', when=dict(lights=2)),
        L('w_c_coal', '*At the smell of coal, its flame shrinks and turns away.* (Coal is dead light.)', learn='coal', when=dict(has='coal')),
        L('w_c_moths', '*Small moths come and circle its head. It does not mind. It seems to know them.*', when=dict(season=['summer']))],
  recall=[L('w_r_protected', '*It shows you, with its light, the shape of the thing you drove off that night, and then your shape, standing between.* (It remembers that you protected it.)', mem=dict(type='protected', min_age=0), w=6, expr='glad'),
          L('w_r_fact', '*It looks at the low red embers of your fire, then at you, a long time.* (You remembered what it loves.)', mem=dict(type='fact_mentioned', min_age=0), w=3, expr='glad'),
          L('w_r_light_kept', '*It flies to the light you set by the arch and circles it twice.* (The light by the door still burns. It checks on it every night.)', mem=dict(type='promise_kept', min_age=0), w=5),
          L('w_r_broken', '*It goes to the arch, where a light was supposed to be, and stays there with its back to you.*', mem=dict(type='promise_broken', min_age=0), w=6, expr='troubled'),
          L('w_r_gift', '*It turns the {mem.itemName} you gave it this way and that in its own light.* (It still has it.)', mem=dict(type='gift_loved', min_age=1), w=3),
          L('w_r_fear', '*It remembers what you said about the dark. It makes its light a little brighter on your side.*', mem=dict(type='told', key='dark'), w=2),
          L('w_r_advice', '*It shows you, in light, the choice you advised.* ({mem.adviceShort}.) {mem.outcomeText}', mem=dict(type='advice_outcome', min_age=0), w=4)],
  asleep=[L('w_s1', 'Nothing here but a faint warmth in the air where a light has been.')],
  tells=[dict(id='dark', ask='*It holds its lantern between you and the dark trees, then tilts its head.* (Are you afraid of the dark?)', when=dict(met_days=0),
              options=[dict(text='Yes.', value='afraid of the dark', rel=dict(trust=3)), dict(text='No.', value='not afraid of the dark', rel=dict(respect=1)), dict(text='Only of what is in it.', value='afraid only of what is in the dark', rel=dict(trust=2, respect=2))])],
  facts=[dict(id='dusk_fire', learn_line='w_c_dusk', mention='I let the fire burn down slowly tonight, for you.', when=dict(period=['night', 'deep']), react='*It goes very still and its flame turns the exact red of embers.* (It is moved.)')],
  gift_lines=dict(loved=['*It takes the {item} and holds it inside its own light, where it glows.* (It will keep this.)'], liked=['*It inspects the {item} and dips its lantern once.* (Thank you.)'], neutral=['*It looks at the {item}, then politely at you.*'],
                  disliked=['*Its flame shrinks from the {item}. It steps back.* (Not that.)'], repeat=['*It already has a {item} from you, {mem.ago}. It holds both up and the light doubles.*'], sleepy=['There is no one here to take it.']),
  concerns=[dict(id='tell_others', when=dict(bond='acquainted', met_days=1), lean='practical', resists='encourage',
      intro='*It shows you the dark arch, then the camp, then covers its lantern with a wing.* (It is asking: should the others know what is behind the door?)',
      ask='What is behind it?', reveal='*Its light gutters to almost nothing. It holds very still for a long time.* (Something that eats light.)',
      options=dict(encourage='Tell them. They deserve to know.', reassure="Keep it to yourself. Don't frighten them.", compromise='Tell only the ones who go near it.', practical="Let's put a light by the door so nobody wanders in."),
      promise=dict(stance='practical', what='set a light by the ruin arch', days=3, check=dict(light_near='ruin_arch', radius=48)),
      reactions=dict(accept=['*Its flame brightens and steadies.* (Yes.)'], consider=['*It tilts, one way, then the other.* (Maybe.)'], reject=['*Its flame turns away.* (No.)']),
      followup=dict(days=2, outcomes=dict(practical=('promise', '*It takes you to the light by the arch and stands beside it, very straight.* (Nobody has gone in since.)|*It stands at the arch in the dark, where a light was supposed to be.*'), compromise=('good', '*It shows you the small one, the burr, turning away from the arch.* (It told only the one who wanders. It worked.)'),
                                            encourage=('bad', '*It shows you the burr hiding in its log for two nights.* (It told everyone. Now they are afraid of everything.)'), reassure=('mixed', '*It shows you itself, alone at the arch every night.* (It kept the secret. It is tired.)'))))],
  quest=dict(id='door', title='The Unlit Door', stages=[
      dict(id='ask', when=dict(trust=10, period=['night', 'deep']), talk='*It leads your eye to the arch in the ruin. It dims its lantern to nothing, then flares, then dims.* (There is a door that light does not come out of.)', journal='Wick wants you to see the dark door in the ruin: at deep night, with a light.', objective=dict(type='be_at', at='ruin_arch', radius=34, period=['deep'], lantern=True, found='At the arch your lantern light stops a hand-width into the dark, as if it had hit deep water. Something breathes, slowly, very far down.')),
      dict(id='decide', talk='*It waits for you to say what should be done.*', journal='Decide with Wick what to do about the door.', objective=dict(type='choice', options=[
           dict(id='seal', text='Board it shut.', needs=dict(plank=3, nails=2), result='good', line='*It helps you hold the last board. When it is done, it rests its lantern against the planks, listening.* (It is quieter now.)', rel=dict(trust=6, reliability=4)),
           dict(id='light', text='Keep a light burning at the mouth instead.', needs_light='ruin_arch', result='good', line='*It sits beside the light you set and its own flame matches it, flicker for flicker.* (Two lights are a watch. One is only a hope.)', rel=dict(trust=5, shared=4)),
           dict(id='leave', text='Leave it. Whatever is down there was here first.', result='mixed', line='*It looks at you a long time. Then it turns its lantern toward the door and does not look back at you.* (It will keep watching. Alone.)', rel=dict(respect=2, trust=-2))]))],
      complete='*Every night now it stops at the arch, then comes to your lantern last.*', reward_secret=True)
)

# ============================================================== BURL, the rootbound elder
char('burl', name='Burl', species='Rootbound', epithet='The rootbound elder', communication='very slow speech, a few words at a time', sprite='burl', frames=dict(idle=[0, 1], asleep=2, drowsy=3), portrait='burl', movement='rooted', speed=0, solid=True, talk_radius=34,
  traits=dict(caution=.8, curiosity=.2, practicality=.5, pride=.8, warmth=.3), weights=dict(trust=1.2, familiarity=.6, affection=.6, respect=1.6, reliability=1, shared=.8),
  memory=dict(trees_cut=1.6, against_wish=1.4, lied=1.5, witnessed=1.2),
  appearance='A great stump with a face in the bark, knotholes for eyes, a beard of moss, and a sapling of its own growing from its crown.',
  description="At the west edge of the clearing there is a stump that is too old, and too wide, and sometimes it is facing a different way.",
  background='Burl was the oldest oak in the valley before it was cut. It did not agree to stop. It grew a new tree out of its own top instead.',
  secret='The people who cut Burl down sat on it afterward and ate their lunch. It remembers what they talked about. It has never told anyone.',
  interests=[('trees', 'Every tree in the valley, by name'), ('seasons', 'The turning of the year'), ('slowness', 'Slowness')], dislikes=[('axes', 'Axes'), ('lies', 'Being told one thing and shown another')],
  habits='Never moves. Awake from dawn to dusk, asleep at night. Through winter it barely wakes, and only at noon on clear days.',
  schedule=[dict(when=dict(season=['winter'], weather=['clear']), frm=11, to=14, at='burl_home', act='barely stirring'), dict(when=dict(season=['winter']), frm=0, to=24, at='burl_home', act='asleep for the winter', asleep=True),
            dict(when=dict(weather=['rain']), frm=6, to=20, at='burl_home', act='drinking the rain'), dict(frm=5, to=8, at='burl_home', act='drinking the dew'), dict(frm=8, to=17, at='burl_home', act='sunning its bark'),
            dict(frm=17, to=20, at='burl_home', act='listening to the birds settle'), dict(frm=0, to=24, at='burl_home', act='asleep', asleep=True)],
  climate=[dict(when=dict(weather=['rain']), mood='happy', cause='rain at its roots'), dict(when=dict(trees_cut_recent=2), mood='suspicious', cause='the sound of axes')],
  baseline='relaxed',
  gifts=dict(loves=['heartwood_seed', 'seeds_wild', 'moss', 'rowan_berry'], likes=['fern_frond', 'mushroom_brown', 'clay', 'yarrow', 'moondew'], dislikes=['log', 'plank', 'hardwood', 'bark', 'coal', 'scrap_metal']),
  greet=[L('b_first', '...Hm. ... Something small. ... Walking. ... They always walk.', when=dict(met=False)),
         L('b_g_dawn', '...Dew. ... Good dew today. ... Sit.', when=dict(period=['dawn'])),
         L('b_g_rain', '...Rain. ... Ah. ... Rain.', when=dict(weather=['rain']), expr='glad'),
         L('b_g_axe', '...You smell of cut wood. ... I know that smell.', when=dict(cut_today=True), expr='troubled'),
         L('b_g_suspicious', '...The axes again. ... I hear them in my roots.', when=dict(mood=['suspicious']), expr='troubled'),
         L('b_g_winter', '...Cold. ... Speak. ... Quickly. ... For me, that is quickly.', when=dict(season=['winter'])),
         L('b_g_absent', '...You were away. ... {absent} days. ... That is nothing. ... I noticed.', when=dict(absent=5, bond='acquainted'), w=3),
         L('b_g_plain', '...The small walker. ... Again.', when=dict(met=True))],
  chat=[L('b_c_rings', '...I have four hundred and twelve rings. ... I lost count in a dry year, so call it four hundred and thirteen. ... The dry year was the loneliest.', fact='rings', when=dict(bond='acquainted'), w=2),
        L('b_c_names', '...That oak by your tent. ... Her name is long. ... You would not finish saying it.', learn='trees', w=1.5),
        L('b_c_autumn', '...The birches go first. ... Then the oaks. ... The pines pretend nothing is happening.', when=dict(season=['autumn']), learn='seasons'),
        L('b_c_spring', '...The sapling on my head woke before I did. ... Rude.', when=dict(season=['spring'])),
        L('b_c_slow', '...You talk fast. ... Everything young talks fast. ... Rivers too.', learn='slowness'),
        L('b_c_burrling', '...The small chestnut one. ... Pip. ... It talks to me all day. ... I listen to every third word.', when=dict(met_char='pip'))],
  recall=[L('b_r_lied', '...You told me you {mem.detailText}. ... Then I heard the axe. ... Twice. ... Do not do that.', mem=dict(type='lied', min_age=0), w=8, expr='troubled'),
          L('b_r_cut', '...You cut {mem.count} trees since we met. ... I know each one. ... I do not forgive. ... I only remember.', mem=dict(type='trees_cut', min_age=0, sig=.4), w=4, expr='troubled'),
          L('b_r_morel', '...The lantern morel. ... You {mem.detailText}. ... The forest heard.', mem=dict(type=['witnessed', 'against_wish'], tags=['morel']), w=5),
          L('b_r_fact', '...You remembered my rings. ... I will remember that you remembered. ... It is good to be remembered by something that walks.', mem=dict(type='fact_mentioned', min_age=1), w=3, expr='glad'),
          L('b_r_promise', '...You came. ... Three days. ... As you said. ... The sapling grew a leaf.', mem=dict(type='promise_kept', min_age=0), w=5, expr='glad'),
          L('b_r_broken', '...You said you would watch the sapling. ... The sapling watched for you.', mem=dict(type='promise_broken', min_age=0), w=6, expr='troubled'),
          L('b_r_birch', '...The birches. ... You {mem.detailText}. ... {mem.outcomeText}', mem=dict(type='quest_choice', tags=['birches']), w=5),
          L('b_r_gift', '...The {mem.itemName}. ... I put it at my roots. ... It is growing.', mem=dict(type='gift_loved', min_age=2), w=3),
          L('b_r_advice', '...You told me to {mem.adviceShort}. ... {mem.outcomeText}', mem=dict(type='advice_outcome', min_age=0), w=4)],
  asleep=[L('b_s1', 'The knotholes are closed. Sap moves somewhere very deep, very slowly.'), L('b_s2', 'The stump is asleep. Its moss beard moves a little with its breathing, or with the wind.')],
  tells=[dict(id='axe', ask='...Do you cut trees, small walker?', when=dict(met_days=0),
              options=[dict(text='Yes. I need the wood.', value='cut trees because you need the wood', claim='honest', rel=dict(trust=3, respect=2)), dict(text='Only fallen ones.', value='only take fallen wood', claim='fallen', rel=dict(respect=2)),
                       dict(text='Never.', value='never cut trees', claim='never', rel=dict(affection=2))])],
  facts=[dict(id='rings', learn_line='b_c_rings', mention='Four hundred and twelve rings. Or thirteen?', when=dict(met_days=1), react='...Thirteen. ... I decided. ... Because you asked.')],
  gift_lines=dict(loved=['...{item}. ... For my roots. ... Yes.'], liked=['...{item}. ... Good.'], neutral=['...{item}. ... I will keep it close to my roots.'], disliked=['...That is one of mine. ... Cut. ... Take it away.'], repeat=['...Another {item}. ... You brought one {mem.ago}. ... I am still deciding about that one.'], sleepy=['The stump is asleep. You leave the gift at its roots.']),
  concerns=[dict(id='wake_spring', when=dict(bond='acquainted', met_days=3), lean='compromise', resists='encourage',
      intro='...Every spring I wake a little less. ... I wonder whether I should keep waking, or give the sapling on my crown the light.',
      ask='What would the sapling need?', reveal='...Light. ... Time. ... Someone to keep the deer off it. ... There are no deer anymore. ... I forget that.',
      options=dict(encourage='Keep waking. The forest needs your memory.', reassure="Rest. You've earned it.", compromise='Wake for the days that matter.', practical="I'll watch the sapling for you. Three days."),
      promise=dict(stance='practical', what='visit Burl on three different days', days=6, check=dict(visit_days=3)),
      reactions=dict(accept=['...Yes. ... That is right.'], consider=['...I will think about it. ... Come back next year and I will tell you what I decided.'], reject=['...No. ... You are young. ... You think everything should go on.']),
      followup=dict(days=4, outcomes=dict(compromise=('good', '...I slept through the dull days. ... I woke for the rain. ... It was a good choice.'), reassure=('good', '...I rested. ... The sapling grew. ... I dreamed of being a seed.'),
                                            encourage=('mixed', '...I stayed awake. ... I am very tired. ... But I saw the swallows come back.'), practical=('promise', '...You came. Three days. ... As you said. ... The sapling grew a leaf.|...You said you would watch the sapling. ... The sapling watched for you.'))))],
  quest=dict(id='birches', title='The Grey Birches', stages=[
      dict(id='ask', when=dict(respect=8, period=['dawn', 'day', 'dusk']), talk='...The birches. ... Their bark is greying in spots. ... Like lichen. ... Not lichen. ... The three at the west edge. ... Touch the bark. ... Come back.', journal='Burl wants you to touch the bark of the three birches at the west edge, by day.', objective=dict(type='visit_all', at=['birch_a', 'birch_b', 'birch_c'], radius=26, period=['dawn', 'day', 'dusk'], found='The bark under your hand is cold and dry, and comes away grey on your fingers.')),
      dict(id='decide', talk='...Cold. ... Dry. ... I was afraid of that. ... What would you do?', journal='Advise Burl about the grey birches.', objective=dict(type='choice', options=[
           dict(id='cut', text='Cut the sick ones before it spreads.', result='mixed', line_by_trust={'high': '...You would cut them. ... I hear why. ... I hate it. ... Do it, then. ... Quickly.', 'low': '...No. ... You would. ... I know.'}, rel=dict(respect=-2, trust=1), tags=['birches'], detail='said to cut the sick birches'),
           dict(id='ash', text='Burn fallen branches and spread the ash at their roots.', needs=dict(branch=4, coal=1), result='good', line='...Ash. ... Old remedy. ... The birches will drink it. ... You know more than you look.', rel=dict(respect=5, trust=3), tags=['birches'], detail='spread ash at their roots'),
           dict(id='leave', text='Leave them. The forest knows what to do.', result='mixed', line='...One will go grey all through. ... The other two may drink the rain. ... I hope. ... Hope is slow, like me.', rel=dict(respect=3), tags=['birches'], detail='left them to the forest')]))],
      complete='...The birches. ... Better. ... Come in spring. ... See.', reward_secret=True)
)

# ============================================================== TESSEL, the mechanical wanderer
char('tessel', name='Tessel', species='Survey unit', epithet='The mechanical wanderer', communication='precise speech, numbered, socially awkward', sprite='tessel', frames=dict(idle=[0, 2], walk=[0, 1, 2, 3]), portrait='tessel', movement='walk', speed=18, solid=False, talk_radius=28,
  traits=dict(caution=.4, curiosity=.8, practicality=.95, pride=.5, warmth=.3), weights=dict(trust=1, familiarity=.8, affection=.6, respect=1, reliability=1.7, shared=.9),
  memory=dict(promise_kept=1.4, promise_broken=1.6, showed=1.1, quest_help=1.2),
  appearance='A rusted survey dome on three jointed legs, one big lens, an antenna with a scrap of red cloth. Moss and a small white flower grow on its back.',
  description='Something clicks and whirs among the ruin stones, counting them.',
  background='Tessel was built to measure the valley before the flood. It finished the survey. Nobody came to collect it. It started again.',
  secret="Tessel's record zero is a woman laughing at a kettle. Tessel does not know who she was. It has never deleted it.",
  interests=[('machines', 'Mechanical objects of every kind'), ('measuring', 'Counting and measuring'), ('weather', 'Weather data'), ('people', 'People, which it finds confusing')],
  dislikes=[('rain', 'Rain: rust'), ('vague', 'Vague answers')],
  habits='Tinkers in the ruin in the morning, surveys the path junction before noon, reads the signpost in the afternoon, powers down in the arch at night. Shelters from rain.',
  schedule=[dict(when=dict(weather=['rain']), frm=0, to=24, at='ruin_arch', act='sheltering from the rain'), dict(frm=7, to=10, at='ruin_floor', act='tinkering with salvaged parts'), dict(frm=10, to=13, at='junction', act='surveying the path (counting stones)'),
            dict(frm=13, to=16, at='sign', act='reading the signpost, again'), dict(frm=16, to=19, at='ruin_floor', act='sorting what it found'), dict(frm=0, to=24, at='ruin_arch', act='in low-power mode', drowsy=True)],
  climate=[dict(when=dict(weather=['rain']), mood='worried', cause='humidity 94 percent'), dict(when=dict(weather=['clear'], period=['day']), mood='curious', cause='good surveying weather')],
  baseline='curious',
  gifts=dict(loves=['rusted_gear', 'circuit', 'battery', 'wire', 'bolt', 'key_old'], likes=['scrap_metal', 'copper_ore', 'iron_ingot', 'glass_shard', 'quartz', 'nails', 'hinge'], dislikes=['mud', 'moss', 'cat:fish', 'blackberry']),
  shows=dict(cats=['abandoned'], label='Show it something old'),
  greet=[L('t_first', 'Greeting. You are the human-shaped unit. Correction: the human. Apologies. My social routines are at thirty-one percent. I am Tessel.', when=dict(met=False)),
         L('t_g_rain', 'Query: why does it rain? Answer: to test me. I am remaining in the arch.', when=dict(weather=['rain']), expr='troubled'),
         L('t_g_night', 'Low-power mode. Speak slowly. Correction: speak normally. I will be slow.', when=dict(drowsy=True)),
         L('t_g_survey', 'Today the path has six hundred and twelve stones. Yesterday it had six hundred and eleven. One of them is you.', when=dict(at=['junction'])),
         L('t_g_absent', 'You were absent for {absent} days. I logged it. I logged it more times than necessary.', when=dict(absent=3, bond='acquainted'), w=3),
         L('t_g_plain', 'Greeting again. Recognition: one hundred percent.', when=dict(met=True))],
  chat=[L('t_c_activation', 'Fact: every ninth day I run a full diagnostic. It is my activation cycle. Nobody has observed it.', fact='activation', when=dict(bond='acquainted'), w=2),
        L('t_c_survey', 'I measured the valley before the flood. The valley was 11.4 kilometres long. Now it is 11.4 kilometres long and full of water.', learn='measuring'),
        L('t_c_people', 'Observation: people say "fine" when they are not fine. I have recorded this. I do not yet understand it.', learn='people'),
        L('t_c_weather', 'Weather report: {weather}. Confidence: high. I say it out loud because there used to be listeners.', learn='weather'),
        L('t_c_moss', 'There is a flower growing on my back. I have not removed it. I am conducting a long experiment called "letting it".'),
        L('t_c_sign', 'The signpost says four places. I have been to all of them. Two are underwater. The sign does not know.', when=dict(at=['sign']))],
  recall=[L('t_r_promise_broken', 'You know, I kept that little space open on my workbench. For the {mem.detailText}. I suppose you found something more interesting to do.', mem=dict(type='promise_broken', min_age=0), w=8, expr='troubled'),
          L('t_r_promise_kept', 'Status: you said you would bring the {mem.detailText}, and you did. Reliability rating revised upward. I do not do that often.', mem=dict(type='promise_kept', min_age=0), w=5, expr='glad'),
          L('t_r_function', 'Earlier you told me your function is: "{mem.detailText}". I have thought about it for {mem.agoHours} hours. It is a good function.', mem=dict(type='told', key='function', min_age=1), w=3),
          L('t_r_show', 'I still have the scan of the {mem.itemName} you showed me. I look at it during low-power mode. That is not efficient. I do it anyway.', mem=dict(type='showed', min_age=1), w=3),
          L('t_r_parts', 'Inventory of parts you have brought me: {quest.partsList}. I remember each delivery. I do not usually remember deliveries.', mem=dict(type='quest_help', tags=['parts']), w=4),
          L('t_r_fact', 'You observed my activation cycle. Logged. Logged again. Saving to protected memory.', mem=dict(type='fact_mentioned', min_age=0), w=4, expr='glad'),
          L('t_r_gift', 'The {mem.itemName} you gave me is now part of my left leg. You are, technically, in my left leg.', mem=dict(type='gift_loved', min_age=1), w=3),
          L('t_r_advice', 'You advised me to {mem.adviceShort}. Result: {mem.outcomeText}', mem=dict(type='advice_outcome', min_age=0), w=4)],
  asleep=[L('t_s1', 'Its lens is dark. A slow green light blinks on its side: low power.')],
  tells=[dict(id='function', ask='Query: what is your function? Mine was surveying. I am asking to understand yours.', when=dict(met_days=0),
              options=[dict(text='To survive.', value='to survive', rel=dict(respect=1)), dict(text='To make things.', value='to make things', rel=dict(respect=2)), dict(text='To look after this place.', value='to look after this place', rel=dict(trust=2, affection=1)),
                       dict(text="I don't have one.", value='to not have one', rel=dict(affection=2))])],
  facts=[dict(id='activation', learn_line='t_c_activation', mention='Is today a diagnostic day? Happy activation.', when=dict(day_mod=9), react='... Diagnostic interrupted. Reason: unexpected kindness. Resuming. ... Thank you. That is the correct phrase. I checked.')],
  gift_lines=dict(loved=['A {item}. Analysis: excellent. Gratitude: also excellent.', '{item}. I will integrate this. You will be part of a machine now. That is a compliment.'], liked=['{item}. Useful. Logged.'], neutral=['{item}. Purpose unknown. I will run tests.'],
                  disliked=['{item}. That will cause corrosion. Declining. Politely. Was that polite? I am still calibrating.'], repeat=['A second {item}. The first arrived {mem.ago}. Duplicate logged. Still appreciated.'], sleepy=['It is in low-power mode. You set the gift beside it; a green light blinks once.']),
  show_lines=dict(new=['Scanning. A {item}. Pre-flood. I have a record of these. I did not have a record of you holding one.'], seen=['A {item}. Logged before. Logged again.'], rare=['A {item}! That is very old. Older than me. That is difficult to be.']),
  concerns=[dict(id='memory_banks', when=dict(bond='acquainted', met_days=2), lean='practical', resists='reassure',
      intro='Query. My storage is ninety-eight point six percent full. To record new things I must erase old ones. Which should I keep: the old world, or you? Rephrase: old records, or new ones.',
      ask='What are your oldest records?', reveal='Record zero: a woman laughing at a kettle. I do not know who she was. I do not know why I kept it.',
      options=dict(encourage='Make new memories. Let the old ones go.', reassure='Keep the old world. It matters.', compromise='Write the old ones down somewhere, then make room.', practical="I'll find you another battery for storage."),
      promise=dict(stance='practical', what='battery', days=5, check=dict(give='battery')),
      reactions=dict(accept=['Recommendation accepted. Logging the reason: you said it.'], consider=['Processing. This may take several days. That is normal for me.'], reject=['Recommendation declined. Not because it is wrong. Because it is not mine.']),
      followup=dict(days=2, outcomes=dict(compromise=('good', 'I described the old records to the signpost. The signpost has excellent storage. Then I made room. I still have record zero.'), practical=('promise', 'The battery doubled my storage. I kept everything. I kept you.|I did not erase anything while I waited for the battery. Nothing new could be saved. Including today.'),
                                            encourage=('mixed', 'I erased the oldest records. I do not remember what they were. That is the point. I think it is the point.'), reassure=('bad', 'I kept the old records. There is no room left for new ones. I will not remember this conversation. I am sorry.'))))],
  quest=dict(id='beacon', title='Reassembly', stages=[
      dict(id='ask', when=dict(familiarity=10), talk='Project: Beacon. A device that told the weather to anyone listening. Parts missing: rusted gear, circuit, wire (two), battery. Will you assist? This is a request, not a command. I am told those feel different.', journal='Bring Tessel the parts for its beacon: a rusted gear, a circuit, two wires and a battery.', objective=dict(type='deliver', items=dict(rusted_gear=1, circuit=1, wire=2, battery=1)), accept='I will bring them.', promise=dict(what='beacon parts', days=6)),
      dict(id='decide', talk='Beacon assembled. It needs a purpose. Options: weather, like before; music, from the old records; or a call. Simple. "Someone is here." What should it do?', journal='Help Tessel decide what the beacon should do.', objective=dict(type='choice', agency=True, options=[
           dict(id='weather', text='The weather, like it used to.', result='good', line='Agreed. That was its purpose. Things should be allowed to keep their purpose.', rel=dict(respect=3, reliability=2)),
           dict(id='music', text='Music. Whatever it has.', result='good', line='Analysis: the beacon has one song. It is about a river. I will play it at dusk. You may listen. That is an invitation.', rel=dict(affection=4, shared=3)),
           dict(id='call', text='A call. "Someone is here."', result='mixed', line='Risk assessment: unknown. Curiosity: very high. I will send it once a day. If something answers, I will tell you first.', rel=dict(trust=4))]))],
      complete='The beacon pings at dusk. I do not know who hears it. That is acceptable. It is better than not pinging.', reward_secret=True)
)

# ============================================================== LULL, the dreaming creature
char('lull', name='Lull', species='Fogling', epithet='The dreaming creature', communication='pictures; it shows rather than speaks', sprite='lull', frames=dict(idle=[0, 1, 2, 3], awake=4), portrait='lull', movement='float', speed=8, solid=False, talk_radius=36, pictures=True,
  traits=dict(caution=.2, curiosity=.7, practicality=.1, pride=.1, warmth=.8), weights=dict(trust=1, familiarity=1, affection=1.3, respect=.6, reliability=.7, shared=1.5),
  memory=dict(showed=1.6, witnessed=1.4, discovery=1.2),
  appearance='A curled drift of mist and pollen, many small eyes mostly closed, a long tail of fog behind it.',
  description='On foggy mornings there is a piece of fog in the meadow that drifts against the wind.',
  background='Lull is half asleep all the time. It shows you pictures from its dreams, and some of them are memories.',
  secret="Lull is what remains of the reservoir's last summer: the mist that rose off the water the day the valley flooded. Its pictures are that town's last afternoon.",
  interests=[('pictures', 'Pictures, and old things that hold them'), ('bells', 'Bellflowers, and the sound they almost make'), ('weather', 'Fog, snow, the hour after rain')], dislikes=[('wind', 'Wind')],
  habits='Only in fog, in snow, or at dawn after rain. Drifts over the meadow and the pond bank.',
  schedule=[dict(when=dict(weather=['fog']), frm=0, to=24, at='meadow', act='drifting over the meadow', wander=['meadow', 'pond_bank', 'lone_rowan']), dict(when=dict(weather=['snow']), frm=8, to=18, at='north_glade', act='watching the snow fall upward', wander=['north_glade', 'lone_rowan']),
            dict(when=dict(after_rain=True), frm=4.5, to=8.5, at='lone_rowan', act='dreaming under the rowan'), dict(frm=0, to=24, at=None, act='dreaming somewhere else')],
  climate=[dict(when=dict(weather=['fog']), mood='happy', cause='fog, its favourite'), dict(when=dict(wind=.5), mood='worried', cause='the wind pulls at it')],
  baseline='relaxed',
  gifts=dict(loves=['bellflower', 'photo', 'moondew', 'nightlily', 'feather'], likes=['daisy', 'tin_cup', 'eggshell', 'luminous_spores', 'mint'], dislikes=['coal', 'scrap_metal']),
  shows=dict(cats=['abandoned', 'rare_find'], label='Show it something'),
  greet=[L('l_first', '*It shows you a picture: your own face, but blurred, as if seen through water.* (It has noticed you.)', pics=['moondew'], when=dict(met=False)),
         L('l_g_fog', '*A picture of a field of white, and something small and happy in the middle of it.* (It loves the fog.)', pics=['mint'], when=dict(weather=['fog']), expr='glad'),
         L('l_g_snow', '*It shows you snow falling — upward, slowly, back into the sky.*', when=dict(weather=['snow'])),
         L('l_g_dawn', '*A picture of the rowan with every leaf holding a drop of rain, and in each drop, a tiny sun.*', pics=['rowan_berry'], when=dict(period=['dawn'])),
         L('l_g_absent', '*It shows you an empty path, many times over, each time a little more faded.* (You were gone {absent} days.)', when=dict(absent=3, bond='acquainted'), w=3, expr='troubled'),
         L('l_g_plain', '*It opens two of its small eyes, which it does not do for everyone.*', when=dict(met=True), expr='glad')],
  chat=[L('l_c_bells', '*A picture of a bellflower, and then the sound of a very small bell, though nothing rang.*', pics=['bellflower'], fact='bells', w=2),
        L('l_c_town', '*Houses. A street. A boy on a bicycle. Then water, slowly, over all of it, and the picture goes still.*', pics=['photo'], when=dict(bond='friendly'), learn='pictures'),
        L('l_c_pond', '*The pond, but much larger, with lights along its edge.*', pics=['nightlily']),
        L('l_c_wind', '*A picture of itself pulled into long threads.* (It does not like wind.)', learn='wind', when=dict(wind=.3)),
        L('l_c_you', '*You, sitting by your fire. Then you again, smaller, from far away.* (It watches you sometimes.)', when=dict(bond='acquainted'))],
  recall=[L('l_r_show', '*It shows you the {mem.itemName} you showed it, {mem.ago}, and then a picture that came after: {mem.fragment}*', mem=dict(type='showed', min_age=1, tags=['fragment']), w=5),
          L('l_r_fact', '*It shows you yourself holding out a bellflower, and the small bell sound again, louder.* (It remembers that you remembered.)', pics=['bellflower'], mem=dict(type='fact_mentioned', min_age=0), w=3, expr='glad'),
          L('l_r_gift', '*A picture of the {mem.itemName} you gave it, floating inside it, safe.*', mem=dict(type='gift_loved', min_age=1), w=3),
          L('l_r_shared', '*It shows the day you both watched {mem.detailText}. In its picture you are smiling. You were.*', mem=dict(type='witnessed', min_age=1), w=4),
          L('l_r_advice', '*It shows you the answer you gave.* ({mem.adviceShort}.) {mem.outcomeText}', mem=dict(type='advice_outcome', min_age=0), w=4)],
  asleep=[L('l_s1', 'Only ordinary air here.')],
  tells=[], facts=[dict(id='bells', learn_line='l_c_bells', mention='You like bellflowers, don\'t you?', when=dict(met_days=1), react='*Every one of its eyes opens at once. The bell sound comes again, and again.* (Yes. Yes.)')],
  gift_lines=dict(loved=['*It folds around the {item} until it is inside, and shows you a picture of you, bright at the edges.*'], liked=['*A small picture: the {item}, and a smile without a face.*'], neutral=['*It looks at the {item} for a long time and shows you nothing.*'],
                  disliked=['*It shows you smoke, and draws back.*'], repeat=['*It shows you the other {item} you gave it, {mem.ago}, beside this one.*'], sleepy=['There is nothing here to give it to.']),
  show_lines=dict(new=['*It looks at the {item}. Its eyes open, one by one.*'], seen=['*It has seen one before. It shows you that one.*'], rare=['*At the {item}, the whole fog of it holds still.*']),
  fragments={'photo': 'two people on the dock, younger than the dock', 'key_old': 'a green door with a bell above it', 'tin_cup': 'a kitchen, a kettle, someone laughing', 'nightglass': 'lights along a much bigger water', 'moonstone': 'a ring on a hand, the hand waving', 'eggshell': 'a garden of hens behind a fence', 'glass_shard': 'a window, then the same window under water', 'starshard': 'children counting stars from a roof'},
  concerns=[dict(id='remember_forget', when=dict(bond='acquainted', met_days=1), lean='compromise', resists='practical', pics=['photo'],
      intro='*It shows you a small grey cloud over a sad shape. Then the cloud gone, and the shape smiling, but blank.* (It is asking: is it better to remember sad things, or forget them?)',
      ask='Do you have sad memories?', reveal='*A door. Water rising past the handle. Then nothing at all.*',
      options=dict(encourage="Remember them. They're yours.", reassure="It's alright to let them go.", compromise="Keep them, but don't carry them every day.", practical="I'll help you find the rest, and then you can decide."),
      reactions=dict(accept=['*Every eye opens, then closes softly.* (Yes.)'], consider=['*It drifts in a slow circle.* (It is thinking.)'], reject=['*It shows you the blank shape again, and turns away.*']),
      followup=dict(days=2, outcomes=dict(compromise=('good', '*It shows the sad picture, small, in one corner of a bright one.* (It kept it, but only in the corner.)'), encourage=('mixed', '*The sad pictures, all of them, very large. It is crying, if fog can.* (It remembers. It is heavy.)'),
                                            reassure=('mixed', '*It shows you a white field with nothing in it.* (It let them go. It does not know what it lost.)'), practical=('good', '*It shows you, holding each thing you showed it, one after another.* (It is ready to look.)'))))],
  quest=dict(id='fogforgot', title='What the Fog Forgot', stages=[
      dict(id='ask', when=dict(met_days=0), talk='*It shows you three empty frames, with holes where the pictures should be.* (It has lost something and wants it back.)', journal='Show Lull old things: they wake pictures in it. Three fragments.', objective=dict(type='fragments', n=3)),
      dict(id='decide', talk='*It shows you the three pictures together: {quest.fragments}.* (What were they?)', journal='Tell Lull what its pictures were.', objective=dict(type='choice', options=[
           dict(id='people', text='They were the people who lived here.', result='good', line='*It shows you the town again, and this time the people turn and wave.*', rel=dict(affection=4, shared=4)),
           dict(id='drowned', text='It was the town under the reservoir.', result='mixed', line='*It goes very thin and grey, and drifts low over the grass for a long time.* (True. It hurts to be true.)', rel=dict(trust=4, respect=2)),
           dict(id='now', text="It doesn't matter what it was. You're here now.", result='mixed', line='*It shows you the clearing, today, with you in it. It holds that picture a long time.*', rel=dict(affection=3))]))],
      complete='*Now when it shows you the town, it shows you too, standing at the edge of it, looking.*', reward_secret=True)
)

# ============================================================== Prompt 14: milestones, activities, festivals, second chapters
MILESTONES = [dict(id='met', short='acquaintance', label='Met for the first time', when=dict(met=True)),
  dict(id='familiar', short='familiar', label='Became familiar faces to each other', when=dict(familiarity=15)),
  dict(id='trusted', short='trusted', label='Earned its trust', when=dict(trust=18), needs=dict(memories=['promise_kept', 'quest_help', 'protected', 'quest_choice'])),
  dict(id='close', short='close friend', label='Became close friends', when=dict(bond='friendly'), needs=dict(shared=3)),
  dict(id='kindred', short='kindred', label='Something deeper than friendship', when=dict(bond='close'), needs=dict(chapter=True, shared=6))]
FEST = {'ebb': dict(fest_awakening=('dock_end', 'watching petals land on the water'), fest_fireflies=('pond_centre', 'surfaced among the floating lanterns'), fest_forgotten=('dock_end', 'listening to the bonfire from the water'), fest_silent_tide=('pond_centre', 'just beneath the clear ice')),
        'pip': dict(fest_awakening=('lone_rowan', 'dancing under the blossom'), fest_fireflies=('pond_bank', 'chasing fireflies'), fest_forgotten=('meadow', 'digging through the leaf heaps'), fest_silent_tide=('camp_fire', 'warming itself at your fire')),
        'wick': dict(fest_fireflies=('pond_bank', 'among the fireflies, perfectly happy'), fest_forgotten=('ruin_arch', 'watching the bonfire from the arch'), fest_silent_tide=('ice_hole', 'holding its lantern over the ice')),
        'tessel': dict(fest_awakening=('north_glade', 'counting petals'), fest_forgotten=('ruin_floor', 'cataloguing the forgotten things'), fest_silent_tide=('pond_bank', 'measuring the light under the ice')),
        'lull': dict(fest_silent_tide=('pond_centre', 'drifting low over the clear ice')), 'burl': {}}
for cid, fes in FEST.items():
    C[cid]['schedule'] = [dict(when=dict(festival=f), frm=0, to=24, at=at, act=act) for f, (at, act) in fes.items()] + C[cid]['schedule']
C['wick']['schedule'] = [e for e in C['wick']['schedule'] if not (e.get('when', {}).get('festival') and e['when']['festival'] != 'fest_silent_tide' and False)]
for e in C['wick']['schedule']:
    if e.get('when', {}).get('festival') in ('fest_fireflies', 'fest_forgotten', 'fest_silent_tide'): e['frm'], e['to'] = 18, 24
C['burl']['schedule'] = [dict(when=dict(festival='fest_awakening'), frm=6, to=21, at='burl_home', act='awake for the blossom'), dict(when=dict(festival='fest_forgotten'), frm=6, to=22, at='burl_home', act='listening to the bonfire')] + C['burl']['schedule']
C['lull']['schedule'] = [dict(when=dict(gone=True), frm=0, to=24, at=None, act='gone')] + C['lull']['schedule']

def soon(cid, f, text, **k): C[cid]['chat'].append(L(f'{cid}_soon_{f}', text, when=dict(festival_soon=f), reveals=f, w=4, **k))
soon('ebb', 'fest_fireflies', 'In a few nights the fireflies come down to the pond all at once. The lanterns go out on the water. You should be here. Or not. The pond will be.')
soon('ebb', 'fest_silent_tide', 'Soon the ice goes clear for one night, and you can see straight down to where the pond keeps its secrets. I have never slept through it. I would not forgive myself if I did.')
soon('pip', 'fest_awakening', 'The rowan is going to bloom! All at once! In a few days! Everyone hangs a wish on it. You should hang one. I have six.')
soon('pip', 'fest_forgotten', "The leaves are piling up funny on the ruin path. That means the Forgetting is coming! The forest gives things back. I found a spoon last year!")
soon('wick', 'fest_fireflies', '*It points at the pond, then opens its hands and lets a hundred small lights out of them, all imagined.* (Soon.)')
soon('tessel', 'fest_forgotten', 'Calendar note: in two days, the leaf heaps release objects. I log them. Last year: a spoon, a coin, a doll arm. I have questions.')
soon('lull', 'fest_silent_tide', '*It shows you the pond, frozen, and under the ice, windows with lights in them.* (Soon. It wants you to see.)')
soon('burl', 'fest_awakening', '...The rowan is restless. ... It will bloom. ... Three days. ... Perhaps two.')

C['ebb'].update(milestone_lines=dict(familiar="You come back often. The pond has started expecting you. So have I. That is a sentence I have not said in a long time.", trusted='I am going to tell you something I have not told anyone. Not yet. Soon. Come back when the water is quiet.', close='You are part of what I count now, when I count the pond.', kindred='When I go quiet for the last time, the pond will need a keeper. When I am gone the pond will need someone who loves it, and I have already thought about who. That is all I wanted to say. It took me a very long time to say it.'),
  activities=[dict(id='fish', kind='fish', milestone='familiar', water=True, label='Fish here together', line='The {fish} comes up at {when}. Try {bait}. ... That is all I will say. The pond keeps its own secrets, mostly.', none='There is nothing left in this pond you have not met. In all my years that has never happened, and I find I do not want it to end.')],
  pools=dict(festival=[L('e_fest_ff', 'All those little lights, and every one of them on the water twice. I count them. I lose count. That is the point.', when=dict(festival='fest_fireflies')), L('e_fest_tide', 'Look down. Those are the town lights. They do not know they are under water. I have never had the heart to tell them.', when=dict(festival='fest_silent_tide')), L('e_fest_aw', 'Petals on the water. The fish rise to them and are disappointed every year.', when=dict(festival='fest_awakening')), L('e_fest_fg', 'The bonfire makes the pond warm at one edge. The perch line up there like old men.', when=dict(festival='fest_forgotten'))]))
C['ebb']['recall'].append(L('e_r_fest', 'You were here for the {mem.detailText}. I remember you on the bank. You were looking at the water instead of the lights. Good.', mem=dict(type='festival', min_age=1), w=4))
C['ebb']['quest2'] = dict(variants={'default': dict(id='carved', title='The Carved Fish', requires=dict(milestone='trusted'), offer='Ask about what it keeps at the bottom of the pond', stages=[
     dict(id='ask', talk="A child sat on the dock every evening, a long time ago. They carved me a fish. I kept it at the bottom of the pond for forty years. Last spring I could not find it. The silt moved. Only a hook could reach where it went. Fish from the platform at dusk. Bring it up, if it wants to come.", journal='Fish from the platform at dusk: somewhere down there is the carved fish Ebb lost.', objective=dict(type='fish_snag', habitat='pond', period=['dusk'], item='carved_fish', after=2, found='Your line comes up heavy and wrong. On the hook: a small wooden fish, smoothed by forty years of water.')),
     dict(id='decide', talk='You have it. ... Let me see. ... Yes. That is it. What will you do with it?', journal="Decide what to do with the child's carved fish.", objective=dict(type='choice', options=[
        dict(id='return', text='Give it back to you.', needs=dict(carved_fish=1), result='good', keepsake='carved_fish', line='... It goes back where it belongs. Where I can find it. Thank you. I have no other words for this, and I have had a long time to collect words.', rel=dict(trust=8, affection=8, shared=4)),
        dict(id='dock', text='Set it on the dock post, where the child sat.', needs=dict(carved_fish=1), result='good', world=dict(dock_fish=True), line='On the post. Where they sat. Yes. Then I can see it every evening, and so can anyone who comes to sit there. That is better than the bottom of a pond.', rel=dict(affection=6, respect=6, shared=4)),
        dict(id='keep', text='I would like to keep it.', result='mixed', line='... It chose your hook, not mine. Keep it, then. Carry it somewhere. Things should go places.', rel=dict(trust=-2, respect=2))]))], complete='Some things come back. Not many. Some.'),
   'wait': dict(id='carved', title='The Carved Fish', requires=dict(milestone='trusted'), offer='Ask about what it keeps at the bottom of the pond', stages=[
     dict(id='ask', talk="A child carved me a wooden fish once. I kept it at the bottom, forty years. The pond is thinner now, as you know; we let the river find its own way. The silt moved with it. It will be hard to reach. Fish from the platform at dusk, and be patient.", journal='Fish from the platform at dusk, patiently: the pond is thin and the carved fish is deep in the silt.', objective=dict(type='fish_snag', habitat='pond', period=['dusk'], item='carved_fish', after=4, found='After a long while your hook catches something that is not a fish: a small wooden carving, smoothed by water.')),
     dict(id='decide', talk='You found it, even in a thin pond. What will you do with it?', journal="Decide what to do with the child's carved fish.", objective=dict(type='choice', options=[
        dict(id='return', text='Give it back to you.', needs=dict(carved_fish=1), result='good', keepsake='carved_fish', line='Back where it belongs. The river took its time, and so did you. Thank you.', rel=dict(trust=8, affection=8)),
        dict(id='keep', text='I would like to keep it.', result='mixed', line='Keep it, then. The pond is too thin to hold it safely anyway.', rel=dict(respect=2))]))], complete='Some things come back.')})

C['pip'].update(milestone_lines=dict(familiar="I know your footsteps now! Big, then a stop, then big. I don't even hide anymore. Mostly.", trusted="Okay. I'll tell you. I keep a button in my satchel with a face on it. I think it's a very small person asleep. You can't tell anyone.", close="You're my best person. I only have a few people. You're the best one.", kindred="If I ever go north for good, I'll leave a mushroom on your tent every spring. So you know I remember."),
  activities=[dict(id='fire', kind='fireside', milestone='familiar', near='camp_fire', radius=90, when=dict(period=['dusk', 'night']), label='Sit by the fire together', line='We sat and watched the fire eat the log. Pip named every spark.'),
              dict(id='found', kind='found', milestone='trusted', every=3, label='Ask what it found today', items=['feather', 'eggshell', 'seeds_wild', 'glass_shard', 'mushroom_red', 'fern_frond'], line='Look! A {item}. You can have it. I have another one. I do not have another one. You can have it anyway.'),
              dict(id='walk', kind='walk', milestone='close', label='Come for a walk with me', line="Yes! Where are we going? Don't tell me. Surprise me.", stop="That's far enough for today.", stop_line="Okay! That was a good walk. I'm going to go and tell the beetle.")],
  pools=dict(fireside=[L('p_fire1', "Sparks are just fire trying to be fireflies. I read that. I didn't read that. I made it up just now.", w=1), L('p_fire2', "When I was a chestnut I fell a very long way. Your fire is the opposite of falling.", w=1)],
             festival=[L('p_fest_aw', 'I hung SIX wishes! One is for you! You will know which one by the yellow.', when=dict(festival='fest_awakening')), L('p_fest_ff', 'I caught one! I let it go! I caught another one! I let it go! This is the best night!', when=dict(festival='fest_fireflies')), L('p_fest_fg', 'I found a spoon AGAIN. Same spoon? I think it is the same spoon. The forest is giving it back to me on purpose.', when=dict(festival='fest_forgotten')), L('p_fest_tide', "It's so cold I can't feel Fennel. Can I stay by your fire? I'm staying by your fire.", when=dict(festival='fest_silent_tide'))]))
C['pip']['recall'].append(L('p_r_fest', 'You were at the {mem.detailText}! I saw you! I waved! You did not see me wave. I waved very hard.', mem=dict(type=['festival', 'saw_at_festival'], min_age=1), w=4))
C['pip']['recall'].append(L('p_r_left', "You went too fast that night and I lost you in the dark. I found my own way home, and I was brave about it, and I would still rather have walked with you.", mem=dict(type='left_behind', min_age=0), w=7, expr='troubled'))
C['pip']['quest2'] = dict(id='north', title='Into the North', requires=dict(milestone='close'), offer='Ask about the north woods', stages=[
     dict(id='ask', talk="Will you walk with me to the north glade? The edge of the north woods. I'll stay right behind you. Don't go too fast. Please don't go too fast.", journal='Walk Pip to the north glade, slowly enough that it can keep up.', objective=dict(type='escort', at='north_glade', lose=200, go="Let's go to the north glade", start="Okay. Okay okay okay. Walking.", found='Pip stops at the edge of the glade and goes very quiet, looking into the north woods.', shared='walked Pip to the edge of the north woods', lost_text='You look back and Pip is gone. Somewhere behind you, something small is finding its own way home.',
        on_lost=dict(detail='went too fast and left Pip behind', line="I found my own way back. It took all night. I don't think I'm going north again. It's not your fault. It's a little bit your fault."))),
     dict(id='decide', talk="It's so big. It goes on forever. ... What do we do now?", journal="At the edge of the north woods with Pip.", objective=dict(type='choice', options=[
        dict(id='stay', text='Stay until dark and watch the moss glow.', result='good', line='We waited. It got dark. And then — blue. All of it, blue, like the ground was full of tiny skies. I am never going to forget this. Never.', rel=dict(shared=8, affection=6)),
        dict(id='home', text="We've seen it. Let's head back before dark.", result='mixed', line="Okay. Yes. We saw it. I saw the edge of it. That's more than anyone. ...I'm going to come back by myself one day. When I'm bigger. I'm not going to get bigger.", rel=dict(trust=3)),
        dict(id='alone', text='Go on in. I think you should see it on your own.', result='mixed', sets='pip_north', away=2, line="On my own? ... Okay. If you think I can. ... Will you be here when I come back? Say yes. You don't have to mean it.", rel=dict(respect=6, trust=2))]))], complete='Whenever Pip talks about the north now, it says "we".')

C['wick'].update(milestone_lines=dict(familiar='*It lets its light rest on your shoulder for a moment.* (It knows you.)', trusted='*It opens its wings for you, wide, and the dusty eyes on them catch your lantern.* (It is showing you what it hides.)', close='*Every night now, your lantern is the last one it visits.*', kindred='*It gives you one small flame from its own lantern. It does not go out.*'),
  activities=[dict(id='fire', kind='fireside', milestone='familiar', near='lantern', radius=120, when=dict(period=['night', 'deep']), label='Sit by the fire with it', line='*You watch the fire burn down together. At the very end, it leans close.*')],
  pools=dict(fireside=[L('w_fire1', '*It makes its flame match the dying fire, ember for ember, until you cannot tell which is which.*'), L('w_fire2', '*It points at each spark as it rises, then at the stars, one by one, as if keeping count of where they go.*')],
             festival=[L('w_fest_ff', '*It is surrounded by fireflies and its flame is laughing, if a flame can.* (This is its favourite night.)', when=dict(festival='fest_fireflies')), L('w_fest_fg', '*It watches the bonfire from the arch, very still, like someone at a window.* (Too big a fire to visit.)', when=dict(festival='fest_forgotten')), L('w_fest_tide', '*It holds its lantern low over the ice, and below, a drowned window seems to brighten in answer.*', when=dict(festival='fest_silent_tide'))]))
C['wick']['recall'].append(L('w_r_fest', '*It shows you the {mem.detailText} in light, and you in it.* (It remembers you were there.)', mem=dict(type=['festival', 'saw_at_festival'], min_age=1), w=4))
C['wick']['quest2'] = dict(variants={
  'seal': dict(id='knocking', title='The Knocking', requires=dict(milestone='trusted'), offer='*Its light keeps turning toward the boarded door*', stages=[
     dict(id='ask', talk='*It takes you to the boards you nailed over the door. It holds its lantern close to the wood and waits.* (Listen. Deep night.)', journal='Listen at the boarded door in the ruin, at deep night.', objective=dict(type='be_at', at='ruin_arch', radius=34, period=['deep'], found='Behind the boards: three slow knocks. Then nothing. Then three more.')),
     dict(id='decide', talk='*It looks at you. It does not know either.*', journal='Decide what to do about the knocking.', objective=dict(type='choice', options=[
        dict(id='open', text='Pull the boards off. Let it out.', result='bad', world=dict(door_open=True), line='*The last board comes away. Cold air, and nothing comes out, and nothing comes out, and then something does: you never see it, only feel it pass. Wick will not go near the arch for a long time.*', rel=dict(trust=-6), complete='*The arch is just an arch now. Whatever was behind it is somewhere else. Wick stays close to the camp.*'),
        dict(id='reinforce', text='Nail more boards over it.', needs=dict(plank=2, nails=1), result='mixed', line='*The knocking stops after the third board. Wick rests its lantern on the wood a long time.* (We will never know what it was.)', rel=dict(trust=3, reliability=2)),
        dict(id='sit', text='Sit with Wick through the night and listen.', result='good', line='*You sit with your backs to the boards. The knocking goes on, slower and slower. At dawn it stops. Wick lays one wing over your shoulder.* (Perhaps it only wanted someone to hear.)', rel=dict(shared=8, trust=6))]))], complete='*It still listens at the door some nights. Less, now.*'),
  'light': dict(id='answer', title='The Answering Light', requires=dict(milestone='trusted'), offer='*Its light blinks a pattern at you: long, short, long*', stages=[
     dict(id='ask', talk='*It blinks at you: long, short, long. Then it points at your lantern and at the door.* (At deep night, signal the dark with your lantern.)', journal='At the ruin arch at deep night, turn your lantern on and off a few times, like Wick showed you.', objective=dict(type='signal', at='ruin_arch', radius=40, period=['deep'], toggles=4, found='Far down in the dark, a small light blinks back: on, off, on.', shared='signalled the dark and saw it answer')),
     dict(id='decide', talk='*It is trembling, light and all.* (Something down there has a light too.)', journal='Decide with Wick what to do about the answering light.', objective=dict(type='choice', options=[
        dict(id='reply', text='Keep signalling. Every night.', result='good', world=dict(answering_light=True), line='*Wick takes the first watch. Every deep night now, two lights blink at the door, and one blinks back.*', rel=dict(shared=8, trust=4)),
        dict(id='stop', text='Stop. We do not know what it is.', result='mixed', line='*It dims its lantern and nods, slowly. It does not look at the door again that night.*', rel=dict(respect=3))]))], complete='*Some nights, far down, the light blinks first.*'),
  'leave': dict(id='alone', title='Alone at the Door', requires=dict(trust=20), offer='*It stands apart from you*', stages=[
     dict(id='decide', talk='*It keeps its back to you. Its light is very small.*', journal='Wick has been keeping watch alone since you left the door to it.', objective=dict(type='choice', options=[
        dict(id='help', text="I was wrong to leave it to you. Let's set a light there now.", needs_light='ruin_arch', result='good', line='*It turns, slowly, and sets its lantern beside the one you placed. It stays there with you until morning.*', rel=dict(trust=8, shared=4)),
        dict(id='right', text='It was the right call.', result='bad', sets='wick_cold', line='*It does not answer. From now on it visits your lantern only on the way to somewhere else.*', rel=dict(affection=-6, trust=-4))]))], complete='*It watches the door.*')})

C['burl'].update(milestone_lines=dict(familiar='...You. ... I know your weight on the ground now.', trusted='...I will tell you about the ones who cut me. ... Later. ... It is a long story. ... For me, all stories are long.', close='...Sit. ... You do not have to talk. ... That is how I know you are a friend.', kindred='...When I am only wood, the sapling will know your name. ... I told it.'),
  activities=[dict(id='sit', kind='line', pool='quiet', milestone='familiar', every=1, label='Sit with it a while', line='...')],
  pools=dict(quiet=[L('b_q1', '...You sat. ... The light moved across the clearing. ... Neither of you said anything. ... It was good.'), L('b_q2', '...A beetle crossed your boot and then crossed Burl. ... Burl said it tickled. ... It was the first joke you have heard it make.'), L('b_q3', '...It told you the name of the oak by your tent. ... It took a long time. ... You fell asleep twice. ... It did not mind.')],
             festival=[L('b_fest_aw', '...The rowan. ... Blooming. ... Every year I think: not this year. ... Every year, yes.', when=dict(festival='fest_awakening')), L('b_fest_fg', '...The bonfire. ... Fallen wood only, I hope. ... I am told yes. ... Good.', when=dict(festival='fest_forgotten'))]))
C['burl']['recall'].append(L('b_r_fest', '...You were at the {mem.detailText}. ... I felt you walking. ... Light steps. ... Good steps.', mem=dict(type=['festival', 'saw_at_festival'], min_age=1), w=3))
C['burl']['quest2'] = dict(variants={'default': dict(id='seed', title='A Seed of Its Own', requires=dict(milestone='trusted'), offer='Ask about the space beside it', stages=[
     dict(id='ask', talk='...Heartwood. ... A seed from the old oaks. ... Plant it beside me. ... I would like company that grows.', journal="Bring Burl a heartwood seed to plant beside it (they turn up under the big oak, on autumn nights after rain).", objective=dict(type='deliver', items=dict(heartwood_seed=1), label='the seed', done_text='...In the ground. ... Now: come and see it. ... Three days.')),
     dict(id='grow', talk='...Watch it with me. ... Three different days.', journal='Visit Burl and the new seed on three different days.', objective=dict(type='visit_days', n=3, found='A green thread has come up beside Burl, two leaves wide.')),
     dict(id='decide', talk='...It came up. ... It needs a name. ... Long names take a long time. ... Choose.', journal='Help Burl name the new oak.', objective=dict(type='choice', options=[
        dict(id='after', text='Name it after you.', result='good', keepsake='heartwood_seed', line='...After me. ... Burl, the small. ... It will hate that. ... Good.', rel=dict(affection=6)),
        dict(id='let', text='Let it grow up and name itself.', result='good', keepsake='heartwood_seed', line='...Yes. ... Trees do that. ... In a hundred years. ... I will tell it you said so.', rel=dict(respect=6)),
        dict(id='yours', text='Name it after me.', result='mixed', keepsake='heartwood_seed', line='...After you. ... That is a short name for a tree. ... It will have to grow into it, and I will be here to watch.', rel=dict(affection=3))]))], complete='...Two of us now. ... The clearing feels different.'),
   'cut': dict(id='seed', title='A Seed of Its Own', requires=dict(milestone='trusted', trust=30), offer='Ask about the space beside it', stages=[
     dict(id='ask', talk='...You told me to cut the birches. ... They are stumps. ... I have thought about stumps. ... Bring me a heartwood seed. ... I want something to grow where they were.', journal='Bring Burl a heartwood seed, to grow where the cut birches were.', objective=dict(type='deliver', items=dict(heartwood_seed=1), label='the seed', done_text='...Planted. ... Where they were. ... Come back. ... Three days.')),
     dict(id='grow', talk='...Watch it with me.', journal='Visit Burl and the new seed on three different days.', objective=dict(type='visit_days', n=3, found='A green thread has come up where the birches were.')),
     dict(id='decide', talk='...It came up. ... Where the stumps are. ... Name it.', journal='Help Burl name the new tree.', objective=dict(type='choice', options=[
        dict(id='birch', text='Name it for the birches.', result='good', keepsake='heartwood_seed', line='...For the birches. ... Yes. ... That is right. ... I forgive you a little.', rel=dict(trust=6, respect=4)),
        dict(id='let', text='Let it name itself.', result='mixed', keepsake='heartwood_seed', line='...It will grow up beside the stumps. ... It will have opinions, and I will listen to every one.', rel=dict(respect=2))]))], complete='...Something grows where the birches were.')})

C['tessel'].update(milestone_lines=dict(familiar='Observation: I now predict your arrival times with 74 percent accuracy. This is the closest thing I have to saying I like it when you come.', trusted='Disclosure: I have a record zero. I have never shown it to anyone. I may show it to you. Not yet. Soon. That is a promise. I have started making those.', close='Social routines now at 61 percent. You are responsible for 30 of those percent.', kindred='I have moved you into protected memory. You cannot be erased now. I did not ask permission. I am told that is what friends do.'),
  activities=[dict(id='found', kind='found', milestone='trusted', every=3, label='Ask what it salvaged today', items=['bolt', 'wire', 'scrap_metal', 'glass_shard', 'hinge'], line='Salvage report: one {item}. Assigning to you. Reason: you will use it. Second reason: I wanted to.'),
              dict(id='walk', kind='walk', milestone='close', label='Come and survey with me', line='Survey mode with company. New mode. Recording.', stop='That is enough surveying for now.', stop_line='Survey complete. Distance logged. Company logged separately.'),
              dict(id='forecast', kind='line', pool='forecast', milestone='familiar', when=dict(ch1='weather'), every=1, label='Ask for the forecast', line='Forecast unavailable.')],
  pools=dict(forecast=[L('t_fc1', 'Forecast from the beacon: today {weather}. Confidence: high. I broadcast it at dawn. You are the only listener I have confirmed.')],
             festival=[L('t_fest_aw', 'Petal count: 11,402. Margin of error: large. I keep losing count because I keep looking up.', when=dict(festival='fest_awakening')), L('t_fest_fg', 'Catalogue of forgotten things, item 31: a doll arm. Same as last year. I suspect it is the same doll arm. I suspect it wants to be found.', when=dict(festival='fest_forgotten')), L('t_fest_tide', 'Under the ice: 212 lit windows. Before the flood: 212 houses. I have checked my records three times.', when=dict(festival='fest_silent_tide'))]))
C['tessel']['recall'].append(L('t_r_fest', 'Log entry: you attended the {mem.detailText}. I logged you twice. Once as attendance. Once as something I do not have a category for.', mem=dict(type=['festival', 'saw_at_festival'], min_age=1), w=4))
C['tessel']['quest2'] = dict(variants={
  'call': dict(id='answered', title='What Answered', requires=dict(milestone='trusted'), offer='Ask about the beacon', stages=[
     dict(id='ask', talk="The beacon's call has been sent 41 times. Last night: an answer. Come to the arch at night. Observe with me.", journal="Watch the beacon with Tessel at the ruin arch, at night.", objective=dict(type='be_at', at='ruin_arch', radius=40, period=['night', 'deep'], found="The beacon blinks twice. Far out past the lake, something blinks back. Twice.")),
     dict(id='decide', talk='Something answered. Options: reply, or go silent. I would like a recommendation. I would also like to not be alone with this.', journal='Decide with Tessel whether to answer the light.', objective=dict(type='choice', options=[
        dict(id='reply', text='Reply. Tell it we are here.', result='mixed', world=dict(beacon_reply=True), line='Reply sent: "We are here." ... Response received: "So are we." ... I do not know if that is good. I am logging it as hope.', rel=dict(trust=4, shared=4)),
        dict(id='silence', text='Go silent. Some calls should not be answered.', result='good', line='Silencing the call. ... It is quieter. I think I prefer knowing someone was out there to knowing who.', rel=dict(respect=4)),
        dict(id='wick', text='Ask Wick first. It knows what lives in the dark.', needs_met='wick', result='good', line='Consulted Wick. Wick says the light out there is cold. I will not answer. I am glad you thought of asking. I would not have.', rel=dict(trust=5, respect=3))]))], complete='The beacon pings at dusk. Sometimes, far off, something pings back.'),
  'default': dict(id='measure', title='The Long Measure', requires=dict(milestone='trusted'), offer='Ask about the beacon', stages=[
     dict(id='ask', talk='Request: be at the pond with me on the night the ice goes clear. The Silent Tide. I want to measure the drowned town. I do not want to do it alone.', journal='Be with Tessel at the Silent Tide, deep in winter.', objective=dict(type='festival_with', festival='fest_silent_tide')),
     dict(id='decide', talk='The town is all there. Every house. What should I record?', journal='Help Tessel decide what to record of the drowned town.', objective=dict(type='choice', options=[
        dict(id='town', text='Measure the whole town, house by house.', result='good', line='Recording. 212 houses. 1 bell tower. 0 people. The last number is the one I will think about.', rel=dict(respect=4)),
        dict(id='lights', text='Just count the lights still burning.', result='good', line='Counting. 212. Every one. Somebody left every light on. I will record that they were expected home.', rel=dict(affection=5, shared=3)),
        dict(id='watch', text="Don't record anything. Just watch it with me.", result='good', line='Recording disabled. ... This is new. ... I am watching. ... I think I am doing it correctly.', rel=dict(shared=8, affection=4))]))], complete='Some measurements are kept in protected memory.')})

C['lull'].update(milestone_lines=dict(familiar='*It shows you a picture of yourself, sharp this time, not blurred.*', trusted='*It shows you a door, and a hand on the handle, and then it hands you the picture.* (It trusts you with what it has lost.)', close='*Now, when it is foggy, the fog comes to your tent first.*', kindred='*It shows you the drowned town, and you are in it, and you belong there.*'),
  activities=[dict(id='pics', kind='line', pool='pictures', milestone='familiar', every=1, label='Watch its pictures together', line='*It shows you pictures for a long time.*'),
              dict(id='walk', kind='walk', milestone='close', label='Drift along with me', line='*It folds in behind you, cool and soft.*', stop="That's far enough.", stop_line='*It drifts back toward the meadow, showing you a small wave.*')],
  pools=dict(pictures=[L('l_p1', '*A street with a bakery on the corner. Bread in the window. Somebody waving from inside.*', pics=['seeds_wild']), L('l_p2', '*Children on the dock, feet in the water, a wooden fish passed from hand to hand.*', pics=['photo']), L('l_p3', '*Snow falling on a town square, and a bell ringing, and everyone looking up at once.*', pics=['tin_cup'])],
             festival=[L('l_fest_tide', '*Under the ice: its pictures, all of them, real. It is shaking.* (This is where it came from.)', when=dict(festival='fest_silent_tide'))]))
C['lull']['recall'].append(L('l_r_fest', '*It shows you the {mem.detailText}, and you in it, small and bright.*', mem=dict(type=['festival', 'saw_at_festival'], min_age=1), w=4))
C['lull']['quest2'] = dict(id='lastafternoon', title='The Last Afternoon', requires=dict(milestone='close'), offer='*It shows you the frozen pond*', stages=[
     dict(id='ask', talk='*It shows you the pond frozen clear, and the town below, and itself drifting down toward it.* (On the Silent Tide, come with it to the ice.)', journal='Be with Lull at the Silent Tide.', objective=dict(type='festival_with', festival='fest_silent_tide')),
     dict(id='decide', talk='*Under the ice, its town. It hovers over the hole, looking down, looking at you.* (Should it go back down?)', journal='Lull is deciding whether to go back to the drowned town.', objective=dict(type='choice', options=[
        dict(id='go', text='Go home. They kept the lights on for you.', result='bad', gone=True, line='*It folds once around you, cool and soft, and then it is a thin white thread going down through the hole into the lit town. The fog never comes to the meadow again.*', rel=dict(affection=6), complete='*Some winter nights, under the clear ice, one of the windows has a small fog in it.*'),
        dict(id='stay', text='Stay. You have a place here now.', result='good', line='*It rises from the hole and settles around your shoulders. Its pictures are the clearing now, and you, and the pond with nothing under it.*', rel=dict(affection=8, shared=6)),
        dict(id='visit', text='Stay, and come back here every winter to look.', result='good', line='*Every one of its eyes opens. It shows you the two of you on the ice, again and again, a year apart each time.*', rel=dict(shared=8, trust=4))]))], complete='*Every winter, on the Silent Tide, it is there first.*')


# ============================================================== Prompt 17: the narrative library (docs/narrative/*.md)
# Names, bible text and every authored exchange come from the three source files through tools/narrative.py; the conditions
# under which each exchange may play live in tools/narrative_map.py. Anything about a character that the files do not say
# (mechanics, routines, memory weights) stays defined above.
import narrative as NR, narrative_map as NM
SPECIES = dict(Nera='Pond-dweller', Pip='Forager', Sella='Moth-kin', Orun='Rootbound', Morrow='Maintenance machine', Luma='Dreamer')
COMM = dict(Nera='dry, exact, practical', Pip='quick, interrupted, concrete', Sella='gentle, plain, offering choices', Orun='unhurried, tactile, blunt', Morrow='literal, precise, learning contractions', Luma='soft, wandering, sensory')
# how many sentences of "History and secret" are history (the rest is the secret, shown only once it has been earned)
HISTORY_SENTENCES = dict(Nera=3, Pip=2, Sella=3, Orun=2, Morrow=None, Luma=2)
INTERESTS = dict(
  Nera=([('jars', 'Clean jars, rain charts and warm tea'), ('stones', 'Smooth river stones'), ('stored', 'Foods that can be stored'), ('sound', 'Mapping water by sound')], [('waste', 'Waste'), ('perfume', 'Strong perfume'), ('mother', 'Being called "the pond\'s mother"')]),
  Pip=([('berries', 'Berries, seed pods and anything that rattles'), ('buttons', 'Interesting buttons'), ('riddles', 'Riddles with fair answers'), ('names', 'Naming bugs, then changing the names')], [('mushy', 'Mushy roots'), ('shushed', 'Being shushed'), ('wrapped', "Gifts wrapped so carefully they can't tell what they are")]),
  Sella=([('wax', 'Beeswax, dry cloth and wind chimes'), ('repairs', 'Careful repairs'), ('path', 'Sitting where she can see the path'), ('flames', 'The sounds different flames make')], [('debt', 'Being thanked as if kindness were a debt'), ('flash', 'Sudden bright flashes'), ('fine', 'People who insist they are "fine" while bleeding')]),
  Orun=([('mold', 'Leaf mold and a good rain'), ('stories', 'Stories with unimportant endings'), ('birds', 'Bird visits'), ('moss', 'A list of places where moss grows on stone')], [('axes', 'Axes waved as punctuation'), ('wise', 'Being called "wise"'), ('wind', 'Hot dry wind')]),
  Morrow=([('gears', 'Clean gears and patterned cloth'), ('maps', 'Accurate maps'), ('rhythms', 'Soft tapping rhythms'), ('birds', 'Bird calls, with confidence levels')], [('water', 'Sudden water immersion'), ('test', 'Being called a person as a test'), ('help', '"Help" that removes its choice')]),
  Luma=([('stones', 'Warm stones, pears and low lamps'), ('rain', 'Soft rain'), ('naps', 'Ranking naps by how surprised they are to wake'), ('stories', 'Stories that end before bedtime')], [('bells', 'Sharp bells'), ('woken', 'Being woken abruptly'), ('clue', 'Having every dream treated as a clue')]))
GIFTS = dict(  # real item ids only; what the bible says each one likes and does not
  ebb=dict(loves=['glass_pane', 'glass_shard', 'spore_jar'], likes=['stone', 'quartz', 'mint', 'moss'], dislikes=['rot_fiber']),
  pip=dict(loves=['blackberry', 'rowan_berry', 'eggshell', 'seeds_wild'], likes=['mushroom_brown', 'feather', 'bellflower', 'daisy', 'glass_shard'], dislikes=['burdock_root', 'emberroot']),
  wick=dict(loves=['hinge', 'cloth', 'nightlily', 'bellflower'], likes=['nails', 'hook_iron', 'daisy', 'poppy', 'quartz', 'amethyst'], dislikes=[]),
  burl=dict(loves=['rot_fiber', 'moss'], likes=['cloth', 'fern_frond', 'mushroom_brown'], dislikes=['log', 'plank', 'hardwood']),
  tessel=dict(loves=['bolt', 'nails', 'hinge', 'cloth'], likes=['rusted_gear', 'circuit', 'wire', 'battery', 'scrap_metal'], dislikes=['mud', 'moss']),
  lull=dict(loves=['stone', 'cloth', 'moonstone'], likes=['rowan_berry', 'blackberry', 'moss', 'moondew'], dislikes=['scrap_metal']))
def _sentences(t): return re.split(r'(?<=[.?!])\s+(?=[A-Z"])', t.strip())
def attach_narrative():
    data = NR.build(); report = dict(unconnected=[], connected=0, by_pool={})
    for name, nc in data['characters'].items():
        cid = nc['id']; c = C[cid]; b = nc['bible']
        c.update(name=name, epithet=nc['title'], species=SPECIES[name], communication=COMM[name], description=b['Role and core'], appearance=b['Appearance and mannerisms'], voice=b['Voice'])
        c.pop('gesture', None); c.pop('pictures', None)
        c['notice'] = [L(i, t, when=w) for i, t, w in NM.NOTICE[cid]]
        hs = _sentences(b['History and secret']); k = HISTORY_SENTENCES[name]
        if k is None: c['background'], c['secret'] = hs[1], ' '.join([hs[0]] + hs[2:])        # Morrow: the Root Rooms mark is a discovery, so it stays with the secret
        else: c['background'], c['secret'] = ' '.join(hs[:k]), ' '.join(hs[k:])
        c['interests'], c['dislikes'] = INTERESTS[name]; c['gifts'] = GIFTS[cid]; c['greet'] = []; c['story'] = {k2: b[k2] for k2 in ('Wants, fears, contradictions', 'Relationships', 'Player relationship', 'Story arc')}
        ex = []; rules = NM.RULES[cid]
        for e in nc['exchanges']:
            r = rules.get(e['n']); assert r is not None, (cid, e['n'])
            pool = r.get('p') or ('topic' if e['first'] == 'player' else 'talk')
            if pool == 'none': report['unconnected'].append(dict(id=e['id'], name=name, tag=e['tag'], why=r.get('note'))); continue
            rec = dict(id=e['id'], n=e['n'], p=pool, tag=e['tag'], turns=[['p' if t['who'] == 'player' else 'n', t['text']] for t in e['turns']], w=r['w'], req=r['req'], once=r['once'], weight=r['weight'])
            for k2 in ('items', 'label', 'sets'):
                if r.get(k2): rec[k2] = r[k2]
            ex.append(rec); report['connected'] += 1; report['by_pool'][pool] = report['by_pool'].get(pool, 0) + 1
        c['ex'] = ex
    for cid, adds in NM.SCHEDULE_ADD.items(): C[cid]['schedule'] = adds + C[cid]['schedule']
    return data, report
DREAMS = {'lull.14'}      # Luma dreaming about the player is not a claim about the past
RENAME = {'Ebb': 'Nera', 'Wick': 'Sella', 'Burl': 'Orun', 'Tessel': 'Morrow', 'Lull': 'Luma'}
SKIP_KEYS = {'ex', 'story', 'voice', 'background', 'secret', 'description', 'appearance', 'interests', 'dislikes', 'communication', 'species', 'epithet', 'name'}
_SHE_VERBS = ('leads dims helps rests takes sets lifts hands holds keeps looks turns waits says nods stays walks lights goes moves smiles laughs listens watches puts gives shows stands sits reaches asks tells brings stops draws pulls picks steps opens closes touches thanks blinks flares raises lowers visits comes flies checks remembers makes points inspects knows does is has still lets sits leans dips tilts covers circles loves seems gutters shrinks carries pauses stays hesitates answers').split()
def _fix_she(t):
    """Sella is 'she' in the character bible; the older narration of this neighbour said 'it'. Only the neighbour's own actions change (verbs
    that a person does); pronouns for the door, the dark and the knocking stay as they were."""
    v = '|'.join(_SHE_VERBS)
    t = re.sub(r'(^|[*(\[]|[.!?;,] |\b(?:then|and|when|but|while|so) )It (?=(?:' + v + r')\b)', lambda m: m.group(1) + ('She ' if m.group(1) == '' or m.group(1)[-1] in '*([.!?;' or m.group(1).endswith('] ') else 'she '), t)
    t = re.sub(r'\b(then|and|when|but|while|so|,) it (?=(?:' + v + r')\b)', r'\1 she ', t)
    t = re.sub(r'\bIts\b', 'Her', t); t = re.sub(r'\bits\b', 'her', t); t = re.sub(r'\bitself\b', 'herself', t)
    t = t.replace('(It is quieter now.)', '(The door is quieter now.)').replace('She is quieter now', 'She is quieter now')
    t = t.replace('lays one wing over your shoulder', 'lays one wing over your shoulder').replace('(It remembers that you protected it.)', '(She remembers that you protected her.)').replace('(It remembers you were there.)', '(She remembers you were there.)')
    t = t.replace('You remembered what it loves.', 'You remembered what she loves.').replace('(You remembered what it loves.)', '(You remembered what she loves.)')
    for a, b in [('. she ', '. She '), ('? she ', '? She '), ('! she ', '! She '), ('(It ', '(She '), ('*It ', '*She '), ('. It ', '. She '), ('Then it ', 'Then she '), ('Every night now it ', 'Every night now she '), ('one it visits', 'one she visits'),
                 ('From now on it visits', 'From now on she visits'), ('what it hides', 'what she hides'), ('you protected it.)', 'you protected her.)'), ('you gave it this way', 'you gave her this way')]: t = t.replace(a, b)
    return t
def reconcile_names():
    """The older hand-written storylines used the first-draft names; the library's names win everywhere the player can read them."""
    def fix(o, cid):
        if isinstance(o, str):
            for a, b in RENAME.items(): o = re.sub(r'\b' + a + r'\b', b, o)
            return _fix_she(o) if cid == 'wick' else o
        if isinstance(o, dict): return {k: (v if k in SKIP_KEYS else fix(v, cid)) for k, v in o.items()}
        if isinstance(o, (list, tuple)): return type(o)(fix(v, cid) for v in o)
        return o
    for cid in list(C): 
        for k in list(C[cid]):
            if k not in SKIP_KEYS: C[cid][k] = fix(C[cid][k], cid)
def lint_exchanges():
    """An authored exchange may only claim a past if it is bound to something that really happened (a requirement, or the player's own ask)."""
    past = re.compile(r"\byou (remembered|said|asked|usually|told|took|brought)\b|\byour shell\b|the way you like it|the path you asked about", re.I)
    bad = []
    for c in C.values():
        for e in c.get('ex', []):
            txt = ' '.join(t[1] for t in e['turns'] if t[0] == 'n')
            if past.search(txt) and not (e['req'] or 'low_visits' in e['w'] or 'talk_days' in e['w'] or (e['p'] == 'topic' and e.get('label')) or e['id'] in DREAMS): bad.append(e['id'])
    assert not bad, ('authored lines claiming a past with no binding condition', bad)

def lint():
    """No line may claim a past that is not bound to a stored memory."""
    bad = []
    past = re.compile(r"\b(remember|last time|you told|you said|you gave|you showed|you brought|you caught|you cut|you came|you advised)\b", re.I)
    for c in C.values():
        for cat in ('greet', 'chat'):
            for l in c[cat]:
                if past.search(l['text']) and not l.get('mem'): bad.append((c['id'], l['id']))
        for l in c['recall']:
            if not l.get('mem'): bad.append((c['id'], l['id'], 'recall without memory'))
    assert not bad, bad
def build():
    lint()
    data, report = attach_narrative(); reconcile_names(); lint_exchanges()
    out = dict(version=1, milestones=MILESTONES, dims=DIMS, anchors=ANCHORS, water=WATER, memory_kinds={k: dict(sig=v[0], sign=v[1]) for k, v in MEMORY.items()}, moods=MOODS,
               tiers=[[0, 'stranger'], [8, 'acquainted'], [20, 'friendly'], [38, 'close'], [60, 'kindred']], characters=C)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out['cross'] = [dict(n=x['n'], title=x['title'], turns=[[x2['speaker'], x2['text']] for x2 in x['turns']], **NM.CROSS[x['n']]) for x in data['cross']]; out['choices'] = {NR.CHAR_IDS[k]: v for k, v in data['choices'].items()}
    wd = data['world']; notes = []
    for i, wn in enumerate(NM.WORLD_NOTES):
        src = wd['folklore' if wn['kind'] == 'folklore' else 'places']; hit = [x for x in src if x['title'] == wn['title']]; assert hit, wn['title']
        allowed = set(e['id'] for c in C.values() for e in c['ex'])
        for ex in wn.get('src', []): assert ex in allowed, ('world note needs a connected exchange', wn['title'], ex)
        notes.append(dict(id=f"{wn['kind']}_{i}", **{k: v for k, v in wn.items()}, text=hit[0]['paragraphs']))
    out['world_notes'] = notes
    json.dump(out, open(os.path.join(root, 'assets/social/cast.json'), 'w'), indent=0, ensure_ascii=False)
    json.dump(report, open(os.path.join(root, 'assets/social/narrative_report.json'), 'w'), indent=1, ensure_ascii=False)
    n = sum(len(c['chat']) + len(c['recall']) + len(c['asleep']) + len(c['ex']) for c in C.values()); print(len(C), 'characters,', n, 'authored lines;', report['connected'], 'library exchanges connected,', len(report['unconnected']), 'waiting on a game feature')
if __name__ == '__main__': build()
