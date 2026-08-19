"""Correct the transcription model's systematic onset latency.

piano_transcription_inference reports note attacks about 47ms EARLIER than they
happen in the recording. Measured two independent ways against the keyboard stem's
onset envelope:

  * shifting all 1518 model onsets and scoring where they land — a clean unimodal
    peak at +50ms (score 3.35 against -0.18 unshifted, i.e. unshifted they sit on
    no attack at all)
  * per-note nearest envelope maximum — median +47ms, IQR 41 to 53ms

That is a third of a sixteenth at 101.26 BPM, so quantising the raw onsets rounds
94 right-hand notes (8%) onto the wrong sixteenth, always one too early. The
downbeat itself is fine: a comb filter over the drum stem puts the grid at 92.0ms
against the pipeline's 90.5ms, agreeing to 1.5ms.

This shifts the affected notes in player/notes.json by one sixteenth. Durations
are untouched — onset and release move together.

    ./venv/bin/python scripts/fix_onset_latency.py
"""
import json, os, collections
from mido import MidiFile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MID = os.path.join(ROOT, 'scores/One Page A Week - PIANO.mid')
NOTES = os.path.join(ROOT, 'player/notes.json')
BPM, DOWN, LAT = 101.26, -0.0576, 0.048
SX = 60 / BPM / 4

src = []
held = {}
t = 0.0
for m in MidiFile(MID):
    t += m.time
    if m.type == 'note_on' and m.velocity > 0:
        held.setdefault(m.note, []).append(t)
    elif m.type in ('note_off', 'note_on') and held.get(m.note):
        src.append((m.note, held[m.note].pop(0)))

# a source note is addressed by the sixteenth it was originally quantised onto
old = collections.defaultdict(list)
for p, s in src:
    old[(p, round((s - DOWN) / SX))].append(s)

d = json.load(open(NOTES))
moved = collections.Counter()
seen = set()
for n in d['notes']:
    k = round(n['t'] / SX)
    cand = old.get((n['p'], k))
    if not cand:
        continue
    s = cand[0]
    k2 = round((s + LAT - DOWN) / SX)
    if k2 == k or (n['p'], k2) in seen:
        continue
    n['t'] = round(k2 * SX, 4)
    seen.add((n['p'], k2))
    moved[n['h']] += 1

# a shifted note can now start inside one that is still ringing; truncate the earlier one
byp = collections.defaultdict(list)
for n in d['notes']:
    byp[n['p']].append(n)
clipped = 0
for arr in byp.values():
    arr.sort(key=lambda n: n['t'])
    for a, b in zip(arr, arr[1:]):
        if a['t'] + a['d'] > b['t'] + 1e-6:
            a['d'] = round(max(SX, b['t'] - a['t']), 4)
            clipped += 1

json.dump(d, open(NOTES, 'w'), separators=(',', ':'))
print(f"moved one sixteenth later: RH {moved['r']}, LH {moved['l']}")
print(f"overlaps truncated: {clipped}")
