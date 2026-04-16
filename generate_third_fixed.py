import numpy as np
import wave
import os

SAMPLE_RATE = 44100
DURATION = 120
NUM_SAMPLES = SAMPLE_RATE * DURATION

audio_left = np.zeros(NUM_SAMPLES)
audio_right = np.zeros(NUM_SAMPLES)

def sine_wave(freq, duration, amp=1.0):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    return amp * np.sin(2 * np.pi * freq * t)

def triangle_wave(freq, duration, amp=1.5):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    return amp * (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * t))

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
C4, D4, E4, F4, G4, A4, B4, C5, D5, E5 = 261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25, 587.33, 659.25

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

# === BASS AND CHORDS (full 2 minutes) ===
# Progression: Am-F-C-G, each chord 8 seconds (16 beats), repeated 3 times = 96 seconds + fill
chords_order = [
    (A3, C4, E4, 8), (F3, A3, C4, 8), (C3, E3, G3, 8), (G3, B3, D4, 8),  # 32 sec
    (A3, C4, E4, 8), (F3, A3, C4, 8), (C3, E3, G3, 8), (G3, B3, D4, 8),  # 32 sec  
    (D3, F3, A3, 8), (E3, G3, B3, 8), (A3, C4, E4, 8), (G3, B3, D4, 8),  # 32 sec - bridge
    (A3, C4, E4, 8), (F3, A3, C4, 8), (C3, E3, G3, 8), (G3, B3, D4, 4),  # 28 sec - return (shortened)
]

bass_time = 0
for root, third, fifth, duration in chords_order:
    # Bass - root on beat 1, fifth on beat 3
    for beat in [0, 1, 2, 3]:  # Play every beat
        note_dur = 0.5
        note_freq = root if beat % 2 == 0 else fifth
        note = triangle_wave(note_freq, note_dur)
        env = adsr(len(note), attack=0.02, decay=0.05, sustain=0.8, release=0.1)
        note = note * env
        pos = bass_time + int(beat * 0.5 * SAMPLE_RATE)
        mix_at(audio_left, audio_right, pos, note * 0.6, note * 0.6)
    
    # Chord pad - sustained for full duration
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    for freq in [root, third, fifth]:
        osc1 = np.sin(2 * np.pi * freq * t)
        osc2 = np.sin(2 * np.pi * (freq * 1.003) * t)
        note = (osc1 + osc2) / 2
        env = adsr(len(note), attack=0.8, decay=1.5, sustain=0.5, release=0.8)
        note = note * env * 0.15
        pan = 0.3 + ((freq - root) / root) * 0.4
        mix_at(audio_left, audio_right, bass_time, note * (1-pan), note * pan)
    
    bass_time += int(duration * SAMPLE_RATE)
    if bass_time >= NUM_SAMPLES:
        break

# === MELODY (complete 2-minute composition with full phrases) ===
# Need ~120 seconds of melody

# 120 BPM = 2 beats per second = 0.5 sec per beat
# 8 seconds per chord = 16 beats per chord
# 32 seconds per section (4 chords)
# Need 3.75 sections = ~4 sections to fill 120 seconds

# Extended melody phrases to fill 2 minutes
rest = 0  # Silence marker

melody_data = [
    # INTRO - 24 seconds (sparse, building)
    (E4, 2.0), (A4, 2.0), (rest, 2.0), (E4, 2.0), (A4, 2.0), (rest, 2.0),
    (E4, 2.0), (C5, 2.0), (A4, 2.0), (E4, 2.0), (rest, 4.0),
    
    # SECTION A - 32 seconds (main theme)
    (E4, 1.0), (A4, 1.0), (E4, 0.5), (C4, 0.5), (E4, 0.5), (A4, 0.5),
    (C4, 1.0), (F4, 1.0), (C4, 0.5), (A3, 0.5), (C4, 0.5), (F4, 0.5),
    (G4, 1.0), (E4, 0.5), (C4, 0.5), (G4, 0.5), (E4, 0.5), (C4, 1.0),
    (D4, 1.0), (B3, 0.5), (D4, 0.5), (G4, 1.0), (D4, 0.5), (B3, 0.5),
    
    # SECTION A' - 32 seconds (variation, more active)
    (E4, 0.5), (A4, 0.5), (G4, 0.5), (E4, 0.5), (A4, 1.0), (C5, 0.5), (A4, 0.5),
    (F4, 0.5), (C4, 0.5), (A3, 0.5), (F3, 0.5), (A3, 1.0), (C4, 0.5), (F4, 0.5),
    (E4, 0.5), (G4, 0.5), (C5, 1.0), (G4, 0.5), (E4, 0.5), (C4, 1.0),
    (B3, 0.5), (D4, 0.5), (G4, 1.0), (B3, 0.5), (D4, 0.5), (G4, 0.5), (B3, 1.0),
    
    # SECTION B - 24 seconds (bridge, higher tension)
    (D4, 0.5), (F4, 0.5), (A4, 1.0), (F4, 0.5), (D4, 0.5), (F4, 1.0),
    (E4, 0.5), (G4, 0.5), (B4, 1.0), (G4, 0.5), (E4, 0.5), (G4, 1.0),
    (E4, 0.5), (A4, 0.5), (C5, 1.0), (E5, 0.5), (C5, 0.5), (A4, 1.0),
    (D4, 1.0), (B3, 1.0), (G3, 2.0),
    
    # RETURN - 32 seconds (back to main theme, extended)
    (A4, 1.0), (E4, 0.5), (C5, 0.5), (A4, 1.0), (E4, 0.5), (C5, 0.5),
    (F4, 1.0), (C4, 0.5), (A4, 0.5), (F4, 1.0), (C4, 0.5), (A4, 0.5),
    (G4, 1.0), (E4, 0.5), (C4, 0.5), (G4, 0.5), (E4, 0.5), (C4, 1.0),
    (G4, 1.0), (E4, 0.5), (D4, 0.5), (C4, 2.0),
    
    # OUTRO - 16 seconds (winding down)
    (E4, 1.0), (C4, 1.0), (A3, 1.0), (rest, 1.0),
    (E4, 0.5), (C4, 0.5), (A3, 2.0), (rest, 2.0),
    (A3, 6.0),  # Final note held
    (rest, 4.0),
]

rest = 0  # Special value for silence

melody_time = 0
for freq, dur in melody_data:
    if freq == rest:
        # Silence - just advance time
        melody_time += int(dur * SAMPLE_RATE)
        continue
    
    note = sine_wave(freq, dur, amp=0.6)
    env = adsr(len(note), attack=0.02, decay=0.1, sustain=0.75, release=0.2)
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

# Verify duration
total_melody = sum(dur for _, dur in melody_data if isinstance(dur, (int, float)))
print(f"Generated: {output_path}")
print(f"Duration: 2 minutes")
print(f"Melody content: {total_melody} seconds")
print(f"BPM: 120")
print(f"Structure: Intro-A-A'-B-Return-Outro")
