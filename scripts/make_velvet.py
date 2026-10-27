"""Makes the two pile textures of the site's velvet (web/pile.webp, web/suede.webp), as transparent layers (light and dark
strokes with a low alpha) that lie under a surface's colour and light (site/src/velvet.css).

  pile   the nap of velvet: fibres all combed one way, so the surface has a grain you can feel with the eye, a cloudy
         unevenness where the pile is pressed flatter or stands taller, and a dust of single fibres that catch the light;
  suede  a shorter, denser nap with hardly any direction: the felt of controls and tiles.

Both tile without a seam.

    python scripts/make_velvet.py
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

SIZE = 256
WEB = Path(__file__).resolve().parent.parent / "web"
rng = np.random.default_rng(5)


def combed(par: float, perp: float, angle: float) -> np.ndarray:
    """Tileable noise stretched along `angle` (degrees): strokes about `par` px long and `perp` px thick, scaled to -1..1."""
    f = np.fft.fft2(rng.standard_normal((SIZE, SIZE)))
    fy = np.fft.fftfreq(SIZE)[:, None]
    fx = np.fft.fftfreq(SIZE)[None, :]
    t = np.radians(angle)
    along = fx * np.cos(t) + fy * np.sin(t)
    across = -fx * np.sin(t) + fy * np.cos(t)
    f *= np.exp(-((2 * np.pi) ** 2) * (along**2 * par**2 + across**2 * perp**2) / 2)
    n = np.real(np.fft.ifft2(f))
    return n / np.abs(n).max()


def dust(count: int, reach: float) -> np.ndarray:
    """Single fibres that catch the light: a few bright, soft points."""
    layer = np.zeros((SIZE, SIZE), np.float32)
    for _ in range(count):
        layer[rng.integers(SIZE), rng.integers(SIZE)] = rng.uniform(0.4, 1.0) * reach
    return cv2.GaussianBlur(layer, (0, 0), 0.7) * 3.2


def write(name: str, v: np.ndarray, light: float, dark: float) -> None:
    v = v / np.abs(v).max()
    pos = np.clip(v, 0, None) ** 1.15 * light  # white: pile lying toward the light
    neg = np.clip(-v, 0, None) ** 1.15 * dark  # black: pile in its own shade
    alpha = np.maximum(pos, neg)
    shade = np.where(v > 0, 255, 0)[..., None].repeat(3, axis=2).astype(np.uint8)
    img = np.dstack([shade, (alpha * 255).astype(np.uint8)])
    path = WEB / name
    cv2.imwrite(str(path), img, [cv2.IMWRITE_WEBP_QUALITY, 82])
    print(path, path.stat().st_size, "bytes", "alpha max", int(alpha.max() * 255))


NAP = 62  # the way the pile is combed
pile = combed(0.75, 0.75, 0) * 0.74 + combed(1.15, 0.6, NAP) * 0.14 + dust(110, 1.0) * 0.14
write("pile.webp", pile, light=0.04, dark=0.075)

suede = combed(0.65, 0.65, 0) * 0.82 + combed(1.0, 0.55, 20) * 0.10 + dust(60, 0.8) * 0.1
write("suede.webp", suede, light=0.035, dark=0.07)
