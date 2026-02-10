from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
IMG_DIR = ROOT / "meu_app" / "static" / "images"

FILES = {
    "favicon-16.png": (16, 16),
    "favicon-32.png": (32, 32),
    "apple-touch-icon.png": (180, 180),
}


def recolor_to_white_keep_bg(img: Image.Image, bg_threshold: int = 20) -> Image.Image:
    """Turn non-background pixels (not near black) into white.

    These assets were rendered on a black background, so a simple threshold is reliable.
    """

    rgba = img.convert("RGBA")
    px = rgba.load()
    w, h = rgba.size

    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            # Treat near-black as background and keep it.
            if max(r, g, b) <= bg_threshold:
                continue
            # Convert foreground to white, preserve alpha for anti-aliasing.
            px[x, y] = (255, 255, 255, a)

    return rgba


def main() -> None:
    for name, expected_size in FILES.items():
        p = IMG_DIR / name
        img = Image.open(p)
        if img.size != expected_size:
            raise SystemExit(f"{name}: expected size {expected_size}, got {img.size}")
        out = recolor_to_white_keep_bg(img)
        out.save(p)
        print(f"updated {p}")

    # Rebuild favicon.ico with multiple sizes from the 32px source.
    src32 = Image.open(IMG_DIR / "favicon-32.png").convert("RGBA")
    ico_path = IMG_DIR / "favicon.ico"
    src32.save(ico_path, sizes=[(16, 16), (32, 32), (48, 48)])
    print(f"rebuilt {ico_path}")


if __name__ == "__main__":
    main()
