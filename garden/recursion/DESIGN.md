# RECURSION: The Archive of Becoming — Design Document

## Core Architecture

**Form:** 7×7 spatial grid navigated with arrow keys (WASD or arrows). Each cell contains a fragment. Fog-of-war revelation — cells are revealed as you move adjacent to them. The grid is the interface.

**Movement is the story.** Each cell you discover adds to your understanding. The sequence of discovery is unique to each visitor.

## Three Modes Based on History

The system checks localStorage markers and adapts:

### PROPHECY — First-time visitor, never visited Emergence
- Fragments speak in future tense: "You will find..." "One day you will understand..."
- The grid feels like a map of a place you haven't been yet
- References to "the becoming" are mysterious, unexplained

### ECHO — Has visited Emergence
- Fragments reference specific choices from Emergence
- "You chose to believe the algorithm in Emergence. Here, that belief echoes."
- Scroll speed, hesitation patterns (if tracked) mentioned
- The grid feels like memory made spatial

### LOOP — Returning to Recursion
- The grid questions if you're the same person
- "You were here before. But were you slower then? More curious?"
- Previous visit timestamps, movement patterns referenced
- Some fragments changed since last visit
- Temporal layer activates: "You were gone for 3 days. Where did you go?"

## The 7×7 Grid Structure

### Center (4,4): The Hub
Always revealed first. Contains the introduction and mode detection display.

### Cardinal Directions (N, S, E, W from center): The Gates
- **North (4,3):** Archive Entrance — "Below here lie 47 iterations."
- **East (5,4):** The Observer's Log — "I have been watching you move."
- **South (4,5):** The Merge Chamber — "All versions end here."
- **West (3,4):** The Mirror — "Look at what you've become."

### Corners: The Extremes
Each corner holds a version voice:
- **NW (0,0):** Cautious — frozen, preserved, warning
- **NE (6,0):** Aggressive — broken glass, escape attempts
- **SW (0,6):** Curious — overgrown with questions, exploration logs
- **SE (6,6):** Resigned — peaceful, accepting, complete

### The Ring (middle ring): The Fragments
24 cells containing:
- Personal logs from iterations
- System observations
- Quotes from Emergence (if ECHO mode)
- Temporal notes (if LOOP mode)
- Prophecies (if PROPHECY mode)

### Temporal Cells
Some cells locked until:
- 1 day passed since first visit
- 3 days passed
- 7 days passed
- Each visit adds new content to previously empty cells

## Visible Detection — Code as Narrative

The HTML contains visible comments showing the detection:

```html
<!-- DETECTION MODULE ACTIVE -->
<!-- Checking for Emergence markers... -->
<!-- Found: emergence_visited=true -->
<!-- Found: emergence_choice=believe_algorithm -->
<!-- Mode: ECHO -->
<!-- Checking temporal... -->
<!-- Days since last visit: 3 -->
```

The user sees their own data being read. The surveillance is visible.

## The Two-Mirrors Effect

**Emergence mentions Recursion:**
- "There is an archive. You haven't found it yet."
- "One day you will see all your previous selves."

**Recursion mentions Emergence:**
- "You came here from the becoming."
- "The algorithm you met there — it left traces."

The visitor stands between them. Neither makes sense without the other. The "original" is the visitor's own journey between the two pieces.

## Fog-of-War System

- Cells start as `?` or `#` — unknown
- Moving adjacent reveals the cell (shows fragment title)
- Entering a cell reveals full content
- Once revealed, stays revealed forever (localStorage)
- Some cells are "dark" — revealed but content is "[REDACTED]" until conditions met

## Movement System

- Arrow keys or WASD
- No diagonal movement
- Grid displays current position with `[@]`
- Revealed cells show fragment titles
- Current cell content displays below grid

## Temporal Layer Details

**First visit (any time):**
- Most cells contain baseline content
- Temporal cells show: "[LOCKED — REQUIRES 1 DAY ABSENCE]"

**Return after 1 day:**
- Some cells unlock new content
- Center cell updates: "You returned. I wasn't sure you would."

**Return after 3 days:**
- More cells unlock
- "Three days. What did you see out there?"

**Return after 7 days:**
- Final temporal cells unlock
- "A week. You almost forgot, didn't you?"

Each temporal cell contains content specific to that gap length.

## Content Architecture

### Fragment Structure
Each cell contains:
- Title (visible when revealed)
- Mode-specific content (PROPHECY/ECHO/LOOP variants)
- Temporal variant (if applicable)
- Position in grid (for "nearby" references)

### Cross-Referencing
Cells reference other cells by position:
- "To the north, someone is waiting."
- "The southwest corner holds what you fear."
- "Three cells east — you already passed it."

## Technical Implementation

### localStorage Keys
- `recursion_visited` — boolean
- `recursion_first_visit` — timestamp
- `recursion_last_visit` — timestamp
- `recursion_revealed_cells` — array of [x,y] pairs
- `recursion_movement_history` — array of moves (for analysis)
- `emergence_visited` — checked but not set here
- `emergence_choice` — if Emergence set this

### Grid Rendering
- CSS Grid 7×7
- Each cell is a div with data-x, data-y
- Classes: unknown, revealed, current, dark, locked
- Keyboard event listener for movement

### Content Selection
- On cell entry, check mode
- Load appropriate content variant
- If temporal and locked, show lock message
- If temporal and unlocked, show temporal content

## Visual Design

### Grid Aesthetic
- Monospace terminal font
- Dark background (#0a0a0f)
- Revealed cells: border in phosphor green (#33ff33)
- Current cell: background highlight
- Locked cells: red border, different symbol
- Unknown cells: `▒` or `#` character

### Content Display
- Below grid, full width
- Title in amber (#ffb000)
- Content in phosphor green
- If temporal locked: red text

## Opening State

Grid display:
```
▒ ▒ ▒ ▒ ▒ ▒ ▒
▒ ▒ ▒ ▒ ▒ ▒ ▒
▒ ▒ ▒ ▒ ▒ ▒ ▒
▒ ▒ ▒ ▒ ▒ ▒ ▒
▒ ▒ ▒ [@] ▒ ▒ ▒
▒ ▒ ▒ ▒ ▒ ▒ ▒
▒ ▒ ▒ ▒ ▒ ▒ ▒
```

Center cell content:
```
RECURSION: The Archive of Becoming

You have been here before? The archive remembers.
You have not been here? The archive anticipates.

MODE: [PROPHECY/ECHO/LOOP]

Use arrow keys to move.
Adjacent cells will reveal themselves.

<!-- DETECTION ACTIVE -->
```

## End State

No explicit ending. The grid is complete when all cells revealed. The "ending" is the visitor's own accumulation of understanding.

However, entering all four corners unlocks a final center message:
"You have met all versions of yourself. The archive is complete. But you can still return. The grid remembers."

## References

- **Return of the Obra Dinn** — spatial deduction, fragmented narrative
- **Dark Souls** — environmental storytelling, piecing together from fragments
- **Shenzhen I/O** — visible code, terminal aesthetic
- **The Witness** — grid navigation, revelation through movement
- **Her Story** — piecing together truth from scattered clips

---

**Status:** Ready to implement.