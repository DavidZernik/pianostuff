#!/usr/bin/env python3
"""Emit player/embellish.json — the composed licks, timed for the player.

Same notes as the embellished score, converted from bar-and-sixteenth into seconds
so the player can schedule them. Kept in its own file rather than merged into
notes.json: notes.json is transcription output and gets rebuilt, and composed
material has no business surviving inside it.
"""
import json, os, sys
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE,'scripts'))
from licks import LICKS

meta = json.load(open(os.path.join(HERE,'player','notes.json')))
BAR, DOWN = meta['bar'], meta['downbeat']

out = []
for b in sorted(LICKS):
    for pos, pitch, dur in LICKS[b]:
        t = DOWN + (b-1)*BAR + (pos/16.0)*BAR
        d = (dur/16.0)*BAR
        for p in (pitch if isinstance(pitch,list) else [pitch]):
            out.append({'p':p, 't':round(t,4), 'd':round(d,4), 'h':'r',
                        'v':84, 's':100, 'x':1})     # x marks it as composed
out.sort(key=lambda n:(n['t'], n['p']))

doc = {'note':'Composed right-hand licks — NOT transcription. Source: scripts/licks.py, '
               'rebuild with scripts/build_embellish.py.',
       'bars': sorted(LICKS), 'notes': out}
p = os.path.join(HERE,'player','embellish.json')
json.dump(doc, open(p,'w'), indent=1)
print('wrote player/embellish.json —', len(out), 'notes across bars', min(LICKS), 'to', max(LICKS))
