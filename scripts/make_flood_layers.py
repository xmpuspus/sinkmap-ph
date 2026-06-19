"""Export the derived Sentinel-1 flood extents as map overlay PNGs.

For each event in pipeline/flood/flood_events.json, download the flood mask as a
transparent PNG (flooded = blue) via Earth Engine, and write web/data/flood-layers.json
(id, name, bounds, png, km2) for the frontend toggles. Run in .venv (GEE):

  SINKMAP_EE_KEY=~/Desktop/leaves-ph/.ee-key.json \
      .venv/bin/python scripts/make_flood_layers.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
import sys
sys.path.insert(0, str(ROOT))
from pipeline.flood import flood_extent as fx
from pipeline import aoi as reg

EVENTS = json.loads((ROOT / "pipeline" / "flood" / "flood_events.json").read_text())["events"]


def main():
    layers = []
    for ev in EVENTS:
        bbox = ev.get("bbox") or list(reg.get(ev["aoi"]).bbox)
        png = ROOT / "web" / "data" / "flood-extent" / f"{ev['id']}.png"
        fx.export_mask_png(bbox, ev["pre"], ev["post"], str(png))
        stat = ROOT / "web" / "data" / "flood" / f"{ev['id']}.json"
        km2 = json.loads(stat.read_text()).get("flooded_km2") if stat.exists() else None
        w, s, e, n = bbox
        layers.append({
            "id": ev["id"], "name": ev["name"],
            "coords": [[w, n], [e, n], [e, s], [w, s]],
            "png": f"data/flood-extent/{ev['id']}.png",
            "km2": round(km2, 1) if km2 else None,
        })
        print(f"{ev['id']}: {png.name} ({round(km2,1) if km2 else '?'} km2)")
    (ROOT / "web" / "data" / "flood-layers.json").write_text(json.dumps({"events": layers}, indent=2))
    print(f"wrote web/data/flood-layers.json ({len(layers)} events)")


if __name__ == "__main__":
    main()
