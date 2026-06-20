"""Automate the two manual MintPy steps that don't scale: reference-point
selection and an anchor-free quality gate. Both run on MintPy products and are
what let a batch of cities finish without per-city babysitting.

auto_reference: the hand-tuned Metro Manila reference (yx 600,376; 298 m Sierra
Madre piedmont; coherence 0.93; inside maskConnComp with a fully in-mask 5x5
neighborhood) encodes a rule: pick the HIGHEST defensibly-stable ground the
radar still unwraps reliably. We reproduce it as: among pixels that are in the
unwrapping mask, have temporal coherence >= 0.9, and sit in a 5x5 fully in-mask
island, take the highest-elevation one (stable piedmont/bedrock, away from the
subsiding alluvium; the coherence filter already drops decorrelated forest).

anchor_free_gate: only five PH cities have a published rate, so most cities
cannot be gated against literature. This gates on internal quality instead --
reliable-pixel count and temporal coherence -- which is what separated the GO
cities (Metro Manila/Cebu/Iloilo, tens of thousands of reliable px) from the
failures (Davao 37 px, Legazpi 0). Ascending+descending agreement is the
stronger gate and is a v2 add.

Run in the MintPy env (h5py + gdal/osr):
  ~/anaconda3/envs/sinkmap-mintpy312/bin/python pipeline/insar/autoref.py metro-manila
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import h5py
from osgeo import osr
from scipy.ndimage import binary_erosion

ROOT = Path(__file__).resolve().parent.parent.parent

MIN_COH_REF = 0.9          # reference must be highly coherent
GATE_RELIABLE_PX = 5000    # >= this many reliable px -> internally consistent
GATE_FAIL_PX = 1000        # < this -> coherence-limited
GATE_MIN_MEDIAN_COH = 0.7


def _run(aoi_id):
    return ROOT / "data" / "insar" / aoi_id / "mintpy_run"


def _latlon(attrs, y, x):
    gt0, dx = float(attrs["X_FIRST"]), float(attrs["X_STEP"])
    gt3, dy = float(attrs["Y_FIRST"]), float(attrs["Y_STEP"])
    X = gt0 + (x + 0.5) * dx; Y = gt3 + (y + 0.5) * dy
    s_utm = osr.SpatialReference(); s_utm.ImportFromEPSG(int(attrs["EPSG"]))
    s_ll = osr.SpatialReference(); s_ll.ImportFromEPSG(4326)
    s_utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    s_ll.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    lon, lat, _ = osr.CoordinateTransformation(s_utm, s_ll).TransformPoint(X, Y)
    return round(lat, 4), round(lon, 4)


def auto_reference(aoi_id):
    run = _run(aoi_id)
    with h5py.File(run / "maskConnComp.h5") as f:
        mask = f["mask"][:].astype(bool)
        attrs = dict(f.attrs)
    with h5py.File(run / "temporalCoherence.h5") as f:
        coh = f["temporalCoherence"][:].astype("float64")
    with h5py.File(run / "inputs" / "geometryGeo.h5") as f:
        h = f["height"][:].astype("float64")
    island = binary_erosion(mask, iterations=2)  # fully in-mask 5x5 neighborhood
    cand = island & (coh >= MIN_COH_REF) & np.isfinite(h)
    if not cand.any():  # relax coherence if the AOI is marginal
        cand = island & (coh >= 0.8) & np.isfinite(h)
    if not cand.any():
        return {"aoi": aoi_id, "ok": False, "reason": "no in-mask, coherent island for a reference"}
    hh = np.where(cand, h, -np.inf)
    y, x = np.unravel_index(np.argmax(hh), hh.shape)  # highest stable coherent ground
    lat, lon = _latlon(attrs, y, x)
    return {"aoi": aoi_id, "ok": True, "ref_yx": [int(y), int(x)],
            "ref_lat": lat, "ref_lon": lon, "ref_height_m": round(float(h[y, x]), 0),
            "ref_coherence": round(float(coh[y, x]), 2), "n_candidates": int(cand.sum())}


def anchor_free_gate(aoi_id):
    run = _run(aoi_id)
    mtc = run / "maskTempCoh.h5"
    tc = run / "temporalCoherence.h5"
    vel = run / "velocity.h5"
    if not (mtc.exists() and tc.exists() and vel.exists()):
        return {"aoi": aoi_id, "verdict": "NO-GO", "reliable_px": 0,
                "reason": "no velocity/coherence products (processing did not converge)"}
    with h5py.File(mtc) as f:
        reliable = f["mask"][:].astype(bool)
    with h5py.File(tc) as f:
        coh = f["temporalCoherence"][:].astype("float64")
    n = int(reliable.sum())
    med = float(np.nanmedian(coh[reliable])) if n else 0.0
    frac = float(reliable.mean())
    if n >= GATE_RELIABLE_PX and med >= GATE_MIN_MEDIAN_COH:
        verdict, conf = "GO", "internally-consistent (desc-only; asc+desc agreement is the v2 gate)"
    elif n < GATE_FAIL_PX:
        verdict, conf = "NO-GO", "too few reliable pixels (coherence-limited)"
    else:
        verdict, conf = "MARGINAL", "borderline reliable coverage; needs PS-InSAR or a tighter AOI"
    return {"aoi": aoi_id, "verdict": verdict, "reliable_px": n,
            "reliable_frac": round(frac, 3), "median_temp_coh_reliable": round(med, 2),
            "confidence": conf}


if __name__ == "__main__":
    aoi = sys.argv[1] if len(sys.argv) > 1 else "metro-manila"
    import json
    print("auto_reference:", json.dumps(auto_reference(aoi)))
    print("anchor_free_gate:", json.dumps(anchor_free_gate(aoi)))
