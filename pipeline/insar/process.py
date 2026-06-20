"""Per-city v1 MintPy chain: clipped HyP3 products -> LOS velocity -> pseudo-
vertical -> gated result. The Phase-A scale-out worker (promoted from the
tmp/phase2 orchestrator that processed Cebu/Iloilo/Davao), now committed and
wired to the anchor-free gate so cities WITHOUT a published rate still gate on
internal consistency. Run in the MintPy env:

  ~/anaconda3/envs/sinkmap-mintpy312/bin/python pipeline/insar/process.py <aoi>

Steps: clip every HyP3 product to one identical AOI grid (subset.lalo mis-crops
them) -> load + masks -> pick a stable in-mask reference (or declare coherence-
limited) -> per-step inversion (each --dostep isolated so MintPy's unclosed
matplotlib figures do not collide) -> LOS->vertical at the highest temporal-
coherence threshold giving enough physically-plausible pixels -> gate. Cities
with a published anchor gate vs it (factor-of-2); the rest gate via
autoref.anchor_free_gate (reliable-pixel count + temporal coherence).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
MP = Path.home() / "anaconda3/envs/sinkmap-mintpy312/bin"
SBAPP = str(MP / "smallbaselineApp.py")

PASS2_STEPS = ["reference_point", "quick_overview", "correct_unwrap_error",
               "invert_network", "correct_SET", "correct_troposphere", "deramp",
               "correct_topography", "residual_RMS", "reference_date", "velocity"]


def sb(cfg, run_dir, *extra):
    env = {**os.environ, "MPLBACKEND": "Agg"}
    return subprocess.run([SBAPP, str(cfg), *extra], cwd=str(run_dir), env=env).returncode


def adaptive_vertical(run_dir, out, min_px=120, max_plausible=150.0):
    """Masked pseudo-vertical at the highest temporal-coherence threshold that
    gives >= min_px reliable pixels whose velocities are physically plausible
    (|v| <= max_plausible mm/yr; rejects decorrelation blow-ups)."""
    import h5py
    import numpy as np
    from osgeo import gdal, osr
    from pyproj import Transformer
    gdal.UseExceptions()
    run_dir = Path(run_dir)
    with h5py.File(run_dir / "velocity.h5") as f:
        los = f["velocity"][:] * 1000.0; a = dict(f.attrs)
    with h5py.File(run_dir / "inputs" / "geometryGeo.h5") as f:
        inc = f["incidenceAngle"][:]
    with h5py.File(run_dir / "temporalCoherence.h5") as f:
        tc = f[next(k for k in f.keys() if f[k].ndim == 2)][:]
    vert = los / np.cos(np.radians(inc))
    chosen = None
    for thr in [0.7, 0.65, 0.6, 0.55, 0.5]:
        m = (tc >= thr) & np.isfinite(vert)
        if int(m.sum()) >= min_px and np.nanmax(np.abs(vert[m])) <= max_plausible:
            chosen = (m, thr); break
    if chosen is None:
        m = (tc >= 0.5) & np.isfinite(vert); chosen = (m, 0.5)
    m, thr = chosen
    v = np.where(m, vert, np.nan)
    np.save(str(out) + ".npy", v)
    xf, yf, xs, ys, epsg = (float(a["X_FIRST"]), float(a["Y_FIRST"]), float(a["X_STEP"]),
                            float(a["Y_STEP"]), int(a["EPSG"]))
    L, W = v.shape
    ds = gdal.GetDriverByName("GTiff").Create(str(out) + ".tif", W, L, 1, gdal.GDT_Float32,
                                              options=["COMPRESS=DEFLATE", "TILED=YES"])
    ds.SetGeoTransform((xf, xs, 0, yf, 0, ys))
    srs = osr.SpatialReference(); srs.ImportFromEPSG(epsg); ds.SetProjection(srs.ExportToWkt())
    b = ds.GetRasterBand(1); b.SetNoDataValue(float("nan")); b.WriteArray(v.astype("float32")); ds = None
    n_px = int(m.sum())
    mn = float(np.nanmin(v))
    robust = float(-np.nanpercentile(v, 1))
    n_hot = int((v <= mn * 0.6).sum())
    mi = np.unravel_index(np.nanargmin(v), v.shape)
    t = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
    lon, lat = t.transform(xf + xs * mi[1], yf + ys * mi[0])
    conf = "high" if thr >= 0.7 else ("medium" if thr >= 0.6 else "low")
    return {"max": -mn, "robust": robust, "n_hot": n_hot, "lat": round(lat, 4),
            "lon": round(lon, 4), "thr": thr, "n_px": n_px, "conf": conf}


def main():
    aoi = sys.argv[1]
    from pipeline.insar import velocity
    from pipeline.insar import validate as val
    from pipeline.insar.autoref import anchor_free_gate
    from pipeline import aoi as reg

    run_dir = ROOT / "data" / "insar" / aoi / "mintpy_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    cfg = ROOT / "data" / "insar" / aoi / f"sinkmap_{aoi}.txt"
    resfile = ROOT / "tmp" / "phase2" / f"{aoi}-result.json"
    resfile.parent.mkdir(parents=True, exist_ok=True)
    anchor = reg.get(aoi).published_rate_mm_yr_max

    if not (ROOT / "data" / "insar" / aoi / "clipped").exists():
        print(f"[{aoi}] clipping products to AOI grid ...", flush=True)
        velocity.clip_products(aoi)

    velocity.write_cfg(aoi, clipped=True)
    print(f"[{aoi}] pass 1: load + auto-ref ...", flush=True)
    sb(cfg, run_dir)
    if not (run_dir / "maskConnComp.h5").exists():
        resfile.write_text(json.dumps({"aoi": aoi, "verdict": "FAIL-LOAD"}, indent=2)); return 1

    try:
        ref = velocity.pick_stable_reference(run_dir)
    except velocity.CoherenceLimited as e:
        resfile.write_text(json.dumps({"aoi": aoi, "verdict": "NO-GO-COHERENCE",
                                       "reason": str(e), "published_anchor_mm_yr": anchor}, indent=2))
        print(f"[{aoi}] COHERENCE-LIMITED: {e}", flush=True); return 0
    print(f"[{aoi}] reference yx={ref['row']},{ref['col']} h={ref['height_m']:.0f}m "
          f"coh={ref['coherence']:.2f}", flush=True)
    velocity.write_cfg(aoi, ref_yx=(ref["row"], ref["col"]), ref_lat=ref["lat"],
                       ref_lon=ref["lon"], clipped=True)

    print(f"[{aoi}] pass 2: per-step inversion ...", flush=True)
    for st in PASS2_STEPS:
        sb(cfg, run_dir, "--dostep", st)
    if not (run_dir / "velocity.h5").exists():
        resfile.write_text(json.dumps({"aoi": aoi, "verdict": "FAIL-INVERT"}, indent=2)); return 1

    r = adaptive_vertical(run_dir, ROOT / "data" / "insar" / aoi / "vertical")
    result = {"aoi": aoi,
              "robust_subsidence_mm_yr": round(r["robust"], 1),
              "peak_subsidence_mm_yr": round(r["max"], 1), "peak_cluster_px": r["n_hot"],
              "peak_lat": r["lat"], "peak_lon": r["lon"],
              "temp_coh_threshold": r["thr"], "reliable_px": r["n_px"], "confidence": r["conf"],
              "reference_yx": [ref["row"], ref["col"]], "reference_h_m": round(ref["height_m"], 0)}
    if anchor is not None:
        gate = val.gate(r["robust"], anchor)
        result.update({"robust_ratio": gate["ratio"], "verdict": gate["verdict"],
                       "published_anchor_mm_yr": anchor, "band": gate["band"]})
    else:
        g = anchor_free_gate(aoi)  # no published rate: gate on internal consistency
        result.update({"verdict": g["verdict"], "anchor_free": True,
                       "gate_confidence": g["confidence"],
                       "gate_reliable_px": g["reliable_px"],
                       "gate_median_temp_coh": g.get("median_temp_coh_reliable"),
                       "published_anchor_mm_yr": None})
    resfile.write_text(json.dumps(result, indent=2))
    print(f"[{aoi}] RESULT: {json.dumps(result)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
