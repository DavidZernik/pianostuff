"""Composed right-hand licks — the only music in this repo that is not transcription.

These ADD to the recorded part, they never stand in for it. The embellished score is
the plain one plus these; every note the record plays is still there. So they go only
where the right hand is currently just comping and nobody is singing:

    A  bars 5-6     C7sus4        answering the first vocal phrase
    B  bar 10       Dm7           one bar, a fill between lines
    C  bars 90-94   Gm7 Bbmaj7 F Gm7 Gm7
    D  bar 113      Bb6           the last bar

C is the useful one. The recorded piano solo runs bars 85-89 and then hands over to
another layer, so the piano simply stops. These five bars carry it to the end.

The song sits on G minor — Gm7 to Csus4 for four and a half minutes — so one scale
covers all of it:

    G minor pentatonic   G  Bb  C  D  F      (= Bb major pentatonic, the same five notes)
    blues note           Db                  the b5, only ever passing, never over F major

The mode is left open on purpose. The IV chord is sus, so it has no third to vote with,
and across the recording Eb outweighs E natural, 0.68 to 0.60 by pitch-class weight —
natural minor rather than dorian. Staying inside the pentatonic means never asking.

One device per lick, so each teaches something instead of being a shape to memorise.
Positions and durations are sixteenths from the top of the bar: a bar is 16, a beat 4.
A note is (position, midi-or-[midi,...], duration).
"""

G4,Bb4,C5,Db5,D5,F5,G5 = 67,70,72,73,74,77,79

LICKS = {
    # ---- A. bars 5-6: grace-note slide, then walk down. Answers the singer. ----
    5:  [(4,Db5,1),(5,D5,3),(8,C5,2),(10,Bb4,2),(12,G4,4)],
    6:  [(0,Bb4,2),(2,C5,2),(4,D5,4),(8,C5,2),(10,Bb4,6)],

    # ---- B. bar 10: double-stop fourths, landing on the "a" of the beat. ----
    #  Dm7 here, so Bb would sit on the b6 — the fourths keep to D, G, C and F.
    10: [(0,[D5,G5],2),(3,[D5,G5],1),(6,[C5,F5],2),(10,[D5,G5],2),(14,[C5,F5],2)],

    # ---- C. bars 90-94: call, the same call displaced, then land. ----
    90: [(0,G4,2),(2,Bb4,2),(4,C5,2),(6,D5,4),(10,F5,2),(12,D5,4)],
    91: [(0,C5,2),(2,D5,2),(4,F5,4),(8,D5,2),(10,C5,2),(12,Bb4,4)],
    92: [(2,C5,2),(4,D5,2),(6,F5,2),(8,G5,4),(12,F5,4)],          # F major: no Db
    93: [(0,D5,2),(2,C5,2),(4,Bb4,2),(6,Db5,1),(7,D5,3),(10,C5,2),(12,Bb4,4)],
    94: [(0,D5,2),(2,Bb4,2),(4,G4,12)],

    # ---- D. bar 113: fourths down, and stop. ----
    113:[(0,[D5,G5],2),(2,[C5,F5],2),(4,[G4,C5],2),(6,D5,2),(8,Bb4,2),(10,G4,6)],
}

# Nothing here leaves G minor pentatonic except Db, which is always a single sixteenth
# and never appears over the F major bar.
