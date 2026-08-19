"""Spread collapsed runs back out in time, and drop exact duplicates.

The transcriber sometimes hears a fast run as a single stacked attack: bar 44
holds G4 A4 Bb4 B4 C5 C#5 all at one sixteenth, six chromatic notes no hand plays
at once. The pitches are right; only the timing was lost, so this is a re-timing
job and not something filtering can fix.

A cluster is 3+ notes packed into roughly a semitone each. Its notes are spread
evenly across the sixteenth they share, ordered by where the line is going —
ascending if the surrounding contour rises, descending if it falls.

Eight clusters in the song, 28 notes, three of them in bar 44.

Also removes notes duplicated at the same pitch, time and hand — nine of them,
left behind when quantisation lands two strikes of one pitch in the same slot.
They are inaudible but they show as a doubled block and inflate the chord.

    ./venv/bin/python scripts/unstack_runs.py
"""
import json, os, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES = os.path.join(ROOT, 'player/notes.json')

d = json.load(open(NOTES))
SX = d['bar'] / 16
rh = sorted([n for n in d['notes'] if n['h'] == 'r'], key=lambda n: n['t'])

groups = collections.defaultdict(list)
for n in rh:
    groups[round(n['t'] / SX)].append(n)
keys = sorted(groups)
centre = {k: sum(x['p'] for x in v) / len(v) for k, v in groups.items()}

def packed(s):
    if len(s) < 3: return False
    ps = sorted(x['p'] for x in s)
    return (ps[-1] - ps[0]) <= len(ps) + 2

moved = 0
for i, k in enumerate(keys):
    s = groups[k]
    if not packed(s): continue
    prev = centre[keys[i-1]] if i else centre[k]
    nxt = centre[keys[i+1]] if i + 1 < len(keys) else centre[k]
    falling = nxt < prev
    order = sorted(s, key=lambda n: -n['p'] if falling else n['p'])
    step = SX / len(order)
    for j, n in enumerate(order):
        n['t'] = round(k * SX + j * step, 4)
        n['d'] = round(step, 4)
    moved += len(order)

# one strike per pitch per slot; keep the loudest, and the longest of those
best = {}
for n in d['notes']:
    k = (n['p'], round(n['t'], 4), n['h'])
    if k not in best or (n['s'], n['d']) > (best[k]['s'], best[k]['d']): best[k] = n
dropped = len(d['notes']) - len(best)
d['notes'] = sorted(best.values(), key=lambda n: (n['t'], n['p']))

json.dump(d, open(NOTES, 'w'), separators=(',', ':'))
print(f"spread {moved} notes out of {len(rh)} right-hand notes; dropped {dropped} duplicates")
