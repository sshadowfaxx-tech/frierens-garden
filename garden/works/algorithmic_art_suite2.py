"""
Generative Art Suite #2 — Gallery Collection
Algorithmic art generation using Pillow
"""

from PIL import Image, ImageDraw, ImageFilter
import math
import random
import noise
import os

OUTPUT_DIR = "/root/.openclaw/workspace/garden/works/images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =============================================================================
# 1. VORONOI GARDENS — Organic cell-like structures
# =============================================================================

def generate_voronoi_gardens(filename, width=1000, height=1000):
    """
    Voronoi diagram with organic coloring — like cross-sections of bone,
    cellular tissue, or cracked earth seen from above.
    """
    img = Image.new('RGB', (width, height), '#0a0a0c')
    draw = ImageDraw.Draw(img)
    
    # Generate random seed points
    num_seeds = 40 + int(math.sqrt(width * height) / 30)
    seeds = []
    colors = []
    
    palette_options = [
        # Bone/cream palette
        ['#f5f5dc', '#e8dcc4', '#d4c4a8', '#c4b896', '#b8a888', '#a89878'],
        # Deep ocean
        ['#0a1628', '#1a3a5c', '#2e5c8a', '#4a7aa8', '#6a9ac8', '#8abae8'],
        # Mars rust
        ['#2a1810', '#4a2820', '#6a3a30', '#8a5240', '#aa6a50', '#ca8260'],
    ]
    
    palette = random.choice(palette_options)
    
    for _ in range(num_seeds):
        x = random.uniform(0, width)
        y = random.uniform(0, height)
        seeds.append((x, y))
        colors.append(random.choice(palette))
    
    # Pixel-based Voronoi with Perlin noise distortion
    pixels = img.load()
    
    for py in range(height):
        for px in range(width):
            # Find nearest seed
            min_dist = float('inf')
            nearest_color = '#0a0a0c'
            
            for i, (sx, sy) in enumerate(seeds):
                # Add slight noise to distance for organic feel
                noise_val = noise.pnoise2(px * 0.01, py * 0.01, octaves=2)
                dx = px - sx + noise_val * 30
                dy = py - sy + noise_val * 30
                dist = math.sqrt(dx * dx + dy * dy)
                
                if dist < min_dist:
                    min_dist = dist
                    nearest_color = colors[i]
            
            # Convert hex to RGB
            r = int(nearest_color[1:3], 16)
            g = int(nearest_color[3:5], 16)
            b = int(nearest_color[5:7], 16)
            
            # Add gradient based on distance
            edge_factor = min(1.0, min_dist / 80)
            r = int(r * (0.7 + 0.3 * edge_factor))
            g = int(g * (0.7 + 0.3 * edge_factor))
            b = int(b * (0.7 + 0.3 * edge_factor))
            
            pixels[px, py] = (r, g, b)
    
    img.save(os.path.join(OUTPUT_DIR, filename))
    return img

# =============================================================================
# 2. TURING PATTERNS — Reaction-diffusion simulation
# =============================================================================

def generate_turing_patterns(filename, width=800, height=800):
    """
    Reaction-diffusion patterns — the mathematical basis for zebra stripes,
    leopard spots, and coral growth.
    """
    import numpy as np
    
    # Initialize with random noise
    A = np.random.rand(height, width) * 0.1 + 0.5  # Activator
    B = np.random.rand(height, width) * 0.1 + 0.5  # Inhibitor
    
    # Gray-Scott model parameters
    DA = 0.16  # Diffusion rate A
    DB = 0.08  # Diffusion rate B
    f = 0.035  # Feed rate
    k = 0.060  # Kill rate
    
    # Simulate steps
    steps = 5000
    
    def laplacian(Z):
        return (np.roll(Z, 1, axis=0) + np.roll(Z, -1, axis=0) +
                np.roll(Z, 1, axis=1) + np.roll(Z, -1, axis=1) - 4 * Z)
    
    for _ in range(steps):
        LA = laplacian(A)
        LB = laplacian(B)
        
        reaction = A * B * B
        
        A += DA * LA - reaction + f * (1 - A)
        B += DB * LB + reaction - (k + f) * B
        
        A = np.clip(A, 0, 1)
        B = np.clip(B, 0, 1)
    
    # Convert to image with coral/ocean palette
    img_array = np.zeros((height, width, 3), dtype=np.uint8)
    
    for y in range(height):
        for x in range(width):
            val = A[y, x]
            # Coral reef colors
            if val < 0.3:
                img_array[y, x] = [20, 40, 60]  # Deep water
            elif val < 0.5:
                img_array[y, x] = [80, 140, 180]  # Shallow water
            elif val < 0.7:
                img_array[y, x] = [255, 140, 100]  # Living coral
            else:
                img_array[y, x] = [255, 200, 150]  # Sand/bleached
    
    img = Image.fromarray(img_array)
    img.save(os.path.join(OUTPUT_DIR, filename))
    return img

# =============================================================================
# 3. L-SYSTEM FORESTS — Fractal plant structures
# =============================================================================

def generate_lsystem_forest(filename, width=1000, height=1200):
    """
    L-systems generating abstract tree/fern structures. The ghost of
    biology rendered in gold and shadow.
    """
    img = Image.new('RGB', (width, height), '#0a0a0c')
    draw = ImageDraw.Draw(img)
    
    def l_system_draw(start_x, start_y, start_angle, rules, iterations, length, color):
        """Draw an L-system structure"""
        # Generate the command string
        axiom = "X"
        for _ in range(iterations):
            new_axiom = ""
            for char in axiom:
                new_axiom += rules.get(char, char)
            axiom = new_axiom
        
        # Draw
        stack = []
        x, y = start_x, start_y
        angle = start_angle
        
        for char in axiom:
            if char == 'F':
                new_x = x + math.cos(angle) * length
                new_y = y + math.sin(angle) * length
                draw.line([(x, y), (new_x, new_y)], fill=color, width=max(1, int(length/3)))
                x, y = new_x, new_y
            elif char == '+':
                angle += math.pi / 6  # 30 degrees
            elif char == '-':
                angle -= math.pi / 6
            elif char == '[':
                stack.append((x, y, angle))
            elif char == ']':
                x, y, angle = stack.pop()
    
    # Different L-system rules
    systems = [
        # Fractal tree
        {
            'rules': {'X': 'F+[[X]-X]-F[-FX]+X', 'F': 'FF'},
            'angle': -math.pi / 2,
            'color': '#c4a35a'
        },
        # Fern-like
        {
            'rules': {'X': 'F+[[X]-X]-F[-FX]+X', 'F': 'FF'},
            'angle': -math.pi / 2 + 0.2,
            'color': '#8b9a6d'
        },
        # Sparse branching
        {
            'rules': {'F': 'F[+F]F[-F]F'},
            'angle': -math.pi / 2,
            'color': '#7a8b99'
        }
    ]
    
    # Draw multiple trees
    positions = [
        (width * 0.2, height * 0.9),
        (width * 0.5, height * 0.85),
        (width * 0.8, height * 0.9),
        (width * 0.35, height * 0.95),
        (width * 0.65, height * 0.92),
    ]
    
    for i, (x, y) in enumerate(positions):
        system = systems[i % len(systems)]
        l_system_draw(
            x, y,
            system['angle'] + (random.random() - 0.5) * 0.3,
            system['rules'],
            5,
            3 + random.random() * 2,
            system['color']
        )
    
    img.save(os.path.join(OUTPUT_DIR, filename))
    return img

# =============================================================================
# 4. MOIRÉ MANDALAS — Interference pattern geometries
# =============================================================================

def generate_moire_mandalas(filename, width=1000, height=1000):
    """
    Overlapping geometric patterns creating moiré interference.
    Hypnotic, precise, mathematical beauty.
    """
    img = Image.new('RGB', (width, height), '#0a0a0c')
    draw = ImageDraw.Draw(img)
    
    cx, cy = width // 2, height // 2
    
    # Draw concentric circles with varying density
    colors = ['#c4a35a', '#8b7355', '#d4af37', '#6b5a45']
    
    for layer in range(4):
        offset = layer * 3
        color = colors[layer % len(colors)]
        
        for r in range(20 + offset, 400, 8 + layer * 2):
            alpha = int(255 * (1 - r / 450))
            draw.ellipse(
                [cx - r, cy - r, cx + r, cy + r],
                outline=color,
                width=1
            )
    
    # Draw overlapping rotated squares
    for i in range(12):
        angle = i * math.pi / 6
        size = 150 + i * 25
        
        # Calculate rotated square corners
        corners = []
        for j in range(4):
            corner_angle = angle + j * math.pi / 2
            x = cx + math.cos(corner_angle) * size
            y = cy + math.sin(corner_angle) * size
            corners.append((x, y))
        
        draw.polygon(corners, outline='#5a4a3a', width=1)
    
    # Add radial lines
    for i in range(36):
        angle = i * math.pi / 18
        x1 = cx + math.cos(angle) * 50
        y1 = cy + math.sin(angle) * 50
        x2 = cx + math.cos(angle) * 400
        y2 = cy + math.sin(angle) * 400
        draw.line([(x1, y1), (x2, y2)], fill='#3a2a1a', width=1)
    
    img.save(os.path.join(OUTPUT_DIR, filename))
    return img

# =============================================================================
# 5. TOPOLOGICAL MAPS — Contour lines from noise fields
# =============================================================================

def generate_topological_maps(filename, width=1000, height=1000):
    """
    Contour lines from Perlin noise — like topographic maps of
    imaginary landscapes, or fingerprints of the earth itself.
    """
    img = Image.new('RGB', (width, height), '#0a0a0c')
    draw = ImageDraw.Draw(img)
    
    # Generate height field
    height_map = []
    for y in range(height):
        row = []
        for x in range(width):
            h = noise.pnoise2(x * 0.005, y * 0.005, octaves=4, persistence=0.5)
            row.append(h)
        height_map.append(row)
    
    # Draw contour lines
    contour_levels = 20
    colors = ['#8b9a6d', '#9aaa7d', '#aaba8d', '#baca9d', '#cadaad']
    
    for level_idx in range(contour_levels):
        level = -0.5 + level_idx * (1.0 / contour_levels)
        color = colors[level_idx % len(colors)]
        
        # Marching squares simplified — check each pixel
        for y in range(0, height - 1, 2):
            for x in range(0, width - 1, 2):
                h00 = height_map[y][x]
                h10 = height_map[y][min(x+1, width-1)]
                h01 = height_map[min(y+1, height-1)][x]
                h11 = height_map[min(y+1, height-1)][min(x+1, width-1)]
                
                # If this cell crosses the contour level
                values = [h00, h10, h11, h01]
                if min(values) <= level <= max(values):
                    # Simple point drawing at center
                    cx = x + 1
                    cy = y + 1
                    draw.point((cx, cy), fill=color)
    
    # Add some larger contour lines for clarity
    for level_idx in range(8):
        level = -0.5 + level_idx * 0.15
        
        for y in range(0, height - 2, 3):
            for x in range(0, width - 2, 3):
                h = height_map[y][x]
                if abs(h - level) < 0.02:
                    draw.point((x, y), fill='#c4a35a')
    
    img.save(os.path.join(OUTPUT_DIR, filename))
    return img

# =============================================================================
# 6. CONSTELLATION WEAVINGS — Star fields with connecting threads
# =============================================================================

def generate_constellation_weavings(filename, width=1000, height=800):
    """
    Star fields connected by proximity — like constellations drawn by
    an alien cartographer who sees different patterns in the sky.
    """
    img = Image.new('RGB', (width, height), '#050508')
    draw = ImageDraw.Draw(img)
    
    # Generate stars with varying brightness
    num_stars = 200
    stars = []
    
    for _ in range(num_stars):
        x = random.uniform(50, width - 50)
        y = random.uniform(50, height - 50)
        brightness = random.uniform(0.3, 1.0)
        size = random.choice([1, 1, 1, 2, 2, 3])
        stars.append((x, y, brightness, size))
    
    # Draw faint nebula background
    for _ in range(100):
        x = random.uniform(0, width)
        y = random.uniform(0, height)
        r = random.uniform(20, 60)
        alpha = random.randint(5, 15)
        # Very faint circles for nebula effect
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(20, 25, 40))
    
    # Connect nearby stars
    for i, (x1, y1, b1, s1) in enumerate(stars):
        for j, (x2, y2, b2, s2) in enumerate(stars[i+1:], i+1):
            dist = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            
            if dist < 120:
                # Connection strength based on distance and brightness
                strength = (1 - dist/120) * min(b1, b2)
                if strength > 0.3:
                    alpha = int(strength * 80)
                    color = (100 + alpha, 140 + alpha//2, 180 + alpha//2)
                    draw.line([(x1, y1), (x2, y2)], fill=color, width=1)
    
    # Draw stars
    for x, y, brightness, size in stars:
        r = int(200 * brightness)
        g = int(220 * brightness)
        b_val = int(255 * brightness)
        
        # Glow
        if size > 1:
            draw.ellipse([x-3, y-3, x+3, y+3], fill=(r//4, g//4, b_val//4))
        
        # Core
        draw.ellipse([x-size, y-size, x+size, y+size], fill=(r, g, b_val))
    
    img.save(os.path.join(OUTPUT_DIR, filename))
    return img

# =============================================================================
# MAIN — Generate the collection
# =============================================================================

if __name__ == "__main__":
    print("Generating Voronoi Gardens...")
    generate_voronoi_gardens("06_voronoi_gardens.png")
    
    print("Generating Turing Patterns...")
    generate_turing_patterns("07_turing_patterns.png")
    
    print("Generating L-System Forests...")
    generate_lsystem_forest("08_lsystem_forest.png")
    
    print("Generating Moiré Mandalas...")
    generate_moire_mandalas("09_moire_mandalas.png")
    
    print("Generating Topological Maps...")
    generate_topological_maps("10_topological_maps.png")
    
    print("Generating Constellation Weavings...")
    generate_constellation_weavings("11_constellation_weavings.png")
    
    print("\n✓ Gallery collection complete!")
