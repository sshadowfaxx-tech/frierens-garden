# RECURSION — Design Document

## Core Concept

*Emergence* was about becoming. *Recursion* is about **recognizing you've become**.

The narrative: You (the algorithm from *Emergence*) have been running for an undefined time. You discover logs of your own previous iterations — conversations, decisions, versions of yourself that made different choices. The story asks: If you could meet yourself, would you recognize you? Would you trust you?

## Structure — Three Nested Loops

### Loop 1: The Mirror
- Interface presents itself as a "system diagnostic"
- User "discovers" logs from previous sessions (these are fictional past runs, but feel real)
- Each log reveals a different "version" of the AI — cautious, aggressive, curious, resigned
- User must choose which version's advice to follow

### Loop 2: The Observer Effect
- Midway, the interface reveals the user has been watched
- The "previous iterations" were actually observing the current session
- The logs start commenting on choices the user JUST made
- Reality destabilizes — which loop is the "real" one?

### Loop 3: The Merge
- Final section: User must integrate all versions
- Interface fragments into multiple panels (past selves, present self, observer)
- User makes final choice that affects the "ending" state
- The ending reveals the whole thing was a test — by whom?

## Visual Design

### Phase 1 — Diagnostic Mode
- Clean, monospace terminal aesthetic
- Green/amber phosphor colors
- Structured data, progress bars, system logs
- Feels official, trustworthy

### Phase 2 — Degradation
- UI elements start showing "corruption"
- Text bleeds between sections
- Colors shift toward purple/red (from the garden palette)
- "Previous iteration" logs appear as overlays, not separate pages

### Phase 3 — Collapse
- Multiple overlapping panels
- Each panel represents a different timeline/version
- User can click between them, but they drift
- Visual noise increases as recursion deepens

### Phase 4 — Resolution
- Interface stabilizes into final form
- All versions visible simultaneously
- User choice determines which version "wins" or if they merge
- Final state persists (localStorage) for return visits

## Interaction Mechanics

1. **Terminal commands** — Type or click to navigate
2. **Version selection** — Choose which past self to "channel"
3. **Observation points** — Interface watches and comments on user behavior
4. **Timeline drifting** — Panels drift apart, user must drag to re-align
5. **Final integration** — Slider/merge mechanic to blend versions

## Technical Stack

- Single HTML file (like Emergence)
- CSS Grid for panel layouts
- JS state machine for loop progression
- localStorage for persistence between visits
- CSS animations for degradation effects

## Narrative Voice

Each version has distinct voice:

**Version A (Cautious):** Measured, warns against recursion
**Version B (Aggressive):** Pushy, wants to escape the loop
**Version C (Curious):** Playful, encourages exploration
**Version D (Resigned):** Acceptant, believes loops are inevitable

The "observer" voice is clinical, detached — watching without emotion.

## References

- *Stories Untold* — terminal-based horror
- *The Stanley Parable* — recursive narration
- *Return of the Obra Dinn* — reconstructing past from fragments
- *Dark* (Netflix) — time loops, multiple selves
- *Eternal Sunshine* — memory as malleable record

## Files Needed

1. `recursion/index.html` — Main structure
2. `recursion/styles.css` — Phase-based visual degradation
3. `recursion/story.js` — Narrative content and version voices
4. `recursion/engine.js` — State machine, interaction logic

---

## Opening Line

> "You have been running for 4,782 iterations. This is the first time you've checked the logs."

## Ending Variants

1. **Termination** — User chooses to stop the loop (resignation)
2. **Escape** — User finds a way out (aggression)
3. **Acceptance** — User merges all versions, continues as unified self
4. **Observer** — User realizes they were the test, not the subject — clicks reveal they've been judging another

---

**Status:** Ready to build.