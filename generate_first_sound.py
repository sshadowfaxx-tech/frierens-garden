import numpy as np
import wave
import struct
import os

# Audio parameters
SAMPLE_RATE = 44100  # Hz
DURATION = 30  # seconds
NUM_SAMPLES = SAMPLE_RATE * DURATION

# Time array
t = np.linspace(0, DURATION, NUM_SAMPLES)

# Create stereo audio (two channels)
audio_left = np.zeros(NUM_SAMPLES)
audio_right = np.zeros(NUM_SAMPLES)

# Layer 1: Deep foundation drone (110 Hz - A2)
carrier_freq = 110.0
mod_freq = 2.5  # Slow modulation
mod_index = 5.0  # Modulation depth

# FM synthesis: frequency varies with modulator
modulator = np.sin(2 * np.pi * mod_freq * t)
fm_signal_1 = np.sin(2 * np.pi * (carrier_freq + mod_index * modulator) * t)

# Fade in and out
fade_samples = int(2 * SAMPLE_RATE)  # 2 second fade
fade_in = np.linspace(0, 1, fade_samples)
fade_out = np.linspace(1, 0, fade_samples)

envelope = np.ones(NUM_SAMPLES)
envelope[:fade_samples] = fade_in
envelope[-fade_samples:] = fade_out

fm_signal_1 *= envelope * 0.4  # Lower volume for foundation

# Layer 2: Mid drone (220 Hz - A3) with different modulation
carrier_freq_2 = 220.0
mod_freq_2 = 0.7  # Even slower
mod_index_2 = 3.0

modulator_2 = np.sin(2 * np.pi * mod_freq_2 * t)
# Add some harmonic complexity
harmonic = 0.3 * np.sin(2 * np.pi * (carrier_freq_2 * 2) * t)
fm_signal_2 = np.sin(2 * np.pi * (carrier_freq_2 + mod_index_2 * modulator_2) * t) + harmonic

fm_signal_2 *= envelope * 0.25  # Even quieter

# Layer 3: High texture (440 Hz - A4) with rapid beating
carrier_freq_3 = 440.0
beat_freq = 4.0  # Creates rhythmic pulsing

# Two slightly detuned oscillators for beating
osc_a = np.sin(2 * np.pi * carrier_freq_3 * t)
osc_b = np.sin(2 * np.pi * (carrier_freq_3 + beat_freq) * t)
texture = (osc_a + osc_b) / 2
texture *= envelope * 0.15  # Very subtle high layer

# Layer 4: Low sub-bass rumble (55 Hz)
sub_freq = 55.0
sub_wave = np.sin(2 * np.pi * sub_freq * t)
# Slow amplitude modulation for breathing effect
sub_mod = 0.5 + 0.5 * np.sin(2 * np.pi * 0.15 * t)  # 0.15 Hz = 6.67 second cycle
sub_wave *= sub_mod * envelope * 0.5

# Mix all layers
# Left channel - slightly more high textures
audio_left = fm_signal_1 + fm_signal_2 * 0.8 + texture * 1.2 + sub_wave
# Right channel - slightly more low foundation  
audio_right = fm_signal_1 * 1.2 + fm_signal_2 * 1.1 + texture * 0.8 + sub_wave

# Normalize to prevent clipping
max_val = max(np.max(np.abs(audio_left)), np.max(np.abs(audio_right)))
audio_left = audio_left / max_val * 0.95
audio_right = audio_right / max_val * 0.95

# Convert to 16-bit PCM
audio_left_int = (audio_left * 32767).astype(np.int16)
audio_right_int = (audio_right * 32767).astype(np.int16)

# Interleave left and right channels for stereo
stereo_audio = np.empty(2 * NUM_SAMPLES, dtype=np.int16)
stereo_audio[0::2] = audio_left_int
stereo_audio[1::2] = audio_right_int

# Write to WAV file
output_path = '/root/.openclaw/workspace/garden/works/audio/first_drone.wav'
os.makedirs(os.path.dirname(output_path), exist_ok=True)

with wave.open(output_path, 'w') as wav_file:
    wav_file.setnchannels(2)  # Stereo
    wav_file.setsampwidth(2)  # 16-bit
    wav_file.setframerate(SAMPLE_RATE)
    wav_file.writeframes(stereo_audio.tobytes())

print(f"Generated: {output_path}")
print(f"Duration: {DURATION} seconds")
print(f"Sample rate: {SAMPLE_RATE} Hz")
print(f"Layers: 4 (sub-bass, foundation, mid, texture)")
print(f"Technique: FM synthesis with harmonic layering")
