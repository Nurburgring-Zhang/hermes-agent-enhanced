---
name: music-production
description: "AI music production pipeline — songwriting craft, AI generation (HeartMuLa/Suno), audio visualization and analysis. Umbrella for songwriting, heartmula, and songsee."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [music, audio, generation, analysis, songwriting, suno, heartmula, visualization, creative]
---

# Music Production Pipeline

AI-powered music creation, analysis, and visualization. This umbrella covers the full pipeline: from songwriting and lyric crafting through AI music generation to audio analysis and spectrogram visualization.

## Skill Structure

This umbrella absorbed 3 narrow skills as labeled subsections:

| Former Skill | Section | Support File |
|---|---|---|
| `songwriting-and-ai-music` | [Section 1: Songwriting & AI Music Prompts](#1-songwriting--ai-music-prompts) | — |
| `heartmula` | [Section 2: HeartMuLa Open-Source Music Generation](#2-heartmula-open-source-music-generation) | — |
| `songsee` | [Section 3: Audio Spectrogram & Feature Visualization](#3-audio-spectrogram--feature-visualization) | `references/audio-visualization.md` |

## 1. Songwriting & AI Music Prompts

### Song Structure (Pick One or Invent Your Own)

Common skeletons — mix, modify, or throw out as needed:

```
ABABCB  Verse/Chorus/Verse/Chorus/Bridge/Chorus    (most pop/rock)
AABA    Verse/Verse/Bridge/Verse (refrain-based)    (jazz standards, ballads)
ABAB    Verse/Chorus alternating                    (simple, direct)
AAA     Verse/Verse/Verse (strophic, no chorus)     (folk, storytelling)
```

The six building blocks:
- **Intro** — set the mood, pull the listener in
- **Verse** — the story, the details, the world-building
- **Pre-Chorus** — optional tension ramp before the payoff
- **Chorus** — the emotional core, the part people remember
- **Bridge** — a detour, a shift in perspective or key
- **Outro** — the farewell, can echo or subvert the rest

### Rhyme, Meter, and Sound

**Rhyme types** (tight to loose): Perfect (lean/mean), Family (crate/braid), Assonance (had/glass), Consonance (scene/when), Near/slant.

Mix them. All perfect rhymes sound like a nursery rhyme; all slant rhymes sound lazy.

**Internal rhyme**: Rhyming within a line, not just at ends.
**Meter**: Stressed syllables matter more than total count. Say it out loud.

### Emotional Arc and Dynamics

Think of a song as a journey:
- Intro: 2-3 | Verse: 5-6 | Pre-Chorus: 7 | Chorus: 8-9 | Bridge: varies
- **Contrast** is the most powerful trick: whisper before a scream, sparse before dense.
- **Silence is an instrument.**

### Writing Lyrics That Work

- **Show, don't tell**: "Your hoodie's still on the hook by the door" > "I was sad"
- **The hook**: The line people remember — usually the title or core phrase
- **Prosody**: Stable feelings ↔ resolved chords, perfect rhymes; Unstable feelings ↔ wandering melodies, near-rhymes

### Parody and Adaptation

1. Map original structure (syllables, rhyme scheme, stressed syllables)
2. Match stressed syllables to same beats
3. On long held notes, match the VOWEL SOUND of the original
4. **Monosyllabic swaps** in key spots keep rhythm intact
5. **Keep some originals** for recognizability

### Suno AI Prompt Engineering

**Style/Genre Formula**: Genre + Mood + Era + Instruments + Vocal Style + Production + Dynamics

Bad: "sad rock song"
Good: "Cinematic orchestral spy thriller, 1960s Cold War era, smoky sultry female vocalist, big band jazz..."

**Describe the journey**, not just the genre:
```
"Begins as a haunting whisper over sparse piano. Gradually layers in muted brass. Builds through the chorus with full orchestra. Second verse erupts with raw belting intensity. Outro strips back to a lone piano and a fragile whisper fading to silence."
```

**Tips**:
- V4.5+ supports up to 1,000 chars in Style field — use them
- NO artist names or trademarks. Describe the sound instead.
- Specify BPM and key when you have a preference
- Unexpected genre combos: "bossa nova trap", "Appalachian gothic", "chiptune jazz"

**Metatags** (place in [brackets] inside lyrics field):

Structure: `[Intro] [Verse] [Pre-Chorus] [Chorus] [Bridge] [Outro] [Instrumental] [Guitar Solo]`
Vocal: `[Whispered] [Spoken Word] [Belted] [Falsetto] [Powerful] [Soulful] [Raspy] [Breathy]`
Dynamics: `[High Energy] [Building Energy] [Emotional Climax] [Gradual swell]`
Atmosphere: `[Melancholic] [Euphoric] [Nostalgic] [Aggressive] [Dreamy]`

**Phonetic tricks for AI singers**:
- Spell words as they SOUND: "through" → "thru"
- Hyphenate to guide syllables: "Re-search", "bio-engineering"
- ALL CAPS = louder, more intense
- Vowel extension: "lo-o-o-ove" = sustained/melisma
- Spell out numbers: "24/7" → "twenty four seven"
- Space acronyms: "AI" → "A I" or "A-I"

## 2. HeartMuLa Open-Source Music Generation

HeartMuLa is a family of open-source music foundation models (Apache-2.0) that generates music conditioned on lyrics and tags, with multilingual support. Comparable to Suno for open-source.

### Hardware Requirements
- **Minimum**: 8GB VRAM with `--lazy_load true`
- **Recommended**: 16GB+ VRAM
- 3B model with lazy_load peaks at ~6.2GB VRAM

### Quick Install
```bash
git clone https://github.com/HeartMuLa/heartlib.git
cd heartlib
uv venv --python 3.10 .venv
. .venv/bin/activate
uv pip install -e .
uv pip install --upgrade datasets transformers
```

### Download Checkpoints
```bash
hf download --local-dir './ckpt' 'HeartMuLa/HeartMuLaGen'
hf download --local-dir './ckpt/HeartMuLa-oss-3B' 'HeartMuLa/HeartMuLa-oss-3B-happy-new-year'
hf download --local-dir './ckpt/HeartCodec-oss' 'HeartMuLa/HeartCodec-oss-20260123'
```

### Basic Generation
```bash
cd heartlib && . .venv/bin/activate
python ./examples/run_music_generation.py \
  --model_path=./ckpt --version="3B" \
  --lyrics="./assets/lyrics.txt" \
  --tags="./assets/tags.txt" \
  --save_path="./assets/output.mp3" \
  --lazy_load true
```

**Tags** (comma-separated, no spaces): `piano,happy,wedding,synthesizer,romantic`
**Lyrics** (use bracketed structural tags): `[Intro] [Verse] [Chorus] [Bridge] [Outro]`

### Source Patches Required (Feb 2026+)
1. **RoPE cache fix** in `src/heartlib/heartmula/modeling_heartmula.py` — add `Llama3ScaledRoPE` reinit after `reset_caches`
2. **HeartCodec loading fix** in `src/heartlib/pipelines/music_generation.py` — add `ignore_mismatched_sizes=True` to all `HeartCodec.from_pretrained()` calls

### Key Parameters
| Parameter | Default | Description |
|---|---|---|
| `--max_audio_length_ms` | 240000 | Max length in ms |
| `--topk` | 50 | Top-k sampling |
| `--temperature` | 1.0 | Sampling temperature |
| `--cfg_scale` | 1.5 | Classifier-free guidance scale |

### Pitfalls
- **Do NOT use bf16 for HeartCodec** — degrades quality. Use fp32.
- Tags may be ignored by model — lyrics dominate.
- No GPU? CPU mode takes 30-60+ min per song.
- RTX 5080 incompatibility reported upstream.

## 3. Audio Spectrogram & Feature Visualization

Generate spectrograms and multi-panel audio feature visualizations from audio files using `songsee`.

### Install
```bash
go install github.com/steipete/songsee/cmd/songsee@latest
```

### Quick Start
```bash
songsee track.mp3
songsee track.mp3 -o spectrogram.png
songsee track.mp3 --viz spectrogram,mel,chroma,hpss,selfsim,loudness,tempogram,mfcc,flux
songsee track.mp3 --start 12.5 --duration 8 -o slice.jpg
```

### Visualization Types
| Type | Description |
|---|---|
| `spectrogram` | Standard frequency spectrogram |
| `mel` | Mel-scaled spectrogram |
| `chroma` | Pitch class distribution |
| `hpss` | Harmonic/percussive separation |
| `selfsim` | Self-similarity matrix |
| `loudness` | Loudness over time |
| `tempogram` | Tempo estimation |
| `mfcc` | Mel-frequency cepstral coefficients |
| `flux` | Spectral flux (onset detection) |

## 4. GIF Search (Tenor API — for reaction/vibe content)

Search and download GIFs via the Tenor API using curl + jq. Useful for finding reaction GIFs for music/creative content.

### Setup
```bash
export TENOR_API_KEY="your_key_here"
```
Get a free API key at https://developers.google.com/tenor/guides/quickstart

### Search
```bash
curl -s "https://tenor.googleapis.com/v2/search?q=thumbs+up&limit=5&key=${TENOR_API_KEY}" | jq -r '.results[].media_formats.gif.url'
```
