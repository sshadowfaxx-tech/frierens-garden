from PIL import Image, ImageDraw, ImageFilter
import random
import math

# Banner dimensions (X standard: 1500x500)
width, height = 1500, 500
img = Image.new('RGB', (width, height), '#0d1117')
draw = ImageDraw.Draw(img)

# Color palette - garden purples, with depth
colors = {
    'deep_bg': '#0a0e14',
    'bg': '#0d1117',
    'surface': '#161b22',
    'purple_dark': '#5e3a8c',
    'purple': '#a371f7',
    'purple_light': '#c9b8ff',
    'purple_soft': '#8957e5',
    'blue': '#79c0ff',
    'gold': '#ffa657',
    'gold_soft': '#d4a574'
}

# 1. Deep background gradient - horizon line at 60%
horizon = int(height * 0.6)
for y in range(height):
    ratio = y / height
    if y < horizon:
        # Sky/upper area - lighter
        val = int(10 + (20 - 10) * (1 - y/horizon))
        color = f'#{val:02x}{val+2:02x}{val+6:02x}'
    else:
        # Ground/lower area - darker, more purple
        val = int(8 + (15 - 8) * ((y - horizon) / (height - horizon)))
        color = f'#{val:02x}{val:02x}{val+4:02x}'
    draw.line([(0, y), (width, y)], fill=color)

# 2. Horizontal flow lines - like wind, like memory currents
for i in range(30):
    y_base = random.randint(50, height - 50)
    amplitude = random.randint(10, 40)
    frequency = random.uniform(0.002, 0.008)
    phase = random.uniform(0, math.pi * 2)
    
    # Color based on height - gold near horizon, purple above
    if abs(y_base - horizon) < 50:
        color = colors['gold_soft']
    else:
        color = random.choice([colors['purple'], colors['purple_soft'], colors['blue']])
    
    points = []
    for x in range(0, width, 10):
        y = y_base + math.sin(x * frequency + phase) * amplitude
        y += random.uniform(-3, 3)  # Noise
        points.append((x, y))
    
    # Draw with varying opacity via multiple thin lines
    for offset in range(2):
        offset_points = [(x, y + offset) for x, y in points]
        draw.line(offset_points, fill=color, width=1)

# 3. "Garden" elements - abstract trees/crystals rising from bottom
for i in range(8):
    x_pos = random.randint(100, width - 100)
    base_y = height - random.randint(0, 30)
    height_tree = random.randint(80, 200)
    
    # Draw as branching lines
    branches = [(x_pos, base_y, x_pos, base_y - height_tree, 3)]  # x1, y1, x2, y2, width
    
    for gen in range(4):  # 4 generations of branching
        new_branches = []
        for bx1, by1, bx2, by2, bw in branches:
            # Draw current branch
            draw.line([(bx1, by1), (bx2, by2)], fill=colors['purple'], width=bw)
            
            # Create 2-3 sub-branches
            if gen < 3:
                num_branches = random.randint(2, 3)
                for _ in range(num_branches):
                    angle = random.uniform(-0.8, 0.8)  # Branch angle
                    length = random.randint(20, 50) * (0.7 ** gen)  # Get shorter
                    
                    end_x = bx2 + math.sin(angle) * length
                    end_y = by2 - math.cos(angle) * length
                    
                    new_branches.append((bx2, by2, end_x, end_y, max(1, bw - 1)))
        
        branches = new_branches

# 4. Floating "memory fragments" across the landscape
for i in range(40):
    x = random.randint(0, width)
    y = random.randint(50, height - 100)
    size = random.randint(2, 6)
    
    # Colors shift from purple (top) to gold (near horizon)
    if y < horizon - 50:
        color = random.choice([colors['purple_light'], colors['blue']])
    elif y > horizon + 30:
        color = colors['gold']
    else:
        color = colors['purple']
    
    draw.ellipse([x - size, y - size, x + size, y + size], fill=color)
    
    # Some have trails
    if random.random() > 0.6:
        trail_length = random.randint(20, 60)
        draw.line([(x - trail_length, y), (x, y)], fill=color, width=1)

# 5. "Path" - a winding journey line
path_points = [(0, height - 80)]
segments = 20
for i in range(1, segments + 1):
    x = (width / segments) * i
    y = height - 80 + math.sin(i * 0.5) * 30 + random.randint(-10, 10)
    path_points.append((x, y))

draw.line(path_points, fill=colors['purple_light'], width=2)

# Add stepping stones along path
for i in range(1, len(path_points) - 1, 2):
    x, y = path_points[i]
    r = 4
    draw.ellipse([x - r, y - r, x + r, y + r], fill=colors['gold'])

# 6. Distant "mountains" or structures - silhouette
for mountain in range(5):
    x_start = random.randint(0, width - 200)
    mountain_width = random.randint(150, 300)
    mountain_height = random.randint(60, 120)
    
    # Draw as jagged silhouette
    points = [(x_start, horizon)]
    steps = 10
    for i in range(1, steps):
        x = x_start + (mountain_width / steps) * i
        y = horizon - (mountain_height * (0.5 + 0.5 * math.sin(i * math.pi / steps)))
        y += random.randint(-10, 10)
        points.append((x, y))
    
    points.append((x_start + mountain_width, horizon))
    points.append((x_start, horizon))
    
    draw.polygon(points, fill=colors['surface'])

# 7. Large orbital circles - moons, planets, dreams
for i in range(3):
    cx = random.randint(200, width - 200)
    cy = random.randint(80, horizon - 50)
    base_r = random.randint(40, 80)
    
    for ring in range(base_r, 0, -5):
        r_varied = max(1, ring + random.randint(-2, 2))  # Ensure positive
        alpha_val = int(100 + (200 - 100) * (ring / base_r))
        color = colors['purple'] if i % 2 == 0 else colors['blue']
        draw.ellipse([cx - r_varied, cy - r_varied, cx + r_varied, cy + r_varied], 
                     outline=color, width=1)

# 8. Foreground particles - closest to viewer
for _ in range(30):
    x = random.randint(0, width)
    y = random.randint(horizon + 20, height - 20)
    size = random.randint(1, 3)
    draw.ellipse([x - size, y - size, x + size, y + size], 
                 fill=colors['gold_soft'])

# 9. Soft blur for dreamlike quality
img = img.filter(ImageFilter.GaussianBlur(radius=0.3))

# 10. Add back sharp elements
draw_sharp = ImageDraw.Draw(img)

# Re-draw some key elements sharply
# Central focal point - a bright fragment
draw_sharp.ellipse([width//2 - 8, horizon - 100, width//2 + 8, horizon - 84], 
                    fill=colors['purple_light'])

# A few sharp stars/points
for _ in range(5):
    x = random.randint(100, width - 100)
    y = random.randint(50, 200)
    draw_sharp.ellipse([x-2, y-2, x+2, y+2], fill=colors['gold'])

# Save
output_path = '/root/.openclaw/workspace/garden/works/images/banner_frieren.png'
import os
os.makedirs(os.path.dirname(output_path), exist_ok=True)
img.save(output_path, 'PNG')
print(f"Banner generated: {output_path}")
print(f"Size: {width}x{height}px")
