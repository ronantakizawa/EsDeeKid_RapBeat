"""
Dirty Phantom — Render Script
EsDeeKid Type Beat | C# minor | 140 BPM | 64 bars

Key differences vs Shadow Ritual render5.py:
  - Jerk drums: ghost snares via velocity, clap layer on note 39
  - 808: C#2 root (+13st PitchShift), hold-envelope trim, heavy distortion on bass bus
  - No sub bass (808 covers low end in EsDeeKid style)
  - No snare delay bus (different feel)
  - No vinyl crackle, no riser samples
  - Laser perc (FX-Laser.wav) at drop entry bars
  - Vocal chop: FX-Ugh.wav pitched -6st at drop entry + accent points
  - Dryer room IR (8% wet vs 15% in witch house)
  - Master: Distortion(drive=8dB) as soft clipper — CRITICAL per all 3 tutorials

MIDI track indices in DirtyPhantom_FULL.mid:
  0: tempo/metadata
  1: drums
  2: 808 bass
  3: chords/pad
  4: melody lead
  5: counter melody
"""

import os
import numpy as np
from collections import defaultdict
from math import gcd
from scipy import signal
from scipy.signal import fftconvolve
from scipy.io import wavfile
import soundfile as sf
from pydub import AudioSegment
import mido
import pedalboard as pb
import dawdreamer as daw
import pyroomacoustics as pra

OUTPUT   = '/Users/ronantakizawa/Documents/EsDeeKid_RapBeat'
INST     = '/Users/ronantakizawa/Documents/instruments/☆ Juicy Jules - Stardust ☆/☆ Juicy Jules - Stardust ☆'
FULL_MID = os.path.join(OUTPUT, 'DirtyPhantom_FULL.mid')
FIXED_MID= os.path.join(OUTPUT, 'DirtyPhantom_FIXED.mid')
OUT_WAV  = os.path.join(OUTPUT, 'DirtyPhantom.wav')
OUT_MP3  = os.path.join(OUTPUT, 'DirtyPhantom.mp3')

SR      = 44100
NYQ     = SR / 2.0
BPM     = 140
BEAT    = 60.0 / BPM
BAR     = BEAT * 4
NBARS   = 64
SONG    = NBARS * BAR
NSAMP   = int((SONG + 4.0) * SR)   # +4s reverb tail

rng = np.random.RandomState(42)

# ─── helpers (same patterns as render5.py) ──────────────────────────────────

def load_sample(path):
    data, orig_sr = sf.read(path, dtype='float32', always_2d=True)
    mono = data.mean(axis=1)
    if orig_sr != SR:
        g = gcd(SR, orig_sr)
        mono = signal.resample_poly(mono, SR // g, orig_sr // g)
    return mono.astype(np.float32)

def apply_pb(arr2ch, board):
    out = board(arr2ch.T.astype(np.float32), SR)
    return out.T.astype(np.float32)

def midi_to_hz(n):
    return 440.0 * (2 ** ((n - 69) / 12.0))

def parse_track(mid_path, track_idx):
    """Return (start_sec, note, vel, dur_sec) for all notes in a MIDI track."""
    mid = mido.MidiFile(mid_path)
    tpb = mid.ticks_per_beat
    tempo_val = 500000
    for msg in mid.tracks[0]:
        if msg.type == 'set_tempo':
            tempo_val = msg.tempo
            break
    active, result = {}, []
    ticks = 0
    for msg in mid.tracks[track_idx]:
        ticks += msg.time
        t = mido.tick2second(ticks, tpb, tempo_val)
        if msg.type == 'note_on' and msg.velocity > 0:
            active[msg.note] = (t, msg.velocity)
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            if msg.note in active:
                s, v = active.pop(msg.note)
                if t - s > 0:
                    result.append((s, msg.note, v, t - s))
    return result

def make_automation(notes, release_gap=0.015):
    """Build sample-rate automation arrays for a mono FAUST voice (same as render5.py)."""
    gap = int(release_gap * SR)
    freq_arr = np.zeros(NSAMP, dtype=np.float32)
    gate_arr = np.zeros(NSAMP, dtype=np.float32)
    gain_arr = np.ones(NSAMP, dtype=np.float32)
    for start_sec, note_num, vel, dur_sec in notes:
        s = int(start_sec * SR)
        e = min(int((start_sec + dur_sec) * SR), NSAMP)
        hz = midi_to_hz(note_num)
        freq_arr[max(0, s - gap):e] = hz
        gate_arr[s:e] = 1.0
        gain_arr[s:e] = vel / 127.0
    # Forward-fill to prevent ghost notes at 440 Hz during rests
    last = midi_to_hz(60)
    for i in range(NSAMP):
        if freq_arr[i] > 0:
            last = freq_arr[i]
        else:
            freq_arr[i] = last
    return freq_arr, gate_arr, gain_arr

def humanize_notes(notes, timing_ms=10, vel_range=6):
    result = []
    jitter_samp = timing_ms / 1000.0
    for start, note_num, vel, dur in notes:
        t_jitter = rng.uniform(-jitter_samp, jitter_samp)
        v_jitter = rng.randint(-vel_range, vel_range + 1)
        result.append((max(0, start + t_jitter), note_num,
                        int(np.clip(vel + v_jitter, 1, 127)), dur))
    return result

def faust_render(dsp_string, freq_arr, gate_arr, gain_arr, vol=1.0):
    """Render a single FAUST voice using audio-rate automation. Returns (NSAMP, 2)."""
    engine = daw.RenderEngine(SR, 512)
    synth = engine.make_faust_processor('s')
    synth.set_dsp_string(dsp_string)
    ok = synth.compile()
    if not ok:
        raise RuntimeError('FAUST compile failed')
    synth.set_automation('/dawdreamer/freq', freq_arr)
    synth.set_automation('/dawdreamer/gate', gate_arr)
    synth.set_automation('/dawdreamer/gain', gain_arr)
    engine.load_graph([(synth, [])])
    engine.render(NSAMP / SR)
    audio = synth.get_audio()   # (2, NSAMP)
    return (audio.T * vol).astype(np.float32)

def separate_voices(notes):
    """Split polyphonic notes into mono voice lines (same as render5.py)."""
    groups = defaultdict(list)
    for n in notes:
        key = round(n[0] * 20) / 20
        groups[key].append(n)
    voices = [[], [], []]
    for key in sorted(groups):
        ch = sorted(groups[key], key=lambda x: x[1])
        for i, n in enumerate(ch[:3]):
            voices[i].append(n)
    return voices

# ─── FAUST DSP strings ──────────────────────────────────────────────────────

PAD_DSP = """
import("stdfaust.lib");
freq = hslider("freq[unit:Hz]", 440, 0.001, 20000, 0.001);
gain = hslider("gain", 1, 0, 1, 0.01);
gate = button("gate");
osc = (os.sawtooth(freq)
     + os.sawtooth(freq * 1.009)
     + os.sawtooth(freq * 0.991)
     + os.sawtooth(freq * 1.018)
     + os.sawtooth(freq * 0.982)) * 0.2;
env  = en.adsr(0.20, 0.30, 0.65, 1.5, gate);
lfo  = os.osc(0.08) * 0.5 + 0.5;
cutoff = 800.0 + lfo * 1200.0;
process = osc * env * gain * 0.40 : fi.lowpass(2, cutoff) <: _, _;
"""

LEAD_DSP = """
import("stdfaust.lib");
freq = hslider("freq[unit:Hz]", 440, 0.001, 20000, 0.001);
gain = hslider("gain", 1, 0, 1, 0.01);
gate = button("gate");
osc  = os.osc(freq) * 0.65 + os.triangle(freq) * 0.35;
env  = en.adsr(0.15, 0.25, 0.60, 1.2, gate);
process = osc * env * gain * 0.32 <: _, _;
"""

# ══════════════════════════════════════════════════════════════════════════════
# STEP 0 — Fix MIDI (strip duplicate tempo events)
# ══════════════════════════════════════════════════════════════════════════════
print('Step 0: Fixing MIDI …')
mid = mido.MidiFile(FULL_MID)
new_t0 = mido.MidiTrack()
seen_tempo = False
for msg in mid.tracks[0]:
    if msg.type == 'set_tempo':
        if not seen_tempo:
            new_t0.append(mido.MetaMessage('set_tempo', tempo=msg.tempo, time=0))
            seen_tempo = True
    else:
        new_t0.append(msg)
mid.tracks[0] = new_t0
mid.save(FIXED_MID)
print(f'  ✓  FIXED_MID saved  ({len(mid.tracks)} tracks)')

# ══════════════════════════════════════════════════════════════════════════════
# STEP 1 — Load Juicy Jules samples
# ══════════════════════════════════════════════════════════════════════════════
print('\nStep 1: Loading Juicy Jules samples …')
KICK     = load_sample(f'{INST}/☆ Kicks/Kick - Distorted.wav')
SNARE    = load_sample(f'{INST}/☆ Snares/Snare - Strike.wav')
CLAP     = load_sample(f'{INST}/☆ Claps/Clap - Layer.wav')
HH_CL    = load_sample(f'{INST}/☆ Closed Hats/HH - 1.wav')
HH_OP    = load_sample(f'{INST}/☆ Open Hats/OH - Long.wav')
CRASH    = load_sample(f'{INST}/☆ Crashes/Crash - Classic.wav')
LASER    = load_sample(f'{INST}/☆ FX/FX - Laser.wav')
UGH      = load_sample(f'{INST}/☆ FX/FX - Ugh.wav')
BASS_808 = load_sample(f'{INST}/☆ 808s/808 - Dark.wav')

# Pitch hi-hats down slightly for darker feel
HH_CL = pb.Pedalboard([pb.PitchShift(semitones=-2)])(HH_CL[np.newaxis, :], SR)[0]
HH_OP = pb.Pedalboard([pb.PitchShift(semitones=-1)])(HH_OP[np.newaxis, :], SR)[0]
print(f'  Kick={len(KICK)/SR:.2f}s  Snare={len(SNARE)/SR:.2f}s  808={len(BASS_808)/SR:.2f}s')

# ══════════════════════════════════════════════════════════════════════════════
# STEP 2 — Drums (real samples + pyroomacoustics room IR)
# ══════════════════════════════════════════════════════════════════════════════
print('\nStep 2: Building drum track + room acoustics …')

# Smaller, dryer room for rap (8% wet vs 15% in witch house)
room = pra.ShoeBox([3.0, 2.5, 2.2], fs=SR,
                   materials=pra.Material(0.45), max_order=3)
room.add_source([1.5, 1.25, 1.0])
room.add_microphone(np.array([[1.8, 1.5, 1.2]]).T)
room.compute_rir()
room_ir = np.array(room.rir[0][0], dtype=np.float32)
room_ir = room_ir[:int(SR * 0.18)]   # shorter reverb tail
room_ir /= (np.abs(room_ir).max() + 1e-9)
print(f'  Room IR: {len(room_ir)/SR*1000:.0f} ms')

drum_L   = np.zeros(NSAMP, dtype=np.float32)
drum_R   = np.zeros(NSAMP, dtype=np.float32)
kick_env = np.zeros(NSAMP, dtype=np.float32)

drum_events = parse_track(FIXED_MID, 1)
MAX_JITTER  = int(0.010 * SR)   # ±10 ms humanization
pan_toggle  = False

for sec, note_num, vel, _ in drum_events:
    base_start = int(sec * SR)
    if base_start >= NSAMP:
        continue
    g = vel / 127.0

    if note_num == 36:   # Kick — tight, no jitter
        snd = KICK * g
        e = min(base_start + len(snd), NSAMP)
        chunk = snd[:e - base_start]
        kick_env[base_start:e] += np.abs(chunk)
        drum_L[base_start:e]   += chunk * 0.95
        drum_R[base_start:e]   += chunk * 0.95

    elif note_num == 38:   # Snare (main vel=95-100 and ghost vel=30-35)
        jitter = rng.randint(-MAX_JITTER // 2, MAX_JITTER // 2 + 1)
        start  = int(np.clip(base_start + jitter, 0, NSAMP - 1))
        snd = SNARE * g * rng.uniform(0.93, 1.07)
        e   = min(start + len(snd), NSAMP)
        drum_L[start:e] += snd[:e - start] * 0.95
        drum_R[start:e] += snd[:e - start] * 0.95

    elif note_num == 39:   # Clap layer (only on main snare beats)
        snd = CLAP * g * rng.uniform(0.92, 1.08)
        e   = min(base_start + len(snd), NSAMP)
        drum_L[base_start:e] += snd[:e - base_start] * 0.85
        drum_R[base_start:e] += snd[:e - base_start] * 0.85

    elif note_num == 42:   # Closed HH — pan alternating
        pan_toggle = not pan_toggle
        jitter = rng.randint(-MAX_JITTER, MAX_JITTER + 1)
        start  = int(np.clip(base_start + jitter, 0, NSAMP - 1))
        v  = g * rng.uniform(0.70, 1.00)
        snd = HH_CL * v
        pr  = 0.62 if pan_toggle else 0.38
        e   = min(start + len(snd), NSAMP)
        ch  = snd[:e - start] * 0.55
        drum_L[start:e] += ch * (1 - pr) * 2
        drum_R[start:e] += ch * pr * 2

    elif note_num == 46:   # Open HH
        jitter = rng.randint(-MAX_JITTER // 2, MAX_JITTER // 2 + 1)
        start  = int(np.clip(base_start + jitter, 0, NSAMP - 1))
        v  = g * rng.uniform(0.70, 0.95)
        snd = HH_OP * v
        e   = min(start + len(snd), NSAMP)
        drum_L[start:e] += snd[:e - start] * 0.50
        drum_R[start:e] += snd[:e - start] * 0.50

    elif note_num == 49:   # Crash
        snd = CRASH * g * 0.65
        e   = min(base_start + len(snd), NSAMP)
        drum_L[base_start:e] += snd[:e - base_start] * 0.48
        drum_R[base_start:e] += snd[:e - base_start] * 0.52

# Apply room IR (8% wet — dryer than witch house)
dl_room = fftconvolve(drum_L, room_ir, mode='full')[:NSAMP]
dr_room = fftconvolve(drum_R, room_ir, mode='full')[:NSAMP]
drum_L = drum_L * 0.92 + dl_room * 0.08
drum_R = drum_R * 0.92 + dr_room * 0.08

drum_stereo = np.stack([drum_L, drum_R], axis=1)
drum_board = pb.Pedalboard([
    pb.Compressor(threshold_db=-12, ratio=4.0, attack_ms=3, release_ms=100),
    pb.Gain(gain_db=3.0),
    pb.Limiter(threshold_db=-1.0),
])
drum_stereo = apply_pb(drum_stereo, drum_board)
print(f'  ✓  {len(drum_events)} drum events, room IR applied (8% wet)')

# ══════════════════════════════════════════════════════════════════════════════
# STEP 3 — 808 Bass (C#2, hold-envelope, distortion)
# ══════════════════════════════════════════════════════════════════════════════
print('\nStep 3: Building 808 bass …')

# C#2 = Db2 = +13 semitones from 808-Dark.wav (tuned at C1)
# Same shift as Db chord in render5.py — empirically confirmed
board_808 = pb.Pedalboard([
    pb.PitchShift(semitones=13),
    pb.LowpassFilter(cutoff_frequency_hz=350),
    pb.Gain(gain_db=2.0),
])
pitched_808 = board_808(BASS_808[np.newaxis, :], SR)[0].astype(np.float32)
print(f'  808 C#2 (+13st): {len(pitched_808)/SR:.2f}s')

bass_L = np.zeros(NSAMP, dtype=np.float32)
bass_R = np.zeros(NSAMP, dtype=np.float32)


def place_808(bar, vel=0.88):
    """Place 808: main hit (3 beats, hold-envelope) + ghost at beat 2."""
    trim_main = int(BEAT * 3.0 * SR)
    if trim_main > len(pitched_808):
        s_main = np.pad(pitched_808, (0, trim_main - len(pitched_808)))
    else:
        s_main = pitched_808[:trim_main].copy()
    # 20ms fade-out to avoid click (hold-envelope style — abrupt cut)
    fade_n = max(1, int(SR * 0.020))
    s_main[-fade_n:] *= np.linspace(1, 0, len(s_main[-fade_n:]))

    pos = int(bar * BAR * SR)
    e   = min(pos + len(s_main), NSAMP)
    ch  = s_main[:e - pos] * vel
    bass_L[pos:e] += ch * 0.95
    bass_R[pos:e] += ch * 0.95

    # Ghost hit at beat 2
    ghost_trim = int(BEAT * 0.75 * SR)
    ghost = pitched_808[:min(ghost_trim, len(pitched_808))] * vel * 0.38
    pos2  = pos + int(2 * BEAT * SR)
    e2    = min(pos2 + len(ghost), NSAMP)
    if pos2 < NSAMP:
        bass_L[pos2:e2] += ghost[:e2 - pos2] * 0.95
        bass_R[pos2:e2] += ghost[:e2 - pos2] * 0.95


for bar in range(4, 8):   place_808(bar, vel=0.48)   # Pre-Drop quiet
for bar in range(8, 40):  place_808(bar, vel=0.88)   # Drop A
for bar in range(48, 60): place_808(bar, vel=0.88)   # Drop A Return
for i, bar in enumerate(range(60, 63)):
    place_808(bar, vel=max(0.14, 0.80 - i * 0.26))   # Outro fade

bass_stereo = np.stack([bass_L, bass_R], axis=1)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 4 — Sidechain (kick → bass)
# ══════════════════════════════════════════════════════════════════════════════
print('\nStep 4: Sidechain + 808 distortion …')
smooth  = int(SR * 0.010)
sc_env  = np.convolve(kick_env, np.ones(smooth) / smooth, mode='same')
sc_env /= sc_env.max() + 1e-9
sc_gain = np.clip(1.0 - sc_env * 0.65, 0.35, 1.0)
bass_stereo[:, 0] *= sc_gain
bass_stereo[:, 1] *= sc_gain

bass_board = pb.Pedalboard([
    pb.HighpassFilter(cutoff_frequency_hz=35),
    pb.LowpassFilter(cutoff_frequency_hz=280),
    pb.Distortion(drive_db=6.0),   # 808 grit — hard and aggressive
    pb.Compressor(threshold_db=-10, ratio=3.5, attack_ms=5, release_ms=150),
    pb.Gain(gain_db=4.0),
    pb.Limiter(threshold_db=-2.0),
])
bass_stereo = apply_pb(bass_stereo, bass_board)
print('  ✓  Bass sidechained + distorted')

# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — Synthesize PADS with dawdreamer FAUST (3-voice C# minor)
# ══════════════════════════════════════════════════════════════════════════════
print('\nStep 5: Synthesizing PADS with FAUST …')
chord_notes = parse_track(FIXED_MID, 3)
voices      = separate_voices(chord_notes)

pad_buf = np.zeros((NSAMP, 2), dtype=np.float32)
for vi, voice in enumerate(voices):
    if not voice:
        continue
    freq_a, gate_a, gain_a = make_automation(voice)
    audio = faust_render(PAD_DSP, freq_a, gate_a, gain_a, vol=0.70)
    pad_buf += audio[:NSAMP]
    print(f'  Voice {vi+1}: {len(voice)} notes  max={np.abs(audio).max():.3f}')

# Gentle sidechain on pads
pad_buf[:, 0] *= (sc_gain * 0.25 + 0.75)
pad_buf[:, 1] *= (sc_gain * 0.25 + 0.75)

pad_board = pb.Pedalboard([
    pb.Reverb(room_size=0.60, damping=0.55, wet_level=0.30, dry_level=0.90, width=0.90),
    pb.LowpassFilter(cutoff_frequency_hz=11000),
    pb.Compressor(threshold_db=-18, ratio=2.5, attack_ms=30, release_ms=400),
    pb.Gain(gain_db=1.0),
])
pad_buf = apply_pb(pad_buf, pad_board)
print(f'  ✓  Pads rendered  max={np.abs(pad_buf).max():.3f}')

# ══════════════════════════════════════════════════════════════════════════════
# STEP 6 — Synthesize LEAD MELODY + COUNTER with dawdreamer FAUST
# ══════════════════════════════════════════════════════════════════════════════
print('\nStep 6: Synthesizing LEAD MELODY + COUNTER with FAUST …')
mel_notes     = parse_track(FIXED_MID, 4)
counter_notes = parse_track(FIXED_MID, 5)
all_mel = humanize_notes(
    sorted(mel_notes + counter_notes, key=lambda x: x[0]),
    timing_ms=10, vel_range=6)

freq_a, gate_a, gain_a = make_automation(all_mel)
lead_buf = faust_render(LEAD_DSP, freq_a, gate_a, gain_a, vol=0.55)[:NSAMP]

lead_board = pb.Pedalboard([
    pb.Reverb(room_size=0.45, damping=0.65, wet_level=0.20, dry_level=0.95, width=0.80),
    pb.LowpassFilter(cutoff_frequency_hz=9000),
    pb.Compressor(threshold_db=-16, ratio=2.5, attack_ms=10, release_ms=200),
    pb.Gain(gain_db=1.5),
])
lead_buf = apply_pb(lead_buf, lead_board)
print(f'  ✓  Lead rendered  notes={len(all_mel)}  max={np.abs(lead_buf).max():.3f}')

# ══════════════════════════════════════════════════════════════════════════════
# STEP 7 — Laser perc + Vocal chop (FX-Ugh -6st)
# ══════════════════════════════════════════════════════════════════════════════
print('\nStep 7: Laser perc + vocal chops …')
atmos_L = np.zeros(NSAMP, dtype=np.float32)
atmos_R = np.zeros(NSAMP, dtype=np.float32)
vocal_L = np.zeros(NSAMP, dtype=np.float32)
vocal_R = np.zeros(NSAMP, dtype=np.float32)

# Laser perc processed
laser_board = pb.Pedalboard([
    pb.Reverb(room_size=0.35, wet_level=0.20, dry_level=0.90),
    pb.Gain(gain_db=-3.0),
])
laser_proc = laser_board(LASER[np.newaxis, :], SR)[0].astype(np.float32)

# Place at drop entries and 8-bar accent points
for drop_bar in [8, 16, 24, 32, 48, 56]:
    s = int(drop_bar * BAR * SR)
    e = min(s + len(laser_proc), NSAMP)
    chunk = laser_proc[:e - s] * 0.40
    atmos_L[s:e] += chunk * 0.55
    atmos_R[s:e] += chunk * 0.45

# Vocal chop: FX-Ugh.wav pitched -6 semitones
ugh_board = pb.Pedalboard([
    pb.PitchShift(semitones=-6),
    pb.Reverb(room_size=0.70, damping=0.55, wet_level=0.50, dry_level=0.60, width=1.0),
    pb.Distortion(drive_db=4.0),
    pb.LowpassFilter(cutoff_frequency_hz=6000),
    pb.Gain(gain_db=2.0),
])
ugh_proc = ugh_board(UGH[np.newaxis, :], SR)[0].astype(np.float32)
peak     = np.abs(ugh_proc).max()
ugh_proc = (ugh_proc / (peak + 1e-9) * 0.28).astype(np.float32)

# Place at drop entries + accent points
vox_placements = [(8, -0.35), (20, 0.30), (32, -0.20), (48, -0.30), (56, 0.25)]
for vox_bar, pan in vox_placements:
    s  = int(vox_bar * BAR * SR)
    e  = min(s + len(ugh_proc), NSAMP)
    ch = ugh_proc[:e - s]
    pr = (pan + 1.0) / 2.0
    vocal_L[s:e] += ch * (1 - pr) * 2
    vocal_R[s:e] += ch * pr * 2

print(f'  ✓  Laser percs ({len([8,16,24,32,48,56])} placements) + vocal chops ({len(vox_placements)} placements)')

# ══════════════════════════════════════════════════════════════════════════════
# STEP 8 — Final mix
# ══════════════════════════════════════════════════════════════════════════════
print('\nStep 8: Final mix …')
atmos_stereo = np.stack([atmos_L, atmos_R], axis=1)
vocal_stereo = np.stack([vocal_L, vocal_R], axis=1)

mix = (drum_stereo   * 0.85 +
       bass_stereo   * 0.82 +
       pad_buf       * 0.65 +
       lead_buf      * 0.45 +
       vocal_stereo  * 0.88 +
       atmos_stereo  * 0.80)

# ══════════════════════════════════════════════════════════════════════════════
# STEP 9 — Master chain (SOFT CLIPPER is the EsDeeKid signature)
# All 3 tutorials explicitly named this as critical.
# "Without the soft clipper, it wouldn't sound distorted at all — just hard clipped."
# ══════════════════════════════════════════════════════════════════════════════
print('Step 9: Master chain (soft clipper) …')
master_board = pb.Pedalboard([
    pb.HighpassFilter(cutoff_frequency_hz=30),
    pb.LowpassFilter(cutoff_frequency_hz=18000),
    pb.Compressor(threshold_db=-10, ratio=2.0, attack_ms=20, release_ms=250),
    pb.Distortion(drive_db=8.0),   # SOFT CLIPPER — critical EsDeeKid signature
    pb.Gain(gain_db=2.0),
    pb.Limiter(threshold_db=-0.5),
])
mix = apply_pb(mix, master_board)
trim = int((SONG + 2.0) * SR)
mix  = mix[:trim]

# ══════════════════════════════════════════════════════════════════════════════
# STEP 10 — Export WAV + MP3
# ══════════════════════════════════════════════════════════════════════════════
print('Step 10: Exporting …')
out_i16 = (mix * 32767).clip(-32767, 32767).astype(np.int16)
wavfile.write(OUT_WAV, SR, out_i16)
print(f'  ✓  WAV: {os.path.getsize(OUT_WAV)/1e6:.1f} MB')

seg = AudioSegment.from_wav(OUT_WAV)
seg.export(OUT_MP3, format='mp3', bitrate='192k', tags={
    'title':  'Dirty Phantom',
    'artist': 'Claude Code',
    'album':  'EsDeeKid Type Beat',
    'genre':  'Jerk / Underground Rap',
})
m, s = divmod(int(len(seg) / 1000), 60)
print(f'  ✓  MP3: {os.path.getsize(OUT_MP3)/1e6:.1f} MB  |  {m}:{s:02d}')
print('\nDone!')
