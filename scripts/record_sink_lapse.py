"""Record the "watch it sink" GIF from the real map (docs/sink-lapse.gif).

Drives the live site with agent-browser: zooms to Metro Manila, switches to the
sink-lapse mode, steps the date slider 2016 -> 2025 capturing one frame each, then
two-pass-palette ffmpeg's them into a GIF with a hold on the final frame. Real
recording of the actual map, never a mockup.

  make serve &                       # Range-capable server on :8788
  python3 scripts/record_sink_lapse.py
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FR = ROOT / "tmp" / "gifframes"
URL = "http://localhost:8788"
NFRAMES = 8


def ab(*args):
    subprocess.run(["agent-browser", *args], capture_output=True)


def main():
    FR.mkdir(parents=True, exist_ok=True)
    ab("open", URL)
    ab("wait", "3000")
    ab("eval", "window.map.jumpTo({center:[120.98,15.0],zoom:8.8});"
       "document.getElementById('mode-l').click();"
       "document.getElementById('head').style.display='none';")
    ab("wait", "800")
    for i in range(NFRAMES):
        ab("eval", f"var s=document.getElementById('slider');s.value={i};"
           "s.dispatchEvent(new Event('input'));")
        ab("wait", "700")
        ab("screenshot", str(FR / f"f{i}.png"))
    # hold the final frame
    for k in range(NFRAMES, NFRAMES + 3):
        subprocess.run(["cp", str(FR / f"f{NFRAMES-1}.png"), str(FR / f"f{k}.png")])
    out = ROOT / "docs" / "sink-lapse.gif"
    out.parent.mkdir(exist_ok=True)
    pal = FR / "pal.png"
    vf = "fps=1.5,scale=860:-1:flags=lanczos"
    subprocess.run(["ffmpeg", "-y", "-framerate", "1.5", "-i", str(FR / "f%d.png"),
                    "-vf", vf + ",palettegen=stats_mode=full", str(pal)], check=True)
    subprocess.run(["ffmpeg", "-y", "-framerate", "1.5", "-i", str(FR / "f%d.png"),
                    "-i", str(pal), "-lavfi", vf + ",paletteuse=dither=sierra2_4a", str(out)], check=True)
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
