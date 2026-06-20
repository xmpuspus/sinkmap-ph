"""Round-5 dig: is the multi-city deceleration synchronized in time? For each
city, take the fastest-sinking hotspot cluster, build its mean cumulative
subsidence curve (median datum), difference it into a per-year subsidence rate,
and find the peak year. If the peak years cluster (~2019-2020, the El Nino
drought), the deceleration is a common climate-driven groundwater pulse, not a
per-city coincidence. Run in the MintPy env:

  ~/anaconda3/envs/sinkmap-mintpy312/bin/python scripts/dig_timing.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.analysis import load_city, _pixel_rate  # noqa: E402

OUT = ROOT / "tmp" / "analysis"
CITIES = ["metro-manila", "dagupan", "cebu-mandaue", "iloilo", "bacolod", "tacloban"]


def timing(aoi):
    vert, years, dates, mask, gt, epsg = load_city(aoi)
    rate = _pixel_rate(years, vert)
    rate = np.where(mask, rate - np.nanmedian(rate[mask]), np.nan)
    # hotspot cluster = the fastest-sinking 0.5% of reliable ground
    thr = np.nanpercentile(rate, 0.5)
    hot = np.isfinite(rate) & (rate <= thr)
    if hot.sum() < 10:
        hot = np.isfinite(rate) & (rate <= np.nanpercentile(rate, 2))
    # mean cumulative displacement over the hotspot, median-referenced each date
    cum = []
    for k in range(len(dates)):
        d = vert[k] - vert[0]
        d = d - np.nanmedian(d[mask])
        cum.append(float(np.nanmean(d[hot])))
    cum = np.array(cum)
    # per-calendar-year subsidence rate (mm/yr) from the cumulative curve
    yr = np.array([int(s[:4]) for s in dates])
    annual = {}
    for y in range(2016, 2025):
        a = np.where(yr <= y)[0]; b = np.where(yr <= y + 1)[0]
        if len(a) and len(b) and b[-1] > a[-1]:
            annual[y] = round(-(cum[b[-1]] - cum[a[-1]]), 1)  # positive = subsidence that year
    peak_year = max(annual, key=annual.get) if annual else None
    return {"aoi": aoi, "hotspot_px": int(hot.sum()),
            "annual_rate_mm": annual, "peak_year": peak_year,
            "total_cum_mm": round(-cum[-1], 0)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for aoi in CITIES:
        if not (ROOT / "data" / "insar" / aoi / "mintpy_run" / "velocity.h5").exists():
            continue
        r = timing(aoi); rows.append(r)
    (OUT / "dig-timing.json").write_text(json.dumps(rows, indent=2))
    print(f"{'city':14} {'peak yr':>7}  per-year subsidence rate (mm/yr)")
    yrs = list(range(2016, 2025))
    print(f"{'':14} {'':>7}  " + " ".join(f"{y%100:>4}" for y in yrs))
    for r in rows:
        cells = " ".join(f"{r['annual_rate_mm'].get(y, float('nan')):>4.0f}" for y in yrs)
        print(f"{r['aoi']:14} {str(r['peak_year']):>7}  {cells}")
    pk = [r["peak_year"] for r in rows if r["peak_year"]]
    print(f"\npeak years: {sorted(pk)}")
    if pk:
        import statistics
        print(f"median peak year {statistics.median(pk)}, "
              f"{sum(1 for y in pk if 2018 <= y <= 2020)}/{len(pk)} peak in 2018-2020")


if __name__ == "__main__":
    main()
