# Dirty Phantom 🖤

A fully programmatic **EsDeeKid / jerk-style rap beat** generated in Python using music21, dawdreamer (FAUST synthesis), real Juicy Jules drum samples, and a pedalboard effects chain.

**Key:** C# minor | **BPM:** 140 | **Length:** ~1:51

---

## Research

### YouTube Tutorial Transcripts

Transcripts were fetched from three EsDeeKid production tutorials using `mcp__youtube-transcript`. Key takeaways that directly shaped the arrangement:

| Video | Key Insights Applied |
|-------|---------------------|
| [How to EsDeeKid beat](https://www.youtube.com/watch?v=2J8yekfFe0Q) | 140–190 BPM range, dark synth melody, LFO volume automation, parametric EQ 40 Hz cut on melody to make room for 808 |
| [INSANE Underground Beats For EsDeeKid](https://www.youtube.com/watch?v=UmQP6uH7kRU) | A# minor scale, jerk drums (different from trap), snare velocity variation = the bounce, counter melody on root/fifth note, 808 one note the whole song, soft clipper on master CRITICAL |
| [ESDEEKID Type Beats on FL Studio](https://www.youtube.com/watch?v=1wKQ27xH618) | Semitone-apart chord pairs for tension, morph pad LFO glitch texture, snare + clap + open hat + hi-hat roll pattern, 808 hold-envelope (everything off except hold knob), soft clipper explained in depth |

### Reference Track Audio Analysis (`mcp__music-analysis`)

Actual EsDeeKid tracks were downloaded and analyzed — not relying on tutorial narration alone:

| Track | Views | Dominant Chroma (avg amplitude) | Librosa BPM | Key Confirmed |
|-------|-------|----------------------------------|-------------|---------------|
| Phantom | 21M | **C#=0.844** >> C=0.490 >> D#=0.204 >> G#=0.201 | 143.5 | **C# minor** |
| 4 Raws Remix | 11M | **D=0.762** >> C#=0.544 >> D#=0.347 | 143.5 | Eb minor area |

**BPM insight:** All tutorials say 190 BPM (FL Studio grid setting). Librosa beat_track measures **143.5** on both tracks. The relationship: `190 × 3/4 = 142.5 ≈ 143.5` — the jerk pattern's ghost snares between main hits create a 3/4 sub-pulse that librosa detects as the dominant tempo. We use **140 BPM** (clean value near the empirical 143.5).

**Key insight:** Tutorials recommend A#/Bb minor. Phantom's chroma shows C# dominating at 0.844 — nearly 2× the next strongest note. **C# minor is empirically confirmed** as Phantom's key. C#2 (69.3 Hz) also gives the classic heavy 808 root.

---

## Song Structure

| Bars | Section | Description |
|------|---------|-------------|
| 1–4 | Intro | Detuned-saw pads only |
| 5–8 | Pre-Drop | 808 enters quietly + snare roll buildup |
| 9–40 | Drop A | Full: jerk drums + 808 + melody loop + counter melody |
| 41–48 | Break | Sparse hi-hat (beats 1+3) + pads only |
| 49–60 | Drop A Return | Full arrangement |
| 61–64 | Outro | Fade out |

**Melody loop (2 bars, repeats):** E4→D#4 (semitone tension) →C#4 / G#4→F#4→E4

---

## Signal Chain

```
compose_rap.py  →  DirtyPhantom_FULL.mid
                        │
                        ▼
                render_rap.py
                ├── Drums
                │   ├── Juicy Jules WAV samples (Kick-Distorted / Snare-Strike / Clap-Layer / HH / Crash)
                │   ├── pyroomacoustics room IR (3.0×2.5×2.2 m, 8% wet — dryer than witch house)
                │   ├── Ghost-snare velocity variation (vel 30–35 vs vel 95–100) = the jerk bounce
                │   ├── Clap layer (note 39) only on main snare hits
                │   ├── ±10 ms humanization jitter on hats/snares
                │   └── Drum bus: Compressor → Gain → Limiter
                │
                ├── 808 Bass
                │   ├── 808-Dark.wav → PitchShift +13st → C#2 (69.3 Hz)
                │   ├── Hold-envelope: 3-beat trim, 20ms fade-out (no natural decay)
                │   ├── Ghost hit at beat 2 (vel × 0.38)
                │   ├── Sidechain ducked −65% by kick envelope
                │   └── Bass bus: Distortion(6dB) → Compressor → Limiter
                │
                ├── Pads  (dawdreamer FAUST — 3-voice detuned saws)
                │   ├── C# minor chord: C#3, E3, G#3 (3 separate voice renders)
                │   ├── 5-oscillator unison (±0.9%, ±1.8% detune)
                │   ├── Slow LFO on filter cutoff (0.08 Hz, 800–2000 Hz)
                │   ├── ADSR: 0.20s attack / 1.5s release (snappier than witch house)
                │   └── Reverb (room=0.60) → LPF → Compressor
                │
                ├── Lead Melody + Counter  (dawdreamer FAUST — saw+square)
                │   ├── Melody: E4→D#4→C#4 / G#4→F#4→E4 (2-bar loop)
                │   ├── Counter: C#3 staccato root pulse (beat 0 + beat 2)
                │   ├── ±10 ms timing humanization + ±6 velocity humanization
                │   └── Reverb → LPF → Compressor
                │
                ├── Laser Perc
                │   ├── FX-Laser.wav + Reverb
                │   └── Placed at bars 8, 16, 24, 32, 48, 56
                │
                └── Vocal Chop
                    ├── FX-Ugh.wav → PitchShift −6st + Reverb + Distortion
                    └── Placed at bars 8, 20, 32, 48, 56 (panned L/R alternating)

Master chain: HPF(30Hz) → LPF(18kHz) → Compressor →
              Distortion(8dB SOFT CLIPPER) → Gain → Limiter(−0.5dB)
```

**The soft clipper is critical** — all 3 tutorials named it explicitly. Without it the 808 sounds hard-clipped instead of warmly saturated. No Bitcrush or Chorus (those are witch house, not EsDeeKid).

---

## How to Replicate

### 1. System dependencies

```bash
brew install fluid-synth ffmpeg
```

### 2. Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Drum sample kit

Update `INST` in `render_rap.py` to your Juicy Jules – Stardust path:

```python
INST = '/path/to/☆ Juicy Jules - Stardust ☆/☆ Juicy Jules - Stardust ☆'
```

Samples used:
- `☆ Kicks/Kick - Distorted.wav`
- `☆ Snares/Snare - Strike.wav`
- `☆ Claps/Clap - Layer.wav`
- `☆ Closed Hats/HH - 1.wav`
- `☆ Open Hats/OH - Long.wav`
- `☆ Crashes/Crash - Classic.wav`
- `☆ FX/FX - Laser.wav`
- `☆ FX/FX - Ugh.wav`
- `☆ 808s/808 - Dark.wav`

### 4. Generate MIDI stems

```bash
python compose_rap.py
```

### 5. Render to WAV + MP3

```bash
python render_rap.py
```

Outputs `DirtyPhantom.wav` (44.1 kHz 16-bit stereo) and `DirtyPhantom.mp3` (192 kbps, ~1:51).

---

## Key Settings

```python
BPM   = 140              # empirical: librosa measures 143.5 on actual Phantom track
KEY   = 'C# minor'       # empirical: C# chroma = 0.844 in Phantom (confirmed vs tutorial claim of A# minor)
BARS  = 64               # ~1:51 at 140 BPM (matches Phantom's 111s runtime)
SR    = 44100

# Jerk bounce: ghost snares between main hits
MAIN_SNARE_VEL  = 95–100   # loud
GHOST_SNARE_VEL = 30–35    # quiet — velocity gap creates the bounce

# 808 hold-envelope
trim_main  = BEAT * 3.0    # 3 beats, then cut (no natural decay)
ghost_vel  = vel * 0.38    # ghost hit at beat 2

# 808 pitch
semitone_shift = +13       # C#2 = Db2 (same as Db chord in Shadow Ritual render5.py)

# Soft clipper (master — CRITICAL)
drive_db = 8.0             # pb.Distortion(drive_db=8.0)
```

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `music21` | MIDI composition (notes, chords, structure) |
| `mido` | MIDI post-processing (program change, channel routing) |
| `dawdreamer` | FAUST DSP synthesis (pads, lead) |
| `pedalboard` | Effects (PitchShift, Distortion, Reverb, Compressor, Limiter) |
| `pyroomacoustics` | Room impulse response for drum acoustics |
| `soundfile` | WAV sample loading |
| `scipy` | Signal processing (filters, resampling) |
| `pydub` | MP3 export |
| `numpy` | Audio buffer arithmetic |
