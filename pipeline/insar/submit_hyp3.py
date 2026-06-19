"""Phase 0: submit the SBAS InSAR stack to ASF HyP3.

Reads the quarterly-subsampled scene list from search.py, builds a short-
baseline (SBAS) pair network, and submits each pair to HyP3 for on-demand
InSAR processing. HyP3 needs an Earthdata login (~/.netrc or interactive) and
spends credits (8,000/month free). Processing queues for 1-7 days; download
and MintPy come after.

    # inspect the pair plan + credit footprint, no auth, no submission:
    python -m pipeline.insar.submit_hyp3 --aoi metro-manila --dry-run

    # actually submit (needs Earthdata login):
    python -m pipeline.insar.submit_hyp3 --aoi metro-manila

Pairing: each scene connects to the next `--connections` scenes within
`--max-days`, which keeps temporal baselines short (coherence) while spanning
the full window for a stable velocity.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def build_pairs(
    scenes: List[dict], connections: int, max_days: int
) -> List[Tuple[str, str]]:
    """SBAS network: connect each scene to the next N within max_days."""
    pairs = []
    for i, ref in enumerate(scenes):
        ref_d = datetime.fromisoformat(ref["date"])
        made = 0
        for sec in scenes[i + 1 :]:
            if made >= connections:
                break
            sec_d = datetime.fromisoformat(sec["date"])
            if (sec_d - ref_d).days <= max_days:
                pairs.append((ref["scene"], sec["scene"]))
                made += 1
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aoi", default="metro-manila")
    ap.add_argument("--connections", type=int, default=3, help="SBAS links per scene")
    ap.add_argument("--max-days", type=int, default=200, help="max temporal baseline")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, do not submit")
    ap.add_argument("--scenes", default=None, help="scenes.json (default data/insar/<aoi>/scenes.json)")
    args = ap.parse_args()

    scenes_path = (
        Path(args.scenes)
        if args.scenes
        else REPO_ROOT / "data" / "insar" / args.aoi / "scenes.json"
    )
    if not scenes_path.exists():
        raise SystemExit(f"no scene list at {scenes_path}. Run pipeline.insar.search first.")

    data = json.loads(scenes_path.read_text())
    scenes = data["scenes_subsampled"]
    pairs = build_pairs(scenes, args.connections, args.max_days)

    est_credits = len(pairs) * 10  # INSAR_GAMMA at 20x4 looks = 10 credits/pair (HyP3 /costs)
    print(f"AOI {args.aoi}: {len(scenes)} subsampled scenes, track {data['chosen_track']}")
    print(f"SBAS pairs (<= {args.connections} links/scene, <= {args.max_days} days): {len(pairs)}")
    print(f"est cost: ~{est_credits} credits (INSAR_GAMMA, 20x4 looks = 10/pair), "
          f"well within the 8,000/month free allotment. "
          f"Burst InSAR (INSAR_ISCE_BURST) is 1 credit/pair if you want it cheaper.")

    if args.dry_run:
        for a, b in pairs[:6]:
            print(f"  pair: {a[17:25]} x {b[17:25]}")
        if len(pairs) > 6:
            print(f"  ... and {len(pairs) - 6} more")
        print("dry run: nothing submitted.")
        return

    try:
        import hyp3_sdk
    except ImportError as e:  # pragma: no cover
        raise SystemExit("hyp3-sdk not installed. `pip install hyp3-sdk`.") from e

    from pipeline.insar._edl import hyp3_client

    hyp3 = hyp3_client()  # EDL bearer token from env/.env (see docs/setup-earthdata.md)
    batch = hyp3_sdk.Batch()
    for ref, sec in pairs:
        batch += hyp3.submit_insar_job(
            ref, sec, name=f"sinkmap-{args.aoi}",
            include_dem=True, include_look_vectors=True,  # look vectors -> incidence for LOS->vertical
        )
    out = scenes_path.parent / "hyp3_batch.json"
    out.write_text(json.dumps([j.to_dict() for j in batch.jobs], indent=2, default=str))
    print(f"submitted {len(batch)} jobs; saved {out}. Poll with hyp3.watch(batch).")


if __name__ == "__main__":
    main()
