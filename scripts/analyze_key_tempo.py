import numpy as np, librosa, json, sys

y, sr = librosa.load(sys.argv[1], sr=22050, mono=True)
tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
tempo = float(np.atleast_1d(tempo)[0])

# --- key estimate: Krumhansl-Schmuckler on mean chroma ---
chroma = librosa.feature.chroma_cqt(y=y, sr=sr, bins_per_octave=36)
mean_c = chroma.mean(axis=1)
MAJ = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
MIN = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
scores = []
for i in range(12):
    scores.append((np.corrcoef(np.roll(MAJ,i), mean_c)[0,1], f"{NAMES[i]} major"))
    scores.append((np.corrcoef(np.roll(MIN,i), mean_c)[0,1], f"{NAMES[i]} minor"))
scores.sort(reverse=True)

# --- beat-synchronous chord estimate vs maj/min/7 templates ---
cs = librosa.util.sync(chroma, beats, aggregate=np.median)
tmpl, lbl = [], []
for i in range(12):
    for iv, suf in [((0,4,7),''), ((0,3,7),'m'), ((0,4,7,10),'7'), ((0,3,7,10),'m7')]:
        v = np.zeros(12)
        for n in iv: v[(i+n)%12] = 1
        tmpl.append(v/np.linalg.norm(v)); lbl.append(NAMES[i]+suf)
tmpl = np.array(tmpl)
norm = cs / (np.linalg.norm(cs, axis=0, keepdims=True)+1e-9)
chords = [lbl[j] for j in (tmpl @ norm).argmax(axis=0)]
times = librosa.frames_to_time(beats, sr=sr)

# collapse repeats
seq = []
for t, c in zip(times, chords):
    if not seq or seq[-1][1] != c: seq.append([round(float(t),2), c])

print(json.dumps({"tempo": round(tempo,1), "key_top3": [[round(s,3),k] for s,k in scores[:3]],
                  "n_beats": len(beats), "chord_changes": len(seq), "sequence": seq}, indent=1))
