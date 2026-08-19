"""Give every lyric word a timestamp, by aligning Whisper against the real lyrics.

Whisper is run on the isolated lead vocal — no instruments in the way — with word
timestamps on. It will mishear parts of this song badly; it has "Kha boo ruh" and
"dahf ha shah voo ah" in it. That does not matter, because we already know the
words. Only Whisper's *timings* are kept, transferred onto the true text by
sequence-matching what it heard against what is actually there.

Words it never matched are spaced evenly between their nearest matched
neighbours. Mid-phrase that is fine; what has to be right is where each line
starts, and a line almost always contains at least one word Whisper got.

Writes scores/lyrics.json: one entry per sung line, with per-word times, in the
player's grid time (audio time minus the downbeat).

    ./venv/bin/python scripts/align_lyrics.py [model]
"""
import json, os, re, subprocess, sys, tempfile
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STEM = os.path.join(ROOT, 'audio/stems/0 Lead Vocals.mp3')
LYRICS = os.path.join(ROOT, 'One Page A Week - lyrics.txt')
OUT = os.path.join(ROOT, 'player/lyrics.json')
DUR, DOWN = 277.45, -0.0576
MODEL = sys.argv[1] if len(sys.argv) > 1 else 'small'

norm = lambda w: re.sub(r"[^a-z']", '', w.lower().replace('’', "'"))

# the true words, kept in lines so the display has something to show
lines, section = [], ''
for raw in open(LYRICS).read().splitlines():
    l = raw.strip()
    if not l: continue
    if l.startswith('[') and l.endswith(']'):
        section = l.strip('[]'); continue
    ws = re.findall(r"[A-Za-z'’]+", l)
    if ws: lines.append({'section': section, 'text': l, 'words': ws})
truth = [(li, wi, norm(w)) for li, L in enumerate(lines) for wi, w in enumerate(L['words'])]
print(f"{len(lines)} sung lines, {len(truth)} words")

wav = os.path.join(tempfile.mkdtemp(), 'vox.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', STEM, '-vn', '-ac', '1',
                '-ar', '16000', '-t', str(DUR), wav], check=True)

# transcription is the slow part, so cache it: alignment gets iterated on, the
# audio does not change
CACHE = os.path.join(ROOT, f'scores/.whisper-{MODEL}.json')
if os.path.exists(CACHE):
    heard = [tuple(x) for x in json.load(open(CACHE))]
    print(f"using cached {MODEL} transcription ({len(heard)} words)")
else:
    import whisper
    print(f"transcribing with the {MODEL} model...")
    res = whisper.load_model(MODEL).transcribe(wav, word_timestamps=True, language='en',
                                               condition_on_previous_text=False)
    heard = [(norm(w['word']), float(w['start']))
             for seg in res['segments'] for w in seg.get('words', []) if norm(w['word'])]
    json.dump(heard, open(CACHE, 'w'))
    print(f"whisper heard {len(heard)} words, first at {heard[0][1]:.2f}s")

# Transfer timings from what it heard onto what is actually sung. Only runs of two
# or more words are trusted as anchors: a lone "the" or "a" matching by chance
# anywhere in the song drags everything after it, and one bad anchor is worse than
# a hundred interpolated words.
times = [None] * len(truth)
sm = SequenceMatcher(None, [t[2] for t in truth], [h[0] for h in heard], autojunk=False)
anchors = [(a, b, n) for a, b, n in sm.get_matching_blocks() if n >= 2]
matched = 0
last = -1.0
for a, b, n in anchors:
    if heard[b][1] < last: continue          # never let an anchor go backwards
    for k in range(n):
        times[a + k] = heard[b + k][1]; matched += 1
    last = heard[b + n - 1][1]
print(f"anchored {matched}/{len(truth)} words ({100*matched/len(truth):.0f}%) "
      f"in {len(anchors)} runs")

# fill the gaps by spreading evenly between the nearest known times
known = [i for i, t in enumerate(times) if t is not None]
if not known: sys.exit("nothing matched — is this the right vocal stem?")
# The lead vocal stem makes sound from 4.6s, but that is a wordless hum over the
# intro — Whisper transcribes all 23 seconds of it as four "hmm"s, the syllable
# rate is half the sung sections, and the first verse lands at bar 13, which is
# exactly where the bass enters. So do not stretch the first line back to the
# start of the stem. Words outside the anchors are spaced at the song's own
# median word gap.
gaps = [times[b] - times[a] for a, b in zip(known, known[1:]) if b == a + 1]
STEP = sorted(gaps)[len(gaps)//2] if gaps else 0.35
for i in range(len(times)):
    if times[i] is not None: continue
    prev = max((k for k in known if k < i), default=None)
    nxt = min((k for k in known if k > i), default=None)
    if prev is None: times[i] = max(0.0, times[nxt] - STEP * (nxt - i))
    elif nxt is None: times[i] = times[prev] + STEP * (i - prev)
    else:
        f = (i - prev) / (nxt - prev)
        times[i] = times[prev] + f * (times[nxt] - times[prev])

# never let a word go backwards
for i in range(1, len(times)):
    times[i] = max(times[i], times[i-1] + 0.02)

out = []
for li, L in enumerate(lines):
    ws = [{'w': w, 't': round(times[i] - DOWN, 3)}
          for i, (l2, wi, _) in enumerate(truth) if l2 == li
          for w in [L['words'][wi]]]
    out.append({'section': L['section'], 'text': L['text'],
                't': ws[0]['t'], 'end': ws[-1]['t'] + 0.6, 'words': ws})
for a, b in zip(out, out[1:]):
    a['end'] = min(a['end'], b['t'])

json.dump(out, open(OUT, 'w'))
print(f"wrote {len(out)} lines, first at {out[0]['t']:.2f}s, last at {out[-1]['t']:.2f}s")
