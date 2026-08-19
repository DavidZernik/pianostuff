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

# A note starts where there is an attack. The first version instead emitted a note
# for every sixteenth-slot whose bass energy cleared a floor, which chops a held
# note into a chain of re-strikes on sixteenths where nothing happens: of the 302
# such notes that landed without a right-hand note beside them, only 15% sat on a
# real attack, median attack strength -0.05 — below the average of the track. In
# the player that showed up as the left hand playing where the right hand was
# silent, which is what gave it away.
#
# So detect the attacks first, take the pitch at each one, and let a note sustain
# until the next attack rather than re-striking it every sixteenth.
onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
# delta chosen by sweep, not by eye: 0.15 through 0.02 all hold the same musical
# validity (48-51% of duration on the chord root), but 0.03-0.04 puts the notes on
# the strongest attacks. A bass attack is soft, so the usual 0.3 finds only 59 of
# them in the whole song.
attacks = librosa.onset.onset_detect(onset_envelope=onset, sr=sr, hop_length=HOP,
                                     units='time', backtrack=False,
                                     delta=0.04, wait=int(0.09 * FPS))
print(f"{len(attacks)} attacks in the bass stem")

def pitch_at(t):
    f0 = int(t * FPS); f1 = int((t + 0.13) * FPS)
    if f0 < 0 or f1 > C.shape[1] or f1 <= f0: return None
    w = C[:, f0:f1]
    if w.sum(axis=0).max() < floor: return None
    e = w.max(axis=1)
    b = int(np.argmax(e))
    # a synth bass has a loud second harmonic; if the octave below carries real
    # weight, that is the fundamental and the peak is its overtone
    if b - 12 >= 0 and e[b - 12] > e[b] * 0.30: b -= 12
    # this bass lives at F1 to C3; under E1 is the correction dropping into rumble
    if LO + b < 28: b += 12
    return LO + b

slots = {}
for t in attacks:
    p = pitch_at(t)
    if p is None: continue
    slots[int(round((t - DOWN) / SX))] = p

# each note holds until the next attack, capped at half a bar so a rest does not
# turn into a drone
ks = sorted(slots)
out = []
for i, k in enumerate(ks):
    nxt = ks[i + 1] if i + 1 < len(ks) else k + 2
    out.append([slots[k], round(k * SX, 4), round(min(nxt - k, 8) * SX, 4)])

json.dump(out, open(OUT, 'w'))
ps = [p for p, t, d in out]
print(f"{len(out)} bass notes, midi {min(ps)}-{max(ps)}, median {int(np.median(ps))}")
print(f"sounding {sum(d for p,t,d in out):.0f}s of {DUR:.0f}s")
