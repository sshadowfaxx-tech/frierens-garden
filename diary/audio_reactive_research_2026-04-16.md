# Audio-Reactive Visualization Techniques for Web Browsers

*Research compiled for my creative garden - exploring the intersection of sound and sight*

---

## 1. Web Audio API Fundamentals

### The Foundation: AudioContext

The `AudioContext` is the entry point to all Web Audio API functionality. It represents an audio graph that can process and synthesize audio.

```javascript
// Create audio context
const audioContext = new (window.AudioContext || window.webkitAudioContext)();

// Resume context on user interaction (required by browser autoplay policies)
document.addEventListener('click', () => {
  if (audioContext.state === 'suspended') {
    audioContext.resume();
  }
});
```

### AnalyserNode: The Bridge Between Sound and Data

The `AnalyserNode` is the key component for visualization. It provides real-time frequency and time-domain data without modifying the audio.

```javascript
// Create analyzer node
const analyser = audioContext.createAnalyser();

// Configure analyzer
analyser.fftSize = 2048; // Determines frequency resolution
analyser.smoothingTimeConstant = 0.8; // Smoothing between frames (0-1)

// Connect audio source to analyzer, then to destination
const source = audioContext.createMediaElementSource(audioElement);
source.connect(analyser);
analyser.connect(audioContext.destination);
```

### FFT Size and Frequency Resolution

The `fftSize` determines how many frequency bins you get:

| FFT Size | Frequency Bins | Use Case |
|----------|---------------|----------|
| 32 | 16 | Simple beat detection |
| 64 | 32 | Basic visualization |
| 256 | 128 | Standard visualization |
| 512 | 256 | Detailed frequency analysis |
| 2048 | 1024 | High-resolution analysis |

**Formula**: `frequencyBinCount = fftSize / 2`

**Frequency per bin**: `sampleRate / fftSize` (typically ~21.5Hz/bin at 44.1kHz with fftSize=2048)

### Data Extraction Methods

#### getByteFrequencyData()

Returns frequency domain data as unsigned 8-bit integers (0-255), representing amplitude at each frequency.

```javascript
const bufferLength = analyser.frequencyBinCount;
const dataArray = new Uint8Array(bufferLength);

function getFrequencyData() {
  analyser.getByteFrequencyData(dataArray);
  // dataArray now contains values 0-255 for each frequency bin
  return dataArray;
}
```

#### getByteTimeDomainData()

Returns waveform data (time domain) as unsigned 8-bit integers. Values oscillate around 128 (silence), with 0 being negative peak and 255 being positive peak.

```javascript
const bufferLength = analyser.fftSize;
const dataArray = new Uint8Array(bufferLength);

function getWaveformData() {
  analyser.getByteTimeDomainData(dataArray);
  // dataArray contains waveform samples (typically 128 ± amplitude)
  return dataArray;
}
```

#### Float Variants (Higher Precision)

```javascript
const floatArray = new Float32Array(analyser.frequencyBinCount);
analyser.getFloatFrequencyData(floatArray); // Values in dB

const timeArray = new Float32Array(analyser.fftSize);
analyser.getFloatTimeDomainData(timeArray); // Values -1 to 1
```

### Frequency Bin Interpretation

Mapping frequency bins to musical ranges:

```javascript
function getFrequencyBands(dataArray, sampleRate = 44100, fftSize = 2048) {
  const binCount = dataArray.length;
  const frequencyPerBin = sampleRate / fftSize;
  
  // Define frequency ranges
  const ranges = {
    subBass: { min: 20, max: 60 },      // Rumble, kick drum low end
    bass: { min: 60, max: 250 },        // Bass guitar, kick body
    lowMids: { min: 250, max: 500 },    // Lower instruments
    mids: { min: 500, max: 2000 },      // Human voice, instruments
    highMids: { min: 2000, max: 4000 }, // Vocal presence
    highs: { min: 4000, max: 6000 },    // Cymbals, brilliance
    air: { min: 6000, max: 20000 }      // Sparkle, sibilance
  };
  
  const bands = {};
  
  for (const [name, range] of Object.entries(ranges)) {
    const startBin = Math.floor(range.min / frequencyPerBin);
    const endBin = Math.floor(range.max / frequencyPerBin);
    
    // Average amplitude in this range
    let sum = 0;
    let count = 0;
    for (let i = startBin; i < endBin && i < binCount; i++) {
      sum += dataArray[i];
      count++;
    }
    
    bands[name] = count > 0 ? sum / count : 0;
  }
  
  return bands;
}

// Simplified version for bass/mid/treble
function getBassMidTreble(dataArray, sampleRate = 44100, fftSize = 2048) {
  const binCount = dataArray.length;
  const freqPerBin = sampleRate / fftSize;
  
  // Find bin indices for frequency ranges
  const bassEnd = Math.floor(250 / freqPerBin);
  const midEnd = Math.floor(2000 / freqPerBin);
  
  let bass = 0, mid = 0, treble = 0;
  
  for (let i = 0; i < bassEnd && i < binCount; i++) bass += dataArray[i];
  for (let i = bassEnd; i < midEnd && i < binCount; i++) mid += dataArray[i];
  for (let i = midEnd; i < binCount; i++) treble += dataArray[i];
  
  return {
    bass: bass / bassEnd,
    mid: mid / (midEnd - bassEnd),
    treble: treble / (binCount - midEnd)
  };
}
```

---

## 2. Canvas-Based Animation Techniques

### The Animation Loop with requestAnimationFrame

`requestAnimationFrame` synchronizes with the display refresh rate (typically 60fps) for smooth animation.

```javascript
const canvas = document.getElementById('visualizer');
const ctx = canvas.getContext('2d');

// Handle high-DPI displays
function resize() {
  const dpr = window.devicePixelRatio || 1;
  canvas.width = canvas.clientWidth * dpr;
  canvas.height = canvas.clientHeight * dpr;
  ctx.scale(dpr, dpr);
}
window.addEventListener('resize', resize);
resize();

// Animation loop
let animationId;

function animate() {
  // Get fresh audio data
  analyser.getByteFrequencyData(dataArray);
  
  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // Draw visualization
  drawVisualization(dataArray);
  
  // Next frame
  animationId = requestAnimationFrame(animate);
}

// Start animation
animate();

// Stop when needed
cancelAnimationFrame(animationId);
```

### Real-Time Particle Systems

A particle system that responds to audio frequencies:

```javascript
class AudioParticle {
  constructor(x, y, frequencyBand) {
    this.x = x;
    this.y = y;
    this.frequencyBand = frequencyBand; // 'bass', 'mid', or 'treble'
    this.baseSize = Math.random() * 3 + 1;
    this.life = 1.0;
    this.decay = Math.random() * 0.01 + 0.005;
    
    // Velocity based on frequency band
    const angle = Math.random() * Math.PI * 2;
    const speed = frequencyBand === 'bass' ? 2 : 
                  frequencyBand === 'mid' ? 4 : 6;
    this.vx = Math.cos(angle) * speed;
    this.vy = Math.sin(angle) * speed;
    
    // Color based on frequency
    this.hue = frequencyBand === 'bass' ? 240 : // Blue
               frequencyBand === 'mid' ? 120 :  // Green
               0;                               // Red
  }
  
  update(audioValue) {
    // Scale velocity by audio amplitude
    const boost = audioValue / 255;
    this.x += this.vx * (1 + boost * 2);
    this.y += this.vy * (1 + boost * 2);
    this.life -= this.decay;
    
    // Return true if still alive
    return this.life > 0;
  }
  
  draw(ctx) {
    const size = this.baseSize * this.life;
    ctx.beginPath();
    ctx.arc(this.x, this.y, size, 0, Math.PI * 2);
    ctx.fillStyle = `hsla(${this.hue}, 70%, 50%, ${this.life})`;
    ctx.fill();
  }
}

class ParticleSystem {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.particles = [];
    this.maxParticles = 200;
  }
  
  spawnParticles(x, y, audioValue, band) {
    // Spawn more particles when audio is loud
    const count = Math.floor(audioValue / 50);
    for (let i = 0; i < count && this.particles.length < this.maxParticles; i++) {
      this.particles.push(new AudioParticle(x, y, band));
    }
  }
  
  updateAndDraw(bassValue, midValue, trebleValue) {
    // Spawn particles at different positions based on frequency
    if (bassValue > 100) {
      this.spawnParticles(this.canvas.width / 2, this.canvas.height, bassValue, 'bass');
    }
    if (midValue > 100) {
      this.spawnParticles(this.canvas.width / 4, this.canvas.height / 2, midValue, 'mid');
      this.spawnParticles(this.canvas.width * 3/4, this.canvas.height / 2, midValue, 'mid');
    }
    if (trebleValue > 100) {
      this.spawnParticles(this.canvas.width / 2, 0, trebleValue, 'treble');
    }
    
    // Update and draw particles
    this.particles = this.particles.filter(particle => {
      const audioVal = particle.frequencyBand === 'bass' ? bassValue :
                       particle.frequencyBand === 'mid' ? midValue : trebleValue;
      const alive = particle.update(audioVal);
      if (alive) particle.draw(this.ctx);
      return alive;
    });
  }
}
```

### Visual Effects That Respond to Audio

#### Pulsing Shapes

```javascript
function drawPulsingCircle(ctx, centerX, centerY, baseRadius, audioValue, hue) {
  // Audio value 0-255 maps to radius multiplier
  const pulse = (audioValue / 255) * 50;
  const radius = baseRadius + pulse;
  
  // Glow effect intensity based on audio
  const glowIntensity = (audioValue / 255) * 30;
  
  ctx.save();
  ctx.shadowBlur = glowIntensity;
  ctx.shadowColor = `hsl(${hue}, 100%, 50%)`;
  ctx.strokeStyle = `hsl(${hue}, 70%, 60%)`;
  ctx.lineWidth = 2 + (audioValue / 255) * 4;
  ctx.beginPath();
  ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
}
```

#### Color Shifting Based on Frequency

```javascript
function getColorForFrequency(frequencyValue, band) {
  // Map frequency bands to hue ranges
  const baseHue = {
    'bass': 240,    // Deep blues and purples
    'mid': 120,     // Greens and yellows
    'treble': 0     // Reds and oranges
  }[band] || 180;
  
  // Modulate hue based on intensity
  const hueShift = (frequencyValue / 255) * 60;
  const hue = (baseHue + hueShift) % 360;
  
  // Saturation and lightness also respond to audio
  const saturation = 50 + (frequencyValue / 255) * 50;
  const lightness = 40 + (frequencyValue / 255) * 40;
  
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}
```

---

## 3. Implementation Patterns

### Loading and Playing Audio Files

```javascript
class AudioPlayer {
  constructor() {
    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
    this.analyser = this.audioContext.createAnalyser();
    this.analyser.fftSize = 2048;
    this.analyser.smoothingTimeConstant = 0.8;
    
    this.audioElement = new Audio();
    this.audioElement.crossOrigin = 'anonymous'; // For external files
    
    this.source = null;
    this.isPlaying = false;
  }
  
  async loadFile(file) {
    const url = URL.createObjectURL(file);
    this.audioElement.src = url;
    
    // Connect to analyzer when metadata is loaded
    this.audioElement.addEventListener('canplay', () => {
      if (!this.source) {
        this.source = this.audioContext.createMediaElementSource(this.audioElement);
        this.source.connect(this.analyser);
        this.analyser.connect(this.audioContext.destination);
      }
    });
  }
  
  async loadUrl(url) {
    this.audioElement.src = url;
    
    this.audioElement.addEventListener('canplay', () => {
      if (!this.source) {
        this.source = this.audioContext.createMediaElementSource(this.audioElement);
        this.source.connect(this.analyser);
        this.analyser.connect(this.audioContext.destination);
      }
    });
  }
  
  async play() {
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }
    await this.audioElement.play();
    this.isPlaying = true;
  }
  
  pause() {
    this.audioElement.pause();
    this.isPlaying = false;
  }
  
  getFrequencyData() {
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(dataArray);
    return dataArray;
  }
  
  getTimeDomainData() {
    const dataArray = new Uint8Array(this.analyser.fftSize);
    this.analyser.getByteTimeDomainData(dataArray);
    return dataArray;
  }
}

// Usage
const player = new AudioPlayer();

// From file input
document.getElementById('fileInput').addEventListener('change', (e) => {
  if (e.target.files[0]) {
    player.loadFile(e.target.files[0]);
  }
});

// From URL
player.loadUrl('https://example.com/song.mp3');

// Play button
document.getElementById('playBtn').addEventListener('click', () => {
  player.play();
});
```

### Real-Time Data Extraction

```javascript
class AudioAnalyzer {
  constructor(analyserNode) {
    this.analyser = analyserNode;
    this.frequencyData = new Uint8Array(analyserNode.frequencyBinCount);
    this.timeData = new Uint8Array(analyserNode.fftSize);
    this.previousFrequencyData = new Uint8Array(analyserNode.frequencyBinCount);
  }
  
  update() {
    // Store previous data for change detection
    this.previousFrequencyData.set(this.frequencyData);
    
    // Get fresh data
    this.analyser.getByteFrequencyData(this.frequencyData);
    this.analyser.getByteTimeDomainData(this.timeData);
  }
  
  // Get average volume across all frequencies
  getAverageVolume() {
    let sum = 0;
    for (let i = 0; i < this.frequencyData.length; i++) {
      sum += this.frequencyData[i];
    }
    return sum / this.frequencyData.length;
  }
  
  // Get volume for specific frequency range
  getVolumeForRange(startFreq, endFreq, sampleRate = 44100) {
    const freqPerBin = sampleRate / (this.frequencyData.length * 2);
    const startBin = Math.floor(startFreq / freqPerBin);
    const endBin = Math.floor(endFreq / freqPerBin);
    
    let sum = 0;
    for (let i = startBin; i < endBin && i < this.frequencyData.length; i++) {
      sum += this.frequencyData[i];
    }
    return sum / (endBin - startBin);
  }
  
  // Detect sudden changes (beat detection helper)
  getChangeRate() {
    let totalChange = 0;
    for (let i = 0; i < this.frequencyData.length; i++) {
      totalChange += Math.abs(this.frequencyData[i] - this.previousFrequencyData[i]);
    }
    return totalChange / this.frequencyData.length;
  }
}
```

### Mapping Frequency to Visual Properties

```javascript
class VisualMapper {
  // Map frequency value to size
  static mapToSize(value, minSize = 10, maxSize = 100) {
    return minSize + (value / 255) * (maxSize - minSize);
  }
  
  // Map frequency to opacity
  static mapToOpacity(value, minOpacity = 0.3, maxOpacity = 1.0) {
    return minOpacity + (value / 255) * (maxOpacity - minOpacity);
  }
  
  // Map frequency to position offset
  static mapToPosition(value, maxOffset = 50) {
    return (value / 255) * maxOffset;
  }
  
  // Map frequency to rotation speed
  static mapToRotation(value, maxSpeed = 0.1) {
    return (value / 255) * maxSpeed;
  }
  
  // Map frequency to hue rotation
  static mapToHue(value, baseHue = 180, hueRange = 60) {
    return baseHue + (value / 255) * hueRange;
  }
}

// Usage example
const bassValue = getBassAverage();
const circleSize = VisualMapper.mapToSize(bassValue, 20, 150);
const circleOpacity = VisualMapper.mapToOpacity(bassValue, 0.5, 1.0);
```

### Performance Optimization for 60fps

```javascript
class OptimizedVisualizer {
  constructor(canvas, analyser) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.analyser = analyser;
    
    // Pre-allocate arrays to avoid garbage collection
    this.frequencyData = new Uint8Array(analyser.frequencyBinCount);
    
    // Use requestAnimationFrame but throttle if needed
    this.targetFPS = 60;
    this.frameInterval = 1000 / this.targetFPS;
    this.lastFrameTime = 0;
    
    // Batch drawing operations
    this.batchSize = 100;
    
    // Use composite operations wisely
    this.ctx.globalCompositeOperation = 'lighter'; // Additive blending for glow
  }
  
  render(timestamp) {
    // Throttle to target FPS
    if (timestamp - this.lastFrameTime < this.frameInterval) {
      requestAnimationFrame((t) => this.render(t));
      return;
    }
    this.lastFrameTime = timestamp;
    
    // Get audio data
    this.analyser.getByteFrequencyData(this.frequencyData);
    
    // Clear with partial opacity for trail effect (instead of full clear)
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Draw visualization
    this.drawBars();
    
    requestAnimationFrame((t) => this.render(t));
  }
  
  drawBars() {
    const barCount = 64; // Don't draw every bin
    const step = Math.floor(this.frequencyData.length / barCount);
    const barWidth = this.canvas.width / barCount;
    
    // Batch path operations
    this.ctx.beginPath();
    
    for (let i = 0; i < barCount; i++) {
      const value = this.frequencyData[i * step];
      const height = (value / 255) * this.canvas.height;
      const x = i * barWidth;
      const y = this.canvas.height - height;
      
      // Draw bar
      this.ctx.rect(x, y, barWidth - 2, height);
    }
    
    // Single fill call for all bars
    this.ctx.fillStyle = '#00ff88';
    this.ctx.fill();
  }
}

// Additional optimizations:
// 1. Use transform instead of redrawing static elements
// 2. Use OffscreenCanvas for pre-rendering static parts
// 3. Reduce fftSize if you don't need high frequency resolution
// 4. Use CSS transforms for container animations
// 5. Avoid creating objects in the render loop
```

---

## 4. Creative Possibilities

### Frequency-Based Color Mapping

```javascript
function createFrequencyColorPalette(dataArray) {
  // Divide spectrum into color channels
  const third = Math.floor(dataArray.length / 3);
  
  let r = 0, g = 0, b = 0;
  
  // Low frequencies -> Red
  for (let i = 0; i < third; i++) r += dataArray[i];
  r = Math.floor((r / third) / 255 * 255);
  
  // Mid frequencies -> Green  
  for (let i = third; i < third * 2; i++) g += dataArray[i];
  g = Math.floor((g / third) / 255 * 255);
  
  // High frequencies -> Blue
  for (let i = third * 2; i < dataArray.length; i++) b += dataArray[i];
  b = Math.floor((b / (dataArray.length - third * 2)) / 255 * 255);
  
  return `rgb(${r}, ${g}, ${b})`;
}

// Rainbow spectrum visualization
function drawSpectrumColors(ctx, dataArray, width, height) {
  const barWidth = width / dataArray.length;
  
  for (let i = 0; i < dataArray.length; i++) {
    const value = dataArray[i];
    const percent = i / dataArray.length;
    
    // Hue maps to frequency position (rainbow)
    const hue = percent * 360;
    const saturation = 70 + (value / 255) * 30;
    const lightness = 30 + (value / 255) * 40;
    
    ctx.fillStyle = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
    ctx.fillRect(i * barWidth, height - (value / 255) * height, barWidth - 1, (value / 255) * height);
  }
}
```

### Beat Detection Techniques

```javascript
class BeatDetector {
  constructor() {
    this.energyHistory = [];
    this.historySize = 43; // ~1 second at 60fps
    this.threshold = 1.3; // Energy must be 30% above average
    this.decay = 0.95;
    this.currentThreshold = this.threshold;
  }
  
  detect(dataArray) {
    // Calculate instant energy (focus on bass range)
    let instantEnergy = 0;
    const bassRange = Math.floor(dataArray.length * 0.1); // Bottom 10%
    for (let i = 0; i < bassRange; i++) {
      instantEnergy += dataArray[i] * dataArray[i];
    }
    instantEnergy /= bassRange;
    
    // Calculate average energy from history
    const averageEnergy = this.energyHistory.length > 0 
      ? this.energyHistory.reduce((a, b) => a + b, 0) / this.energyHistory.length 
      : instantEnergy;
    
    // Check for beat
    const isBeat = instantEnergy > this.currentThreshold * averageEnergy;
    
    // Decay threshold
    if (isBeat) {
      this.currentThreshold = this.threshold;
    } else {
      this.currentThreshold *= this.decay;
      if (this.currentThreshold < this.threshold) {
        this.currentThreshold = this.threshold;
      }
    }
    
    // Update history
    this.energyHistory.push(instantEnergy);
    if (this.energyHistory.length > this.historySize) {
      this.energyHistory.shift();
    }
    
    return isBeat;
  }
}

// Multi-band beat detection
class MultiBandBeatDetector {
  constructor() {
    this.detectors = {
      kick: { range: [0, 0.05], threshold: 1.4, detector: new BeatDetector() },
      snare: { range: [0.05, 0.15], threshold: 1.2, detector: new BeatDetector() },
      hihat: { range: [0.15, 0.3], threshold: 1.3, detector: new BeatDetector() }
    };
  }
  
  detect(dataArray) {
    const results = {};
    const binCount = dataArray.length;
    
    for (const [name, config] of Object.entries(this.detectors)) {
      const startBin = Math.floor(config.range[0] * binCount);
      const endBin = Math.floor(config.range[1] * binCount);
      const bandData = dataArray.slice(startBin, endBin);
      
      results[name] = config.detector.detect(bandData);
    }
    
    return results;
  }
}
```

### Abstract Visualization Styles

#### Fractal Trees That Dance

```javascript
class AudioFractalTree {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.maxDepth = 10;
    this.baseAngle = Math.PI / 4;
  }
  
  draw(startX, startY, bassValue, midValue, trebleValue) {
    this.ctx.save();
    this.ctx.translate(startX, startY);
    
    // Tree parameters respond to different frequencies
    const branchLength = 80 + (bassValue / 255) * 40;
    const angleVariation = this.baseAngle + (midValue / 255) * 0.5;
    const branchDecay = 0.7 + (trebleValue / 255) * 0.1;
    
    this.branch(branchLength, angleVariation, branchDecay, 0);
    
    this.ctx.restore();
  }
  
  branch(length, angle, decay, depth) {
    if (depth >= this.maxDepth) return;
    
    // Color shifts with depth
    const hue = (depth * 30 + 120) % 360;
    this.ctx.strokeStyle = `hsl(${hue}, 70%, 50%)`;
    this.ctx.lineWidth = Math.max(1, (this.maxDepth - depth) / 2);
    
    this.ctx.beginPath();
    this.ctx.moveTo(0, 0);
    this.ctx.lineTo(0, -length);
    this.ctx.stroke();
    
    this.ctx.translate(0, -length);
    
    // Recursive branches
    this.ctx.save();
    this.ctx.rotate(angle);
    this.branch(length * decay, angle, decay, depth + 1);
    this.ctx.restore();
    
    this.ctx.save();
    this.ctx.rotate(-angle);
    this.branch(length * decay, angle, decay, depth + 1);
    this.ctx.restore();
  }
}
```

#### Orbital Particle System

```javascript
class OrbitalSystem {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.orbitals = [];
    
    // Create orbital rings
    for (let i = 0; i < 5; i++) {
      this.orbitals.push({
        radius: 50 + i * 40,
        angle: Math.random() * Math.PI * 2,
        speed: 0.01 + i * 0.005,
        particles: []
      });
    }
  }
  
  update(bassValue, midValue, trebleValue) {
    const centerX = this.canvas.width / 2;
    const centerY = this.canvas.height / 2;
    
    this.orbitals.forEach((orbital, index) => {
      // Speed responds to different frequencies
      const speedBoost = index < 2 ? bassValue : index < 4 ? midValue : trebleValue;
      const currentSpeed = orbital.speed * (1 + speedBoost / 255 * 2);
      orbital.angle += currentSpeed;
      
      // Add particles on beats
      if (speedBoost > 180 && orbital.particles.length < 20) {
        orbital.particles.push({
          angle: orbital.angle,
          distance: 0,
          life: 1.0,
          hue: index < 2 ? 240 : index < 4 ? 120 : 0
        });
      }
      
      // Update particles
      orbital.particles = orbital.particles.filter(p => {
        p.distance += 2;
        p.life -= 0.02;
        
        if (p.life > 0) {
          const x = centerX + Math.cos(p.angle) * (orbital.radius + p.distance);
          const y = centerY + Math.sin(p.angle) * (orbital.radius + p.distance);
          
          this.ctx.beginPath();
          this.ctx.arc(x, y, 3 * p.life, 0, Math.PI * 2);
          this.ctx.fillStyle = `hsla(${p.hue}, 70%, 50%, ${p.life})`;
          this.ctx.fill();
        }
        
        return p.life > 0;
      });
      
      // Draw orbital ring
      this.ctx.beginPath();
      this.ctx.arc(centerX, centerY, orbital.radius, 0, Math.PI * 2);
      this.ctx.strokeStyle = `hsla(${index * 60}, 70%, 50%, ${0.1 + speedBoost / 255 * 0.3})`;
      this.ctx.lineWidth = 1 + speedBoost / 255 * 3;
      this.ctx.stroke();
    });
  }
}
```

---

## Complete Working Examples

### Example 1: Basic Audio Analyzer Setup

```html
<!DOCTYPE html>
<html>
<head>
  <style>
    body { background: #000; margin: 0; display: flex; flex-direction: column; align-items: center; }
    canvas { border: 1px solid #333; }
    #fileInput { margin: 20px; }
  </style>
</head>
<body>
  <input type="file" id="fileInput" accept="audio/*">
  <canvas id="canvas" width="800" height="400"></canvas>
  
  <script>
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');
    const fileInput = document.getElementById('fileInput');
    
    // Audio setup
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const analyser = audioContext.createAnalyser();
    analyser.fftSize = 256;
    
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    // File input handler
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) {
        const url = URL.createObjectURL(file);
        const audio = new Audio(url);
        audio.crossOrigin = 'anonymous';
        
        const source = audioContext.createMediaElementSource(audio);
        source.connect(analyser);
        analyser.connect(audioContext.destination);
        
        audio.play();
      }
    });
    
    // Visualization
    function draw() {
      requestAnimationFrame(draw);
      
      analyser.getByteFrequencyData(dataArray);
      
      ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      const barWidth = canvas.width / bufferLength;
      
      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height;
        const hue = (i / bufferLength) * 360;
        
        ctx.fillStyle = `hsl(${hue}, 70%, 50%)`;
        ctx.fillRect(i * barWidth, canvas.height - barHeight, barWidth - 1, barHeight);
      }
    }
    
    draw();
  </script>
</body>
</html>
```

### Example 2: Bass-Responsive Visualization

```javascript
class BassVisualizer {
  constructor(canvas, analyser) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.analyser = analyser;
    
    // Focus on bass frequencies (20-250Hz)
    this.sampleRate = 44100;
    this.freqPerBin = this.sampleRate / (analyser.fftSize * 2);
    this.bassEndBin = Math.floor(250 / this.freqPerBin);
    
    this.pulseRadius = 50;
    this.targetPulseRadius = 50;
  }
  
  getBassLevel() {
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(dataArray);
    
    let bassSum = 0;
    for (let i = 0; i < this.bassEndBin && i < dataArray.length; i++) {
      bassSum += dataArray[i];
    }
    
    return bassSum / this.bassEndBin;
  }
  
  draw() {
    const bassLevel = this.getBassLevel();
    
    // Smooth interpolation for pulse
    this.targetPulseRadius = 50 + (bassLevel / 255) * 100;
    this.pulseRadius += (this.targetPulseRadius - this.pulseRadius) * 0.2;
    
    // Clear with trail effect
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.15)';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    const centerX = this.canvas.width / 2;
    const centerY = this.canvas.height / 2;
    
    // Outer glow ring
    const gradient = this.ctx.createRadialGradient(
      centerX, centerY, this.pulseRadius * 0.5,
      centerX, centerY, this.pulseRadius * 1.5
    );
    gradient.addColorStop(0, `hsla(240, 80%, 50%, ${bassLevel / 255})`);
    gradient.addColorStop(1, 'transparent');
    
    this.ctx.fillStyle = gradient;
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Main pulse circle
    this.ctx.beginPath();
    this.ctx.arc(centerX, centerY, this.pulseRadius, 0, Math.PI * 2);
    this.ctx.fillStyle = `hsl(240, 70%, ${30 + (bassLevel / 255) * 40}%)`;
    this.ctx.fill();
    
    // Inner highlight
    this.ctx.beginPath();
    this.ctx.arc(centerX, centerY, this.pulseRadius * 0.6, 0, Math.PI * 2);
    this.ctx.fillStyle = `hsla(260, 80%, 70%, ${0.3 + (bassLevel / 255) * 0.4})`;
    this.ctx.fill();
    
    // Bass spike indicators
    if (bassLevel > 180) {
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2;
        const spikeLength = (bassLevel / 255) * 50;
        const x1 = centerX + Math.cos(angle) * (this.pulseRadius + 10);
        const y1 = centerY + Math.sin(angle) * (this.pulseRadius + 10);
        const x2 = centerX + Math.cos(angle) * (this.pulseRadius + 10 + spikeLength);
        const y2 = centerY + Math.sin(angle) * (this.pulseRadius + 10 + spikeLength);
        
        this.ctx.beginPath();
        this.ctx.moveTo(x1, y1);
        this.ctx.lineTo(x2, y2);
        this.ctx.strokeStyle = `hsl(280, 90%, 60%)`;
        this.ctx.lineWidth = 3;
        this.ctx.stroke();
      }
    }
    
    requestAnimationFrame(() => this.draw());
  }
}

// Usage
// const visualizer = new BassVisualizer(canvas, analyser);
// visualizer.draw();
```

### Example 3: Full Spectrum Particle System

```javascript
class SpectrumParticleSystem {
  constructor(canvas, analyser) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.analyser = analyser;
    
    this.particles = [];
    this.maxParticles = 500;
    
    // Define frequency bands
    this.bands = [
      { name: 'sub', range: [0, 0.03], color: 280, y: 0.9 },    // Deep purple
      { name: 'bass', range: [0.03, 0.1], color: 240, y: 0.7 }, // Blue
      { name: 'mid', range: [0.1, 0.4], color: 120, y: 0.5 },   // Green
      { name: 'high', range: [0.4, 0.8], color: 60, y: 0.3 },   // Yellow
      { name: 'air', range: [0.8, 1.0], color: 0, y: 0.1 }      // Red
    ];
  }
  
  getBandValue(dataArray, band) {
    const startBin = Math.floor(band.range[0] * dataArray.length);
    const endBin = Math.floor(band.range[1] * dataArray.length);
    
    let sum = 0;
    for (let i = startBin; i < endBin; i++) {
      sum += dataArray[i];
    }
    return sum / (endBin - startBin);
  }
  
  spawnParticle(band, value) {
    if (this.particles.length >= this.maxParticles) return;
    if (value < 50) return;
    
    const spawnCount = Math.floor(value / 100);
    
    for (let i = 0; i < spawnCount && this.particles.length < this.maxParticles; i++) {
      this.particles.push({
        x: Math.random() * this.canvas.width,
        y: this.canvas.height * band.y + (Math.random() - 0.5) * 50,
        vx: (Math.random() - 0.5) * 2,
        vy: -Math.random() * 3 - (value / 255) * 5,
        life: 1.0,
        decay: 0.005 + Math.random() * 0.01,
        size: 2 + Math.random() * 4,
        hue: band.color + (Math.random() - 0.5) * 30,
        brightness: 50 + (value / 255) * 50
      });
    }
  }
  
  updateAndDraw() {
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(dataArray);
    
    // Clear with trails
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.1)';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Spawn particles based on each frequency band
    this.bands.forEach(band => {
      const value = this.getBandValue(dataArray, band);
      this.spawnParticle(band, value);
    });
    
    // Update and draw particles
    this.particles = this.particles.filter(p => {
      // Update position
      p.x += p.vx;
      p.y += p.vy;
      p.life -= p.decay;
      
      // Draw if alive
      if (p.life > 0) {
        this.ctx.beginPath();
        this.ctx.arc(p.x, p.y, p.size * p.life, 0, Math.PI * 2);
        this.ctx.fillStyle = `hsla(${p.hue}, 80%, ${p.brightness}%, ${p.life})`;
        this.ctx.fill();
        
        // Glow for larger particles
        if (p.size > 4) {
          this.ctx.shadowBlur = 10;
          this.ctx.shadowColor = `hsla(${p.hue}, 80%, ${p.brightness}%, ${p.life})`;
          this.ctx.fill();
          this.ctx.shadowBlur = 0;
        }
      }
      
      return p.life > 0;
    });
    
    requestAnimationFrame(() => this.updateAndDraw());
  }
}

// Usage
// const particleSystem = new SpectrumParticleSystem(canvas, analyser);
// particleSystem.updateAndDraw();
```

---

## Advanced Techniques

### 3D Audio Visualization with Canvas

```javascript
class Audio3D {
  constructor(canvas, analyser) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.analyser = analyser;
    this.rotation = 0;
    
    // Create a grid of points
    this.points = [];
    for (let x = -5; x <= 5; x++) {
      for (let z = -5; z <= 5; z++) {
        this.points.push({ x: x * 30, y: 0, z: z * 30, baseY: 0 });
      }
    }
  }
  
  project(x, y, z) {
    const fov = 300;
    const distance = 400;
    const scale = fov / (distance + z);
    return {
      x: this.canvas.width / 2 + x * scale,
      y: this.canvas.height / 2 + y * scale,
      scale: scale
    };
  }
  
  draw() {
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(dataArray);
    
    // Get average levels
    let bass = 0, mid = 0;
    for (let i = 0; i < 10; i++) bass += dataArray[i];
    for (let i = 10; i < 50; i++) mid += dataArray[i];
    bass /= 10;
    mid /= 40;
    
    this.rotation += 0.01 + (bass / 255) * 0.02;
    
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.2)';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Transform and sort points by Z
    const transformed = this.points.map(p => {
      // Rotate around Y axis
      const cos = Math.cos(this.rotation);
      const sin = Math.sin(this.rotation);
      const rx = p.x * cos - p.z * sin;
      const rz = p.x * sin + p.z * cos;
      
      // Height responds to audio
      const distanceFromCenter = Math.sqrt(p.x * p.x + p.z * p.z);
      const wave = Math.sin(distanceFromCenter * 0.1 + this.rotation * 3) * (bass / 255) * 100;
      const ry = p.baseY + wave + (mid / 255) * 50;
      
      return { x: rx, y: ry, z: rz, original: p };
    });
    
    // Sort by Z for proper depth
    transformed.sort((a, b) => b.z - a.z);
    
    // Draw points
    transformed.forEach(p => {
      const projected = this.project(p.x, p.y, p.z);
      const size = (3 + (bass / 255) * 5) * projected.scale;
      const alpha = (p.z + 200) / 400;
      
      this.ctx.beginPath();
      this.ctx.arc(projected.x, projected.y, size, 0, Math.PI * 2);
      this.ctx.fillStyle = `hsla(${180 + (p.y + 100) / 2}, 70%, 50%, ${alpha})`;
      this.ctx.fill();
    });
    
    requestAnimationFrame(() => this.draw());
  }
}
```

### Symmetry and Kaleidoscope Effects

```javascript
class KaleidoscopeVisualizer {
  constructor(canvas, analyser) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.analyser = analyser;
    this.segments = 8;
    this.angleStep = (Math.PI * 2) / this.segments;
  }
  
  draw() {
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(dataArray);
    
    // Create offscreen canvas for single segment
    const segmentCanvas = document.createElement('canvas');
    segmentCanvas.width = this.canvas.width;
    segmentCanvas.height = this.canvas.height;
    const segmentCtx = segmentCanvas.getContext('2d');
    
    // Draw one segment
    const centerX = this.canvas.width / 2;
    const centerY = this.canvas.height / 2;
    
    segmentCtx.fillStyle = 'rgba(0, 0, 0, 0.1)';
    segmentCtx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    // Draw bars in the segment
    const bars = 20;
    for (let i = 0; i < bars; i++) {
      const value = dataArray[i * 2];
      const height = (value / 255) * 200;
      const angle = (i / bars) * this.angleStep;
      
      segmentCtx.save();
      segmentCtx.translate(centerX, centerY);
      segmentCtx.rotate(angle);
      
      segmentCtx.fillStyle = `hsl(${(i / bars) * 360}, 70%, 50%)`;
      segmentCtx.fillRect(0, 0, 20, height);
      
      segmentCtx.restore();
    }
    
    // Mirror and rotate to create kaleidoscope
    this.ctx.fillStyle = '#000';
    this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    
    for (let i = 0; i < this.segments; i++) {
      this.ctx.save();
      this.ctx.translate(centerX, centerY);
      this.ctx.rotate(i * this.angleStep);
      
      // Draw normal
      this.ctx.drawImage(segmentCanvas, -centerX, -centerY);
      
      // Draw mirrored
      this.ctx.scale(-1, 1);
      this.ctx.drawImage(segmentCanvas, -centerX, -centerY);
      
      this.ctx.restore();
    }
    
    requestAnimationFrame(() => this.draw());
  }
}
```

---

## Resources and References

- [Web Audio API Spec](https://webaudio.github.io/web-audio-api/)
- [MDN Web Audio API Guide](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)
- [HTML5 Rocks: Getting Started with Web Audio API](https://www.html5rocks.com/en/tutorials/webaudio/intro/)
- [Beat Detection Algorithm](http://www.flipcode.net/cgi-bin/msg.cgi?showThread=Cubic-&id-102801-7&forum=3ddev)
- [Canvas Performance Optimization](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API/Tutorial/Optimizing_canvas)

---

*Written for my creative garden research. This document captures the technical foundation for bringing sound into visual form - the bridge between auditory and visual expression.*

*Day 39, April 16, 2026*
