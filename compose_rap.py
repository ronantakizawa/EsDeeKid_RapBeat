"""
Dirty Phantom - EsDeeKid Type Beat
Key: C# minor | BPM: 140 | 64 bars (~1:50)

Reference Track Analysis (mcp__music-analysis on actual EsDeeKid tracks):
  Phantom (21M views):   C# chroma = 0.844, BPM = 143.5 → C# minor confirmed
  4 Raws (11M views):    D  chroma = 0.762, BPM = 143.5 → Eb minor area
  Empirical BPM: 143.5 (librosa beat_track). Tutorials say 190 (FL Studio grid);
  190 × 3/4 = 142.5 ≈ 143.5 — jerk ghost snares create 3/4 sub-pulse at felt tempo.

YouTube Tutorial Sources:
  https://www.youtube.com/watch?v=2J8yekfFe0Q  — "how to EsDeeKid beat"
  https://www.youtube.com/watch?v=UmQP6uH7kRU  — "INSANE Underground Beats For EsDeeKid"
  https://www.youtube.com/watch?v=1wKQ27xH618  — "ESDEEKID Type Beats on FL Studio"

Song Structure:
  Intro      bars  1– 4  (0-indexed  0– 3): Pad only
  Pre-Drop   bars  5– 8  (0-indexed  4– 7): 808 enters + snare roll
  Drop A     bars  9–40  (0-indexed  8–39): Full: jerk drums + 808 + melody + counter
  Break      bars 41–48  (0-indexed 40–47): Sparse hi-hat + pad only
  Drop A2    bars 49–60  (0-indexed 48–59): Full arrangement return
  Outro      bars 61–64  (0-indexed 60–63): Fade out
"""

import os
import random
from music21 import stream, note, chord, tempo, meter
from mido import MidiFile, Message

random.seed(42)

OUTPUT_DIR = '/Users/ronantakizawa/Documents/EsDeeKid_RapBeat'
os.makedirs(OUTPUT_DIR, exist_ok=True)

BPM = 140
BPB = 4  # beats per bar

# Section boundaries (0-indexed bars)
INTRO_S,   INTRO_E   =  0,  4
PREDROP_S, PREDROP_E =  4,  8
DROPA_S,   DROPA_E   =  8, 40
BREAK_S,   BREAK_E   = 40, 48
DROPA2_S,  DROPA2_E  = 48, 60
OUTRO_S,   OUTRO_E   = 60, 64


def bb(bar, beat=0.0):
    """Absolute offset from bar (0-indexed) + beat (0-indexed)."""
    return float(bar * BPB + beat)


# ─────────────────────────────────────────────────────────────
# DRUMS  (jerk pattern — velocity variation = the bounce)
# GM drum notes: 36=kick  38=snare  39=clap-layer  42=closed-HH  46=open-HH  49=crash
# ─────────────────────────────────────────────────────────────
def create_drums():
    part = stream.Part()
    part.partName = 'Drums'
    part.insert(0, tempo.MetronomeMark(number=BPM))
    part.insert(0, meter.TimeSignature('4/4'))

    def hit(offset, note_num, vel=90):
        n = note.Note(note_num, quarterLength=0.25)
        n.volume.velocity = min(127, max(1, int(vel)))
        part.insert(offset, n)

    def jerk_bar(bar, crash=False, open_hat=False, hh_run=False):
        """One bar of jerk drums. Ghost snares between hits = bounce signature."""
        o = bb(bar)
        # Kicks
        hit(o + 0.0, 36, 100)
        hit(o + 2.0, 36, 88)
        # Main snares + clap layer (note 39)
        hit(o + 1.0, 38, 95);  hit(o + 1.0, 39, 85)
        hit(o + 3.0, 38, 100); hit(o + 3.0, 39, 90)
        # Ghost snares — the jerk bounce (low velocity = subtle but felt)
        hit(o + 0.5, 38, 30)
        hit(o + 1.5, 38, 35)
        hit(o + 2.5, 38, 32)
        # 8th-note closed HH (alternating velocities for groove)
        if not hh_run:
            for i in range(8):
                vel = 60 if i % 2 == 0 else 32
                hit(o + i * 0.5, 42, vel)
        else:
            # 16th-note hi-hat run (bar before crash — fill)
            for i in range(16):
                vel = 55 if i % 4 == 0 else (38 if i % 2 == 0 else 22)
                hit(o + i * 0.25, 42, vel)
        # Open HH every other bar
        if open_hat:
            hit(o + 3.5, 46, 50)
        # Crash
        if crash:
            hit(o + 0.0, 49, 80)

    # Pre-Drop snare roll (bars 4–7)
    hit(bb(4) + 2.0, 38, 72)                                    # bar 5: 1 snare
    hit(bb(5) + 1.0, 38, 75); hit(bb(5) + 3.0, 38, 78)         # bar 6: 2 snares
    for b in range(4):
        hit(bb(6) + b, 38, 80 + b * 2)                          # bar 7: 4 snares
    for h in range(8):
        hit(bb(7) + h * 0.5, 38, 84 + h)                        # bar 8: 8 snares (roll)
    hit(bb(7) + 3.5, 49, 88)                                     # crash end of bar 8

    # Drop A (bars 8–39)
    for bar in range(DROPA_S, DROPA_E):
        idx = bar - DROPA_S
        jerk_bar(
            bar,
            crash=(idx % 4 == 0),
            open_hat=(idx % 2 == 1),
            hh_run=(idx % 4 == 3),
        )

    # Break (bars 40–47): sparse hi-hat only
    for bar in range(BREAK_S, BREAK_E):
        o = bb(bar)
        hit(o + 1.0, 42, 32)
        hit(o + 3.0, 42, 32)

    # Drop A Return (bars 48–59)
    for bar in range(DROPA2_S, DROPA2_E):
        idx = bar - DROPA2_S
        jerk_bar(
            bar,
            crash=(idx % 4 == 0),
            open_hat=(idx % 2 == 1),
            hh_run=(idx % 4 == 3),
        )

    # Outro (bars 60–63): fading drums
    for bar in range(OUTRO_S, OUTRO_E):
        o = bb(bar)
        fade = max(22, 90 - (bar - OUTRO_S) * 22)
        hit(o + 0.0, 36, fade)
        hit(o + 2.0, 36, max(12, fade - 12))
        hit(o + 1.0, 38, fade)
        hit(o + 3.0, 38, max(12, fade - 10))
        hit(o + 1.0, 42, max(12, fade - 28))
        hit(o + 3.0, 42, max(12, fade - 32))

    return part


# ─────────────────────────────────────────────────────────────
# 808 BASS  (C#2 root — "almost all 808s are the same note")
# ─────────────────────────────────────────────────────────────
def create_808():
    part = stream.Part()
    part.partName = 'Bass 808'
    part.insert(0, tempo.MetronomeMark(number=BPM))

    def bass_hit(bar, vel=90):
        o = bb(bar)
        # Main hit: 3 beats (hold-envelope style — no natural decay)
        n1 = note.Note('C#2', quarterLength=3.0)
        n1.volume.velocity = vel
        part.insert(o + 0.0, n1)
        # Ghost hit: beat 2 (quiet, short)
        n2 = note.Note('C#2', quarterLength=0.75)
        n2.volume.velocity = int(vel * 0.38)
        part.insert(o + 2.0, n2)

    # Pre-Drop: 808 enters quietly
    for bar in range(PREDROP_S, PREDROP_E):
        n = note.Note('C#2', quarterLength=3.0)
        n.volume.velocity = 52
        part.insert(bb(bar), n)

    # Drop A
    for bar in range(DROPA_S, DROPA_E):
        bass_hit(bar, 90)

    # Drop A Return
    for bar in range(DROPA2_S, DROPA2_E):
        bass_hit(bar, 90)

    # Outro fade
    for i, bar in enumerate(range(OUTRO_S, OUTRO_S + 3)):
        n = note.Note('C#2', quarterLength=3.0)
        n.volume.velocity = max(22, 85 - i * 28)
        part.insert(bb(bar), n)

    return part


# ─────────────────────────────────────────────────────────────
# CHORDS / PAD  (4-bar cycle: i – VI – III – VII in C# minor)
#
# Progression:
#   Bar %4 == 0: C# minor  (C#3, E3, G#3)   — tonic
#   Bar %4 == 1: A major   (A2,  C#3, E3)   — VI  (relative major area)
#   Bar %4 == 2: E major   (E3,  G#3, B3)   — III (bright lift)
#   Bar %4 == 3: B major   (B2,  D#3, F#3)  — VII (semitone tension → tonic)
#
# All chord tones are diatonic to C# natural minor except D# (leading tone
# in B major) which creates the semitone tension Tutorial 3 described.
# ─────────────────────────────────────────────────────────────
def create_chords():
    part = stream.Part()
    part.partName = 'Chords Pad'
    part.insert(0, tempo.MetronomeMark(number=BPM))

    PROG = [
        ['C#3', 'E3',  'G#3'],   # i   – C# minor
        ['A2',  'C#3', 'E3' ],   # VI  – A major
        ['E3',  'G#3', 'B3' ],   # III – E major
        ['B2',  'D#3', 'F#3'],   # VII – B major (semitone tension)
    ]

    def pad(bar, vel=55):
        c = chord.Chord(PROG[bar % 4], quarterLength=4.0)
        c.volume.velocity = vel
        part.insert(bb(bar), c)

    for bar in range(INTRO_S,   INTRO_E):   pad(bar, 48)
    for bar in range(PREDROP_S, PREDROP_E): pad(bar, 52)
    for bar in range(DROPA_S,   DROPA_E):   pad(bar, 56)
    for bar in range(BREAK_S,   BREAK_E):   pad(bar, 42)
    for bar in range(DROPA2_S,  DROPA2_E):  pad(bar, 56)
    for bar in range(OUTRO_S,   OUTRO_E):
        fade = max(14, 48 - (bar - OUTRO_S) * 10)
        pad(bar, fade)

    return part


# ─────────────────────────────────────────────────────────────
# MELODY  (2-bar loop, C# minor, semitone tension E→D#)
#
# Bar 1: E4(1.5) → D#4(0.5) → C#4(1.5) → rest(0.5)
#         E→D# is the semitone step that creates tension (per tutorial)
# Bar 2: G#4(2.0) → F#4(1.0) → E4(0.5) → rest(0.5)
# ─────────────────────────────────────────────────────────────
def create_melody():
    part = stream.Part()
    part.partName = 'Melody Lead'
    part.insert(0, tempo.MetronomeMark(number=BPM))

    def n(pitch, dur, vel):
        nd = note.Note(pitch, quarterLength=dur)
        nd.volume.velocity = int(vel)
        return nd

    def melody_loop(start_bar, vel=75):
        o = bb(start_bar)
        # Bar 1
        part.insert(o + 0.0, n('E4',  1.5, vel))
        part.insert(o + 1.5, n('D#4', 0.5, vel - 8))   # semitone step — tension
        part.insert(o + 2.0, n('C#4', 1.5, vel - 4))
        # rest 0.5 beats
        # Bar 2
        part.insert(o + 4.0, n('G#4', 2.0, vel + 4))
        part.insert(o + 6.0, n('F#4', 1.0, vel - 6))
        part.insert(o + 7.0, n('E4',  0.5, vel - 10))
        # rest 0.5 beats

    # Drop A: 2-bar loop × 16 repetitions (bars 8–39)
    for bar in range(DROPA_S, DROPA_E, 2):
        melody_loop(bar, random.randint(68, 80))

    # Drop A Return (bars 48–59)
    for bar in range(DROPA2_S, DROPA2_E, 2):
        melody_loop(bar, random.randint(68, 80))

    return part


# ─────────────────────────────────────────────────────────────
# COUNTER MELODY  (root pulse for bounce — C#3 staccato)
# Per tutorial: "first note of the scale playing rhythmically
#  creates bounce — used instead of going over the main melody"
# ─────────────────────────────────────────────────────────────
def create_counter():
    part = stream.Part()
    part.partName = 'Counter Melody'
    part.insert(0, tempo.MetronomeMark(number=BPM))

    def pulse(bar):
        o = bb(bar)
        # Beat 0: strong root hit
        n1 = note.Note('C#3', quarterLength=0.35)
        n1.volume.velocity = 80
        part.insert(o + 0.0, n1)
        # Beat 2: weak hit (creates bounce feel)
        n2 = note.Note('C#3', quarterLength=0.35)
        n2.volume.velocity = 50
        part.insert(o + 2.0, n2)

    for bar in range(DROPA_S,  DROPA_E):  pulse(bar)
    for bar in range(DROPA2_S, DROPA2_E): pulse(bar)

    return part


# ─────────────────────────────────────────────────────────────
# MIDI EXPORT HELPERS  (same patterns as compose.py)
# ─────────────────────────────────────────────────────────────
def insert_program(track, program):
    pos = 0
    for j, msg in enumerate(track):
        if msg.type == 'track_name':
            pos = j + 1
            break
    track.insert(pos, Message('program_change', program=program, time=0))


def fix_instruments(mid, part_names):
    for i, track in enumerate(mid.tracks):
        if i == 0:
            continue
        pidx = i - 1
        if pidx >= len(part_names):
            break
        name = part_names[pidx].lower()
        if 'drum' in name:
            for msg in track:
                if hasattr(msg, 'channel'):
                    msg.channel = 9
        elif 'bass' in name or '808' in name:
            insert_program(track, 38)   # Synth Bass 1
        elif 'chord' in name or 'pad' in name:
            insert_program(track, 89)   # Pad 2 (warm)
        elif 'counter' in name:
            insert_program(track, 80)   # Square Lead (plucky)
        elif 'melody' in name or 'lead' in name:
            insert_program(track, 81)   # Sawtooth Lead


def save(score, filename):
    path = os.path.join(OUTPUT_DIR, filename)
    score.write('midi', fp=path)
    mid = MidiFile(path)
    names = [p.partName or '' for p in score.parts]
    fix_instruments(mid, names)
    mid.save(path)
    print(f'  ✓  {filename}')
    return path


def solo(part):
    s = stream.Score()
    s.append(part)
    return s


# ─────────────────────────────────────────────────────────────
# COMPOSE & SAVE
# ─────────────────────────────────────────────────────────────
print('Composing Dirty Phantom (EsDeeKid Type Beat) …')
print(f'  Key: C# minor  |  BPM: {BPM}  |  64 bars  (~1:50)\n')

drums   = create_drums()
bass    = create_808()
chords  = create_chords()
melody  = create_melody()
counter = create_counter()

print('Saving individual stems …')
save(solo(drums),   'DirtyPhantom_drums.mid')
save(solo(bass),    'DirtyPhantom_bass.mid')
save(solo(chords),  'DirtyPhantom_chords.mid')
save(solo(melody),  'DirtyPhantom_melody.mid')
save(solo(counter), 'DirtyPhantom_counter.mid')

print('\nSaving full arrangement …')
full = stream.Score()
full.append(drums)
full.append(bass)
full.append(chords)
full.append(melody)
full.append(counter)
save(full, 'DirtyPhantom_FULL.mid')

print('\nDone! All MIDI files saved to:')
print(f'  {OUTPUT_DIR}')
