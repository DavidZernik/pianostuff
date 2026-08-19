# pianostuff

Turning an AI-generated song into something you can actually sit down and play.

The source track — *One Page A Week* — was generated in Suno. There is no pianist and no
performance to transcribe from; the "piano" is layered generated audio. This repo holds the
pipeline that pulls a playable piano part out of it, plus a browser player for learning the licks.

## What's here

```
player/          browser player — falling notes over a keyboard, RH/LH colored, play-along overlay
scores/          MusicXML + MIDI (PDFs are gitignored — regenerate them)
scripts/         the build pipeline
audio/           gitignored: source mp3 and the 9 Suno stems
```

## Established facts about the track

These were each confirmed by multiple independent methods, and the tempo in particular
matters — getting it wrong destroys the notation.

| | |
|---|---|
| **Key** | B♭ major |
| **Tempo** | **101.26 BPM**, constant (no drift) |
| **Downbeat** | t = −0.058s |
| **Meter** | 4/4, 118 bars |
| **Progression** | I–ii–vi–V: B♭maj7, Cm7, Gm7, F7, with Dm7 and E♭maj7 as color |
| **Vocal entry** | 4.60s (bar 3) |
| **Instrumental sections** | bars 43–49 (1:40.7–1:52.6) and bars 86–89 |

**The Suno prompt says 105 BPM. It is not 105.** Onset-grid fitting puts 60.9% of note attacks
within 30ms of the grid at 101.26, versus 22% at both 103.4 and 105. A 3.7% tempo error
accumulates ~10 seconds of drift across the track, which renders the back half unreadable.

## Pipeline

```
Suno stems ──► ffmpeg re-encode to WAV  (REQUIRED — see gotchas)
                    │
       ┌────────────┼─────────────┬──────────────┐
   Keyboard       Bass          Lead Vocals    (all 9)
       │            │               │
  piano_transcription_inference   pyin + continuity octave fix
       │            │               │
       └──── chroma chord detection ┘
                    │
          scripts/build_scores.py
                    │
        ┌───────────┴───────────┐
   MusicXML ──► MuseScore ──► PDF      player/notes.json ──► browser player
```

## Gotchas that cost real time

**1. The Suno stem MP3s have corrupt duration headers.** Bass reports 688s, Drums 1306s,
Synth 858s — for a 277s song. Only Keyboard is correct. Any analysis reading them directly
gets garbage, and array shapes won't match. Always re-encode first:

```bash
for f in audio/stems/*.mp3; do
  ffmpeg -v error -y -i "$f" -vn -ac 1 -ar 22050 -t 277.45 "wav/$(basename "$f" .mp3).wav"
done
```

**2. `piano_transcription_inference` is broken two ways on modern setups.** Its `load_audio()`
calls `librosa.core.audio.util`, removed in librosa 0.11 — load the audio yourself with
`librosa.load(path, sr=sample_rate)` and pass the array. It also shells out to `wget`, which
macOS doesn't ship — fetch the checkpoint manually:

```bash
curl -L -o ~/piano_transcription_inference_data/'note_F1=0.9677_pedal_F1=0.9186.pth' \
  'https://zenodo.org/record/4034264/files/CRNN_note_F1%3D0.9677_pedal_F1%3D0.9186.pth?download=1'
```

**3. MuseScore CLI needs the cocoa Qt platform, not offscreen.** The macOS cask ships only
`cocoa`; passing `QT_QPA_PLATFORM=offscreen` aborts with exit 134. Also expect Gatekeeper to
block the cask on first run and offer only "Move to Trash" — approve it via right-click → Open.

**4. The transcription model's onsets are ~47ms early.** `piano_transcription_inference`
reports attacks a third of a sixteenth ahead of where they land in the recording, which rounds
8% of right-hand notes onto the wrong sixteenth — always one too early. Two independent
measurements agree: shifting all 1518 onsets and scoring where they fall peaks cleanly at
+50ms (3.35 against −0.18 unshifted, i.e. unshifted they sit on no attack at all), and taking
each note's nearest envelope maximum gives a median of +47ms, IQR 41 to 53ms. The downbeat
itself is fine — a comb filter over the drum stem puts the grid at 92.0ms against the
pipeline's 90.5ms. Add the latency before quantising; `scripts/fix_onset_latency.py` repairs
an already-built `notes.json`.

**5. Octave errors in vocal pitch tracking are best fixed by melodic continuity, not spectra.**
A spectral fundamental-vs-octave energy test flagged 14% of notes and was wrong in both
directions. Comparing each note to the median of its neighbors and shifting by ±12 only when it
moves closer corrected 17 notes (4%) and produced a smooth, singable line.

## Verification

`build_scores.py` output was checked three ways:

- **Measure arithmetic** — every voice-measure sums to exactly 16 divisions across all 118 bars
- **Note survival** — 0 notes silently dropped by the renderer
- **Audio ground truth** — 300 notated pitches sampled and tested for real spectral energy at
  that exact moment in the recording: **297/300 (99%)**
- **Every note, spectrally** — `add_note_strength.py` scores all 1903; 1824 (96%) have real
  energy at their own pitch at their own attack
- **Recall** — the model was re-run at onset thresholds 0.30, 0.15 and 0.08 and the results
  diffed. Lowering the threshold to 0.08 surfaces 213 right-hand notes the shipped part does
  not have, but 29 of the 34 that clear both a control pass and an audibility test sit exactly
  an octave, fifth or twelfth above a note already sounding — they are harmonics, not missed
  notes. **Five hold up as genuinely missed**, 0.4% of the right hand. The right hand is not
  missing licks; its problem was rhythm, and that was the onset latency above.

  Run the control. Re-running the model at the *same* threshold reproduces only 91% of the
  original transcription, because decoding the audio to 16kHz a different way moves the result.
  That 9% is the noise floor any recall claim has to clear.

## Running the player

```bash
./scripts/serve.py          # then open http://127.0.0.1:8899/
```

**Not `python3 -m http.server`.** It does not implement HTTP Range, and without Range a browser
cannot seek inside a media file: `audio.currentTime = x` silently fails and the element snaps
back to 0. The player follows the audio clock, so that dragged the display with it and clicking
anywhere on the timeline restarted the song. `scripts/serve.py` answers ranges with 206.

Audio is gitignored. Copy `song.mp3` (the full mix) into `player/`, then build the rest with
`./scripts/build_playalong.sh`.

There are two different pianos here and the labels have to keep them apart:

- **app piano** — Salamander samples playing `notes.json`, our reading of the recording,
  quantised to sixteenths, reach-clamped and thinned. Its volume is the App piano group.
- **keyboard** — Suno's generated audio, straight off the record.

| Play along | use it to |
|---|---|
| vocals only | hear the melody over your comping |
| bass only | solo the line your left hand covers |
| bass + drums | play piano and sing |
| vocals + bass + drums | play piano |
| keyboard + bass + vocals | study the part |
| full song | check yourself against the record |

Six mixes built from three parts you can name. Drums go in the two you play along to and stay
out of the ones you study with.

Two things step aside on their own rather than competing with the recording. A mix containing
the original keyboard **ducks the app piano to 25%** — otherwise two pianos play nearly the same
part a few milliseconds apart and flam, which reads as a broken transcription when it is only
doubling. Ducked rather than muted on purpose: at 25% you can still hear where the two genuinely
disagree. And a mix containing drums **switches the generated percussion off**, since two grooves
that do not quite agree on the feel is worse than either alone.

The percussion stays in the app for slow and looped practice, where a stretched MP3 goes muddy
and a click built from the beat grid does not.

Deliberately a list of mixes rather than per-stem toggles. Toggles would mean several `<audio>`
elements each running its own clock, and they separate by tens of milliseconds over four
minutes — audible as flamming, worst on the drums. Fixing that means reopening the single-clock
sync, which is the thing that made the overlay line up in the first place.

### Reach clamp

Suno layered several keyboard tracks and the transcriber folds them into one part, so a single
attack can span 27 semitones: 46 right-hand attacks and 58 left-hand attacks exceed an octave.
No hand plays that. The clamp keeps the widest window a hand can actually take.

Which notes survive is decided by measurement, not by a rule of thumb. `scripts/add_note_strength.py`
writes an `s` field on every note — peak CQT energy at that note's own pitch just after its
attack, as a share of the loudest bin in the same frames. The right hand keeps the window with
the most total `s`, ties broken toward the more compact voicing, so a lick note that dominates
the mix beats a doubled layer that barely sounds. The left hand anchors on its bottom note
instead, because it is carrying the bass.

At `octave max` this drops 54 right-hand notes (4.3%) and 24 left-hand (4.8%), with a median
strength of 25 against 48 for the track as a whole — it is removing the inaudible layer. The
loudest note of a group survives in 45 of 46 cases.

`s` also drives the "hide faint" slider, which MIDI velocity did badly: 87 notes are effectively
absent from the recording, and hiding 59 of them by velocity meant hiding 708 notes in total.

## Pipeline order

The steps mutate `player/notes.json` in place and are not commutative:

```bash
./venv/bin/python scripts/fix_onset_latency.py   # quantise onsets correctly
./venv/bin/python scripts/extract_bass.py        # transcribe the bass stem
./venv/bin/python scripts/merge_bass.py          # fold it into the left hand
./venv/bin/python scripts/unstack_runs.py        # spread collapsed runs, drop duplicates
./venv/bin/python scripts/add_note_strength.py   # measure audibility of the final set
```

## Rebuilding the scores

The page and the player are built from the same notes: `build_scores.py` reads
`player/notes.json`, so the corrected onsets, the measured audibility and the reach clamp all
apply to the PDFs too. The sung melody used to come from a pickle in a temp directory, which
meant the scores could not be rebuilt once that directory was cleaned — `extract_melody.py`
regenerates it into `scores/melody.json`, which is committed.

```bash
./venv/bin/python scripts/extract_melody.py     # only if melody.json is missing
./venv/bin/python scripts/build_scores.py
mscore -S scripts/musescore-lyric-spacing.mss -o "scores/PIANO VOCAL.pdf" "scores/One Page A Week - PIANO VOCAL.musicxml"
```

The style file widens lyric and note spacing. Without it MuseScore jams adjacent words together
on closely-spaced notes.

## Known limitations

- Chord symbols are one per bar; genuine mid-bar changes show only the dominant chord
- Lyrics are placed one word per melody note, so melismas and crowded phrases misalign
- Right hand caps at 3 simultaneous notes (keeping the highest), left hand at 3 (lowest) —
  dense chord stabs are thinned. The PDFs do not yet have the player's reach clamp
- Fast runs used to arrive as one stacked attack — bar 44 held six chromatic notes at a single
  sixteenth. `scripts/unstack_runs.py` spreads them back across the sixteenth they share,
  ordered by the surrounding contour. Eight clusters in the song, 28 notes, three in bar 44
- The transcription is faithful to generated audio that no two hands ever played; a human
  pianist's cleanup pass is still the missing step
