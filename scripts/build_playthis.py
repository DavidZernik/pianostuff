#!/usr/bin/env python3
"""Build the singalong score: voice and lyrics over a playable piano part.

    ./scripts/build_playthis.py              -> One Page A Week - PLAY THIS.musicxml
    ./scripts/build_playthis.py --embellish  -> ... - PLAY THIS (EMBELLISHED).musicxml

Right hand comps on the backbeat so there is room to sing, and gives way to a lick
where the record plays one. The two builds differ only in which licks those are:
plain takes them off the transcription, embellished takes them from scripts/licks.py.
Left hand is the bass line from the recording either way.

Harmony and bass come from scores/derived-harmony.json so this runs without redoing
the audio analysis. Melody and lyrics are lifted from the LEAD SHEET, which already
has them placed.
"""
import xml.etree.ElementTree as ET, copy, json, sys, os

HERE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCORES = os.path.join(HERE, 'scores')
DIV    = 4                                    # divisions per quarter -> sixteenths
NBARS  = 113
EMBELLISH = '--embellish' in sys.argv

PC   = {'C':0,'C#':1,'D':2,'Eb':3,'E':4,'F':5,'F#':6,'G':7,'Ab':8,'A':9,'Bb':10,'B':11}
STEP = {0:('C',0),1:('C',1),2:('D',0),3:('E',-1),4:('E',0),5:('F',0),
        6:('F',1),7:('G',0),8:('A',-1),9:('A',0),10:('B',-1),11:('B',0)}
QUAL = {'':[0,4,7],'6':[0,4,7,9],'maj7':[0,4,7,11],'m':[0,3,7],'m7':[0,3,7,10],
        '7':[0,4,7,10],'sus4':[0,5,7],'7sus4':[0,5,7,10],'m7b5':[0,3,6,10]}
KIND = {'':'major','6':'major-sixth','maj7':'major-seventh','m':'minor','m7':'minor-seventh',
        '7':'dominant','sus4':'suspended-fourth','7sus4':'suspended-fourth','m7b5':'half-diminished'}
TEXT = {'':'','6':'6','maj7':'maj7','m':'m','m7':'m7','7':'7','sus4':'sus4','7sus4':'7sus4','m7b5':'m7b5'}
SCALE = {10,0,2,3,5,7,9}                      # Bb C D Eb F G A

d = json.load(open(os.path.join(SCORES,'derived-harmony.json')))
HARMONY, BASS = d['harmony'], d['bass_by_beat']
for i in range(12*4): BASS[i] = None          # the bass does not enter until bar 13

def split(lbl):
    r = lbl[:2] if len(lbl) > 1 and lbl[1] in 'b#' else lbl[:1]
    return r, lbl[len(r):]

def midi_name(m):
    s,a = STEP[m%12]
    return s, a, m//12 - 1

def voicing(lbl):
    """Three notes above the root, sitting in C4..B4. The left hand has the root."""
    r,q = split(lbl)
    return sorted({60 + (PC[r]+i) % 12 for i in QUAL[q][1:]})[:3]

# ---------------------------------------------------------------- licks
def transcribed_licks(bars):
    """Pull the right hand out of the machine transcription and thin it to a line.

    The raw part re-strikes a held note on every sixteenth, so a sustained chord
    reads as thirty-five notes. Take the top of each attack, drop anything below
    middle C (that is the left hand's register), collapse repeats, and cap the
    register so the solo does not become a tower of ledger lines."""
    t = ET.parse(os.path.join(SCORES,'One Page A Week - RIGHT HAND.musicxml'))
    part = t.getroot().find('.//part')
    src_div = int(part.find('.//divisions').text)
    out = {}
    for m in part.findall('measure'):
        n = int(m.get('number'))
        if n not in bars: continue
        ev, pos = [], 0
        for note in m.findall('note'):
            dur = int(note.findtext('duration') or 0)
            chord = note.find('chord') is not None
            if note.find('rest') is not None:
                # kept, not skipped: a bar of the transcription that is all rests must
                # stay a rest, or the comping fills a hole the record deliberately left
                if not chord: ev.append([pos,None,dur]); pos += dur
                continue
            p = note.find('pitch')
            step, alt, octv = p.findtext('step'), int(p.findtext('alter') or 0), int(p.findtext('octave'))
            mid = (octv+1)*12 + (PC[step]+alt) % 12
            if chord and ev: ev[-1][1].append(mid)
            else: ev.append([pos,[mid],dur]); pos += dur
        line = []
        for pos0, pitches, dur in ev:
            if pitches is None: line.append((pos0, None, dur)); continue
            top = max(pitches)
            if top < 60: continue
            while top > 84: top -= 12
            if line and line[-1][1] == top: line[-1] = (line[-1][0], top, line[-1][2]+dur)
            else: line.append((pos0, top, dur))
        sc = DIV/src_div
        out[n] = [(int(round(p*sc)), pit, max(1,int(round(du*sc)))) for p,pit,du in line]
    return out

LICK_BARS = set(list(range(1,5)) + list(range(44,48)) + list(range(85,90)) + [109,110])
LICK_NOTES = transcribed_licks(LICK_BARS)
if EMBELLISH:
    # added, never substituted: the embellished score is the plain one plus these, so
    # every note the recording plays is still in it. licks.py only writes into bars
    # where the right hand was comping and nobody was singing.
    sys.path.insert(0, os.path.join(HERE,'scripts'))
    from licks import LICKS as COMPOSED
    clash = set(COMPOSED) & set(LICK_NOTES)
    if clash: raise SystemExit('composed licks would displace the recording at bars %s' % sorted(clash))
    LICK_NOTES = {**LICK_NOTES, **COMPOSED}   # int keys, so not dict(a, **b)

# ---------------------------------------------------------------- musicxml plumbing
def el(tag, text=None, **kw):
    e = ET.Element(tag, **kw)
    if text is not None: e.text = str(text)
    return e

DURTYPE = {16:('whole',0),12:('half',1),8:('half',0),6:('quarter',1),4:('quarter',0),
           3:('eighth',1),2:('eighth',0),1:('16th',0)}
def dur_type(d): return DURTYPE.get(d,('16th',0))
def split_dur(d):
    out = []
    for v in (16,12,8,6,4,3,2,1):
        while d >= v: out.append(v); d -= v
    return out

def note_el(mid, dur, typ, staff, voice, chord=False, dots=0):
    n = el('note')
    if chord: n.append(el('chord'))
    if mid is None: n.append(el('rest'))
    else:
        s,a,o = midi_name(mid)
        p = el('pitch'); p.append(el('step',s))
        if a: p.append(el('alter',a))
        p.append(el('octave',o)); n.append(p)
    n.append(el('duration',dur)); n.append(el('voice',voice)); n.append(el('type',typ))
    for _ in range(dots): n.append(el('dot'))
    n.append(el('staff',staff))
    return n

def emit(m, pitches, dur, staff, voice):
    """One event, split into printable note values, chorded if several pitches."""
    for i, d in enumerate(split_dur(dur)):
        ty, dots = dur_type(d)
        if pitches is None:
            m.append(note_el(None, d, ty, staff, voice, dots=dots))
        else:
            for j, p in enumerate(pitches):
                m.append(note_el(p, d, ty, staff, voice, chord=(j>0), dots=dots))

# ---------------------------------------------------------------- build
lead = ET.parse(os.path.join(SCORES,'One Page A Week - LEAD SHEET.musicxml'))
lmeasures = {int(m.get('number')): m for m in lead.getroot().find('.//part').findall('measure')}

score = el('score-partwise', version='4.0')
w = el('work'); w.append(el('work-title','One Page A Week' + (' — embellished right hand' if EMBELLISH else '')))
score.append(w)
ident = el('identification'); enc = el('encoding')
enc.append(el('software','scripts/build_playthis.py' + (' --embellish' if EMBELLISH else '')))
ident.append(enc); score.append(ident)
pl = el('part-list')
for pid, nm in (('P1','Voice'),('P2','Piano')):
    sp = el('score-part', id=pid); sp.append(el('part-name', nm)); pl.append(sp)
score.append(pl)

# ---- Voice: melody, lyrics and chord symbols ----
p1 = el('part', id='P1')
for b in range(1, NBARS+1):
    m = el('measure', number=str(b))
    if b == 1:
        at = el('attributes'); at.append(el('divisions',DIV))
        k = el('key'); k.append(el('fifths',-2)); at.append(k)
        t = el('time'); t.append(el('beats',4)); t.append(el('beat-type',4)); at.append(t)
        c = el('clef'); c.append(el('sign','G')); c.append(el('line',2))
        c.append(el('clef-octave-change','-1')); at.append(c)
        m.append(at)
        dr = el('direction', placement='above'); dt = el('direction-type')
        mt = el('metronome'); mt.append(el('beat-unit','quarter')); mt.append(el('per-minute','101'))
        dt.append(mt); dr.append(dt); m.append(dr)
    lbl = HARMONY[b-1]; r,q = split(lbl)
    h = el('harmony'); rt = el('root'); rt.append(el('root-step', r[0]))
    if len(r) > 1: rt.append(el('root-alter', -1 if r[1]=='b' else 1))
    h.append(rt)
    kd = ET.Element('kind'); kd.text = KIND[q]; kd.set('text', TEXT[q]); h.append(kd)
    m.append(h)
    src = lmeasures.get(b)
    if src is None: m.append(note_el(None,16,'whole','1','1'))
    else:
        for e in src:
            if e.tag != 'note': continue
            n = copy.deepcopy(e)
            st = n.find('staff')
            if st is not None: n.remove(st)
            m.append(n)
    p1.append(m)
score.append(p1)

# ---- Piano ----
p2 = el('part', id='P2')
for b in range(1, NBARS+1):
    m = el('measure', number=str(b))
    if b == 1:
        at = el('attributes'); at.append(el('divisions',DIV))
        k = el('key'); k.append(el('fifths',-2)); at.append(k)
        t = el('time'); t.append(el('beats',4)); t.append(el('beat-type',4)); at.append(t)
        at.append(el('staves',2))
        for num, sign, line in (('1','G',2),('2','F',4)):
            c = el('clef', number=num); c.append(el('sign',sign)); c.append(el('line',line)); at.append(c)
        m.append(at)
    # right hand
    ev = LICK_NOTES.get(b)
    if ev:
        cur = 0
        for pos, pitch, dur in ev:
            if pos > cur: emit(m, None, pos-cur, '1', '1'); cur = pos
            dur = min(dur, 16-cur)
            if dur <= 0: break
            emit(m, None if pitch is None else (pitch if isinstance(pitch,list) else [pitch]),
                 dur, '1', '1'); cur += dur
        if cur < 16: emit(m, None, 16-cur, '1', '1')
    else:
        ch = voicing(HARMONY[b-1])
        for kind in (None,'hit',None,'hit'):          # rest 1, hit 2, rest 3, hit 4
            emit(m, ch if kind else None, 4, '1', '1')
    m.append(el('backup')); m[-1].append(el('duration',16))
    # left hand
    beats = BASS[(b-1)*4:(b-1)*4+4]
    if all(x is None for x in beats):
        r,q = split(HARMONY[b-1])
        emit(m, [48 + PC[r] % 12], 16, '2', '5')
    else:
        runs = []
        for x in beats:
            if runs and runs[-1][0] == x: runs[-1][1] += 4
            else: runs.append([x,4])
        for pit, dur in runs:
            if pit is not None:
                pit += 12                                   # into playable register
                while pit < 40: pit += 12
                while pit > 64: pit -= 12
                if pit % 12 not in SCALE:                   # kill pitch-tracker artifacts
                    for off in (-1,1,-2,2):
                        if (pit+off) % 12 in SCALE: pit += off; break
            emit(m, None if pit is None else [pit], dur, '2', '5')
    p2.append(m)
score.append(p2)

ET.indent(score, space='  ')
name = 'One Page A Week - PLAY THIS' + (' (EMBELLISHED)' if EMBELLISH else '') + '.musicxml'
out = os.path.join(SCORES, name)
with open(out,'w') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN"'
            ' "http://www.musicxml.org/dtds/partwise.dtd">\n')
    f.write(ET.tostring(score, encoding='unicode'))
print('wrote', name)
print('  licks:', 'composed (scripts/licks.py)' if EMBELLISH else 'transcribed from the recording',
      '—', len(LICK_NOTES), 'bars')
