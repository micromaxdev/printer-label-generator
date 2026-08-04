"""
render_label.py — Standalone label renderer for Brother QL labels.

Public API
----------
    from render_label import render_label

    img = render_label("layouts/woodward-visitor.json", {
        "visitorName": "Mike Barkley",
        "company":     "Court Corp",
        "host":        "Host: Martin Dillich",
        "date":        "04/08/26",
        "visitorType": "Visitor",
        "visitorId":   "VIS-001",
        "logoPath":    "static/assets/Woodward W ONLY.png",
    })
    img.save("output.png")

CLI
---
    python render_label.py \\
        --layout layouts/woodward-visitor.json \\
        --data '{"visitorName":"Mike Barkley",...}' \\
        --output output.png
"""

from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

try:
    import qrcode
    import qrcode.constants
    _HAS_QR = True
except ImportError:  # pragma: no cover
    _HAS_QR = False

# ── Paths ─────────────────────────────────────────────────────────────────────

# The script lives in the project root; all relative asset paths resolve from here.
_HERE: Path = Path(__file__).resolve().parent
FONTS_DIR: Path = _HERE / "static" / "fonts"


# ── Font Loading ──────────────────────────────────────────────────────────────

# Sorted list of TTF files in the fonts directory (rebuilt on first call)
_font_files_cache: list[Path] | None = None

def _all_font_files() -> list[Path]:
    global _font_files_cache
    if _font_files_cache is None:
        _font_files_cache = sorted(FONTS_DIR.glob("*.ttf"))
    return _font_files_cache


def _font_file(family: str, bold: bool, italic: bool) -> tuple[Path, bool] | tuple[None, bool]:
    """
    Return ``(path, is_variable)`` for the best matching font file.

    ``is_variable`` is True when the file is a variable font and the caller
    must set axes to select weight/style.
    """
    stem_target = family.replace(" ", "")

    # --- 1. Try static fonts first (e.g. Roboto-Bold.ttf) -------------------
    static_candidates: list[str] = []
    if bold and italic:
        static_candidates = [
            f"{stem_target}-BoldItalic.ttf",
            f"{stem_target}-Bold.ttf",
            f"{stem_target}-Regular.ttf",
        ]
    elif bold:
        static_candidates = [
            f"{stem_target}-Bold.ttf",
            f"{stem_target}-SemiBold.ttf",
            f"{stem_target}-Regular.ttf",
        ]
    elif italic:
        static_candidates = [
            f"{stem_target}-Italic.ttf",
            f"{stem_target}-Regular.ttf",
        ]
    else:
        static_candidates = [f"{stem_target}-Regular.ttf"]

    for name in static_candidates:
        p = FONTS_DIR / name
        if p.exists() and p.stat().st_size > 1000:
            return p, False

    # --- 2. Try variable fonts (e.g. Inter[opsz,wght].ttf) ------------------
    # A variable font filename contains "[" and starts with the family stem.
    for p in _all_font_files():
        if "[" in p.name and p.stem.startswith(stem_target):
            # Prefer italic variable font when italic is requested
            if italic and "Italic" in p.name:
                return p, True
            if not italic and "Italic" not in p.name:
                return p, True
    # Fallback: any variable font for this family
    for p in _all_font_files():
        if "[" in p.name and p.stem.startswith(stem_target):
            return p, True

    # --- 3. Last resort: any font in the directory ---------------------------
    for p in _all_font_files():
        if p.stat().st_size > 1000:
            return p, "[" in p.name

    return None, False


@lru_cache(maxsize=128)
def _get_font(family: str, size: int, bold: bool = False, italic: bool = False) -> ImageFont.FreeTypeFont:
    """Load and cache a TrueType font, handling both static and variable fonts."""
    path, is_variable = _font_file(family, bold, italic)
    if path is None:
        return ImageFont.load_default(size=max(10, size))
    try:
        font = ImageFont.truetype(str(path), max(6, size))
        if is_variable:
            # Set weight axis: 700 for bold, 400 for regular
            weight = 700 if bold else 400
            try:
                font.set_variation_by_axes([weight])
            except (AttributeError, Exception):
                try:
                    font.set_variation_by_name("Bold" if bold else "Regular")
                except (AttributeError, Exception):
                    pass  # Old Pillow or font doesn't support it — use default weight
        return font
    except Exception as exc:
        print(f"[render_label] Font load failed ({path}): {exc}", file=sys.stderr)
    return ImageFont.load_default(size=max(10, size))



# ── Element Renderers ─────────────────────────────────────────────────────────

def _draw_text(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    el: dict,
    data: dict,
    base_dir: Path,
) -> None:
    field = el.get("field", "")
    text = str(data.get(field, f"[{field}]"))
    if not text:
        return

    x, y  = el["x"], el["y"]
    el_w  = el.get("w", img.width - x)
    font  = _get_font(
        el.get("fontFamily", "Inter"),
        el.get("fontSize", 24),
        bool(el.get("bold", False)),
        bool(el.get("italic", False)),
    )
    color = el.get("color", "#000000")
    align = el.get("align", "left")

    # Map alignment to Pillow anchor + x coordinate
    if align == "center":
        tx, anchor = x + el_w // 2, "mt"
    elif align == "right":
        tx, anchor = x + el_w, "rt"
    else:
        tx, anchor = x, "lt"

    draw.text((tx, y), text, fill=color, font=font, anchor=anchor)


def _draw_image(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    el: dict,
    data: dict,
    base_dir: Path,
) -> None:
    # Field value (if present) overrides the static 'src' in the layout
    field = el.get("field", "")
    src   = data.get(field) or el.get("src", "")
    if not src:
        return

    src_path = Path(src) if Path(src).is_absolute() else base_dir / src
    if not src_path.exists():
        print(f"[render_label] Image not found: {src_path}", file=sys.stderr)
        return

    logo = Image.open(src_path).convert("RGBA")
    el_w, el_h = el.get("w", 100), el.get("h", 100)

    if el.get("lockAspect", True):
        logo.thumbnail((el_w, el_h), Image.LANCZOS)
    else:
        logo = logo.resize((el_w, el_h), Image.LANCZOS)

    # Composite using alpha channel (handles anti-aliased edges)
    img.paste(logo, (el["x"], el["y"]), logo.split()[3])


def _draw_qrcode(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    el: dict,
    data: dict,
    base_dir: Path,
) -> None:
    field    = el.get("field", "visitorId")
    data_str = str(data.get(field, field or "QR"))
    size     = max(10, el.get("w", 150))
    x, y     = el["x"], el["y"]

    if not _HAS_QR:
        # Draw a visible placeholder if qrcode library is missing
        draw.rectangle([x, y, x + size, y + size], outline="#000000", width=2)
        draw.text((x + 4, y + 4), "QR\n(install\nqrcode)", fill="#888888")
        return

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=1,
    )
    qr.add_data(data_str)
    qr.make(fit=True)

    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_img = qr_img.resize((size, size), Image.LANCZOS)
    img.paste(qr_img, (x, y))


def _draw_line(
    img: Image.Image,
    draw: ImageDraw.ImageDraw,
    el: dict,
    data: dict,
    base_dir: Path,
) -> None:
    x, y      = el["x"], el["y"]
    length    = el.get("w", img.width - x)
    thickness = max(1, el.get("h", 2))
    color     = el.get("color", "#000000")
    draw.rectangle([x, y, x + length, y + thickness - 1], fill=color)


# ── Dispatch table ────────────────────────────────────────────────────────────

_RENDERERS: dict[str, Any] = {
    "text":   _draw_text,
    "image":  _draw_image,
    "qrcode": _draw_qrcode,
    "line":   _draw_line,
}


# ── Core render function ──────────────────────────────────────────────────────

def _render_from_layout(
    layout: dict,
    data_dict: dict[str, Any],
    base_dir: Path,
) -> Image.Image:
    canvas = layout["canvas"]
    w, h   = int(canvas["width"]), int(canvas["height"])
    bg     = canvas.get("background", "#ffffff")

    img  = Image.new("RGB", (w, h), color=bg)
    draw = ImageDraw.Draw(img)

    elements = sorted(layout.get("elements", []), key=lambda e: e.get("zIndex", 0))

    for el in elements:
        renderer = _RENDERERS.get(el.get("type", ""))
        if renderer is None:
            continue
        try:
            renderer(img, draw, el, data_dict, base_dir)
        except Exception as exc:
            eid = el.get("id", "?")
            print(f"[render_label] Error on element '{eid}': {exc}", file=sys.stderr)

    return img


def render_label(
    layout_json_path: str | Path,
    data_dict: dict[str, Any],
) -> Image.Image:
    """
    Render a label image from a saved layout JSON file.

    Parameters
    ----------
    layout_json_path : str | Path
        Path to the layout JSON file (e.g. ``"layouts/woodward-visitor.json"``).
    data_dict : dict
        Field values to substitute into the layout.  Required keys depend on
        which elements the layout defines (e.g. ``visitorName``, ``company``, …).

    Returns
    -------
    PIL.Image.Image
        An RGB image.  Call ``.save("output.png")`` on it to write to disk.
    """
    path     = Path(layout_json_path).resolve()
    base_dir = path.parent.parent  # layouts/../ == project root

    with open(path, encoding="utf-8") as f:
        layout = json.load(f)

    return _render_from_layout(layout, data_dict, base_dir)


def render_label_from_dict(
    layout: dict,
    data_dict: dict[str, Any],
    base_dir: Path | None = None,
) -> Image.Image:
    """
    Like :func:`render_label` but accepts an already-parsed layout dict.
    Used by the Flask preview endpoint to avoid writing a temp file.

    Parameters
    ----------
    layout : dict
        Parsed layout JSON.
    data_dict : dict
        Field values.
    base_dir : Path, optional
        Project root used to resolve relative asset paths.
        Defaults to the directory containing this module.
    """
    return _render_from_layout(layout, data_dict, base_dir or _HERE)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Render a Brother QL label to PNG.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example
-------
  python render_label.py \\
      --layout layouts/woodward-visitor.json \\
      --data '{"visitorName":"Mike Barkley","company":"Court Corp","host":"Host: Martin Dillich","date":"04/08/26","visitorType":"Visitor","visitorId":"VIS-001","logoPath":"static/assets/Woodward W ONLY.png"}' \\
      --output output.png
""",
    )
    parser.add_argument("--layout", required=True, help="Path to layout JSON file")
    parser.add_argument("--data",   required=True, help="JSON string of field values")
    parser.add_argument("--output", default="output.png", help="Output PNG path (default: output.png)")
    args = parser.parse_args()

    data_dict = json.loads(args.data)
    image     = render_label(args.layout, data_dict)
    image.save(args.output)
    print(f"✓ Saved {args.output}  ({image.width} × {image.height} px)")
