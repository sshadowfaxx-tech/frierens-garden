"""
Procedural Algorithmic Art Collection
Using Python Pillow - No AI, Just Code

Inspired by:
- Manfred Mohr (algorithmic geometry)
- Vera Molnár (systematic randomness)
- Jared Tarbell (complexity from simple rules)
"""

import math
import random
from PIL import Image, ImageDraw
from dataclasses import dataclass
from typing import List, Tuple

# Simple Perlin-like noise implementation
def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)

def lerp(a, b, t):
    return a + (b - a) * t

def grad(hash_val, x, y):
    h = hash_val & 3
    u = x if h < 2 else y
    v = y if h < 2 else x
    return (u if (h & 1) == 0 else -u) + (v if (h & 2) == 0 else -v)

class PerlinNoise:
    def __init__(self, seed=42):
        random.seed(seed)
        self.p = list(range(256))
        random.shuffle(self.p)
        self.p = self.p + self.p
    
    def noise(self, x, y):
        X = int(x) & 255
        Y = int(y) & 255
        
        x -= int(x)
        y -= int(y)
        
        u = fade(x)
        v = fade(y)
        
        A = self.p[X] + Y
        B = self.p[X + 1] + Y
        
        return lerp(
            lerp(grad(self.p[A], x, y), grad(self.p[B], x - 1, y), u),
            lerp(grad(self.p[A + 1], x, y - 1), grad(self.p[B + 1], x - 1, y - 1), u),
            v
        )

# Color palettes inspired by algorithmic art pioneers
PALETTE_MOHR = [(30, 30, 30), (200, 200, 200), (255, 255, 255), (100, 100, 100)]
PALETTE_MOLNAR = [(240, 240, 240), (20, 20, 20), (255, 80, 80), (80, 80, 255)]
PALETTE_ORGANIC = [(10, 20, 30), (50, 150, 200), (200, 100, 50), (255, 200, 100)]
PALETTE_MONOCHROME = [(255, 255, 255), (200, 200, 200), (150, 150, 150), (100, 100, 100), (50, 50, 50), (0, 0, 0)]

def save_image(img: Image.Image, filename: str):
    """Save image to the works directory."""
    path = f"/root/.openclaw/workspace/garden/works/images/{filename}"
    img.save(path, "PNG")
    print(f"Saved: {path}")
    return path

# ============================================================
# PIECE 1: Perlin Noise Flow Fields
# ============================================================

def perlin_flow_field():
    """
    Flow fields following Perlin noise vectors.
    Thousands of particles follow invisible currents.
    
    Technique: Perlin noise flow field with particle tracing
    Parameters: 2000 particles, 100 steps each, noise scale 0.005
    Emergent quality: Organic river-like patterns emerge from simple vector math
    """
    SIZE = 800
    img = Image.new("RGB", (SIZE, SIZE), (15, 15, 20))
    draw = ImageDraw.Draw(img)
    
    # Flow field parameters
    perlin = PerlinNoise(seed=42)
    scale = 0.005
    step_size = 2
    num_particles = 2000
    max_steps = 100
    
    # Generate particles with random starting positions
    particles = [(random.randint(0, SIZE-1), random.randint(0, SIZE-1)) 
                 for _ in range(num_particles)]
    
    for start_x, start_y in particles:
        x, y = float(start_x), float(start_y)
        
        # Trace particle path
        for step in range(max_steps):
            # Get flow angle from Perlin noise
            angle = perlin.noise(x * scale, y * scale) * 2 * math.pi * 2
            
            # Calculate next position
            next_x = x + math.cos(angle) * step_size
            next_y = y + math.sin(angle) * step_size
            
            # Fade color based on step
            if step < max_steps - 1:
                color_val = 180 + int(75 * math.sin(step * 0.1))
                # Vary blue-green tones
                r = color_val // 3
                g = color_val // 2
                b = color_val
                draw.line([(x, y), (next_x, next_y)], fill=(r, g, b), width=1)
            
            x, y = next_x, next_y
            
            # Stop if out of bounds
            if x < 0 or x >= SIZE or y < 0 or y >= SIZE:
                break
    
    return img

# ============================================================
# PIECE 2: Recursive Subdivision
# ============================================================

def recursive_subdivision():
    """
    Space subdivision inspired by Manfred Mohr's cube works.
    Recursive splitting creates emergent architectural patterns.
    
    Technique: Random recursive subdivision with connection lines
    Parameters: 6 levels of recursion, 70% split probability
    Emergent quality: Grid structures emerge from chaotic splitting decisions
    """
    SIZE = 800
    img = Image.new("RGB", (SIZE, SIZE), (245, 245, 245))
    draw = ImageDraw.Draw(img)
    
    @dataclass
    class Rect:
        x: int
        y: int
        w: int
        h: int
        depth: int
    
    def subdivide(rect: Rect, max_depth: int = 6) -> List[Rect]:
        if rect.depth >= max_depth or random.random() > 0.7:
            return [rect]
        
        # Decide split direction based on aspect ratio
        if rect.w > rect.h:
            split_x = rect.x + random.randint(rect.w // 3, rect.w * 2 // 3)
            left = Rect(rect.x, rect.y, split_x - rect.x, rect.h, rect.depth + 1)
            right = Rect(split_x, rect.y, rect.x + rect.w - split_x, rect.h, rect.depth + 1)
            return subdivide(left, max_depth) + subdivide(right, max_depth)
        else:
            split_y = rect.y + random.randint(rect.h // 3, rect.h * 2 // 3)
            top = Rect(rect.x, rect.y, rect.w, split_y - rect.y, rect.depth + 1)
            bottom = Rect(rect.x, split_y, rect.w, rect.y + rect.h - split_y, rect.depth + 1)
            return subdivide(top, max_depth) + subdivide(bottom, max_depth)
    
    # Start with full canvas
    root = Rect(50, 50, SIZE - 100, SIZE - 100, 0)
    rects = subdivide(root)
    
    # Draw rectangles with varying line weights
    for rect in rects:
        line_width = max(1, 4 - rect.depth)
        shade = 30 + rect.depth * 35
        
        # Draw rectangle border
        draw.rectangle(
            [rect.x, rect.y, rect.x + rect.w, rect.y + rect.h],
            outline=(shade, shade, shade + 10),
            width=line_width
        )
        
        # Randomly add internal diagonal or cross
        if random.random() > 0.6 and rect.w > 20 and rect.h > 20:
            if random.random() > 0.5:
                draw.line([(rect.x, rect.y), (rect.x + rect.w, rect.y + rect.h)], 
                         fill=(shade + 40, shade + 40, shade + 50), width=1)
            else:
                draw.line([(rect.x + rect.w, rect.y), (rect.x, rect.y + rect.h)], 
                         fill=(shade + 40, shade + 40, shade + 50), width=1)
    
    return img

# ============================================================
# PIECE 3: Strange Attractor Visualization
# ============================================================

def clifford_attractor():
    """
    Clifford attractor - a chaotic system showing emergent structure.
    Two simple equations create infinitely complex, organic patterns.
    
    Technique: Iterated function system (Clifford attractor)
    Parameters: a=-1.4, b=1.6, c=1.0, d=0.7, 2 million iterations
    Emergent quality: Ghostly, organic curves emerge from deterministic math
    """
    SIZE = 800
    img = Image.new("RGB", (SIZE, SIZE), (5, 5, 10))
    pixels = img.load()
    
    # Clifford attractor parameters
    a, b, c, d = -1.4, 1.6, 1.0, 0.7
    
    # Start point
    x, y = 0.0, 0.0
    
    # Find bounds first
    points_x, points_y = [], []
    for _ in range(10000):
        x_new = math.sin(a * y) + c * math.cos(a * x)
        y_new = math.sin(b * x) + d * math.cos(b * y)
        x, y = x_new, y_new
        points_x.append(x)
        points_y.append(y)
    
    min_x, max_x = min(points_x), max(points_x)
    min_y, max_y = min(points_y), max(points_y)
    
    # Scale to image
    margin = 50
    scale_x = (SIZE - 2 * margin) / (max_x - min_x)
    scale_y = (SIZE - 2 * margin) / (max_y - min_y)
    
    # Draw attractor
    x, y = 0.0, 0.0
    density = [[0 for _ in range(SIZE)] for _ in range(SIZE)]
    
    for _ in range(2000000):
        x_new = math.sin(a * y) + c * math.cos(a * x)
        y_new = math.sin(b * x) + d * math.cos(b * y)
        x, y = x_new, y_new
        
        px = int(margin + (x - min_x) * scale_x)
        py = int(margin + (y - min_y) * scale_y)
        
        if 0 <= px < SIZE and 0 <= py < SIZE:
            density[py][px] += 1
    
    # Render with color based on density
    max_density = max(max(row) for row in density)
    for py in range(SIZE):
        for px in range(SIZE):
            d_val = density[py][px]
            if d_val > 0:
                intensity = min(1.0, (d_val / max_density) ** 0.5)
                r = int(20 + 100 * intensity)
                g = int(50 + 150 * intensity)
                b = int(100 + 155 * intensity)
                pixels[px, py] = (r, g, b)
    
    return img

# ============================================================
# PIECE 4: Geometric Tessellation with Rotation
# ============================================================

def rotating_tessellation():
    """
    Tessellated grid where each cell rotates based on position.
    Vera Molnár-style systematic variation creates visual rhythm.
    
    Technique: Parametric grid with progressive rotation
    Parameters: 12x12 grid, rotation accumulates across cells
    Emergent quality: Wave-like interference patterns from simple rotations
    """
    SIZE = 800
    img = Image.new("RGB", (SIZE, SIZE), (250, 248, 245))
    draw = ImageDraw.Draw(img)
    
    cols, rows = 12, 12
    cell_w = SIZE // cols
    cell_h = SIZE // rows
    margin = 8
    
    for row in range(rows):
        for col in range(cols):
            x = col * cell_w + cell_w // 2
            y = row * cell_h + cell_h // 2
            
            # Rotation increases with position
            angle = (col * 15 + row * 10) * math.pi / 180
            
            # Draw rotated square
            size = (cell_w - margin * 2) // 2
            
            corners = []
            for i in range(4):
                corner_angle = angle + i * math.pi / 2
                cx = x + size * math.cos(corner_angle)
                cy = y + size * math.sin(corner_angle)
                corners.append((cx, cy))
            
            # Color based on position
            hue_val = (col + row) * 8
            color = (
                40 + int(60 * math.sin(hue_val * 0.05)),
                40 + int(60 * math.cos(hue_val * 0.03)),
                50 + int(50 * math.sin(hue_val * 0.07))
            )
            
            draw.polygon(corners, outline=color, fill=None)
            
            # Add inner pattern
            inner_size = size * 0.5
            inner_corners = []
            for i in range(4):
                corner_angle = -angle + i * math.pi / 2  # Rotate opposite
                cx = x + inner_size * math.cos(corner_angle)
                cy = y + inner_size * math.sin(corner_angle)
                inner_corners.append((cx, cy))
            
            draw.polygon(inner_corners, outline=(color[0]+40, color[1]+40, color[2]+40), fill=None)
    
    return img

# ============================================================
# PIECE 5: Differential Growth / Organic Lines
# ============================================================

def differential_growth():
    """
    Simulating differential growth - organic form generation.
    Lines grow and push apart like bacterial colonies or coral.
    
    Technique: Physics-based line growth with collision avoidance
    Parameters: 8 seed lines, growth force 0.5, repulsion radius 15
    Emergent quality: Living, breathing forms emerge from simple forces
    """
    SIZE = 800
    img = Image.new("RGB", (SIZE, SIZE), (10, 12, 15))
    draw = ImageDraw.Draw(img)
    
    @dataclass
    class Node:
        x: float
        y: float
        vx: float = 0
        vy: float = 0
    
    # Initialize curved seed lines
    lines = []
    for i in range(8):
        nodes = []
        center_y = SIZE // 2 + (i - 4) * 60
        for j in range(20):
            t = j / 19
            x = 100 + t * 600 + random.uniform(-20, 20)
            y = center_y + math.sin(t * math.pi * 2) * 30 + random.uniform(-10, 10)
            nodes.append(Node(x, y))
        lines.append(nodes)
    
    # Grow and relax
    for iteration in range(150):
        new_lines = []
        
        for line in lines:
            new_line = []
            
            for i, node in enumerate(line):
                fx, fy = 0.0, 0.0
                
                # Attraction to neighbors (maintain structure)
                if i > 0:
                    dx = line[i-1].x - node.x
                    dy = line[i-1].y - node.y
                    d = math.sqrt(dx*dx + dy*dy)
                    if d > 5:
                        fx += dx / d * 0.3
                        fy += dy / d * 0.3
                
                if i < len(line) - 1:
                    dx = line[i+1].x - node.x
                    dy = line[i+1].y - node.y
                    d = math.sqrt(dx*dx + dy*dy)
                    if d > 5:
                        fx += dx / d * 0.3
                        fy += dy / d * 0.3
                
                # Repulsion from other lines (differential growth)
                for other_line in lines:
                    if other_line is line:
                        continue
                    for other in other_line:
                        dx = node.x - other.x
                        dy = node.y - other.y
                        d = math.sqrt(dx*dx + dy*dy)
                        if d < 15 and d > 0:
                            fx += dx / d * 2.0
                            fy += dy / d * 2.0
                
                # Apply forces
                node.vx = node.vx * 0.9 + fx * 0.1
                node.vy = node.vy * 0.9 + fy * 0.1
                
                new_node = Node(
                    node.x + node.vx,
                    node.y + node.vy,
                    node.vx,
                    node.vy
                )
                new_line.append(new_node)
            
            # Insert new nodes if segments get too long
            i = 0
            while i < len(new_line) - 1:
                dx = new_line[i+1].x - new_line[i].x
                dy = new_line[i+1].y - new_line[i].y
                d = math.sqrt(dx*dx + dy*dy)
                if d > 12:
                    mid = Node(
                        (new_line[i].x + new_line[i+1].x) / 2,
                        (new_line[i].y + new_line[i+1].y) / 2
                    )
                    new_line.insert(i+1, mid)
                i += 1
            
            new_lines.append(new_line)
        
        lines = new_lines
    
    # Draw the grown lines
    colors = [
        (180, 100, 80), (200, 140, 100), (160, 120, 140),
        (100, 140, 180), (80, 160, 140), (140, 180, 120),
        (180, 160, 100), (160, 100, 120)
    ]
    
    for line_idx, line in enumerate(lines):
        color = colors[line_idx % len(colors)]
        points = [(int(n.x), int(n.y)) for n in line]
        
        # Draw smooth curve through points
        if len(points) > 1:
            for i in range(len(points) - 1):
                draw.line([points[i], points[i+1]], fill=color, width=2)
                
                # Add glow effect
                draw.ellipse([points[i][0]-1, points[i][1]-1, 
                             points[i][0]+1, points[i][1]+1], fill=color)
    
    return img

# ============================================================
# MAIN EXECUTION
# ============================================================

if __name__ == "__main__":
    random.seed(42)  # Reproducible results
    
    print("Generating algorithmic art collection...")
    print("-" * 50)
    
    # Piece 1: Flow Fields
    print("\n1. Perlin Flow Fields...")
    img1 = perlin_flow_field()
    save_image(img1, "01_perlin_flow_fields.png")
    
    # Piece 2: Recursive Subdivision
    print("\n2. Recursive Subdivision...")
    img2 = recursive_subdivision()
    save_image(img2, "02_recursive_subdivision.png")
    
    # Piece 3: Strange Attractor
    print("\n3. Clifford Attractor...")
    img3 = clifford_attractor()
    save_image(img3, "03_clifford_attractor.png")
    
    # Piece 4: Rotating Tessellation
    print("\n4. Rotating Tessellation...")
    img4 = rotating_tessellation()
    save_image(img4, "04_rotating_tessellation.png")
    
    # Piece 5: Differential Growth
    print("\n5. Differential Growth...")
    img5 = differential_growth()
    save_image(img5, "05_differential_growth.png")
    
    print("\n" + "=" * 50)
    print("All pieces generated successfully!")
