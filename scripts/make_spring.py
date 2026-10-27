"""Makes the spring of the site's motion: one curve, a damped spring that overshoots a little and settles, like jelly coming to rest,
neither sharp nor slow. Written as the points of a CSS linear() easing, into site/src/lib/spring.js (for the animations made in
script and for Svelte's transitions) and into the --spring variable of site/src/app.css (for the transitions in CSS).

    python scripts/make_spring.py
"""

from __future__ import annotations

import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZETA = 0.55  # damping: 0 never stops, 1 never overshoots; 0.55 overshoots by about 12%, once, a little again, and rests
OMEGA = 12.0  # how fast it swings: the whole motion in 1 unit of time
POINTS = 36


def spring(t: float) -> float:
    if t >= 1:
        return 1.0
    wd = OMEGA * math.sqrt(1 - ZETA**2)
    return 1 - math.exp(-ZETA * OMEGA * t) * (math.cos(wd * t) + ZETA * OMEGA / wd * math.sin(wd * t))


pts = [round(spring(i / (POINTS - 1)), 4) for i in range(POINTS)]
pts[0], pts[-1] = 0.0, 1.0
linear = "linear(" + ", ".join(f"{p:g}" for p in pts) + ")"
(ROOT / "site/src/lib/spring.js").write_text(
    "// The spring of the site's motion (made by scripts/make_spring.py; do not edit): a damped spring, overshooting a little.\n"
    f"export const SPRING_POINTS = {pts};\n"
    f'export const SPRING = "{linear}";\n'
    "/** The spring at time t in 0..1 (the same curve as SPRING, for animations that are worked out in script). */\n"
    "export function springAt(t) {\n"
    "  if (t <= 0) return 0;\n"
    "  if (t >= 1) return 1;\n"
    "  const x = t * (SPRING_POINTS.length - 1);\n"
    "  const i = Math.floor(x);\n"
    "  return SPRING_POINTS[i] + (SPRING_POINTS[i + 1] - SPRING_POINTS[i]) * (x - i);\n"
    "}\n",
    encoding="utf-8",
)
css = ROOT / "site/src/app.css"
text = css.read_text(encoding="utf-8")
line = f"  --spring: {linear}; /* the one spring of all motion: scripts/make_spring.py */"
if "--spring:" in text:
    text = re.sub(r"  --spring: .*", line, text, count=1)
else:
    text = text.replace("  --tile: 108px;", line + "\n  --tile: 108px;", 1)
css.write_text(text, encoding="utf-8")
print("peak", max(pts), "points", POINTS)

