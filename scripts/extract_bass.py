"""Transcribe the bass line, so the left hand can cover it.

There is no bassist when you play this alone, and the transcribed left hand does
not cover the part: it is only the Keyboard stem's notes below middle C. The Bass
stem is louder than the Keyboard (-24.3 dB against -28.5) and sits at Bb1 to F2 —
the register the left hand has to take over.

pyin was tried first and is not reliable here. Its voiced_prob runs so low on a
synth bass that only 11% of frames clear 0.5, and the notes it does return
disagree with the recording: they landed on the chord root only 25% of the time
at the bar line, where a direct spectral reading of the same stem gets 66%.

So this reads the CQT per sixteenth instead. For each slot it takes the strongest
bin in the bass register, then checks an octave below — a synth bass has a strong
second harmonic, and picking it would notate the whole line an octave high.

Writes scores/bass.json as [midi, grid_time, duration], in the same grid time as
player/notes.json.

    ./venv/bin/python scripts/extract_bass.py
"""
import json, os, subprocess, tempfile
import numpy as np, librosa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEM = os.path.join(ROOT, 'audio/stems/3 Bass.mp3')
OUT = os.path.join(ROOT, 'scores/bass.json')
DUR, SR, HOP = 277.45, 22050, 256
BPM, DOWN = 101.26, -0.0576
SX = 60 / BPM / 4
LO, HI = 24, 50                      # C1 to D3: where this bass actually lives

wav = os.path.join(tempfile.mkdtemp(), 'bass.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', STEM, '-vn', '-ac', '1',
                '-ar', str(SR), '-t', str(DUR), wav], check=True)
y, sr = librosa.load(wav, sr=SR)
C = np.abs(librosa.cqt(y, sr=sr, hop_length=HOP, fmin=librosa.midi_to_hz(LO),
                       n_bins=HI - LO + 1, bins_per_octave=12))
FPS = sr / HOP
floor = np.percentile(C.sum(axis=0), 45)      # below this the bass is not playing

slots = {}
for k in range(int(DUR / SX)):
    f0 = int((k * SX + DOWN) * FPS)
    f1 = int(((k + 1) * SX + DOWN) * FPS)
    if f0 < 0 or f1 > C.shape[1] or f1 <= f0: continue
    w = C[:, f0:f1]
    if w.sum(axis=0).max() < floor: continue
    e = w.max(axis=1)
    b = int(np.argmax(e))
    # a synth bass has a loud second harmonic; if the octave below carries real
    # weight, that is the fundamental and the peak is its overtone
    if b - 12 >= 0 and e[b - 12] > e[b] * 0.30: b -= 12
    # this bass lives at F1 to C3; anything under E1 is the correction overshooting
    # into rumble, so put it back
    if LO + b < 28: b += 12
    slots[k] = LO + b

# merge repeated pitches into held notes
out, ks = [], sorted(slots)
i = 0
while i < len(ks):
    j = i
    while j + 1 < len(ks) and ks[j + 1] == ks[j] + 1 and slots[ks[j + 1]] == slots[ks[i]]:
        j += 1
    out.append([slots[ks[i]], round(ks[i] * SX, 4), round((ks[j] - ks[i] + 1) * SX, 4)])
    i = j + 1

json.dump(out, open(OUT, 'w'))
ps = [p for p, t, d in out]
print(f"{len(out)} bass notes, midi {min(ps)}-{max(ps)}, median {int(np.median(ps))}")
print(f"sounding {sum(d for p,t,d in out):.0f}s of {DUR:.0f}s")
