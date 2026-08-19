"""Pull the sung melody out of the lead vocal stem, as notes.

Writes scores/melody.json — a list of [midi, start, end] in seconds. Committed so
the scores can be rebuilt without the audio, which is gitignored.

Octave errors are fixed by melodic continuity, not by spectra. A spectral
fundamental-vs-octave energy test flagged 14% of notes and was wrong in both
directions; comparing each note to the median of its neighbours and shifting by
an octave only when that moves it closer is both gentler and more accurate.

    ./venv/bin/python scripts/extract_melody.py
"""
import json, os, subprocess, tempfile
import numpy as np, librosa

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEM = os.path.join(ROOT, 'audio/stems/0 Lead Vocals.mp3')
OUT = os.path.join(ROOT, 'scores/melody.json')
DUR, SR, HOP = 277.45, 22050, 256

wav = os.path.join(tempfile.mkdtemp(), 'vox.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', STEM, '-vn', '-ac', '1',
                '-ar', str(SR), '-t', str(DUR), wav], check=True)
y, sr = librosa.load(wav, sr=SR)

f0, voiced, prob = librosa.pyin(y, sr=sr, hop_length=HOP,
                                fmin=librosa.note_to_hz('C2'),
                                fmax=librosa.note_to_hz('C6'), fill_na=np.nan)
times = librosa.times_like(f0, sr=sr, hop_length=HOP)
midi = librosa.hz_to_midi(f0)
rms = librosa.feature.rms(y=y, hop_length=HOP)[0][:len(midi)]
gate = rms > rms.max() * 0.02
ok = voiced & (prob > 0.5) & np.isfinite(midi) & gate

# segment: break on a gap, or on a pitch move of more than ~0.7 semitones
notes, cur = [], []
for i in range(len(midi)):
    if not ok[i]:
        if len(cur) >= 4: notes.append(cur)
        cur = []
        continue
    if cur and abs(midi[i] - np.median([midi[j] for j in cur[-4:]])) > 0.7:
        if len(cur) >= 4: notes.append(cur)
        cur = []
    cur.append(i)
if len(cur) >= 4: notes.append(cur)

mel = [[float(np.median(midi[c])), float(times[c[0]]), float(times[c[-1]])] for c in notes]

# octave correction by melodic continuity
fixed = 0
for i, n in enumerate(mel):
    lo, hi = max(0, i - 3), min(len(mel), i + 4)
    ctx = [m[0] for j, m in enumerate(mel[lo:hi], lo) if j != i]
    if not ctx: continue
    med = np.median(ctx)
    best = min((abs(n[0] + d - med), d) for d in (-12, 0, 12))
    if best[1]:
        n[0] += best[1]; fixed += 1

out = [[int(round(p)), round(s, 4), round(e, 4)] for p, s, e in mel]
json.dump(out, open(OUT, 'w'))
ps = [p for p, s, e in out]
print(f"{len(out)} melody notes, midi {min(ps)}-{max(ps)}, octave-corrected {fixed}")
print(f"first note at {out[0][1]:.2f}s")
