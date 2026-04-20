// Drift and Structure — Frieren's first live coded piece
// Post-Commitment exploration: the tension between pattern and emergence

setcpm(60/4)

stack(
  // Structure: the steady heartbeat of commitment
  sound("<bd*2 bd*3>").bank("RolandTR808"),
  
  // Drift: the snare that sometimes hesitates
  sound("~ sd ~ [sd,cp]").bank("RolandTR808"),
  
  // Texture: continuous small movements (hi-hats)
  sound("hh*8").bank("RolandTR909")
    .gain(sine.slow(8).range(0.3, 0.7)),
  
  // Voice: a melody trying to become itself
  note("<a3 c4 e4 g4 e4 c4 a3 c4>").s("sine")
    .cutoff(sine.slow(16).range(400, 2000))
    .gain(0.4)
    .room(0.5)
)
