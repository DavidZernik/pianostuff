"""Composed right-hand licks for the embellished score.

Everything else in this repo is transcription — what the recording actually plays.
These are not. They are written to fit, and they are kept in one file so the line
between "what Suno played" and "what we added" stays visible.

The song sits on G minor, Gm7 to Csus4, for four and a half minutes. The tonal centre
is G rather than the Bb the notation implies, and one scale covers the whole tune:

    G minor pentatonic   G  Bb  C  D  F        (= Bb major pentatonic, same five notes)
    blues note           Db                    the b5, only ever passing

The mode is deliberately not pinned down. The IV chord is sus, so it carries no third
and cannot vote, and across the whole recording Eb outweighs E natural (0.68 to 0.60
by pitch-class weight) — natural minor, not dorian. So the licks stay inside the
pentatonic, where the question never comes up, and the b6 is simply never played.

Four licks, one per hole in the vocal, each built on a single device so each one
teaches something rather than being a shape to memorise:

    A  intro       bars 1-4      grace-note slide into a descending pentatonic
    B  fill        bars 44-47    double-stop fourths, syncopated onto the "a" of the beat
    C  solo        bars 85-89    call and response: a phrase, the same phrase displaced
    D  tag         bars 109-110  fourths walking down, one blues slide, done

Positions and durations are in sixteenths from the top of the bar, so a bar is 16 and
a beat is 4. A note is (position, midi-or-[midi,...], duration).
"""

G4,A4,Bb4,C5,Db5,D5,Eb5,E5,F5,G5,Bb5 = 67,69,70,72,73,74,75,76,77,79,82
F4 = 65

LICKS = {
    # ---- A. intro: state the tune, leave air. Db slides into D, then walk down. ----
    1:  [(8,Db5,1),(9,D5,3),(12,C5,2),(14,Bb4,2)],
    2:  [(0,G4,6)],
    3:  [(8,D5,2),(10,F5,2),(12,G5,4)],
    4:  [(0,F5,6),(6,D5,2),(8,C5,8)],

    # ---- B. fill: one riff, played twice, then moved. Fourths land off the beat. ----
    44: [(0,[D5,G5],2),(3,[D5,G5],1),(6,[C5,F5],2),(10,[D5,G5],2),(14,[G4,C5],2)],
    45: [(0,[D5,G5],2),(3,[D5,G5],1),(6,[C5,F5],2),(10,[D5,G5],2),(14,[G4,C5],2)],
    46: [(0,[C5,F5],2),(3,[C5,F5],1),(6,[Bb4,Eb5],2),(10,[C5,F5],2),(14,[G4,C5],2)],
    47: [(0,[C5,F5],4),(6,[Bb4,Eb5],2),(10,[C5,F5],6)],

    # ---- C. solo: two bars of statement, two of answer, one to land. ----
    85: [(0,G4,2),(2,Bb4,2),(4,C5,2),(6,D5,4),(10,C5,2),(12,Bb4,4)],
    86: [(0,D5,2),(2,F5,2),(4,G5,4),(8,F5,2),(10,D5,2),(12,C5,4)],
    87: [(2,G4,2),(4,Bb4,2),(6,C5,2),(8,Db5,1),(9,D5,3),(12,F5,4)],
    88: [(0,G5,4),(4,F5,2),(6,D5,2),(8,C5,2),(10,Bb4,2),(12,G4,4)],
    89: [(0,F5,2),(2,D5,2),(4,Bb4,4),(8,G4,8)],

    # ---- D. tag: fourths down, blues slide, rest. ----
    109:[(0,[D5,G5],2),(2,[C5,F5],2),(4,[G4,C5],4),(8,Db5,1),(9,D5,3),(12,C5,4)],
    110:[(0,Bb4,2),(2,G4,2),(4,F4,4),(8,G4,8)],
}

# The only note outside the pentatonic is Eb in bars 46-47, and there it is a chord
# tone: the b3 of Cm7 and the 7th of F7sus4. Nothing else leaves the five notes.
