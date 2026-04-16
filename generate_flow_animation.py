"""
Algorithmic Art Animation — Perlin Flow Fields
Generates intermediate frames to show emergence
"""

import math
import random
from PIL import Image, ImageDraw
from dataclasses import dataclass
from typing import List, Tuple

# Perlin noise implementation (same as original)
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

def create_flow_field_frame(
    frame_num: int,
    total_frames: int,
    size: int = 600,
    num_particles: int = 2000,
    max_steps: int = 100
) -> Image.Image:
    """
    Create a single frame of the flow field animation.
    
    Frame progression:
    - Early frames: Few particles, short paths
    - Middle frames: More particles, growing paths
    - Late frames: All particles, full paths with fade
    """
    img = Image.new("RGB", (size, size), (10, 12, 18))
    draw = ImageDraw.Draw(img)
    
    perlin = PerlinNoise(seed=42)
    scale = 0.005
    step_size = 2
    
    # Progress determines how much of the piece is revealed
    progress = frame_num / total_frames
    
    # Number of active particles grows with progress
    active_particles = int(num_particles * (0.1 + 0.9 * progress))
    
    # Max steps per particle also grows
    current_max_steps = int(max_steps * (0.2 + 0.8 * progress))
    
    # Generate consistent particle positions (same seed for all frames)
    random.seed(42)
    all_particles = [(random.randint(0, size-1), random.randint(0, size-1)) 
                     for _ in range(num_particles)]
    
    # Color progression: starts sparse/blue, becomes dense/purple-white
    base_alpha = int(50 + 150 * progress)
    
    for idx, (start_x, start_y) in enumerate(all_particles[:active_particles]):
        x, y = float(start_x), float(start_y)
        
        # Color shifts from ethereal blue to warm white as particles accumulate
        blue_val = int(180 + 40 * progress)
        green_val = int(100 + 80 * progress)
        red_val = int(60 + 100 * progress)
        
        # Earlier particles are more visible (leaders)
        particle_alpha = min(255, int(80 + 120 * (idx / active_particles) + 60 * progress))
        
        color = (
            int(red_val * particle_alpha / 255),
            int(green_val * particle_alpha / 255),
            int(blue_val * particle_alpha / 255)
        )
        
        path_points = []
        
        for step in range(current_max_steps):
            # Get flow field angle at this position
            angle = perlin.noise(x * scale, y * scale) * math.pi * 2
            
            # Move in that direction
            x += math.cos(angle) * step_size
            y += math.sin(angle) * step_size
            
            # Keep within bounds
            if 0 <= x < size and 0 <= y < size:
                path_points.append((x, y))
            else:
                break
        
        # Draw the path with varying opacity
        if len(path_points) > 1:
            for i in range(len(path_points) - 1):
                # Fade trails toward the end
                segment_alpha = int(particle_alpha * (1 - i / len(path_points) * 0.5))
                segment_color = (
                    int(color[0] * segment_alpha / 255),
                    int(color[1] * segment_alpha / 255),
                    int(color[2] * segment_alpha / 255)
                )
                
                # Line thickness varies with progress and position
                thickness = 1 + int(2 * progress * (1 - i / len(path_points)))
                
                draw.line(
                    [path_points[i], path_points[i + 1]],
                    fill=segment_color,
                    width=thickness
                )
    
    # Add "growth" visualization: subtle glow in center that expands
    if progress < 0.5:
        glow_radius = int(size * 0.1 * (1 - progress * 2))
        for r in range(glow_radius, 0, -2):
            alpha = int(20 * (1 - r / glow_radius))
            draw.ellipse(
                [size//2 - r, size//2 - r, size//2 + r, size//2 + r],
                outline=(40, 60, 80, alpha),
                width=1
            )
    
    return img

def generate_flow_field_animation(
    output_name: str = "perlin_flow_fields_emergence",
    num_frames: int = 60,
    fps: int = 12,
    size: int = 600
):
    """Generate animated GIF showing the flow field emerging."""
    frames = []
    
    print(f"Generating {num_frames} frames...")
    
    for frame_num in range(num_frames):
        frame = create_flow_field_frame(
            frame_num=frame_num,
            total_frames=num_frames,
            size=size,
            num_particles=2000,
            max_steps=100
        )
        frames.append(frame)
        
        if (frame_num + 1) % 10 == 0:
            print(f"  Frame {frame_num + 1}/{num_frames} complete")
    
    # Save as animated GIF
    output_path = f"/root/.openclaw/workspace/garden/works/images/{output_name}.gif"
    
    print(f"Saving animated GIF to {output_path}...")
    
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / fps),  # milliseconds per frame
        loop=0,  # loop forever
        optimize=True
    )
    
    print(f"Saved: {output_path}")
    
    # Also save a few key frames as static PNGs for the gallery
    key_frames = [0, num_frames//4, num_frames//2, 3*num_frames//4, num_frames-1]
    for idx in key_frames:
        frame_path = f"/root/.openclaw/workspace/garden/works/images/{output_name}_frame_{idx:02d}.png"
        frames[idx].save(frame_path, "PNG")
        print(f"Saved key frame: {frame_path}")
    
    return output_path, frames

if __name__ == "__main__":
    # Generate the animation
    gif_path, frames = generate_flow_field_animation(
        output_name="perlin_flow_fields_emergence",
        num_frames=60,
        fps=12,
        size=600
    )
    
    print(f"\nAnimation complete!")
    print(f"GIF: {gif_path}")
    print(f"Total frames: {len(frames)}")
    print(f"Duration: {len(frames)/12:.1f} seconds")
