"""Phase 2: derive a recent flood extent from Sentinel-1 SAR in Earth Engine.

Standard pre/post change-detection recipe (UN-SPIDER): a flood shows up as a
drop in SAR backscatter (smooth water reflects radar away). Compare a dry-
reference median against the flood-peak median, threshold the drop, then remove
permanent water (JRC) and steep slopes (false positives).

SAR sees through the typhoon cloud that blinds optical, which is the whole point
of using Sentinel-1 here. This is the flood overlay the subsidence map is
corroborated against; it is independent of the InSAR (HyP3) track and runs on
the personal GEE service account, so it is not blocked on an Earthdata login.

    SINKMAP_EE_KEY=/path/to/.ee-key.json \
        python -m pipeline.flood.flood_extent --event carina-habagat-2024

Thresholds are calibration starting points, not final. Output is a flooded-area
number plus scene counts (so a window with no overpass at the flood peak is
visible, not silently zero).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline import _gee_init
from pipeline import aoi as aoi_registry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS = Path(__file__).resolve().parent / "flood_events.json"


def _resolve_bbox(event: dict):
    if "bbox" in event:
        return event["bbox"]
    return list(aoi_registry.get(event["aoi"]).bbox)


def _flood_mask(geom, pre, post, drop_db, water_db, direction):
    """The selfMasked flooded ee.Image + the pre/post collections (for counts)."""
    import ee

    s1 = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(geom)
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .filter(ee.Filter.eq("orbitProperties_pass", direction))
        .select("VH")
    )
    pre_col = s1.filterDate(pre[0], pre[1])
    post_col = s1.filterDate(post[0], post[1])
    pre_img = pre_col.median().clip(geom)
    post_img = post_col.median().clip(geom)
    # VH backscatter is in dB; a flood drops it. Flagged where post is at least
    # drop_db below pre AND below an absolute open-water level.
    drop = pre_img.subtract(post_img)  # positive = backscatter fell
    flooded = drop.gt(drop_db).And(post_img.lt(water_db))
    # Remove permanent water (>=10 months/yr) and steep slope.
    perm = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("seasonality").gte(10)
    slope = ee.Terrain.slope(ee.Image("USGS/SRTMGL1_003"))
    flooded = flooded.And(perm.Not()).And(slope.lt(5)).selfMask()
    return flooded, pre_col, post_col


def flood_extent(bbox, pre, post, drop_db=1.5, water_db=-18.0, direction="DESCENDING"):
    """Compute flooded area (km2) for a pre/post Sentinel-1 window over bbox."""
    _gee_init.init()
    import ee

    geom = ee.Geometry.Rectangle(bbox)
    flooded, pre_col, post_col = _flood_mask(geom, pre, post, drop_db, water_db, direction)
    area_km2 = (
        flooded.multiply(ee.Image.pixelArea())
        .reduceRegion(reducer=ee.Reducer.sum(), geometry=geom, scale=30,
                      maxPixels=int(1e10), bestEffort=True)
        .get("VH")
    )
    return ee.Dictionary({
        "flooded_km2": ee.Number(area_km2).divide(1e6),
        "pre_scenes": pre_col.size(), "post_scenes": post_col.size(),
    }).getInfo()


def export_mask_png(bbox, pre, post, out_png, drop_db=1.5, water_db=-18.0,
                    direction="DESCENDING", dim=900):
    """Download the flood mask as a transparent PNG overlay (flooded = blue)."""
    import urllib.request

    _gee_init.init()
    import ee

    geom = ee.Geometry.Rectangle(bbox)
    flooded, _, _ = _flood_mask(geom, pre, post, drop_db, water_db, direction)
    vis = flooded.visualize(palette=["1f6feb"], min=0, max=1)  # selfMasked -> transparent elsewhere
    url = vis.getThumbURL({"region": geom, "dimensions": dim, "format": "png"})
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, out_png)
    return out_png


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--event", required=True)
    ap.add_argument("--direction", default="DESCENDING", choices=["DESCENDING", "ASCENDING"])
    args = ap.parse_args()

    events = {e["id"]: e for e in json.loads(EVENTS.read_text())["events"]}
    if args.event not in events:
        raise SystemExit(f"unknown event {args.event!r}. Known: {list(events)}")
    ev = events[args.event]
    bbox = _resolve_bbox(ev)

    res = flood_extent(bbox, ev["pre"], ev["post"], direction=args.direction)

    out = REPO_ROOT / "web" / "data" / "flood" / f"{ev['id']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {"event": ev["id"], "name": ev["name"], "bbox": bbox,
               "direction": args.direction, **ev, **res}
    out.write_text(json.dumps(payload, indent=2))

    print(f"event: {ev['name']} ({args.direction})")
    print(f"pre window {ev['pre']}: {res['pre_scenes']} S1 scenes")
    print(f"post window {ev['post']}: {res['post_scenes']} S1 scenes")
    print(f"flooded area: {res['flooded_km2']:.1f} km2")
    print(f"wrote {out}")
    if res["post_scenes"] == 0:
        print("WARNING: no Sentinel-1 overpass in the post window; the flood peak "
              "was likely between revisits. Widen the window or try --direction ASCENDING.")


if __name__ == "__main__":
    main()
