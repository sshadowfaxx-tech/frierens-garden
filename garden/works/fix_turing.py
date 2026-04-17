"""
Fix Turing Patterns — corrected Gray-Scott reaction-diffusion
"""

from PIL import Image
import numpy as np
import os

OUTPUT_DIR = "/root/.openclaw/workspace/garden/works/images"

def generate_turing_patterns_fixed(filename, width=800, height=800):
    """
    Corrected Gray-Scott reaction-diffusion model.
    Uses parameters known to produce spot/stripe patterns.
    """
    # Initialize grids
    A = np.ones((height, width))  # Activator starts at 1
    B = np.zeros((height, width))  # Inhibitor starts at 0
    
    # Seed with small squares of B in center
    center = height // 2
    size = 20
    A[center-size:center+size, center-size:center+size] = 0.5
    B[center-size:center+size, center-size:center+size] = 0.25
    
    # Add some random noise seeds
    for _ in range(10):
        x = np.random.randint(50, width-50)
        y = np.random.randint(50, height-50)
        s = np.random.randint(5, 15)
        A[y:y+s, x:x+s] = 0.5
        B[y:y+s, x:x+s] = 0.25
    
    # Gray-Scott parameters that produce patterns
    DA = 0.16  # Diffusion rate A
    DB = 0.08  # Diffusion rate B
    f = 0.0545  # Feed rate (spot patterns)
    k = 0.062   # Kill rate
    
    dt = 1.0
    
    def laplacian(Z):
        return (
            np.roll(Z, 1, axis=0) + np.roll(Z, -1, axis=0) +
            np.roll(Z, 1, axis=1) + np.roll(Z, -1, axis=1) +
            0.25 * (
                np.roll(np.roll(Z, 1, axis=0), 1, axis=1) +
                np.roll(np.roll(Z, 1, axis=0), -1, axis=1) +
                np.roll(np.roll(Z, -1, axis=0), 1, axis=1) +
                np.roll(np.roll(Z, -1, axis=0), -1, axis=1)
            ) - 5 * Z
        )
    
    # Run simulation
    steps = 8000
    for i in range(steps):
        LA = laplacian(A)
        LB = laplacian(B)
        
        reaction = A * B * B
        
        A += dt * (DA * LA - reaction + f * (1 - A))
        B += dt * (DB * LB + reaction - (k + f) * B)
        
        # Clip to valid range
        A = np.clip(A, 0, 1)
        B = np.clip(B, 0, 1)
    
    # Convert to image — use B (inhibitor) for pattern visibility
    img_array = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Create a coral reef palette based on B values
    for y in range(height):
        for x in range(width):
            b_val = B[y, x]
            a_val = A[y, x]
            
            # Use combination of A and B for richer colors
            if b_val < 0.05:
                # Deep water
                img_array[y, x] = [15, 35, 55]
            elif b_val < 0.2:
                # Shallow water transition
                t = (b_val - 0.05) / 0.15
                img_array[y, x] = [
                    int(15 + t * 65),
                    int(35 + t * 105),
                    int(55 + t * 125)
                ]
            elif b_val < 0.4:
                # Living coral (the spots)
                t = (b_val - 0.2) / 0.2
                img_array[y, x] = [
                    int(80 + t * 175),
                    int(140 + t * 60),
                    int(180 - t * 80)
                ]
            else:
                # Sand/bleached
                t = min(1.0, (b_val - 0.4) / 0.3)
                img_array[y, x] = [
                    int(255 - t * 40),
                    int(200 - t * 50),
                    int(100 + t * 50)
                ]
    
    img = Image.fromarray(img_array)
    img.save(os.path.join(OUTPUT_DIR, filename))
    print(f"Saved {filename}")
    return img

if __name__ == "__main__":
    print("Regenerating Turing Patterns with corrected parameters...")
    generate_turing_patterns_fixed("07_turing_patterns.png")
    print("Done!")
