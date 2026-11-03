# Social simulation (Prompt 13)

Six intelligent, non-human, non-hostile inhabitants. Data in `tools/social_data.py` (written to `assets/social/cast.json`), engine in `preview/social.js`, art in `tools/pixelart/folk.py`, tests in `tests/social_tests.js`.

## What is data and what is engine
A character is only data: identity, traits, relationship weights, memory weights, schedule, climate moods, gift preferences, authored lines with conditions, questions it asks, facts it shares, one concern for advice, one storyline. The engine names no character. Adding a seventh means adding one `char(...)` block plus sprites.

## Memory
Each character holds its own list of records (`id, kind, category, day, time, significance, sign, key/value, tags, item, detail, ref`). Kinds have default significance; characters weight them (Burl weights cut trees, Tessel weights promises). Repeat visits consolidate into one record with a count. Each list is capped at 40; the lowest-salience records are dropped first, never quest, promise, protection or lie records.

## Recall
A line that refers to the past must bind a memory (`mem`). `tools/social_data.py` refuses to build if any non-recall line uses past-tense claims without one. At runtime the line is only eligible when a matching memory exists, and its details come from that record. Every spoken line is logged with the memory it used; `Social.audit()` checks each one existed and predates the line.

## Choosing what to say
Candidate lines are filtered by conditions (time, season, weather, mood, place, activity, relationship tier or dimension, absence, recent events), scored by weight, specificity and memory binding, and broken by a seeded hash, so the same situation gives the same answer and nothing repeats within six lines.

## Advice
A concern offers stances (encourage, reassure, compromise, practical) plus "ask first". The reaction comes from the character's traits, what it already leans toward or resists, its mood, trust, and how your last advice turned out. It may accept, consider or reject. Days later it reports what happened, which may be its own choice instead of yours.

## Relationship, mood, promises
Six dimensions: trust, familiarity, affection, respect, reliability, shared. Each change is logged with a reason, which the journal shows. Familiarity from talking is capped per day; extra gifts in one day count for a quarter. Moods have a cause, come from events or conditions, and fade by the hour. Promises have a due time and a real check (be somewhere, give something, set a light, visit on several days). A kept or broken promise becomes a memory and changes reliability.

## Optional language-model voice (prepared, not used)
`Social.setProvider({ compose(charId, pool, context) })` may replace the authored chooser. Whatever it proposes goes through `Social.validate`: it must cite a memory that exists, belongs to this character and is older than the line, or it is thrown away and the authored line is used. `Social.factsFor(charId)` gives the facts a model would be allowed to use. Nothing in the game requires a network connection, and the tests refuse any outside request.
