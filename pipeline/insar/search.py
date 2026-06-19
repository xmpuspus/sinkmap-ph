"""Phase 0 reconnaissance: find the Sentinel-1 SLC stack for an AOI.

Queries the ASF archive (public, no auth needed for search) for Sentinel-1 IW
SLC scenes over an AOI, restricted to one flight direction, and reports the
per-track (relative-orbit) breakdown so you can pick a single coherent stack
for InSAR. Writes the chosen track's scene list plus a quarterly-subsampled
subset for the SBAS plan.

    python -m pipeline.insar.search --aoi metro-manila \
        --start 2016-01-01 --end 2026-01-01 --direction DESCENDING

This is the only Phase 0 step that runs without credentials. The actual InSAR
processing (submit_hyp3.py) needs an Earthdata login.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from pipeline import aoi as aoi_registry

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _quarter(dt: datetime) -> str:
    return f"{dt.year}Q{(dt.month - 1) // 3 + 1}"


def search(aoi_id: str, start: str, end: str, direction: str) -> dict:
    try:
        import asf_search as asf
    except ImportError as e:  # pragma: no cover
        raise SystemExit(
            "asf_search not installed. `pip install asf-search` "
            "(pure-Python, no auth needed for search)."
        ) from e

    aoi = aoi_registry.get(aoi_id)
    results = asf.geo_search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel=asf.PRODUCT_TYPE.SLC,
        beamMode=asf.BEAMMODE.IW,
        flightDirection=direction,
        intersectsWith=aoi.wkt(),
        start=start,
        end=end,
    )

    by_track = defaultdict(list)
    for r in results:
        p = r.properties
        by_track[p["pathNumber"]].append(
            {
                "scene": p["sceneName"],
                "date": p["startTime"][:10],
                "frame": p.get("frameNumber"),
                "orbit": p["pathNumber"],
            }
        )

    tracks = []
    for path, scenes in sorted(by_track.items(), key=lambda kv: -len(kv[1])):
        scenes.sort(key=lambda s: s["date"])
        tracks.append(
            {
                "path": path,
                "n_scenes": len(scenes),
                "frames": sorted({s["frame"] for s in scenes}),
                "date_min": scenes[0]["date"],
                "date_max": scenes[-1]["date"],
            }
        )

    chosen = tracks[0]["path"] if tracks else None
    chosen_scenes = sorted(by_track.get(chosen, []), key=lambda s: s["date"])

    # Quarterly subsample of the chosen track: first scene seen per quarter.
    seen_q = set()
    subsampled = []
    for s in chosen_scenes:
        q = _quarter(datetime.fromisoformat(s["date"]))
        if q not in seen_q:
            seen_q.add(q)
            subsampled.append(s)

    return {
        "aoi": aoi.id,
        "aoi_name": aoi.name,
        "bbox": list(aoi.bbox),
        "direction": direction,
        "window": [start, end],
        "total_scenes": sum(len(v) for v in by_track.values()),
        "tracks": tracks,
        "chosen_track": chosen,
        "chosen_track_n_scenes": len(chosen_scenes),
        "subsampled_quarterly_n": len(subsampled),
        "scenes_full": chosen_scenes,
        "scenes_subsampled": subsampled,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aoi", default="metro-manila")
    ap.add_argument("--start", default="2016-01-01")
    ap.add_argument("--end", default="2026-01-01")
    ap.add_argument("--direction", default="DESCENDING", choices=["DESCENDING", "ASCENDING"])
    ap.add_argument("--out", default=None, help="output JSON path (default data/insar/<aoi>/scenes.json)")
    args = ap.parse_args()

    res = search(args.aoi, args.start, args.end, args.direction)

    out = Path(args.out) if args.out else REPO_ROOT / "data" / "insar" / res["aoi"] / "scenes.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2))

    print(f"AOI: {res['aoi_name']}  ({args.direction})")
    print(f"window: {args.start} .. {args.end}")
    print(f"total {args.direction} SLC scenes intersecting bbox: {res['total_scenes']}")
    print("tracks (relative orbit -> scene count, date span, frames):")
    for t in res["tracks"]:
        print(
            f"  path {t['path']:>4}: {t['n_scenes']:>4} scenes  "
            f"{t['date_min']} .. {t['date_max']}  frames={t['frames']}"
        )
    print(f"chosen track: {res['chosen_track']} "
          f"({res['chosen_track_n_scenes']} scenes, "
          f"{res['subsampled_quarterly_n']} after quarterly subsample)")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
