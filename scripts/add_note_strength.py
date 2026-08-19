"""Measure how strongly each transcribed note actually sounds in the keyboard stem.

The transcription folds several layered Suno keyboard tracks into one part, so a
single attack can span two octaves. Deciding which notes to keep needs to know
which ones are actually audible, and MIDI velocity from the transcriber does not
tell you that. This measures it from the recording: peak CQT energy at the note's
own pitch just after its attack, as a share of the loudest bin in the same frames.

Writes an `s` field (0-100) onto every note in player/notes.json.

    ./venv/bin/python scripts/add_note_strength.py
"""
import json, os, subprocess, sys, tempfile
import numpy as np, librosa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEM = os.path.join(ROOT, 'audio/stems/4 Keyboard.mp3')
NOTES = os.path.join(ROOT, 'player/notes.json')
DUR = 277.45          # true length; the stem headers lie (see README)
SR, HOP = 22050, 256
FPS = SR / HOP

if not os.path.exists(STEM):
    sys.exit(f"missing {STEM} — audio/ is gitignored, restore the stems first")

wav = os.path.join(tempfile.mkdtemp(), 'keyboard.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', STEM, '-vn', '-ac', '1',
                '-ar', str(SR), '-t', str(DUR), wav], check=True)

y, sr = librosa.load(wav, sr=SR)
C = np.abs(librosa.cqt(y, sr=sr, hop_length=HOP, fmin=librosa.midi_to_hz(24),
                       n_bins=84, bins_per_octave=12))

d = json.load(open(NOTES))
scored = 0
for n in d['notes']:
    b = n['p'] - 24
    f0 = int(max(0, (n['t'] + 0.02) * FPS))
    f1 = int(min(C.shape[1], (n['t'] + 0.14) * FPS))
    if not (0 <= b < 84) or f1 <= f0:
        n['s'] = 50                       # out of range: stay neutral, never bias a decision
        continue
    w = C[:, f0:f1]
    n['s'] = int(round(100 * min(1.0, float(w[b].max() / max(w.max(), 1e-9)))))
    scored += 1

json.dump(d, open(NOTES, 'w'), separators=(',', ':'))
ss = [n['s'] for n in d['notes']]
print(f"scored {scored}/{len(d['notes'])} notes")
print(f"  median {int(np.median(ss))}  inaudible (<6): {sum(1 for s in ss if s < 6)}")
