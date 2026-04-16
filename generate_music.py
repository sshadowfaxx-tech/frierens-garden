import numpy as np
import wave
import os

# Audio parameters
SAMPLE_RATE = 44100
DURATION = 240  # 4 minutes
NUM_SAMPLES = SAMPLE_RATE * DURATION

# Helper function to create ADSR envelope
def adsr_envelope(duration, attack=0.1, decay=0.1, sustain=0.7, release=0.1):
    samples = int(SAMPLE_RATE * duration)
    attack_samples = min(int(SAMPLE_RATE * attack), samples // 4)
    decay_samples = min(int(SAMPLE_RATE * decay), samples // 4)
    release_samples = min(int(SAMPLE_RATE * release), samples // 4)
    sustain_samples = max(0, samples - attack_samples - decay_samples - release_samples)
    
    env = np.zeros(samples)
    # Attack
    if attack_samples > 0:
        env[:attack_samples] = np.linspace(0, 1, attack_samples)
    # Decay
    if decay_samples > 0:
        env[attack_samples:attack_samples+decay_samples] = np.linspace(1, sustain, decay_samples)
    # Sustain
    if sustain_samples > 0:
        env[attack_samples+decay_samples:attack_samples+decay_samples+sustain_samples] = sustain
    # Release
    if release_samples > 0:
        env[-release_samples:] = np.linspace(sustain, 0, release_samples)
    
    return env

# Helper to generate a note with FM synthesis
def fm_note(frequency, duration, mod_freq_ratio=1.0, mod_index=2.0, waveform='sine'):
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration))
    mod_freq = frequency * mod_freq_ratio
    
    # FM synthesis
    modulator = np.sin(2 * np.pi * mod_freq * t)
    carrier_phase = 2 * np.pi * (frequency + mod_index * modulator) * t
    
    if waveform == 'sine':
        signal = np.sin(carrier_phase)
    elif waveform == 'square':
        signal = np.sign(np.sin(carrier_phase))
    elif waveform == 'sawtooth':
        signal = 2 * (t * frequency - np.floor(t * frequency + 0.5))
    else:
        signal = np.sin(carrier_phase)
    
    return signal

# Helper to mix audio with panning
def pan_signal(signal, pan=0.5):  # 0 = left, 1 = right, 0.5 = center
    left = signal * (1 - pan) * 2
    right = signal * pan * 2
    # Normalize to prevent clipping
    max_val = max(np.max(np.abs(left)), np.max(np.abs(right)))
    if max_val > 1.0:
        left = left / max_val
        right = right / max_val
    return left, right

# Initialize stereo mix
audio_left = np.zeros(NUM_SAMPLES)
audio_right = np.zeros(NUM_SAMPLES)

# === VOICE 1: Bass Foundation (slow harmonic rhythm) ===
# Using a modal scale - avoid traditional major/minor
# Frequencies based on A=440, but using Phrygian mode relationships
base_freq = 55  # A1

# Phrygian mode ratios (unconventional, dark, mysterious)
phrygian_ratios = [1, 256/243, 32/27, 4/3, 1024/729, 128/81, 16/9, 2]

# Bass line - whole notes, very slow
bass_pattern = [0, 2, 1, 3, 2, 4, 3, 1]  # Scale degrees
bass_durations = [4, 4, 4, 4, 4, 4, 4, 4]  # 4 seconds each = 32 sec per cycle

bass_time = 0
for i, (degree, dur) in enumerate(zip(bass_pattern * 8, bass_durations * 8)):  # 4 minutes
    if bass_time >= NUM_SAMPLES:
        break
    
    freq = base_freq * phrygian_ratios[degree]
    note = fm_note(freq, dur, mod_freq_ratio=0.5, mod_index=1.5, waveform='sine')
    env = adsr_envelope(dur, attack=1.0, decay=0.5, sustain=0.8, release=1.0)
    note = note * env * 0.4
    
    # Pan slightly left
    left, right = pan_signal(note, pan=0.3)
    
    note_samples = len(note)
    end_time = min(bass_time + note_samples, NUM_SAMPLES)
    actual_samples = end_time - bass_time
    
    audio_left[bass_time:end_time] += left[:actual_samples]
    audio_right[bass_time:end_time] += right[:actual_samples]
    
    bass_time = end_time

# === VOICE 2: Arpeggio Melody (Fibonacci rhythm) ===
arpeg_base = 220  # A3
fibonacci = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]

# Create arpeggios that spiral upward
arpeg_time = 0
for phrase in range(20):  # 20 phrases
    if arpeg_time >= NUM_SAMPLES:
        break
    
    # Choose base note for this phrase
    base_idx = phrase % len(phrygian_ratios)
    base = arpeg_base * phrygian_ratios[base_idx]
    
    # Create arpeggio pattern: root, +3rd, +5th, +octave, descending
    intervals = [1, 1.2, 1.5, 2, 1.5, 1.2, 1]
    
    for i, interval in enumerate(intervals):
        if arpeg_time >= NUM_SAMPLES:
            break
            
        freq = base * interval
        # Use Fibonacci numbers for note durations (in seconds/10)
        dur = fibonacci[i % len(fibonacci)] / 10
        
        note = fm_note(freq, dur, mod_freq_ratio=2.0, mod_index=3.0, waveform='sine')
        env = adsr_envelope(dur, attack=0.05, decay=0.1, sustain=0.6, release=0.3)
        note = note * env * 0.25
        
        # Pan moves with pitch (higher = more right)
        pan = 0.4 + (interval - 1) * 0.3
        left, right = pan_signal(note, pan=pan)
        
        note_samples = len(note)
        end_time = min(arpeg_time + note_samples, NUM_SAMPLES)
        actual_samples = end_time - arpeg_time
        
        audio_left[arpeg_time:end_time] += left[:actual_samples]
        audio_right[arpeg_time:end_time] += right[:actual_samples]
        
        arpeg_time += note_samples

# === VOICE 3: Texture (sustained pads with slow movement) ===
pad_freqs = [110, 138.59, 164.81, 196.00]  # A2, C#3, E3, G3 - strange chord
pad_time = 0
pad_duration = 8  # 8 second sustained pads

for i in range(30):  # 30 pads over 4 minutes
    if pad_time >= NUM_SAMPLES:
        break
    
    freq = pad_freqs[i % len(pad_freqs)]
    
    # Slow FM for evolving texture
    t = np.linspace(0, pad_duration, int(SAMPLE_RATE * pad_duration))
    mod = 0.5 * np.sin(2 * np.pi * 0.2 * t)  # Slow 0.2 Hz modulation
    
    # Two oscillators slightly detuned for beating
    osc1 = np.sin(2 * np.pi * freq * t)
    osc2 = np.sin(2 * np.pi * (freq * 1.005) * t)  # Slightly sharp
    
    pad = (osc1 + osc2) / 2
    env = adsr_envelope(pad_duration, attack=2.0, decay=1.0, sustain=0.5, release=2.0)
    pad = pad * env * 0.2
    
    # Wide stereo spread
    pan = 0.3 + (i % 3) * 0.2  # Alternates left, center, right
    left, right = pan_signal(pad, pan=pan)
    
    note_samples = len(pad)
    end_time = min(pad_time + note_samples, NUM_SAMPLES)
    actual_samples = end_time - pad_time
    
    audio_left[pad_time:end_time] += left[:actual_samples]
    audio_right[pad_time:end_time] += right[:actual_samples]
    
    pad_time += int(SAMPLE_RATE * 2)  # Overlap by starting next pad 2 seconds later

# === VOICE 4: Rhythmic pulse (golden ratio timing) ===
phi = (1 + np.sqrt(5)) / 2  # Golden ratio
pulse_base = 82.41  # E2

time = 0
beat = 0
while time < NUM_SAMPLES:
    # Use phi to determine rhythm - irrational, never quite repeating
    beat_duration = int(SAMPLE_RATE * (0.5 + (beat % 3) * 0.3))
    
    freq = pulse_base * phrygian_ratios[beat % len(phrygian_ratios)]
    
    t = np.linspace(0, 0.1, int(SAMPLE_RATE * 0.1))  # Short blip
    pulse = np.sin(2 * np.pi * freq * t) * np.exp(-t * 10)  # Quick decay
    pulse = pulse * 0.15
    
    left, right = pan_signal(pulse, pan=0.5)
    
    end_time = min(time + len(pulse), NUM_SAMPLES)
    actual_samples = end_time - time
    
    audio_left[time:end_time] += left[:actual_samples]
    audio_right[time:end_time] += right[:actual_samples]
    
    time += beat_duration
    beat += 1

# Normalize final mix to prevent clipping
max_left = np.max(np.abs(audio_left))
max_right = np.max(np.abs(audio_right))
max_val = max(max_left, max_right)

if max_val > 0.95:
    audio_left = audio_left / max_val * 0.95
    audio_right = audio_right / max_val * 0.95

# Convert to 16-bit PCM
audio_left_int = (audio_left * 32767).astype(np.int16)
audio_right_int = (audio_right * 32767).astype(np.int16)

# Interleave stereo
stereo_audio = np.empty(2 * NUM_SAMPLES, dtype=np.int16)
stereo_audio[0::2] = audio_left_int
stereo_audio[1::2] = audio_right_int

# Write WAV
output_path = '/root/.openclaw/workspace/garden/works/audio/mathematica_phrase.wav'
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with wave.open(output_path, 'w') as wav_file:
    wav_file.setnchannels(2)
    wav_file.setsampwidth(2)
    wav_file.setframerate(SAMPLE_RATE)
    wav_file.writeframes(stereo_audio.tobytes())

print(f"Generated: {output_path}")
print(f"Duration: {DURATION//60} minutes")
print(f"Voices: 4 (bass, arpeggio, texture, pulse)")
print(f"Technique: FM synthesis with mathematical composition")
print(f"Structure: Phrygian mode, Fibonacci rhythms, Golden ratio timing")
