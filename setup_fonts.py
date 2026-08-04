"""
setup_fonts.py — One-time script to download bundled TrueType fonts.

Run once before starting the app:
    python setup_fonts.py
"""

import urllib.request
import sys
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent / "static" / "fonts"
FONTS_DIR.mkdir(parents=True, exist_ok=True)

# Stable TTF download URLs
FONTS = {
    # Inter — rsms/inter stable release
    "Inter-Regular.ttf":
        "https://github.com/rsms/inter/raw/v4.1/extras/ttf/Inter-Regular.ttf",
    "Inter-Bold.ttf":
        "https://github.com/rsms/inter/raw/v4.1/extras/ttf/Inter-Bold.ttf",
    "Inter-Italic.ttf":
        "https://github.com/rsms/inter/raw/v4.1/extras/ttf/Inter-Italic.ttf",
    "Inter-BoldItalic.ttf":
        "https://github.com/rsms/inter/raw/v4.1/extras/ttf/Inter-BoldItalic.ttf",

    # Roboto — googlefonts/roboto hinted static
    "Roboto-Regular.ttf":
        "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf",
    "Roboto-Bold.ttf":
        "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf",
    "Roboto-Italic.ttf":
        "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Italic.ttf",

    # Roboto Condensed
    "RobotoCondensed-Regular.ttf":
        "https://github.com/googlefonts/roboto/raw/main/src/hinted/RobotoCondensed-Regular.ttf",
    "RobotoCondensed-Bold.ttf":
        "https://github.com/googlefonts/roboto/raw/main/src/hinted/RobotoCondensed-Bold.ttf",

    # Oswald — google/fonts static
    "Oswald-Regular.ttf":
        "https://github.com/google/fonts/raw/main/ofl/oswald/static/Oswald-Regular.ttf",
    "Oswald-Bold.ttf":
        "https://github.com/google/fonts/raw/main/ofl/oswald/static/Oswald-Bold.ttf",
}


def download_fonts():
    ok = 0
    fail = 0
    for filename, url in FONTS.items():
        dest = FONTS_DIR / filename
        if dest.exists() and dest.stat().st_size > 1000:
            print(f"  [OK] {filename}  (already present)")
            ok += 1
            continue
        print(f"  [...] {filename} ...", end=" ", flush=True)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp, open(dest, "wb") as f:
                f.write(resp.read())
            size = dest.stat().st_size
            print(f"OK ({size // 1024} KB)")
            ok += 1
        except Exception as exc:
            print(f"FAILED -- {exc}")
            if dest.exists():
                dest.unlink()
            fail += 1

    print()
    if fail:
        print(f"  [WARN] {fail} font(s) failed to download.  "
              f"The app will use Pillow's default font as fallback.")
    print(f"  [OK] {ok} font(s) ready in static/fonts/")


if __name__ == "__main__":
    print("=" * 56)
    print("  LabelForge — Font Setup")
    print("=" * 56)
    download_fonts()
    print()
    print("Done!  Start the editor with:  python app.py")
