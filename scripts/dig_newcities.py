"""Round-5 dig: mine the newly-processed cities (Dagupan, Bacolod, Tacloban) the
same way Metro Manila was mined -- hotspot, acceleration (is it worsening or past
peak?), decade footprint growth, cumulative loss -- and synthesize the cross-city
regime pattern now that six cities are measured. Median datum throughout
(reference-invariant). Run in the MintPy env:

  ~/anaconda3/envs/sinkmap-mintpy312/bin/python scripts/dig_newcities.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts.analysis import load_city, _pixel_rate, _latlon_of  # noqa: E402

OUT = ROOT / "tmp" / "analysis"
PX_KM2 = (80.0 * 80.0) / 1e6
NEW = ["dagupan", "bacolod", "tacloban"]


def dig(aoi):
    vert, years, dates, mask, gt, epsg = load_city(aoi)
    # full-period per-pixel rate on the median datum
    rate = _pixel_rate(years, vert)
    rate = np.where(mask, rate - np.nanmedian(rate[mask]), np.nan)
    rate[:2, :] = np.nan; rate[-2:, :] = np.nan; rate[:, :2] = np.nan; rate[:, -2:] = np.nan
    robust = float(-np.nanpercentile(rate, 1))
    i, j = np.unravel_index(np.nanargmin(rate), rate.shape)
    hlat, hlon = _latlon_of(gt, epsg, i, j)
    peak = float(-rate[i, j])

    # acceleration: early vs late half rate, each referenced to its own median
    early, late = years < 2021, years >= 2021
    re = _pixel_rate(years[early], vert[early]); rl = _pixel_rate(years[late], vert[late])
    re -= np.nanmedian(re[mask]); rl -= np.nanmedian(rl[mask])
    acc = np.where(mask, rl - re, np.nan)
    acc[:2, :] = np.nan; acc[-2:, :] = np.nan; acc[:, :2] = np.nan; acc[:, -2:] = np.nan
    up = float(np.nansum(acc < -3) * PX_KM2); dn = float(np.nansum(acc > 3) * PX_KM2)
    hot_early = float(re[i, j]); hot_late = float(rl[i, j])  # at the full-period hotspot

    # footprint of cumulative subsidence since 2016 (median-ref each date)
    base = vert[0]
    f50, f100 = [], []
    for k in range(len(dates)):
        cum = vert[k] - base
        cum = np.where(mask, cum - np.nanmedian(cum[mask]), np.nan)
        f50.append(float(np.nansum(cum <= -50) * PX_KM2))
        f100.append(float(np.nansum(cum <= -100) * PX_KM2))
    # cumulative loss at the hotspot
    cum_hot = float((vert[-1] - vert[0])[i, j] - np.nanmedian((vert[-1] - vert[0])[mask]))

    res = {"aoi": aoi, "robust_mm_yr": round(robust, 1), "peak_mm_yr": round(peak, 1),
           "hotspot": [hlat, hlon], "reliable_px": int(mask.sum()),
           "accel_at_hotspot_mm_yr": round(hot_late - hot_early, 1),
           "hotspot_early_mm_yr": round(hot_early, 1), "hotspot_late_mm_yr": round(hot_late, 1),
           "area_accelerating_km2": round(up, 1), "area_decelerating_km2": round(dn, 1),
           "footprint_50mm_km2": [round(f50[0], 1), round(f50[-1], 1), round(max(f50), 1)],
           "footprint_100mm_km2": [round(f100[0], 1), round(f100[-1], 1), round(max(f100), 1)],
           "cumulative_loss_at_hotspot_mm": round(cum_hot, 0),
           "trend": "accelerating" if (hot_late - hot_early) < -2 else
                    ("decelerating/past-peak" if (hot_late - hot_early) > 2 else "steady")}
    (OUT / f"dig-{aoi}.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return res


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for aoi in NEW:
        run = ROOT / "data" / "insar" / aoi / "mintpy_run"
        if not (run / "velocity.h5").exists():
            print(f"{aoi}: no velocity yet"); continue
        rows.append(dig(aoi))
    if rows:
        print("\n=== cross-city dig summary ===")
        for r in rows:
            print(f"  {r['aoi']:10} {r['robust_mm_yr']:>5} mm/yr robust, peak {r['peak_mm_yr']:>5}, "
                  f"{r['trend']:>22}, cum loss {r['cumulative_loss_at_hotspot_mm']:>5} mm")


if __name__ == "__main__":
    main()
