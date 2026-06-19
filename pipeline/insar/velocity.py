"""Phase 0/1: MintPy time-series -> LOS velocity -> pseudo-vertical.

After HyP3 produces the InSAR pairs, MintPy inverts them into a line-of-sight
(LOS) velocity field. This module:

  1. writes a MintPy config (a CUSTOM template named sinkmap_<aoi>.txt, never
     smallbaselineApp.cfg, or MintPy treats it as its own default and ignores
     the overrides) pointed at the downloaded HyP3 products,
  2. picks a defensible stable reference pixel from the loaded masks
     (`pick-reference`), and
  3. converts the resulting LOS velocity to pseudo-vertical under the
     vertical-dominant assumption (valid for aquifer/delta/reclamation
     subsidence; see docs/planning/METHOD-decomposition.md), writing both a
     plain .npy and a georeferenced GeoTIFF.

LOS sensitivity to a purely vertical signal is cos(incidence). Sentinel-1 IW
incidence runs ~29-46 deg (~39 mid-swath), so cos is ~0.69-0.87. Dividing LOS
by cos(incidence) recovers vertical IF motion is vertical-dominant. For
horizontal-significant motion (landslides, Baguio) this is wrong; use full
ascending+descending decomposition instead (v2).

v1 method (the Metro Manila gate, 2026-06-20): stable reference on coherent
in-mask piedmont ground (NOT the auto minCoherence pixel, which lands on low
alluvium), and `height_correlation` tropospheric correction (no CDS key needed).
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

MINTPY_CFG_TEMPLATE = """\
# MintPy smallbaselineApp config for sinkmap.ph (auto-written; v1 method)
mintpy.load.processor      = hyp3
mintpy.load.unwFile        = {products}/*/*unw_phase.tif
mintpy.load.corFile        = {products}/*/*corr.tif
mintpy.load.demFile        = {products}/*/*dem.tif
mintpy.load.incAngleFile   = {products}/*/*lv_theta.tif
mintpy.load.azAngleFile    = {products}/*/*lv_phi.tif
mintpy.subset.lalo         = {subset}    # crop all products to one common grid over the AOI
mintpy.network.tempBaseMax = 200
{ref_line}
# v1 troposphere: empirical phase-elevation fit, NO external data/CDS key (unlike ERA5/PyAPS).
# Safe for a flat delta where subsidence is not topo-correlated; review near the upland fringe.
mintpy.troposphericDelay.method          = height_correlation
mintpy.troposphericDelay.polyOrder       = 1
mintpy.troposphericDelay.looks           = 8
mintpy.troposphericDelay.minCorrelation  = 0.1
mintpy.topographicResidual = yes               # DEM-error correction from the HyP3 DEM
mintpy.deramp              = linear
mintpy.plot                = no                 # skip matplotlib plot step (crashes on some mpl versions; data unaffected)
# Output: velocity.h5 (LOS mm/yr). Convert with `velocity.py to-vertical`.
"""


def los_to_vertical(los: float, incidence_deg: float) -> float:
    """Convert LOS displacement/velocity to pseudo-vertical (vertical-dominant).

    vertical = los / cos(incidence). incidence is the radar incidence angle in
    degrees (angle of the line-of-sight from vertical).
    """
    c = math.cos(math.radians(incidence_deg))
    # cos(90 deg) is ~6e-17 in floating point, not 0, so guard on a small epsilon:
    # near-grazing geometry has ~no vertical sensitivity and the division is
    # meaningless. Sentinel-1 IW incidence is 29-46 deg (cos 0.69-0.87) anyway.
    if c < 1e-9:
        raise ValueError(f"incidence {incidence_deg} deg gives ~zero vertical sensitivity")
    return los / c


def write_cfg(aoi_id, ref_yx=None, ref_lat=None, ref_lon=None):
    """Write the MintPy v1 config for an AOI.

    ref_yx = (row, col) is the OPERATIVE reference (unambiguous on the projected
    UTM grid; the lat/lon -> UTM conversion is bypassed). ref_lat/ref_lon are
    kept only as a human-readable label. With neither, MintPy auto-picks via
    minCoherence (acceptable for a quick pass, but it tends to land on low
    alluvium, not stable ground -- prefer `pick-reference` then pass --ref-yx).
    """
    products = REPO_ROOT / "data" / "insar" / aoi_id / "hyp3_products"
    cfg = REPO_ROOT / "data" / "insar" / aoi_id / f"sinkmap_{aoi_id}.txt"
    cfg.parent.mkdir(parents=True, exist_ok=True)

    if ref_yx is not None:
        row, col = ref_yx
        label = ""
        if ref_lat is not None and ref_lon is not None:
            label = f"  # ~lat {ref_lat}, lon {ref_lon}"
        ref_line = (
            f"mintpy.reference.yx        = {row}, {col}{label}   # stable in-mask ground (see pick-reference)"
        )
    else:
        ref_line = (
            "mintpy.reference.minCoherence = 0.85   # auto-pick (fallback; prefer an explicit --ref-yx)"
        )

    from pipeline import aoi as aoi_registry

    lon0, lat0, lon1, lat1 = aoi_registry.get(aoi_id).bbox
    subset = f"{lat0}:{lat1},{lon0}:{lon1}"
    cfg.write_text(MINTPY_CFG_TEMPLATE.format(products=products, subset=subset, ref_line=ref_line))
    return cfg


def pick_stable_reference(run_dir, min_coh=0.75, min_h=40.0, max_h=300.0, edge=20):
    """Pick a defensible stable reference pixel from a loaded MintPy run.

    A trustworthy reference sits on stable ground (elevated piedmont/bedrock,
    off the subsiding alluvium), is reliably unwrapped (in maskConnComp -- the
    constraint reference_point.py actually enforces), is coherent, and is not on
    the noisy grid edge. Above ~max_h the forested slopes get masked out, so the
    pick is the highest stable ground InSAR still unwraps. Returns a dict with
    (row, col, lat, lon, height_m, coherence) or raises if no candidate.
    """
    import h5py  # type: ignore
    import numpy as np  # type: ignore

    run_dir = Path(run_dir)

    def _2d(p):
        with h5py.File(p, "r") as f:
            key = next(k for k in f.keys() if f[k].ndim == 2)
            return f[key][:]

    mcc = _2d(run_dir / "maskConnComp.h5")
    coh = _2d(run_dir / "avgSpatialCoh.h5")
    with h5py.File(run_dir / "inputs" / "geometryGeo.h5", "r") as f:
        hgt = f["height"][:]
        attrs = dict(f.attrs)

    L, W = mcc.shape
    ii, jj = np.mgrid[0:L, 0:W]
    cand = (
        (mcc > 0)
        & (coh >= min_coh)
        & (hgt >= min_h)
        & (hgt <= max_h)
        & (ii >= edge)
        & (ii < L - edge)
        & (jj >= edge)
        & (jj < W - edge)
    )
    if not cand.any():
        raise SystemExit(
            f"no stable in-mask reference candidate (coh>={min_coh}, {min_h}<=h<={max_h}). "
            f"Relax thresholds or inspect masks in {run_dir}."
        )
    # prefer higher coherence, then higher (more stable) elevation
    score = coh + (hgt / max_h) * 0.5
    score = np.where(cand, score, -np.inf)
    i, j = np.unravel_index(np.argmax(score), score.shape)

    xf, yf = float(attrs["X_FIRST"]), float(attrs["Y_FIRST"])
    xs, ys = float(attrs["X_STEP"]), float(attrs["Y_STEP"])
    epsg = int(attrs.get("EPSG", 0))
    lat = lon = None
    try:
        from pyproj import Transformer  # type: ignore

        tr = Transformer.from_crs(f"EPSG:{epsg}", "EPSG:4326", always_xy=True)
        lon, lat = tr.transform(xf + xs * j, yf + ys * i)
    except Exception:
        pass
    return {
        "row": int(i),
        "col": int(j),
        "height_m": float(hgt[i, j]),
        "coherence": float(coh[i, j]),
        "lat": round(lat, 4) if lat is not None else None,
        "lon": round(lon, 4) if lon is not None else None,
        "n_candidates": int(cand.sum()),
    }


def _to_vertical_raster(vel_h5, geom_h5, out_path, mask_h5=None):
    """Apply los_to_vertical pixelwise and write .npy + georeferenced GeoTIFF.

    With mask_h5 (e.g. maskTempCoh.h5), unreliable pixels are set to NaN so the
    product only carries trustworthy velocities. The GeoTIFF carries the MintPy
    UTM geotransform + EPSG, which the Phase 3 flood overlay and Phase 4 web
    tiling both need.
    """
    import h5py  # type: ignore
    import numpy as np  # type: ignore

    with h5py.File(vel_h5, "r") as f:
        los = f["velocity"][:] * 1000.0  # m/yr -> mm/yr
        a = dict(f.attrs)
    with h5py.File(geom_h5, "r") as f:
        inc = f["incidenceAngle"][:]
    vert = los / np.cos(np.radians(inc))

    if mask_h5 is not None:
        with h5py.File(mask_h5, "r") as f:
            key = next(k for k in f.keys() if f[k].ndim == 2)
            mask = f[key][:].astype(bool)
        vert = np.where(mask, vert, np.nan)

    out_path = Path(out_path)
    np.save(out_path.with_suffix(".npy"), vert)

    wrote_tif = False
    try:
        from osgeo import gdal, osr  # type: ignore

        xf, yf = float(a["X_FIRST"]), float(a["Y_FIRST"])
        xs, ys = float(a["X_STEP"]), float(a["Y_STEP"])
        epsg = int(a.get("EPSG", 0))
        L, W = vert.shape
        drv = gdal.GetDriverByName("GTiff")
        ds = drv.Create(str(out_path.with_suffix(".tif")), W, L, 1, gdal.GDT_Float32,
                        options=["COMPRESS=DEFLATE", "TILED=YES"])
        ds.SetGeoTransform((xf, xs, 0.0, yf, 0.0, ys))
        if epsg:
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(epsg)
            ds.SetProjection(srs.ExportToWkt())
        band = ds.GetRasterBand(1)
        band.SetNoDataValue(float("nan"))
        band.WriteArray(np.asarray(vert, dtype="float32"))
        band.FlushCache()
        ds = None
        wrote_tif = True
    except ImportError:
        pass

    import numpy as _np

    finite = _np.isfinite(vert)
    print(f"vertical velocity (mm/yr): min {float(_np.nanmin(vert)):.1f} max {float(_np.nanmax(vert)):.1f}")
    print(f"max subsidence (most negative): {float(_np.nanmin(vert)):.1f} mm/yr  (reliable px: {int(finite.sum())})")
    print(f"wrote {out_path.with_suffix('.npy')}" + (f" and {out_path.with_suffix('.tif')}" if wrote_tif else ""))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("write-cfg", help="write the MintPy v1 config for an AOI")
    c.add_argument("--aoi", default="metro-manila")
    c.add_argument("--ref-yx", default=None, help="operative stable reference as 'row,col' (see pick-reference)")
    c.add_argument("--ref-lat", type=float, default=None, help="reference lat (label only)")
    c.add_argument("--ref-lon", type=float, default=None, help="reference lon (label only)")

    p = sub.add_parser("pick-reference", help="pick a stable in-mask reference pixel from a loaded run")
    p.add_argument("--run-dir", required=True, help="MintPy run dir (has maskConnComp.h5, avgSpatialCoh.h5, inputs/)")

    v = sub.add_parser("to-vertical", help="convert MintPy LOS velocity.h5 to vertical")
    v.add_argument("--vel", required=True, help="MintPy velocity.h5 (LOS)")
    v.add_argument("--geom", required=True, help="MintPy geometryGeo.h5 (incidenceAngle)")
    v.add_argument("--out", required=True, help="output raster path (.npy + .tif)")
    v.add_argument("--mask", default=None, help="mask h5 (e.g. maskTempCoh.h5); unreliable px -> NaN")

    args = ap.parse_args()
    if args.cmd == "write-cfg":
        ref_yx = None
        if args.ref_yx:
            row, col = (int(x) for x in args.ref_yx.replace(" ", "").split(","))
            ref_yx = (row, col)
        print(f"wrote {write_cfg(args.aoi, ref_yx, args.ref_lat, args.ref_lon)}")
    elif args.cmd == "pick-reference":
        ref = pick_stable_reference(args.run_dir)
        print(f"stable reference: row={ref['row']} col={ref['col']} "
              f"(lat {ref['lat']}, lon {ref['lon']}) h={ref['height_m']:.0f}m coh={ref['coherence']:.2f}")
        print(f"  config line: mintpy.reference.yx = {ref['row']}, {ref['col']}")
        print(f"  (chosen from {ref['n_candidates']} in-mask candidates)")
    elif args.cmd == "to-vertical":
        _to_vertical_raster(Path(args.vel), Path(args.geom), Path(args.out),
                            Path(args.mask) if args.mask else None)


if __name__ == "__main__":
    main()
