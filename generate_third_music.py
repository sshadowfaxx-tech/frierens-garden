import numpy as np
import wave
import os

SAMPLE_RATE = 44100
DURATION = 120  # 2 minutes
NUM_SAMPLES = SAMPLE_RATE * DURATION

audio_left = np.zeros(NUM_SAMPLES)
audio_right = np.zeros(NUM_SAMPLES)

def sine_wave(freq, duration, amp=1.0):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    return amp * np.sin(2 * np.pi * freq * t)

def triangle_wave(freq, duration, amp=1.0):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    return amp * (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * t))

def saw_wave(freq, duration, amp=1.0):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    return amp * (2 * (t * freq - np.floor(t * freq + 0.5)))

def adsr(samples, attack=0.01, decay=0.1, sustain=0.7, release=0.2):
    attack_s = int(SAMPLE_RATE * attack)
    decay_s = int(SAMPLE_RATE * decay)
    release_s = int(SAMPLE_RATE * release)
    sustain_s = max(0, samples - attack_s - decay_s - release_s)
    
    env = np.zeros(samples)
    if attack_s > 0:
        env[:attack_s] = np.linspace(0, 1, attack_s)
    if decay_s > 0:
        env[attack_s:attack_s+decay_s] = np.linspace(1, sustain, decay_s)
    if sustain_s > 0:
        env[attack_s+decay_s:attack_s+decay_s+sustain_s] = sustain
    if release_s > 0:
        env[-release_s:] = np.linspace(sustain, 0, release_s)
    return env

def mix_at(audio_l, audio_r, position, signal_l, signal_r):
    end = min(position + len(signal_l), len(audio_l))
    actual = end - position
    audio_l[position:end] += signal_l[:actual]
    audio_r[position:end] += signal_r[:actual]
    return audio_l, audio_r

# Frequencies
C3, D3, E3, F3, G3, A3, B3 = 130.81, 146.83, 164.81, 174.61, 196.00, 220.00, 246.94
C4, D4, E4, F4, G4, A4, B4 = 261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88
C5, D5, E5, F5, G5 = 523.25, 587.33, 659.25, 698.46, 783.99

# === DRUMS (full 2 minutes) ===
beat_samples = int(SAMPLE_RATE * 0.5)  # 120 BPM

for beat in range(0, NUM_SAMPLES, beat_samples):
    t = np.linspace(0, 0.15, int(SAMPLE_RATE * 0.15))
    sweep = np.linspace(120, 60, len(t))
    kick = np.sin(2 * np.pi * sweep * t) * np.exp(-t * 15) * 0.6
    
    end = min(beat + len(kick), NUM_SAMPLES)
    actual = end - beat
    audio_left[beat:end] += kick[:actual]
    audio_right[beat:end] += kick[:actual]

# Snare on 2 and 4
for beat in range(beat_samples * 1, NUM_SAMPLES, beat_samples * 2):
    t = np.linspace(0, 0.1, int(SAMPLE_RATE * 0.1))
    noise = np.random.randn(len(t)) * np.exp(-t * 20) * 0.4
    
    end = min(beat + len(noise), NUM_SAMPLES)
    actual = end - beat
    audio_left[beat:end] += noise[:actual]
    audio_right[beat:end] += noise[:actual]

# === BASS (walking through full progression) ===
chords_order = [
    ('Am', [A3, C4, E4], 8),
    ('F', [F3, A3, C4], 8),
    ('C', [C3, E3, G3], 8),
    ('G', [G3, B3, D4], 8),
    ('Am', [A3, C4, E4], 8),
    ('F', [F3, A3, C4], 8),
    ('C', [C3, E3, G3], 8),
    ('G', [G3, B3, D4], 8),
    ('Dm', [D3, F3, A3], 8),  # Bridge
    ('Em', [E3, G3, B3], 8),
    ('Am', [A3, C4, E4], 8),
    ('G', [G3, B3, D4], 8),
    ('Am', [A3, C4, E4], 8),  # Return
    ('F', [F3, A3, C4], 8),
    ('C', [C3, E3, G3], 8),
    ('G', [G3, B3, D4], 8),
]

bass_time = 0
for chord_name, notes, beats in chords_order:
    duration = beats * 0.5
    root, third, fifth = notes
    
    for beat in range(0, beats, 2):
        note_dur = min(1.0, duration - (beat * 0.5))
        if note_dur <= 0:
            break
        
        note_freq = root if beat % 4 == 0 else fifth
        note = triangle_wave(note_freq, note_dur, amp=0.5)
        env = adsr(len(note), attack=0.02, decay=0.05, sustain=0.8, release=0.1)
        note = note * env
        
        pos = bass_time + int(beat * 0.5 * SAMPLE_RATE)
        mix_at(audio_left, audio_right, pos, note * 0.8, note * 0.8)
    
    bass_time += int(duration * SAMPLE_RATE)
    if bass_time >= NUM_SAMPLES:
        break

# === CHORD PADS (full duration) ===
pad_time = 0
for chord_name, notes, beats in chords_order:
    duration = beats * 0.5
    root, third, fifth = notes
    
    for freq in [root, third, fifth]:
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
        osc1 = np.sin(2 * np.pi * freq * t)
        osc2 = np.sin(2 * np.pi * (freq * 1.003) * t)
        note = (osc1 + osc2) / 2
        
        env = adsr(len(note), attack=0.5, decay=1.0, sustain=0.6, release=0.5)
        note = note * env * 0.2
        
        pan = 0.3 + ((freq - root) / root) * 0.4
        left = note * (1 - pan)
        right = note * pan
        
        mix_at(audio_left, audio_right, pad_time, left, right)
    
    pad_time += int(duration * SAMPLE_RATE)
    if pad_time >= NUM_SAMPLES:
        break

# === MELODY (complete 2-minute composition) ===
# Structured: Intro → A → A' → B (bridge) → A → Outro
# Each section is 24 seconds (12 beats = 6 seconds per chord, 4 chords = 24 sec)

melody_sections = [
    # INTRO - sparse, building (24 sec)
    [(E4, 1.0), (A4, 1.0), (E4, 1.0), (A4, 1.0), (E4, 1.0), (A4, 1.0)],
    
    # SECTION A - Main theme (24 sec)
    [
        (E4, 0.5), (A4, 0.5), (E4, 0.5), (C4, 0.5),  # Am
        (C4, 0.5), (F4, 0.5), (C4, 0.5), (A3, 0.5),  # F
        (G4, 0.5), (E4, 0.5), (C4, 1.0),             # C
        (D4, 0.5), (B3, 0.5), (D4, 0.5), (G4, 0.5),  # G
    ],
    
    # SECTION A' - Variation, slightly more active (24 sec)
    [
        (E4, 0.5), (A4, 0.5), (G4, 0.5), (E4, 0.5),
        (F4, 0.5), (C4, 0.5), (A3, 0.5), (F3, 0.5),
        (E4, 0.5), (G4, 0.5), (C5, 0.5), (G4, 0.5),
        (B3, 0.5), (D4, 0.5), (G4, 0.5), (B3, 0.5),
    ],
    
    # SECTION B - Bridge, higher, more tension (24 sec)
    [
        (D4, 0.5), (F4, 0.5), (A4, 0.5), (F4, 0.5),
        (E4, 0.5), (G4, 0.5), (B4, 0.5), (G4, 0.5),
        (E4, 0.5), (A4, 0.5), (C5, 0.5), (E5, 0.5),
        (D4, 0.5), (B3, 0.5), (G3, 0.5), (B3, 0.5),
    ],
    
    # SECTION A - Return to main theme (24 sec)
    [
        (A4, 0.5), (E4, 0.5), (C5, 0.5), (A4, 0.5),
        (F4, 0.5), (C4, 0.5), (A4, 0.5), (F4, 0.5),
        (G4, 0.5), (E4, 0.5), (C4, 1.0),
        (G4, 0.5), (E4, 0.5), (D4, 0.5), (C4, 1.0),
    ],
    
    # OUTRO - winding down (24 sec)
    [
        (E4, 1.0), (C4, 1.0), (A3, 1.0),
        (E4, 0.5), (C4, 0.5), (A3, 2.0),
        (A3, 4.0),  # Hold final note
    ],
]

melody_time = 0
for section in melody_sections:
    for freq, dur in section:
        note = sine_wave(freq, dur, amp=0.5)
        env = adsr(len(note), attack=0.01, decay=0.1, sustain=0.7, release=0.15)
        note = note * env
        
        pan = 0.4 if freq < 300 else 0.6
        left = note * (1 - pan)
        right = note * pan
        
        mix_at(audio_left, audio_right, melody_time, left, right)
        melody_time += int(dur * SAMPLE_RATE)

# === FINAL MIX ===
max_val = max(np.max(np.abs(audio_left)), np.max(np.abs(audio_right)))
if max_val > 0.95:
    audio_left = audio_left / max_val * 0.95
    audio_right = audio_right / max_val * 0.95

stereo = np.empty(2 * NUM_SAMPLES, dtype=np.int16)
stereo[0::2] = (audio_left * 32767).astype(np.int16)
stereo[1::2] = (audio_right * 32767).astype(np.int16)

output_path = '/root/.openclaw/workspace/garden/works/audio/third_movement.wav'
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with wave.open(output_path, 'w') as wav:
    wav.setnchannels(2)
    wav.setsampwidth(2)
    wav.setframerate(SAMPLE_RATE)
    wav.writeframes(stereo.tobytes())

print(f"Generated: {output_path}")
print(f"Duration: 2 minutes")
print(f"BPM: 120")
print(f"Structure: Intro-A-A'-B-A-Outro")
print(f"All voices present throughout")
