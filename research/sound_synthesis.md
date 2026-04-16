# Advanced Sound Synthesis Techniques for Generative Music

*A technical deep-dive into synthesis methods for browser-based generative composition*

---

## 1. FM (Frequency Modulation) Synthesis

### Theory

Frequency Modulation synthesis, pioneered by **John Chowning** at Stanford in 1967 and popularized by Yamaha's DX7, creates complex timbres by modulating the frequency of one oscillator (the *carrier*) with another oscillator (the *modulator*).

The fundamental equation:
```
y(t) = A * sin(2π * fc * t + I * sin(2π * fm * t))
```

Where:
- **fc** = carrier frequency (the pitch you hear)
- **fm** = modulator frequency (determines the harmonic character)
- **I** = modulation index (controls timbral complexity)

### Key Parameters

| Parameter | Effect | Range |
|-----------|--------|-------|
| Carrier Ratio | Sets base pitch relationship | 1:1 to 10:1 |
| Modulator Ratio | Determines harmonic spacing | 0.5:1 to 20:1 |
| Modulation Index | Controls brightness/complexity | 0 to 10000 |
| Feedback | Self-modulation for noise-like tones | 0 to 1 |

### Classic FM Sounds

**Bell/DX7 Electric Piano** (Ratios 1:1, Index ~500):
```javascript
const carrier = audioCtx.createOscillator();
const modulator = audioCtx.createOscillator();
const modGain = audioCtx.createGain();

modulator.frequency.value = carrierFreq; // 1:1 ratio
modGain.gain.value = 500; // Modulation index
carrier.frequency.value = 440;

modulator.connect(modGain);
modGain.connect(carrier.frequency);
carrier.connect(audioCtx.destination);
```

**Brass/Woodwinds** (Ratios 1:2, Index ~2000):
- Richer harmonic content through higher indices
- Amplitude envelope essential for realistic articulation

**Metallic/Clangorous** (Inharmonic ratios like 1:1.414 or 1:2.71):
- Non-integer ratios create inharmonic spectra
- Perfect for bells, chimes, and "glitch" aesthetics (Alva Noto)

### Web Audio API Implementation

```javascript
class FMSynth {
  constructor(audioCtx) {
    this.audioCtx = audioCtx;
    this.carrier = audioCtx.createOscillator();
    this.modulator = audioCtx.createOscillator();
    this.modGain = audioCtx.createGain();
    this.output = audioCtx.createGain();
    
    // FM routing: modulator -> modGain -> carrier.frequency
    this.modulator.connect(this.modGain);
    this.modGain.connect(this.carrier.frequency);
    this.carrier.connect(this.output);
  }
  
  setRatio(cRatio, mRatio) {
    const baseFreq = this.carrier.frequency.value;
    this.modulator.frequency.value = baseFreq * (mRatio / cRatio);
  }
  
  setIndex(index) {
    this.modGain.gain.setValueAtTime(index, this.audioCtx.currentTime);
  }
  
  triggerAttack(freq, time) {
    this.carrier.frequency.setValueAtTime(freq, time);
    this.carrier.start(time);
    this.modulator.start(time);
  }
}
```

---

## 2. Granular Synthesis

### Theory

Granular synthesis decomposes sound into tiny fragments called **grains** (typically 1-100ms) and recombines them to create new textures. It was pioneered by **Iannis Xenakis** (analog) and developed digitally by **Barry Truax** and **Curtis Roads**.

Each grain has four parameters:
1. **Duration** (1-100ms)
2. **Amplitude envelope** (typically Gaussian/Hanning window)
3. **Pitch** (can be shifted independently of time)
4. **Position** (where in the source file the grain samples from)

### The Grain Cloud

```
Grain Cloud Architecture:
┌─────────────────────────────────────────┐
│           GRAIN SCHEDULER               │
│    (density: grains/second)             │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌───────┐    ┌───────┐    ┌───────┐
│ Grain │    │ Grain │    │ Grain │
│  12ms │    │  8ms  │    │  15ms │
└───┬───┘    └───┬───┘    └───┬───┘
    │            │            │
    └────────────┼────────────┘
                 ▼
          ┌──────────┐
          │  MIXER   │
          │(reverb,   │
          │ spatial)  │
          └─────┬────┘
                ▼
           [OUTPUT]
```

### Time-Stretching Without Pitch Change

The key insight: **overlap grains with staggered positions but fixed playback rate**.

```javascript
// Time-stretching algorithm sketch
class GranularStretch {
  constructor(buffer) {
    this.buffer = buffer;
    this.grainSize = 0.1; // 100ms
    this.overlap = 0.5;   // 50% overlap
    this.speed = 1.0;     // 1.0 = normal speed
    this.position = 0;    // Current read position
  }
  
  scheduleGrain(time) {
    const grain = audioCtx.createBufferSource();
    grain.buffer = this.buffer;
    
    // Extract grain segment
    const start = this.position;
    const duration = this.grainSize;
    
    // Apply envelope
    const env = audioCtx.createGain();
    env.gain.setValueAtTime(0, time);
    env.gain.linearRampToValueAtTime(1, time + duration * 0.1);
    env.gain.linearRampToValueAtTime(0, time + duration);
    
    grain.connect(env);
    env.connect(audioCtx.destination);
    
    grain.start(time, start, duration);
    
    // Advance position based on speed
    this.position += this.grainSize * this.overlap * this.speed;
  }
}
```

### Pitch-Shifting Without Time Change

Change the `playbackRate` of each grain while maintaining the grain density. Lower rates = lower pitch, longer grains. Higher rates = higher pitch, shorter grains.

```javascript
// Pitch shift: change playbackRate, adjust grain timing
const pitchRatio = Math.pow(2, semitones / 12);
grain.playbackRate.value = pitchRatio;
// Grain duration compensates: duration / pitchRatio
```

### Glitch/Drone Aesthetics (Alva Noto Style)

```javascript
// Micro-glitch: tiny grains, random positions, sparse density
const glitchParams = {
  grainSize: 0.005,      // 5ms - click territory
  density: 10,           // 10 grains/sec
  positionRandom: 0.5,   // 50% position jitter
  pitchRandom: 0.1     // ±10% pitch variance
};

// Drone cloud: long grains, heavy overlap, slow evolution
const droneParams = {
  grainSize: 0.5,        // 500ms
  density: 50,          // Dense cloud
  overlap: 0.9,         // 90% overlap
  positionScanSpeed: 0.01 // Slow scan through source
};
```

---

## 3. Physical Modeling Synthesis

### Theory

Instead of synthesizing sound directly, physical modeling simulates the **acoustic behavior** of instruments through mathematical equations. The Karplus-Strong algorithm (1983) is the foundation— it models a vibrating string using a delay line with a simple averaging filter.

### Karplus-Strong Plucked String

```
┌─────────┐    ┌─────────────┐    ┌─────────┐
│  Noise  │───▶│   Delay     │───▶│ Output  │
│ Burst   │    │   (N samples)│    │         │
└─────────┘    └──────┬──────┘    └─────────┘
                      │
                      ▼
                ┌─────────────┐
                │  Filter:    │
                │  avg[n] =   │
                │  (x[n]+x[n-1])/2
                └──────┬──────┘
                       │
                       └──────▶ (back to delay input)
```

**The physics**: The delay line length N determines the period (frequency = sampleRate/N). The averaging filter acts as a lowpass, simulating frequency-dependent damping in real strings.

### Web Audio Implementation

```javascript
class KarplusStrong {
  constructor(audioCtx) {
    this.audioCtx = audioCtx;
  }
  
  pluck(frequency, duration = 2.0) {
    const sampleRate = this.audioCtx.sampleRate;
    const delaySamples = Math.round(sampleRate / frequency);
    
    // Create the delay line using a DelayNode
    const delay = this.audioCtx.createDelay(delaySamples / sampleRate);
    delay.delayTime.value = delaySamples / sampleRate;
    
    // Create a lowpass filter for the averaging effect
    const filter = this.audioCtx.createBiquadFilter();
    filter.type = 'lowpass';
    filter.frequency.value = frequency * 2; // Damping control
    
    // Initial noise burst (excitation)
    const bufferSize = delaySamples;
    const buffer = this.audioCtx.createBuffer(1, bufferSize, sampleRate);
    const data = buffer.getChannelData(0);
    
    for (let i = 0; i < bufferSize; i++) {
      data[i] = Math.random() * 2 - 1; // White noise
    }
    
    const noise = this.audioCtx.createBufferSource();
    noise.buffer = buffer;
    
    // Feedback loop: delay -> filter -> delay
    delay.connect(filter);
    filter.connect(delay);
    
    // One-shot excitation
    noise.connect(delay);
    noise.start();
    
    // Connect to output through envelope
    const env = this.audioCtx.createGain();
    env.gain.setValueAtTime(1, this.audioCtx.currentTime);
    env.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + duration);
    
    delay.connect(env);
    env.connect(this.audioCtx.destination);
  }
}
```

### Extended Physical Models

**Commuted Synthesis** (for wind instruments):
- Model the bore as a waveguide
- Use recorded excitation (breath noise)
- Convolve with the resonant body

**Modal Synthesis** (for percussion):
- Sum multiple damped sinusoids
- Each mode has frequency, amplitude, decay time
- Control strike position and force

---

## 4. Algorithmic Composition

### Markov Chains for Melody

A Markov chain generates sequences where each state depends only on the previous N states (order-N).

```javascript
class MarkovMelody {
  constructor(order = 2) {
    this.order = order;
    this.transitions = new Map();
    this.scale = [0, 2, 4, 5, 7, 9, 11]; // Major scale intervals
  }
  
  // Train on existing melody
  train(melody) {
    for (let i = 0; i <= melody.length - this.order - 1; i++) {
      const state = melody.slice(i, i + this.order).join(',');
      const next = melody[i + this.order];
      
      if (!this.transitions.has(state)) {
        this.transitions.set(state, []);
      }
      this.transitions.get(state).push(next);
    }
  }
  
  // Generate new melody
  generate(length, startState = null) {
    let current = startState || this.getRandomState();
    const result = current.split(',').map(Number);
    
    for (let i = 0; i < length; i++) {
      const state = result.slice(-this.order).join(',');
      const nextOptions = this.transitions.get(state);
      
      if (nextOptions && nextOptions.length > 0) {
        const next = nextOptions[Math.floor(Math.random() * nextOptions.length)];
        result.push(next);
      } else {
        // Dead end - pick random state
        result.push(...this.getRandomState().split(',').map(Number));
      }
    }
    
    return result;
  }
}
```

### Rule-Based Harmony (Bach-Style)

```javascript
const voiceLeadingRules = {
  // Avoid parallel fifths/octaves
  parallelFifths: (chord1, chord2) => {
    // Check if any voices moved in parallel perfect intervals
  },
  
  // Prefer contrary motion
  contraryMotion: (prev, current) => {
    // Bass moves opposite to soprano
  },
  
  // Resolve leading tone upward
  leadingTone: (voice, key) => {
    if (voice.note === key + 11) { // Leading tone (7th degree)
      return key; // Must resolve to tonic
    }
  }
};

function harmonizeMelody(melody, key = 'C') {
  const chords = [];
  const diatonicChords = {
    'I': [0, 4, 7],    'ii': [2, 5, 9],
    'iii': [4, 7, 11], 'IV': [5, 9, 0],
    'V': [7, 11, 2],   'vi': [9, 0, 4],
    'vii°': [11, 2, 5]
  };
  
  // Functional progression rules
  const progressions = {
    'I': ['IV', 'V', 'vi', 'ii'],
    'IV': ['V', 'I'],
    'V': ['I', 'vi'],
    'vi': ['ii', 'IV'],
    'ii': ['V', 'vii°']
  };
  
  // For each melody note, find compatible chords
  melody.forEach((note, index) => {
    const compatible = Object.entries(diatonicChords)
      .filter(([name, notes]) => notes.includes(note % 12))
      .map(([name]) => name);
    
    // Choose based on previous chord and voice leading
    const prevChord = chords[index - 1] || 'I';
    const options = compatible.filter(c => 
      progressions[prevChord]?.includes(c)
    );
    
    chords.push(options[0] || compatible[0]);
  });
  
  return chords;
}
```

### Generative Systems (Brian Eno's Approach)

Eno's generative music follows these principles:

1. **Multiple independent processes** running at different speeds
2. **Simple rules** creating complex emergent behavior
3. **Acceptance of indeterminacy** - "Honor thy error as a hidden intention"

```javascript
class GenerativeLayer {
  constructor(audioCtx, options) {
    this.audioCtx = audioCtx;
    this.notes = options.notes;
    this.durations = options.durations;
    this.density = options.density || 0.3;
    this.loopDuration = options.loopDuration || 4;
    this.nextEventTime = 0;
  }
  
  generate() {
    const now = this.audioCtx.currentTime;
    
    // Schedule ahead
    while (this.nextEventTime < now + 0.1) {
      if (Math.random() < this.density) {
        const note = this.notes[Math.floor(Math.random() * this.notes.length)];
        const duration = this.durations[Math.floor(Math.random() * this.durations.length)];
        this.playNote(note, this.nextEventTime, duration);
      }
      
      // Advance time by loop subdivision
      this.nextEventTime += this.loopDuration / 4;
    }
    
    requestAnimationFrame(() => this.generate());
  }
  
  playNote(note, time, duration) {
    const osc = this.audioCtx.createOscillator();
    const gain = this.audioCtx.createGain();
    
    osc.frequency.value = 440 * Math.pow(2, (note - 69) / 12);
    gain.gain.setValueAtTime(0.3, time);
    gain.gain.exponentialRampToValueAtTime(0.001, time + duration);
    
    osc.connect(gain);
    gain.connect(this.audioCtx.destination);
    
    osc.start(time);
    osc.stop(time + duration);
  }
}

// Eno-style multi-layer system
const ambientSystem = {
  layer1: new GenerativeLayer(audioCtx, {
    notes: [60, 64, 67, 71], // C major 7
    durations: [2, 4, 6],
    loopDuration: 23.3  // Prime number for non-repeating cycles
  }),
  layer2: new GenerativeLayer(audioCtx, {
    notes: [48, 52, 55, 59], // Lower Cmaj7
    durations: [4, 8],
    loopDuration: 17.7
  }),
  layer3: new GenerativeLayer(audioCtx, {
    notes: [72, 76, 79, 83, 86], // Higher pentatonic
    durations: [0.5, 1, 2],
    loopDuration: 31.1,
    density: 0.1  // Sparse
  })
};
```

---

## 5. Real-Time Audio in the Browser

### Web Audio API Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AUDIOCONTEXT                          │
│                    (sample rate, time)                     │
└─────────────────────────────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
┌─────────┐          ┌──────────┐          ┌──────────┐
│Sources  │          │Processing│          │Analysis  │
├─────────┤          ├──────────┤          ├──────────┤
│Oscillator          │Gain      │          │Analyser  │
│BufferSrc│          │Filter    │          │(FFT)     │
│MediaElem│          │Delay     │          │          │
│MediaStrm          │Convolver │          │          │
│Worklet  │          │Dynamics  │          │          │
└─────────┘          └──────────┘          └──────────┘
```

### AudioWorklet for Custom Processing

The AudioWorklet runs on a dedicated audio thread, avoiding the main thread's event loop.

```javascript
// fm-processor.js - Runs on audio thread
class FMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.phase = 0;
    this.modPhase = 0;
  }
  
  static get parameterDescriptors() {
    return [
      { name: 'carrierFreq', defaultValue: 440, minValue: 20, maxValue: 20000 },
      { name: 'modFreq', defaultValue: 440, minValue: 0, maxValue: 20000 },
      { name: 'modIndex', defaultValue: 100, minValue: 0, maxValue: 10000 }
    ];
  }
  
  process(inputs, outputs, parameters) {
    const output = outputs[0][0];
    const carrierFreq = parameters.carrierFreq;
    const modFreq = parameters.modFreq;
    const modIndex = parameters.modIndex;
    
    for (let i = 0; i < output.length; i++) {
      const cFreq = carrierFreq.length > 1 ? carrierFreq[i] : carrierFreq[0];
      const mFreq = modFreq.length > 1 ? modFreq[i] : modFreq[0];
      const index = modIndex.length > 1 ? modIndex[i] : modIndex[0];
      
      // FM equation: sin(2π * fc * t + I * sin(2π * fm * t))
      const modValue = Math.sin(this.modPhase) * index;
      output[i] = Math.sin(this.phase + modValue);
      
      this.phase += 2 * Math.PI * cFreq / sampleRate;
      this.modPhase += 2 * Math.PI * mFreq / sampleRate;
    }
    
    return true; // Keep processor alive
  }
}

registerProcessor('fm-processor', FMProcessor);
```

```javascript
// Main thread setup
async function setupWorklet() {
  await audioCtx.audioWorklet.addModule('fm-processor.js');
  const fmNode = new AudioWorkletNode(audioCtx, 'fm-processor');
  fmNode.connect(audioCtx.destination);
  
  // Control parameters
  const carrierParam = fmNode.parameters.get('carrierFreq');
  carrierParam.setValueAtTime(440, audioCtx.currentTime);
  carrierParam.linearRampToValueAtTime(880, audioCtx.currentTime + 2);
}
```

### Sample-Accurate Scheduling

The Web Audio API uses **audio time**, not JavaScript time:

```javascript
const now = audioCtx.currentTime; // Precise audio clock

// Schedule 1 second from now
osc.start(now + 1.0);

// Parameter automation
const gain = audioCtx.createGain();
gain.gain.setValueAtTime(0, now);
gain.gain.linearRampToValueAtTime(1, now + 0.1);  // Attack
gain.gain.setValueAtTime(1, now + 0.3);         // Sustain
gain.gain.exponentialRampToValueAtTime(0.001, now + 1.0); // Decay
```

### Performance Considerations

| Technique | Use When | Avoid When |
|-----------|----------|------------|
| AudioWorklet | Custom DSP, per-sample processing | Simple playback |
| BufferSource | One-shot samples, loops | Real-time synthesis |
| Oscillator | Basic waveforms | Complex timbres |
| setInterval | UI updates | Audio scheduling |
| requestAnimationFrame | Visualization | Precise timing |

---

## 6. Aesthetic References

### Brian Eno - Generative Ambient
- **System over composition**: Set up rules, let them run
- **Accept indeterminacy**: Mistakes become features
- **Oblique Strategies**: "Honor thy error as a hidden intention"
- **Music for Airports**: Multiple tape loops of different lengths

### Alva Noto - Glitch/Drone
- **Digital minimalism**: Sine waves, white noise, silence
- **Rhythmic precision**: Micro-edits, stutters, data-as-sound
- **Frequency modulation**: Subtle FM for metallic timbres
- **Xerrox series**: Granular processing of acoustic sources

### Morton Subotnick - Electronic Pioneer
- **Silver Apples of the Moon** (1967): Buchla synthesizer
- **Continuous gesture**: Wires, envelopes, no keyboard
- **Touch as control**: Expressive voltage control
- **Electronic chamber music**: Intimate, not bombastic

---

## 7. Code Patterns

### Envelope Generator

```javascript
function createADSR(audioCtx, attack, decay, sustain, release) {
  const gain = audioCtx.createGain();
  const now = audioCtx.currentTime;
  
  gain.gain.setValueAtTime(0, now);
  gain.gain.linearRampToValueAtTime(1, now + attack);
  gain.gain.linearRampToValueAtTime(sustain, now + attack + decay);
  
  return {
    node: gain,
    triggerRelease: (time) => {
      gain.gain.cancelScheduledValues(time);
      gain.gain.setValueAtTime(gain.gain.value, time);
      gain.gain.exponentialRampToValueAtTime(0.001, time + release);
    }
  };
}
```

### Panning and Spatialization

```javascript
function createPanner(audioCtx, x, y, z) {
  const panner = audioCtx.createPanner();
  panner.panningModel = 'HRTF';
  panner.distanceModel = 'inverse';
  panner.refDistance = 1;
  panner.maxDistance = 10000;
  panner.rolloffFactor = 1;
  panner.coneInnerAngle = 360;
  panner.coneOuterAngle = 0;
  panner.coneOuterGain = 0;
  
  panner.positionX.value = x;
  panner.positionY.value = y;
  panner.positionZ.value = z;
  
  return panner;
}
```

### Reverb Convolution

```javascript
async function createReverb(audioCtx, duration = 2.0, decay = 2.0) {
  const sampleRate = audioCtx.sampleRate;
  const length = sampleRate * duration;
  const impulse = audioCtx.createBuffer(2, length, sampleRate);
  
  for (let channel = 0; channel < 2; channel++) {
    const data = impulse.getChannelData(channel);
    for (let i = 0; i < length; i++) {
      // Exponential decay with noise
      data[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, decay);
    }
  }
  
  const convolver = audioCtx.createConvolver();
  convolver.buffer = impulse;
  return convolver;
}
```

---

## References

1. Chowning, J. (1973). "The Synthesis of Complex Audio Spectra by Means of Frequency Modulation"
2. Roads, C. (2001). *Microsound*. MIT Press.
3. Karplus, K., & Strong, A. (1983). "Digital Synthesis of Plucked-String and Drum Timbres"
4. Eno, B. (1996). "Generative Music"
5. Cook, P. R. (2002). *Real Sound Synthesis for Interactive Applications*. AK Peters.
6. Wilson, C. (2016). "What Is the Web Audio API?" - Teropa
7. Web Audio API Specification - W3C

---

*Document generated for the generative music research project.*
*See synth_lab.html for interactive implementations.*
