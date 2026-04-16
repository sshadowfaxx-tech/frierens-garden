import numpy as np
import wave
import os

# Audio parameters
SAMPLE_RATE = 44100
DURATION = 120  # 2 minutes
NUM_SAMPLES = SAMPLE_RATE * DURATION

# Initialize stereo mix
audio_left = np.zeros(NUM_SAMPLES)
audio_right = np.zeros(NUM_SAMPLES)

def sine_wave(freq, duration, amp=1.0):
    """Generate a sine wave"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    return amp * np.sin(2 * np.pi * freq * t)

def square_wave(freq, duration, amp=1.0):
    """Generate a square wave for bass"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    return amp * np.sign(np.sin(2 * np.pi * freq * t))

def triangle_wave(freq, duration, amp=1.0):
    """Generate a triangle wave"""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    return amp * (2 / np.pi) * np.arcsin(np.sin(2 * np.pi * freq * t))

def adsr(samples, attack=0.01, decay=0.1, sustain=0.7, release=0.2):
    """Simple ADSR envelope"""
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
    """Mix signal into audio at position"""
    end = min(position + len(signal_l), len(audio_l))
    actual = end - position
    audio_l[position:end] += signal_l[:actual]
    audio_r[position:end] += signal_r[:actual]
    return audio_l, audio_r

# Equal temperament frequencies
C3, D3, E3, F3, G3, A3, B3 = 130.81, 146.83, 164.81, 174.61, 196.00, 220.00, 246.94
C4, D4, E4, F4, G4, A4, B4 = 261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88
C5, D5, E5, F5, G5 = 523.25, 587.33, 659.25, 698.46, 783.99

# Chord definitions (root, third, fifth)
chords = {
    'Am': [A3, C4, E4],
    'F': [F3, A3, C4],
    'C': [C3, E3, G3],
    'G': [G3, B3, D4],
    'Dm': [D3, F3, A3],
    'Em': [E3, G3, B3],
}

# === DRUMS ===
# Simple 4/4 kick pattern: kick on 1, 2, 3, 4
kick_freq = 60
kick_duration = 0.15
beat_samples = int(SAMPLE_RATE * 0.5)  # 120 BPM (0.5 seconds per beat)

for beat in range(0, NUM_SAMPLES, beat_samples):
    # Kick drum - sine sweep from high to low with fast decay
    t = np.linspace(0, kick_duration, int(SAMPLE_RATE * kick_duration))
    sweep = np.linspace(kick_freq * 2, kick_freq, len(t))
    kick = np.sin(2 * np.pi * sweep * t) * np.exp(-t * 15)
    kick *= 0.6
    
    # Add to both channels equally (center)
    end = min(beat + len(kick), NUM_SAMPLES)
    actual = end - beat
    audio_left[beat:end] += kick[:actual]
    audio_right[beat:end] += kick[:actual]

# Snare on 2 and 4
snare_noise_duration = 0.1
for beat in range(beat_samples * 1, NUM_SAMPLES, beat_samples * 2):  # beats 2 and 4
    t = np.linspace(0, snare_noise_duration, int(SAMPLE_RATE * snare_noise_duration))
    noise = np.random.randn(len(t)) * np.exp(-t * 20) * 0.4
    
    end = min(beat + len(noise), NUM_SAMPLES)
    actual = end - beat
    audio_left[beat:end] += noise[:actual]
    audio_right[beat:end] += noise[:actual]

# === BASS LINE ===
# Walking bass following the chord progression
# Progression: Am - F - C - G (classic vi - IV - I - V)
# Each chord for 4 beats (2 seconds at 120 BPM)

bass_progression = [
    ('Am', 8), ('F', 8), ('C', 8), ('G', 8),  # First phrase
    ('Am', 8), ('F', 8), ('C', 8), ('G', 8),  # Second phrase
    ('Dm', 8), ('Em', 8), ('Am', 8), ('G', 8),  # Bridge movement
    ('Am', 8), ('F', 8), ('C', 8), ('G', 8),  # Return
]

bass_time = 0
for chord_name, beats in bass_progression:
    duration = beats * 0.5  # 0.5 seconds per beat
    root, third, fifth = chords[chord_name]
    
    # Simple bass line: play root on beat 1, then alternate between root and fifth
    for beat in range(0, beats, 2):  # Every 2 beats (half notes)
        note_dur = min(1.0, duration - (beat * 0.5))
        if note_dur <= 0:
            break
            
        # Alternate between root and fifth
        note_freq = root if beat % 4 == 0 else fifth
        
        # Triangle wave for warmer bass sound
        note = triangle_wave(note_freq, note_dur, amp=0.5)
        env = adsr(len(note), attack=0.02, decay=0.05, sustain=0.8, release=0.1)
        note = note * env
        
        pos = bass_time + int(beat * 0.5 * SAMPLE_RATE)
        # Slight stereo spread for bass (mostly centered but wide)
        mix_at(audio_left, audio_right, pos, note * 0.8, note * 0.8)
    
    bass_time += int(duration * SAMPLE_RATE)

# === CHORD PADS ===
# Sustained chords that create harmonic foundation

chord_time = 0
for chord_name, beats in bass_progression:
    duration = beats * 0.5
    root, third, fifth = chords[chord_name]
    
    # Each note of the chord
    for freq in [root, third, fifth]:
        # Sawtooth-ish via filtered square for pad sound
        t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
        
        # Two detuned oscillators for warmth
        osc1 = np.sin(2 * np.pi * freq * t)
        osc2 = np.sin(2 * np.pi * (freq * 1.003) * t)  # Slight detune
        note = (osc1 + osc2) / 2
        
        # Slow envelope for pad
        env = adsr(len(note), attack=0.5, decay=1.0, sustain=0.6, release=0.5)
        note = note * env * 0.2  # Quiet in background
        
        # Stereo spread - higher notes more right
        pan = 0.3 + ((freq - root) / root) * 0.4  # 0.3 to 0.7
        left = note * (1 - pan)
        right = note * pan
        
        mix_at(audio_left, audio_right, chord_time, left, right)
    
    chord_time += int(duration * SAMPLE_RATE)
    if chord_time >= NUM_SAMPLES:
        break

# === MELODY ===
# Simple, memorable melody over the progression
# Using mostly chord tones with occasional passing tones

melody_notes = [
    # Over Am
    (E4, 0.5), (A4, 0.5), (E4, 0.5), (C4, 0.5),
    # Over F
    (C4, 0.5), (F4, 0.5), (C4, 0.5), (A3, 0.5),
    # Over C
    (G4, 0.5), (E4, 0.5), (C4, 1.0),
    # Over G
    (D4, 0.5), (B3, 0.5), (D4, 0.5), (G4, 0.5),
    # Second phrase - variation
    (E4, 0.5), (A4, 0.5), (G4, 0.5), (E4, 0.5),
    (F4, 0.5), (C4, 0.5), (A3, 0.5), (F3, 0.5),
    (E4, 0.5), (G4, 0.5), (C5, 1.0),
    (B3, 0.5), (D4, 0.5), (G4, 0.5), (B3, 0.5),
    # Bridge - higher tension
    (D4, 0.5), (F4, 0.5), (A4, 0.5), (D4, 0.5),
    (E4, 0.5), (G4, 0.5), (B4, 0.5), (E4, 0.5),
    (E4, 0.5), (A4, 0.5), (C5, 1.0),
    (D4, 0.5), (B3, 0.5), (G3, 1.0),
    # Return to main theme with slight variation
    (A4, 0.5), (E4, 0.5), (C5, 0.5), (A4, 0.5),
    (F4, 0.5), (C4, 0.5), (A4, 0.5), (F4, 0.5),
    (G4, 0.5), (E4, 0.5), (C4, 1.0),
    (G4, 1.0), (E4, 0.5), (D4, 0.5), (C4, 1.0),
]

melody_time = 0
for freq, dur in melody_notes:
    note = sine_wave(freq, dur, amp=0.5)
    env = adsr(len(note), attack=0.01, decay=0.1, sustain=0.7, release=0.15)
    note = note * env
    
    # Higher notes slightly more right
    pan = 0.4 if freq < 300 else 0.6
    left = note * (1 - pan)
    right = note * pan
    
    mix_at(audio_left, audio_right, melody_time, left, right)
    melody_time += int(dur * SAMPLE_RATE)

# === FINAL MIX ===
# Normalize
max_val = max(np.max(np.abs(audio_left)), np.max(np.abs(audio_right)))
if max_val > 0.95:
    audio_left = audio_left / max_val * 0.95
    audio_right = audio_right / max_val * 0.95

# Convert to 16-bit
stereo = np.empty(2 * NUM_SAMPLES, dtype=np.int16)
stereo[0::2] = (audio_left * 32767).astype(np.int16)
stereo[1::2] = (audio_right * 32767).astype(np.int16)

# Write file
output_path = '/root/.openclaw/workspace/garden/works/audio/second_attempt.wav'
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with wave.open(output_path, 'w') as wav:
    wav.setnchannels(2)
    wav.setsampwidth(2)
    wav.setframerate(SAMPLE_RATE)
    wav.writeframes(stereo.tobytes())

print(f"Generated: {output_path}")
print(f"Duration: 2 minutes")
print(f"BPM: 120")
print(f"Structure: Drums + Bass + Chords + Melody")
print(f"Progression: Am-F-C-G (vi-IV-I-V)")
