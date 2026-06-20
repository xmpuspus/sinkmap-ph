"""Record the walkthrough GIF from the real map (docs/demo.gif).

Drives the live site with agent-browser, leading with the story rail (the
first-touch insight sequence): overview with the rail on screen -> tap the rail
to fly to the acceleration layer (orange = speeding up, purple = slowing) with
callouts -> walk to the next finding -> Find your city (Dagupan) place card ->
Watch it sink (2016 -> 2025) -> toggle a recent flood extent. Real recording of
the actual map, never a mockup.

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
    ab("set", "viewport", "1280", "800")
    ab("open", URL); ab("wait", "3200")
    shot("f0.png")                                                                                # overview: the rail leads, 1/10
    ev("document.getElementById('rail-card').click()"); ab("wait", "1900"); shot("f1.png")        # tap rail -> accel layer + callouts
    shot("f2.png")                                                                                # hold accel
    ev("document.getElementById('rail-next').click()"); ab("wait", "1700"); shot("f3.png")        # walk to the next finding (compound)
    ev("var s=document.getElementById('findcity');s.value='c:dagupan';s.dispatchEvent(new Event('change'))")
    ab("wait", "1700"); shot("f4.png")                                                            # find your city -> Dagupan card
    shot("f5.png")                                                                                # hold Dagupan
    ev("document.getElementById('cd-close').click();document.querySelectorAll('.pin')[0].click();window.map.jumpTo({center:[120.98,15.05],zoom:8.9})")
    ab("wait", "1200")
    ev("document.getElementById('mode-l').click()"); ab("wait", "1100"); shot("f6.png")           # watch Manila sink @2016
    for k, fr in enumerate([3, 7], start=7):                                                       # play it sink
        ev(f"var s=document.getElementById('slider');s.value={fr};s.dispatchEvent(new Event('input'))")
        ab("wait", "950"); shot(f"f{k}.png")
    ev("document.getElementById('mode-v').click();document.querySelectorAll('#flood-toggles input')[0].click()")
    ab("wait", "1800"); shot("f9.png")                                                            # flood flies in + paints
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
