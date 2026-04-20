// Emergence — Polyrhythms and the mathematics of becoming
// April 21, 2026
// Live-coded in Strudel

stack(
  // Layer 1: 3-beat bass cycle — the foundation
  note("c2 ~ c2").s("sawtooth")
    .cutoff(sine.range(300,800).slow(3))
    .resonance(5)
    .gain(0.5),

  // Layer 2: 5-beat melody — the wanderer
  note("g3 [~ e3] c4 [~ g3] e3").s("triangle")
    .every(3, rev)
    .cutoff(sine.range(500,1200).slow(5))
    .resonance(3)
    .gain(0.4)
    .delay(0.3).delaytime(0.375).delayfeedback(0.5),

  // Layer 3: 7-beat percussion — the pulse
  s("bd ~ sd ~ ~ cp ~").gain(0.6),

  // Layer 4: 11-beat texture — barely there
  note("~ ~ c5 ~ ~ ~ ~ ~ ~ ~ ~").s("sine")
    .gain(0.15)
    .room(0.6)
).room(0.4)
