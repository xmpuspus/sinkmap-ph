"""Record the walkthrough GIF from the real map (docs/demo.gif).

Drives the live site with agent-browser: overview -> click Metro Manila (place
card) -> Watch it sink (2016 -> 2025 with the cumulative-mm readout) -> toggle a
recent flood extent (flies to it and paints it over the velocity layer). Real
recording of the actual map, never a mockup.

  make serve &
  python3 scripts/record_demo.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FR = ROOT / "tmp" / "demoframes"
URL = "http://localhost:8788"


def ab(*a): subprocess.run(["agent-browser", *a], capture_output=True)
def shot(n): ab("screenshot", str(FR / n))
def ev(js): ab("eval", js)


def main():
    FR.mkdir(parents=True, exist_ok=True)
    ab("open", URL); ab("wait", "3000")
    ev("window.map.jumpTo({center:[122.2,12.6],zoom:5.2})"); ab("wait", "900"); shot("f0.png")   # overview
    ev("document.querySelectorAll('.pin')[0].click()"); ab("wait", "1700"); shot("f1.png")        # MM card
    ev("window.map.jumpTo({center:[120.98,15.05],zoom:8.9})"); ab("wait", "1000"); shot("f2.png") # wider, card open
    ev("document.getElementById('mode-l').click()"); ab("wait", "1100"); shot("f3.png")           # sink @ 2016 (clean)
    for k, fr in enumerate([2, 4, 6, 7], start=4):                                                # play it sink
        ev(f"var s=document.getElementById('slider');s.value={fr};s.dispatchEvent(new Event('input'))")
        ab("wait", "850"); shot(f"f{k}.png")
    ev("document.getElementById('mode-v').click();document.querySelectorAll('#flood-toggles input')[0].click()")
    ab("wait", "1700"); shot("f8.png")                                                            # flood flies in + paints
    shot("f9.png")
    for k in (10, 11):
        subprocess.run(["cp", str(FR / "f9.png"), str(FR / f"f{k}.png")])                         # hold last
    out = ROOT / "docs" / "demo.gif"
    pal = FR / "pal.png"; vf = "fps=1.05,scale=900:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-y", "-framerate", "1.05", "-i", str(FR / "f%d.png"),
                    "-vf", vf + ",palettegen=stats_mode=full", str(pal)], check=True)
    subprocess.run(["ffmpeg", "-y", "-framerate", "1.05", "-i", str(FR / "f%d.png"),
                    "-i", str(pal), "-lavfi", vf + ",paletteuse=dither=sierra2_4a", str(out)], check=True)
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
