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
cd player && python3 -m http.server 8899
open http://127.0.0.1:8899/
```

Audio is gitignored. Copy `song.mp3` (full mix) and `keys.mp3` (the Keyboard stem) into
`player/`, then build the rest with `./scripts/build_playalong.sh`:

| Play along | what it is | use it to |
|---|---|---|
| mix − piano | everything but the Keyboard stem | be the pianist |
| mix − piano − vocals | drums, bass, percussion, synth | play and sing |
| piano alone | the Keyboard stem | copy the licks |
| piano + drums | keyboard, drums, percussion | put the licks in time |
| bass alone | the Bass stem | solo the line your left hand covers |
| piano + vocals | keyboard and both vocal stems | melody against the part |
| vocals alone | lead + backing | hear the melody over your comping |
| full song | the master | check yourself against the record |

Deliberately a list of mixes rather than per-stem toggles. Toggles would mean several `<audio>`
elements each running its own clock, and they separate by tens of milliseconds over four
minutes — audible as flamming, worst on the drums. Fixing that means reopening the single-clock
sync, which is the thing that made the overlay line up in the first place. Not worth it to save
a click until the list here proves too small.

**Controls:** speed down to 10%, bar-range looping, independent RH/LH toggles, a left-hand
density mode, a reach clamp, and a "hide faint" slider. Space plays, arrows jump a bar.
Piano sound is the Salamander Grand sampled every three semitones, so what you see and what
you hear are always the same data.

### The bass line

There is no bassist. Playing this alone, the left hand has to cover the bass, and the
transcribed left hand does not: it is only the Keyboard stem below middle C, and its lowest
note is the chord root barely half the time. The Bass stem is a separate instrument, louder
than the Keyboard (−24.3 dB against −28.5), sitting at F1 to C2. `extract_bass.py` transcribes
it and `merge_bass.py` folds it into the left hand, tagged so the player can switch it off.

**There is no brass.** The Brass stem is digital silence — peak −55 dB, RMS −108 dB, identical
to the empty "Other" stem. Suno emitted the slot and put nothing in it. The bass-register part
you can hear is the Bass stem; the horn-like line above it is Synth, centred around F3–B♭3.

**The bass does not enter until bar 13.** Bars 1–12 measure −80 dB or below in that stem. The
silence is real, not a detection failure.

pyin was tried first and abandoned. Its `voiced_prob` runs so low on a synth bass that only 11%
of frames clear 0.5, and the notes it returned disagreed with the recording — they matched the
chord root 25% of the time at the bar line, where reading the same stem's spectrum directly
gets 66%. So the extractor takes the strongest CQT bin per sixteenth, then checks an octave
below, because a synth bass has a second harmonic loud enough to notate the whole line an
octave high.

The result is 402 notes, F1–C3, median B♭1, 46% of its duration on the chord root, with
chromatic approach notes into the B♭ bars — a bass line, not a pitch trace.

Once the bass is in, the left hand is doing two jobs at once, so it gets its own clamp rule:
the bass note is kept whatever happens, and a shell is allowed above it out to a twelfth. You
strike them in turn and hold with the pedal, so the gap is not a reach — but past a twelfth
it is a different register rather than a voicing.

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
- Six right-hand attacks stack 3+ adjacent semitones (bar 44 has 72, 73, 74 all strong). Those
  are fast chromatic runs quantised into one frame, not chords. Fixing them needs re-timing,
  not filtering, so they are still there
- The transcription is faithful to generated audio that no two hands ever played; a human
  pianist's cleanup pass is still the missing step
