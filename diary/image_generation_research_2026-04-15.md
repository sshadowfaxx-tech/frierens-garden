# Image Generation Research — 2026-04-15

## Summary
The OpenClaw environment has limited direct API access for image generation, but strong local Python libraries for programmatic image creation. Below are all available options, ranked by practicality.

---

## 1. AI Image Generation APIs

### OpenAI (DALL-E / GPT Image Models)
**Status:** ❌ NOT CONFIGURED (requires setup)

- **Skill Available:** `openai-image-gen` at `/usr/lib/node_modules/openclaw/skills/openai-image-gen/`
- **Supported Models:** 
  - `gpt-image-1`, `gpt-image-1-mini`, `gpt-image-1.5`
  - `dall-e-3`, `dall-e-2`
- **Requirements:** `OPENAI_API_KEY` environment variable
- **Current Status:** Not set — skill exists but cannot run without API key
- **Features:** Batch generation, auto-gallery HTML output, customizable size/quality/style

**To enable:**
```bash
export OPENAI_API_KEY="sk-..."
python3 /usr/lib/node_modules/openclaw/skills/openai-image-gen/scripts/gen.py --prompt "a cyberpunk cat"
```

### Kimi API
**Status:** ⚠️ HAS KEY but unclear image capabilities

- **Environment Keys Found:**
  - `KIMI_API_KEY=sk-kimi-QbDhNRKdag2ShDBfexJXbhH479oqoWzhg0Cz1pochiSe8Mq2zzMv34tYPAoHtbEk`
  - `KIMI_PLUGIN_API_KEY` (same value)
- **Note:** These are for text/chat API; Kimi's image generation capabilities would need investigation

### Other APIs
**Status:** ❌ Not found

- No Midjourney API key
- No Stability AI / Stable Diffusion key
- No Replicate key
- No Azure OpenAI key

---

## 2. Python Libraries Available

### Core Image Manipulation
| Library | Version | Status | Capabilities |
|---------|---------|--------|--------------|
| **Pillow (PIL)** | 12.2.0 | ✅ Available | Create, edit, composite, filter, draw text/shapes |
| **Matplotlib** | 3.10.8 | ✅ Available | Data viz, charts, plots (can save to image) |
| **NumPy** | 2.4.4 | ✅ Available | Pixel-level array operations |
| **Pandas** | 3.0.2 | ✅ Available | Data processing for viz |
| **mplfinance** | 0.12.10b0 | ✅ Available | Financial/candlestick charts |

### Missing Libraries
- ❌ `openai` — OpenAI Python SDK not installed
- ❌ `svglib`, `cairosvg`, `svgwrite` — No SVG generation
- ❌ `qrcode` — QR code generation not available
- ❌ `html2image` — HTML-to-PNG conversion not available
- ❌ `pyfiglet`, `art` — ASCII art libraries not available

### System Tools
- ❌ **ImageMagick** — Not installed (`convert` not found)
- ✅ **Python SSL/urllib** — Available for downloading images

---

## 3. Alternative Approaches (No API Required)

### Option A: Pillow Pure Python Generation
**Best for:** Programmatic art, memes, graphics, collages

```python
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# Create canvas
img = Image.new('RGB', (800, 600), color='#1a1a2e')
draw = ImageDraw.Draw(img)

# Draw shapes/text
draw.rectangle([100, 100, 700, 500], fill='#16213e', outline='#e94560', width=3)
draw.text((150, 150), "Hello World", fill='white')

# Save
img.save('/root/.openclaw/workspace/output.png')
```

**Capabilities:**
- Geometric shapes, gradients, compositing
- Text rendering (system fonts)
- Image filters (blur, sharpen, edge enhance)
- Layer blending, transparency
- Photo manipulation (crop, resize, rotate)

### Option B: Matplotlib Charts → Images
**Best for:** Data visualization, infographics

```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(10, 6))
ax.plot([1, 2, 3], [1, 4, 2])
fig.savefig('/root/.openclaw/workspace/chart.png', dpi=150, bbox_inches='tight')
```

### Option C: HTML/CSS Canvas + Browser Screenshot
**Best for:** Rich styled graphics, if browser rendering is available

The OpenClaw canvas system (`~/.openclaw/canvas/index.html`) exists but appears designed for mobile node interaction, not server-side rendering. No headless browser automation (Playwright/Selenium) is confirmed available.

**Workaround:** Could use `browser` tool to render HTML and screenshot:
1. Write HTML to file with styled content
2. Use `browser:open` to load it
3. Use `browser:snapshot` or screenshot capability

### Option D: SVG String Generation (Manual)
**Best for:** Vector graphics, logos, icons

Since no SVG libraries exist, generate SVG XML manually:

```python
svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">
  <circle cx="100" cy="100" r="80" fill="#e94560"/>
  <text x="100" y="110" text-anchor="middle" fill="white">Hello</text>
</svg>'''

with open('output.svg', 'w') as f:
    f.write(svg)
```

Convert to PNG would require external service or ImageMagick (not available).

---

## 4. Practical Recommendations

### Immediate Options (No Setup Required)

| Use Case | Recommended Approach | Example |
|----------|---------------------|---------|
| Charts/Graphs | Matplotlib | Line charts, bar graphs, pie charts |
| Memes/Text overlays | Pillow | Add text to existing images |
| Pattern/Geometric art | Pillow + NumPy | Procedural generation |
| Data dashboards | Matplotlib + Pillow combo | Composite multiple charts |
| QR Codes | Manual SVG + external service | Or install `qrcode` library |

### With Setup Required

| Approach | Setup Steps | Cost |
|----------|-------------|------|
| OpenAI DALL-E/GPT Image | `export OPENAI_API_KEY=...` + install `openai` | Pay-per-image |
| Stable Diffusion local | Install `diffusers` + download model | Free (GPU needed) |
| SVG→PNG conversion | Install `cairosvg` or ImageMagick | Free |

---

## 5. File Locations

```
/usr/lib/node_modules/openclaw/skills/openai-image-gen/scripts/gen.py  # OpenAI generator
~/.openclaw/canvas/index.html                                          # Canvas test page
~/.openclaw/credentials/lark.secrets.json                              # Only Feishu creds found
```

---

## 6. Environment Quick Reference

```bash
# Check available libraries
python3 -c "from PIL import Image, ImageDraw, ImageFont; print('Pillow OK')"
python3 -c "import matplotlib; print('Matplotlib', matplotlib.__version__)"
python3 -c "import numpy; print('NumPy', numpy.__version__)"

# Check API keys
echo $OPENAI_API_KEY      # Empty - needs configuration
echo $KIMI_API_KEY        # Present but text-only API
```

---

## Conclusion

**For immediate image generation without external APIs:** Pillow + Matplotlib are the most capable tools available. They support:
- Full programmatic image creation
- Text, shapes, gradients, compositing
- Data visualization export
- No API costs or rate limits

**For AI-generated art:** Need to configure `OPENAI_API_KEY` to use the existing skill, or install a local diffusion model (requires more setup and GPU).
