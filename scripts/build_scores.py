import pickle, re, html, collections
from mido import MidiFile
D='/Users/davidzernik/Desktop/one page a week/'
SPD='/private/tmp/claude-501/-Users-davidzernik-Desktop-projects-one-off-projects/001539f6-ddcc-4c28-95c3-8d29248d3a4b/scratchpad/piano/'
d=pickle.load(open(SPD+'leadsheet.pkl','rb')); mel=d['mel']; chords=d['chords']
BPM=101.26; beat=60/BPM; sx=beat/4; DOWN=-0.0576
VF_RH=22          # lower floor for RH: licks include quieter notes
VF_LH=22
words=[]
for line in open(D+'One Page A Week - lyrics.txt').read().splitlines():
    l=line.strip()
    if not l or (l.startswith('[') and l.endswith(']')): continue
    words += re.findall(r"[A-Za-z’']+", l)
kb=[];on={};t=0.0
for m in MidiFile(D+'One Page A Week - PIANO.mid'):
    t+=m.time
    if m.type=='note_on' and m.velocity>0: on.setdefault(m.note,[]).append((t,m.velocity))
    elif m.type in ('note_off','note_on'):
        if on.get(m.note): s,v=on[m.note].pop(0); kb.append([m.note,s,t,v])
q16=lambda x:int(round((x-DOWN)/sx))            # 16th grid
q8 =lambda x:int(round((x-DOWN)/(sx*2)))*2      # 8th grid
# RIGHT HAND at 16ths
sl16=collections.defaultdict(dict)
for p,s,e,v in kb:
    if p<60 or v<VF_RH: continue
    a=max(0,q16(s)); sl16[a][p]=max(sl16[a].get(p,0),max(a+1,q16(e)))
RH={a:{p:pm[p] for p in sorted(pm)[-3:]} for a,pm in sl16.items()}
# LEFT HAND at 8ths
sl8=collections.defaultdict(dict)
for p,s,e,v in kb:
    if p>=60 or v<VF_LH: continue
    a=max(0,q16(s)); sl8[a][p]=max(sl8[a].get(p,0),max(a+1,q16(e)))
LH={a:{p:pm[p] for p in sorted(pm)[:3]} for a,pm in sl8.items()}
print(f"RH {sum(len(v) for v in RH.values())} @16th | LH {sum(len(v) for v in LH.values())} @16th")
ev=sorted([[p,max(0,q8(s)),max(q8(s)+2,q8(e))] for p,s,e in mel],key=lambda x:x[1])
mg=[]
for p,a,b in ev:
    if mg and a<mg[-1][2]:
        if b>mg[-1][2] and p==mg[-1][0]: mg[-1][2]=b
        continue
    if mg and mg[-1][0]==p and a-mg[-1][2]<=2: mg[-1][2]=b
    else: mg.append([p,a,b])
for i in range(len(mg)-1):
    if mg[i+1][1]-mg[i][2]<=2: mg[i][2]=mg[i+1][1]
mgrid={m[1]:(m[0],m[2]) for m in mg}
PC={0:('C',0),1:('D',-1),2:('D',0),3:('E',-1),4:('E',0),5:('F',0),6:('G',-1),7:('G',0),8:('A',-1),9:('A',0),10:('B',-1),11:('B',0)}
KIND={'':'major','maj7':'major-seventh','m':'minor','m7':'minor-seventh','7':'dominant','m7b5':'half-diminished'}
ROOTPC={'C':0,'D':2,'Eb':3,'F':5,'G':7,'A':9,'Bb':10,'Ab':8}
def sk(c):
    for s in ['maj7','m7b5','m7','m','7']:
        if c.endswith(s): return c[:-len(s)],s
    return c,''
UNITS=[(16,'whole',0),(12,'half',1),(8,'half',0),(6,'quarter',1),(4,'quarter',0),(3,'eighth',1),(2,'eighth',0),(1,'16th',0)]
def pieces(n):
    o=[]
    while n>0:
        for u,ty,dt in UNITS:
            if u<=n: o.append((u,ty,dt)); n-=u; break
        else: break
    return o
def nx(p,dur,ty,dots,staff,voice,chord=False,lyric=None):
    st,al=PC[p%12]; s=['<note>']
    if chord: s.append('<chord/>')
    s.append('<pitch><step>%s</step>%s<octave>%d</octave></pitch>'%(st,(f'<alter>{al}</alter>' if al else ''),p//12-1))
    s.append(f'<duration>{dur}</duration><voice>{voice}</voice><type>{ty}</type>'+'<dot/>'*dots)
    if staff: s.append(f'<staff>{staff}</staff>')
    if lyric: s.append('<lyric><syllabic>single</syllabic><text>%s</text></lyric>'%html.escape(lyric))
    s.append('</note>'); return ''.join(s)
def rx(dur,ty,dots,staff,voice):
    return f'<note><rest/><duration>{dur}</duration><voice>{voice}</voice><type>{ty}</type>{"<dot/>"*dots}'+(f'<staff>{staff}</staff>' if staff else '')+'</note>'
def render(grid,staff,voice,bar_i,minlen=1):
    st=bar_i*16; out=[]; pos=0
    while pos<16:
        if st+pos in grid:
            pm=grid[st+pos]; ps=sorted(pm)
            nxt=16
            for k in range(pos+1,16):
                if st+k in grid: nxt=k; break
            dur=max(minlen,min(max(pm[p] for p in ps)-(st+pos),nxt-pos,16-pos))
            for u,ty,dt in pieces(dur):
                for j,p in enumerate(ps): out.append(nx(p,u,ty,dt,staff,voice,chord=(j>0)))
            pos+=dur
        else:
            nxt=16
            for k in range(pos+1,16):
                if st+k in grid: nxt=k; break
            for u,ty,dt in pieces(nxt-pos): out.append(rx(u,ty,dt,staff,voice))
            pos=nxt
    return out
def harmony(b):
    c=chords[b][2]
    if c and (b==0 or chords[b-1][2]!=c):
        rt,suf=sk(c); stp,alt=PC[ROOTPC[rt]]
        return ['<harmony><root><root-step>%s</root-step>%s</root><kind>%s</kind></harmony>'
                %(stp,(f'<root-alter>{alt}</root-alter>' if alt else ''),KIND[suf])]
    return []

# ---------- A. full piano/vocal ----------
wi=0; V=[]; P=[]
for b in range(len(chords)):
    st=b*16; V.append(f'<measure number="{b+1}">')
    if b==0:
        V.append('<attributes><divisions>4</divisions><key><fifths>-2</fifths></key>'
                 '<time><beats>4</beats><beat-type>4</beat-type></time>'
                 '<clef><sign>G</sign><line>2</line><clef-octave-change>-1</clef-octave-change></clef></attributes>'
                 '<direction placement="above"><direction-type><metronome><beat-unit>quarter</beat-unit>'
                 '<per-minute>101</per-minute></metronome></direction-type></direction>')
    V+=harmony(b)
    pos=0
    while pos<16:
        if st+pos in mgrid:
            p,en=mgrid[st+pos]; dur=min(en-(st+pos),16-pos); first=True
            for u,ty,dt in pieces(dur):
                V.append(nx(p,u,ty,dt,1,1,lyric=(words[wi] if first and wi<len(words) else None)))
                if first and wi<len(words): wi+=1
                first=False
            pos+=dur
        else:
            nxt=16
            for k in range(pos+1,16):
                if st+k in mgrid: nxt=k; break
            for u,ty,dt in pieces(nxt-pos): V.append(rx(u,ty,dt,1,1))
            pos=nxt
    V.append('</measure>')
    P.append(f'<measure number="{b+1}">')
    if b==0:
        P.append('<attributes><divisions>4</divisions><key><fifths>-2</fifths></key>'
                 '<time><beats>4</beats><beat-type>4</beat-type></time><staves>2</staves>'
                 '<clef number="1"><sign>G</sign><line>2</line></clef>'
                 '<clef number="2"><sign>F</sign><line>4</line></clef></attributes>')
    P+=render(RH,1,1,b,1); P.append('<backup><duration>16</duration></backup>'); P+=render(LH,2,5,b,1)
    P.append('</measure>')
o=['<?xml version="1.0" encoding="UTF-8"?>',
   '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">',
   '<score-partwise version="3.1">','<work><work-title>One Page A Week</work-title></work>',
   '<part-list>','<score-part id="P1"><part-name>Voice</part-name></score-part>',
   '<score-part id="P2"><part-name>Piano</part-name></score-part>','</part-list>',
   '<part id="P1">']+V+['</part>','<part id="P2">']+P+['</part>','</score-partwise>']
open(D+'One Page A Week - PIANO VOCAL.musicxml','w').write('\n'.join(o))

# ---------- B. right hand only ----------
R=[]
for b in range(len(chords)):
    R.append(f'<measure number="{b+1}">')
    if b==0:
        R.append('<attributes><divisions>4</divisions><key><fifths>-2</fifths></key>'
                 '<time><beats>4</beats><beat-type>4</beat-type></time>'
                 '<clef><sign>G</sign><line>2</line></clef></attributes>'
                 '<direction placement="above"><direction-type><metronome><beat-unit>quarter</beat-unit>'
                 '<per-minute>101</per-minute></metronome></direction-type></direction>')
    R+=harmony(b); R+=render(RH,None,1,b,1); R.append('</measure>')
o2=['<?xml version="1.0" encoding="UTF-8"?>',
    '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">',
    '<score-partwise version="3.1">','<work><work-title>One Page A Week - Right Hand</work-title></work>',
    '<part-list><score-part id="P1"><part-name>R.H.</part-name></score-part></part-list>',
    '<part id="P1">']+R+['</part>','</score-partwise>']
open(D+'One Page A Week - RIGHT HAND.musicxml','w').write('\n'.join(o2))
print("wrote both scores")
