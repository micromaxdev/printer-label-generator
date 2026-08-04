# Label Design Editor

A browser-based label design tool for generating **Brother QL** printer label images (PNG output).

Designed for 62 mm continuous rolls (black/red/white), with a live visual editor, drag-to-position elements, and a standalone Python render function for production printing.

---

## Quick Start

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Download bundled fonts (one-time)
python setup_fonts.py

# 3. Start the editor
python app.py
```

Then open **http://localhost:5000** in your browser.

---

## Directory Layout

```
printer-label-generator/
├── app.py                  # Flask web server
├── render_label.py         # Standalone renderer (no Flask dependency)
├── setup_fonts.py          # One-time font downloader
├── requirements.txt
├── layouts/
│   └── woodward-visitor.json   # Saved layout (structure/style, no sample values)
├── static/
│   ├── fonts/              # Bundled TTF fonts
│   └── assets/
│       └── Woodward W ONLY.png
└── templates/
    └── index.html          # Editor UI
```

---

## Editor Features

| Feature | Details |
|---|---|
| **Drag to position** | Grab any element handle on the canvas and drag it |
| **Resize** | Drag the bottom-right corner handle to resize |
| **Fine-tune** | Numeric X/Y/W/H inputs in the Properties pane |
| **Live preview** | Label re-renders automatically as you edit (~150 ms debounce during drag) |
| **Color picker** | Three-swatch picker: Black / Red / White (matching the Brother DK roll) |
| **Font** | Select from bundled fonts: Inter, Roboto, Roboto Condensed, Oswald |
| **Sample data** | Edit preview values in the Sample Data pane (not saved to the layout file) |
| **Save layout** | Saves `layouts/<name>.json` — structure/style only |
| **Load layout** | Load any previously saved layout from the Load dropdown |
| **Duplicate** | Clone the current layout under a new name |
| **Export PNG** | Downloads a PNG at the full print resolution |

---

## Canvas Dimensions

| Property | Value |
|---|---|
| Width | **1066 px** (95 mm @ Brother 11.226 px/mm) |
| Height | **696 px** (62 mm @ Brother 11.226 px/mm) |
| Orientation | Horizontal (landscape) |
| Color model | Black / Red `#cc0000` / White |

---

## Standalone Rendering (for production printing)

```python
from render_label import render_label

img = render_label(
    "layouts/woodward-visitor.json",
    {
        "visitorName": "Mike Barkley",
        "company":     "Court Corp",
        "host":        "Host: Martin Dillich",
        "date":        "04/08/26",
        "visitorType": "Visitor",
        "visitorId":   "68a1f2b3c4d5e6f700000001",   # MongoDB ObjectId
        "logoPath":    "static/assets/Woodward W ONLY.png",
    },
)
img.save("output.png")
```

### CLI

```bash
python render_label.py \
  --layout layouts/woodward-visitor.json \
  --data '{"visitorName":"Mike Barkley","company":"Court Corp","host":"Host: Martin Dillich","date":"04/08/26","visitorType":"Visitor","visitorId":"VIS-001","logoPath":"static/assets/Woodward W ONLY.png"}' \
  --output output.png
```

---

## Layout JSON Format

```json
{
  "version": 1,
  "name": "woodward-visitor",
  "canvas": { "width": 1066, "height": 696, "background": "#ffffff" },
  "elements": [
    {
      "id": "visitorName",
      "type": "text",
      "field": "visitorName",
      "x": 18, "y": 185, "w": 840,
      "fontSize": 90, "fontFamily": "Inter",
      "bold": true, "italic": false,
      "color": "#000000", "align": "left",
      "zIndex": 4
    }
  ]
}
```

**Element types:**

| Type | Key properties |
|---|---|
| `text` | `field`, `x`, `y`, `w`, `fontSize`, `fontFamily`, `bold`, `italic`, `color`, `align` |
| `image` | `field` (data-dict override) or `src` (static path), `x`, `y`, `w`, `h`, `lockAspect` |
| `qrcode` | `field` (encodes the value), `x`, `y`, `w` |
| `line` | `x`, `y`, `w` (length), `h` (thickness), `color` |

---

## Creating a New Customer Layout

1. Open the editor and click **New** (or **Duplicate** an existing layout)
2. Set the canvas size if different
3. Add/remove/reposition elements by dragging on the canvas
4. Adjust fonts, colors, and styles in the Properties pane
5. Enter realistic sample values in the Sample Data pane
6. Click **Save** → creates `layouts/<your-name>.json`

---

## Linux / Ubuntu Production Notes

- All dependencies (`flask`, `Pillow`, `qrcode`) are Linux-compatible
- Fonts are bundled in `static/fonts/` — no system fonts required
- Run `python render_label.py …` from the project directory; relative asset paths resolve from there
- The output PNG is 1066 × 696 px; pass it to `brother_ql` with `--rotate 0` (already landscape)

---

## Dependencies

```
flask>=3.0
Pillow>=10.0
qrcode[pil]>=7.4
```
