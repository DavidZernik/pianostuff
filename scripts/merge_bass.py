"""Fold the transcribed bass line into the left hand of player/notes.json.

Playing this alone there is no bassist, so the left hand has to cover the bass.
The transcribed left hand does not: it is only the Keyboard stem below middle C,
and its lowest note is the chord root barely half the time.

Bass notes are tagged "b":1 so the player can switch them off, and are marked
h:"l" so they get left-hand fingering and colour. Exact duplicates of a keyboard
note already at that pitch and slot are dropped.

    ./venv/bin/python scripts/extract_bass.py && ./venv/bin/python scripts/merge_bass.py
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES = os.path.join(ROOT, 'player/notes.json')
BASS = os.path.join(ROOT, 'scores/bass.json')

d = json.load(open(NOTES))
d['notes'] = [n for n in d['notes'] if not n.get('b')]        # idempotent
have = {(n['p'], round(n['t'], 4)) for n in d['notes'] if n['h'] == 'l'}

added = 0
for p, t, dur in json.load(open(BASS)):
    if (p, round(t, 4)) in have: continue
    d['notes'].append({'p': p, 't': t, 'd': dur, 'h': 'l', 'v': 88, 's': 90, 'b': 1})
    added += 1

d['notes'].sort(key=lambda n: (n['t'], n['p']))
d['range'] = [min(n['p'] for n in d['notes']), max(n['p'] for n in d['notes'])]
json.dump(d, open(NOTES, 'w'), separators=(',', ':'))

lh = [n for n in d['notes'] if n['h'] == 'l']
print(f"added {added} bass notes; left hand now {len(lh)}, range {min(n['p'] for n in lh)}-{max(n['p'] for n in lh)}")
print(f"total {len(d['notes'])}, overall range {d['range']}")
