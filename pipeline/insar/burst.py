"""Burst-InSAR scale-out path (1 credit/pair vs 10 for full-scene GAMMA).

For validation we process the single descending burst that covers a city's known
subsidence hotspot (or urban core) and compare the rate there to the GAMMA truth.
HyP3 INSAR_ISCE_BURST emits the same band names as GAMMA (unw_phase, corr, dem,
lv_theta, lv_phi), so the existing lean_fetch + clip + MintPy chain handles the
products unchanged.

  .venv/bin/python pipeline/insar/burst.py plan metro-manila cebu-mandaue ...
  .venv/bin/python pipeline/insar/burst.py submit cebu-mandaue --budget 320
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.insar.submit_hyp3 import build_pairs  # noqa: E402

# Known subsidence hotspots (from tmp/phase2/<aoi>-result.json); coherence-limited
# cities fall back to their urban core. The validation compares the burst rate
# here against the GAMMA-measured rate at the same point.
TARGET = {
    "metro-manila": (15.177, 120.983),   # Bulacan hotspot, GAMMA 72 mm/yr
    "cebu-mandaue": (10.2625, 123.8693),  # Talisay/SRP coast, GAMMA ~10 (peak 35)
    "iloilo": (10.7676, 122.5127),        # coastal peak, GAMMA ~10
    "davao": (7.072, 125.613),            # urban core (GAMMA coherence-limited)
    "legazpi": (13.143, 123.744),         # urban core (GAMMA coherence-limited)
}
CONNECTIONS, MAX_DAYS = 3, 200


def _quarterly(scenes):
    seen, out = set(), []
    for s in sorted(scenes, key=lambda x: x["date"]):
        d = datetime.fromisoformat(s["date"])
        q = (d.year, (d.month - 1) // 3)
        if q not in seen:
            seen.add(q); out.append(s)
    return out


def covering_burst(lat, lon, pad=0.02):
    """The descending burst stack covering (lat,lon): pick the fullBurstID with
    the most acquisitions intersecting a small box around the point."""
    import asf_search as asf
    wkt = (f"POLYGON(({lon-pad} {lat-pad},{lon+pad} {lat-pad},{lon+pad} {lat+pad},"
           f"{lon-pad} {lat+pad},{lon-pad} {lat-pad}))")
    r = asf.search(dataset=asf.DATASET.SLC_BURST, intersectsWith=wkt,
                   start="2016-01-01", end="2026-01-01", flightDirection="DESCENDING")
    by = defaultdict(list)
    for x in r:
        p = x.properties
        if "_VV_" not in (p.get("fileID") or ""):  # InSAR pairs need one polarization
            continue
        b = p.get("burst") or {}
        by[b.get("fullBurstID")].append({"scene": p["fileID"], "date": p["startTime"][:10]})
    if not by:
        return None
    fb = max(by, key=lambda k: len(by[k]))
    return fb, _quarterly(by[fb])


def recon(aoi):
    lat, lon = TARGET[aoi]
    res = covering_burst(lat, lon)
    if not res:
        return {"aoi": aoi, "ok": False, "reason": "no burst covers the target point"}
    fb, sub = res
    pairs = build_pairs(sub, CONNECTIONS, MAX_DAYS)
    return {"aoi": aoi, "ok": True, "burst": fb, "target": [lat, lon],
            "scenes": len(sub), "pairs": len(pairs), "credits": len(pairs),
            "date_min": sub[0]["date"], "date_max": sub[-1]["date"], "subsampled": sub}


def plan(aois, budget):
    rows, picked, spent = [], [], 0
    for a in aois:
        r = recon(a)
        if not r.get("ok"):
            print(f"{a:14} {r.get('reason')}"); continue
        fits = (spent + r["credits"]) <= budget
        if fits:
            picked.append(a); spent += r["credits"]
        print(f"{a:14} burst {r['burst']:>16}  {r['scenes']:>2} scenes  {r['pairs']:>3} pairs"
              f"  ~{r['credits']:>3} cr  {r['date_min']}..{r['date_max']}  [{'PICK' if fits else 'skip-budget'}]")
        rows.append(r)
    print(f"\nselected {len(picked)} of {len(aois)}, ~{spent} credits of {budget}: {', '.join(picked)}")
    return rows, picked, spent


def submit(aois, budget):
    import hyp3_sdk
    from pipeline.insar._edl import hyp3_client
    rows, picked, spent = plan(aois, budget)
    if not picked:
        print("nothing fits the budget."); return
    hyp3 = hyp3_client()
    have = hyp3.check_credits()
    if have is not None and have < spent:
        raise SystemExit(f"need ~{spent} credits, have {have}; narrow the list.")
    for r in [x for x in rows if x["aoi"] in picked]:
        pairs = build_pairs(r["subsampled"], CONNECTIONS, MAX_DAYS)
        batch = hyp3_sdk.Batch()
        for ref, sec in pairs:
            batch += hyp3.submit_insar_isce_burst_job(ref, sec, name=f"sinkmap-burst-{r['aoi']}")
        out = ROOT / "data" / "insar" / f"burst-{r['aoi']}"
        out.mkdir(parents=True, exist_ok=True)
        (out / "hyp3_batch.json").write_text(json.dumps([j.to_dict() for j in batch.jobs], indent=2, default=str))
        print(f"submitted {len(batch):>3} burst jobs for {r['aoi']} (burst {r['burst']}, sinkmap-burst-{r['aoi']})")
    print(f"\nremaining credits: {hyp3.check_credits()}. Burst jobs queue 1-7 days.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["plan", "submit"])
    ap.add_argument("aois", nargs="*")
    ap.add_argument("--budget", type=int, default=320)
    a = ap.parse_args()
    (plan if a.cmd == "plan" else submit)(a.aois or list(TARGET), a.budget)
