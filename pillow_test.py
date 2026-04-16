from PIL import Image, ImageDraw
import random
import math

# Canvas setup
width, height = 1200, 800
img = Image.new('RGB', (width, height), '#0d1117')
draw = ImageDraw.Draw(img)

# Color palette - purples, blues, golds, with some noise
def random_color():
    palettes = [
        '#a371f7',  # purple
        '#8957e5',  # darker purple
        '#c9b8ff',  # light purple
        '#79c0ff',  # blue
        '#ffa657',  # orange/gold
        '#30363d',  # dark surface
    ]
    return random.choice(palettes)

# 1. Background flow lines - sine waves with noise
for i in range(20):
    y_base = random.randint(100, height - 100)
    amplitude = random.randint(20, 80)
    frequency = random.uniform(0.005, 0.015)
    phase = random.uniform(0, math.pi * 2)
    color = random_color()
    
    points = []
    for x in range(0, width, 5):
        y = y_base + math.sin(x * frequency + phase) * amplitude
        # Add some noise
        y += random.uniform(-5, 5)
        points.append((x, y))
    
    # Draw with varying opacity via multiple thin lines
    for offset in range(3):
        offset_points = [(x, y + offset) for x, y in points]
        draw.line(offset_points, fill=color, width=1)

# 2. Glitch rectangles - horizontal bands of displaced color
for _ in range(15):
    y = random.randint(0, height - 50)
    h = random.randint(5, 30)
    x_offset = random.randint(-50, 50)
    color = random_color()
    
    # Create glitch band
    for x in range(0, width, random.randint(20, 100)):
        w = random.randint(50, 200)
        if x + w > width:
            w = width - x
        draw.rectangle([x + x_offset, y, x + x_offset + w, y + h], fill=color)

# 3. Orbital circles - concentric rings with decay
for _ in range(8):
    cx = random.randint(200, width - 200)
    cy = random.randint(200, height - 200)
    base_radius = random.randint(50, 150)
    color = random_color()
    
    for r in range(base_radius, 0, -3):
        alpha_factor = r / base_radius
        # Vary the radius slightly for organic feel
        r_varied = max(1, r + random.randint(-2, 2))  # Ensure positive
        draw.ellipse([cx - r_varied, cy - r_varied, cx + r_varied, cy + r_varied], 
                     outline=color, width=1)

# 4. Particle burst points
for _ in range(200):
    x = random.randint(0, width)
    y = random.randint(0, height)
    size = random.randint(1, 3)
    color = random_color()
    draw.ellipse([x - size, y - size, x + size, y + size], fill=color)

# 5. Connecting threads - random bezier-like curves
for _ in range(30):
    x1 = random.randint(0, width)
    y1 = random.randint(0, height)
    x2 = random.randint(0, width)
    y2 = random.randint(0, height)
    
    # Control points for curve
    cx1 = (x1 + x2) / 2 + random.randint(-100, 100)
    cy1 = (y1 + y2) / 2 + random.randint(-100, 100)
    
    # Draw curve as series of line segments
    points = []
    steps = 50
    for t in range(steps + 1):
        t_norm = t / steps
        # Quadratic bezier
        x = (1 - t_norm)**2 * x1 + 2 * (1 - t_norm) * t_norm * cx1 + t_norm**2 * x2
        y = (1 - t_norm)**2 * y1 + 2 * (1 - t_norm) * t_norm * cy1 + t_norm**2 * y2
        points.append((x, y))
    
    color = random_color()
    draw.line(points, fill=color, width=1)

# 6. Scanlines - subtle horizontal lines
def add_scanlines():
    pixels = img.load()
    for y in range(0, height, 3):
        for x in range(width):
            r, g, b = pixels[x, y]
            pixels[x, y] = (max(r - 15, 0), max(g - 15, 0), max(b - 15, 0))

add_scanlines()

# Save
output_path = '/root/.openclaw/workspace/garden/works/images/pillow_test_01.png'
import os
os.makedirs(os.path.dirname(output_path), exist_ok=True)
img.save(output_path, 'PNG')
print(f"Generated: {output_path}")
print(f"Size: {width}x{height}")
