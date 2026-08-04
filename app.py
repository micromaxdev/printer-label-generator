"""
app.py — Flask web server for the Label Design Editor.

Run:
    python app.py
Then open http://localhost:5000
"""

from __future__ import annotations

import base64
import io
import json
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory, send_file

from render_label import FONTS_DIR, _HERE, render_label_from_dict

# ── Flask app setup ───────────────────────────────────────────────────────────

app = Flask(
    __name__,
    static_folder=str(_HERE / "static"),
)

LAYOUTS_DIR = _HERE / "layouts"
LAYOUTS_DIR.mkdir(exist_ok=True)

ASSETS_DIR = _HERE / "static" / "assets"
ASSETS_DIR.mkdir(parents=True, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_name(raw: str) -> str:
    """Sanitise a layout name to a safe filename stem."""
    cleaned = raw.strip().lower().replace(" ", "-")
    return re.sub(r"[^a-z0-9\-_]", "", cleaned)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    # Send the file directly — bypasses Jinja2, which would choke on {{ }} in JS
    return send_file(str(_HERE / "templates" / "index.html"))


@app.route("/api/preview", methods=["POST"])
def preview():
    """Render a preview PNG from layout + sample data; return as a base64 data URL."""
    body        = request.get_json(force=True) or {}
    layout      = body.get("layout")
    sample_data = body.get("sampleData", {})

    if not layout:
        return jsonify({"error": "layout required"}), 400

    try:
        img = render_label_from_dict(layout, sample_data, base_dir=_HERE)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    buf.seek(0)
    data_url = "data:image/png;base64," + base64.b64encode(buf.read()).decode()

    return jsonify({"image": data_url, "width": img.width, "height": img.height})


@app.route("/api/layouts", methods=["GET"])
def list_layouts():
    """Return sorted list of saved layout names."""
    names = sorted(p.stem for p in LAYOUTS_DIR.glob("*.json"))
    return jsonify({"layouts": names})


@app.route("/api/load/<name>", methods=["GET"])
def load_layout(name: str):
    """Load a saved layout by name."""
    safe = _safe_name(name)
    path = LAYOUTS_DIR / f"{safe}.json"
    if not path.exists():
        return jsonify({"error": f"Layout '{safe}' not found"}), 404
    with open(path, encoding="utf-8") as f:
        return jsonify(json.load(f))


@app.route("/api/save", methods=["POST"])
def save_layout():
    """Persist a layout JSON to disk (layout only — no sample data)."""
    body   = request.get_json(force=True) or {}
    name   = body.get("name", "").strip()
    layout = body.get("layout")

    if not name:
        return jsonify({"error": "name required"}), 400
    if not layout:
        return jsonify({"error": "layout required"}), 400

    safe = _safe_name(name)
    if not safe:
        return jsonify({"error": "invalid layout name"}), 400

    path = LAYOUTS_DIR / f"{safe}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(layout, f, indent=2, ensure_ascii=False)

    return jsonify({"saved": f"layouts/{safe}.json", "name": safe})


@app.route("/api/fonts", methods=["GET"])
def list_fonts():
    """Return available font families from both static (-Regular.ttf) and variable ([...].ttf) fonts."""
    families: list[dict] = []
    seen: set[str] = set()

    # Static fonts: e.g. Roboto-Regular.ttf → family "Roboto"
    for p in sorted(FONTS_DIR.glob("*-Regular.ttf")):
        raw = p.stem.replace("-Regular", "")
        if raw not in seen:
            spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", raw)
            families.append({"id": raw, "name": spaced})
            seen.add(raw)

    # Variable fonts: e.g. Inter[opsz,wght].ttf → family "Inter"
    #                       Oswald[wght].ttf     → family "Oswald"
    for p in sorted(FONTS_DIR.glob("*.ttf")):
        if "[" not in p.name:
            continue
        # stem is e.g. "Inter[opsz,wght]" or "Inter-Italic[opsz,wght]"
        base = p.stem.split("[")[0].rstrip("-")  # → "Inter" or "Inter-Italic"
        if "Italic" in base or "italic" in base:
            continue  # skip italic variable file; listed under its upright family
        if base not in seen:
            spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", base)
            families.append({"id": base, "name": spaced})
            seen.add(base)

    families.sort(key=lambda f: f["name"])
    return jsonify({"fonts": families})


# ── Static file overrides (so Flask serves from correct subdirs) ──────────────

@app.route("/static/assets/<path:filename>")
def static_asset(filename: str):
    return send_from_directory(ASSETS_DIR, filename)


@app.route("/static/fonts/<path:filename>")
def static_font(filename: str):
    return send_from_directory(FONTS_DIR, filename)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 58)
    print("  Label Design Editor")
    print("  ->  http://localhost:5000")
    print("=" * 58)
    available_fonts = sorted(p.stem for p in FONTS_DIR.glob("*-Regular.ttf"))
    if available_fonts:
        print(f"  Fonts loaded: {', '.join(available_fonts)}")
    else:
        print("  ⚠  No fonts in static/fonts/ — Pillow default will be used.")
        print("     Run: python setup_fonts.py  to download bundled fonts.")
    print("=" * 58)
    app.run(debug=True, host="127.0.0.1", port=5000)
