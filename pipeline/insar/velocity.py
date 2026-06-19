"""Phase 0: MintPy time-series -> LOS velocity -> pseudo-vertical.

After HyP3 produces the InSAR pairs, MintPy inverts them into a line-of-sight
(LOS) velocity field. This module:

  1. writes a MintPy `smallbaselineApp.cfg` pointed at the downloaded HyP3
     products (run MintPy separately: `smallbaselineApp.py <cfg>`), and
  2. converts the resulting LOS velocity to pseudo-vertical under the
     vertical-dominant assumption (valid for aquifer/delta/reclamation
     subsidence; see docs/planning/METHOD-decomposition.md).

LOS sensitivity to a purely vertical signal is cos(incidence). Sentinel-1 IW
incidence runs ~29-46 deg (~39 mid-swath), so cos is ~0.69-0.87. Dividing LOS
by cos(incidence) recovers vertical IF motion is vertical-dominant. For
horizontal-significant motion (landslides, Baguio) this is wrong; use full
ascending+descending decomposition instead (v2).
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

MINTPY_CFG_TEMPLATE = """\
# MintPy smallbaselineApp config for sinkmap.ph (auto-written)
mintpy.load.processor      = hyp3
mintpy.load.unwFile        = {products}/*/*unw_phase.tif
mintpy.load.corFile        = {products}/*/*corr.tif
mintpy.load.demFile        = {products}/*/*dem.tif
mintpy.load.incAngleFile   = {products}/*/*lv_theta.tif
mintpy.load.azAngleFile    = {products}/*/*lv_phi.tif
mintpy.subset.lalo         = {subset}    # crop all products to one common grid over the AOI
mintpy.network.tempBaseMax = 200
mintpy.reference.minCoherence = 0.85           # auto-pick a stable, high-coherence reference pixel
mintpy.troposphericDelay.method = no           # v0: skip ERA5/PyAPS (no CDS key needed)
mintpy.topographicResidual = yes               # DEM-error correction from the HyP3 DEM
mintpy.deramp              = linear
mintpy.plot                = no                 # skip matplotlib plotting (crashes on some mpl versions; data is unaffected)
{ref_line}
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


def write_cfg(aoi_id: str, ref_lat=None, ref_lon=None) -> Path:
    products = REPO_ROOT / "data" / "insar" / aoi_id / "hyp3_products"
    # MintPy's own default config is named smallbaselineApp.cfg; a CUSTOM template
    # MUST use a different name or MintPy treats it as the default (all `auto`)
    # and silently ignores your overrides (processor stays isce). Use <aoi>.txt.
    cfg = REPO_ROOT / "data" / "insar" / aoi_id / f"sinkmap_{aoi_id}.txt"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    if ref_lat is not None and ref_lon is not None:
        ref_line = f"mintpy.reference.lalo      = {ref_lat}, {ref_lon}   # stable ground"
    else:
        ref_line = "# mintpy.reference.lalo (auto: highest-coherence pixel via minCoherence)"

    from pipeline import aoi as aoi_registry

    lon0, lat0, lon1, lat1 = aoi_registry.get(aoi_id).bbox
    subset = f"{lat0}:{lat1},{lon0}:{lon1}"
    cfg.write_text(
        MINTPY_CFG_TEMPLATE.format(products=products, subset=subset, ref_line=ref_line)
    )
    return cfg


def _to_vertical_raster(vel_h5: Path, geom_h5: Path, out_tif: Path) -> None:
    """Apply los_to_vertical pixelwise using MintPy outputs. Needs mintpy+h5py."""
    import h5py  # type: ignore
    import numpy as np  # type: ignore

    with h5py.File(vel_h5, "r") as f:
        los = f["velocity"][:] * 1000.0  # m/yr -> mm/yr
    with h5py.File(geom_h5, "r") as f:
        inc = f["incidenceAngle"][:]
    vert = los / np.cos(np.radians(inc))
    try:
        import rasterio  # type: ignore
        from rasterio.transform import from_bounds  # noqa: F401
        # Real geotransform comes from the MintPy geometry; left as a follow-up
        # to wire the affine. Write a plain array dump for now.
    except ImportError:
        pass
    import numpy as _np

    _np.save(out_tif.with_suffix(".npy"), vert)
    print(f"vertical velocity (mm/yr): min {float(vert.min()):.1f} max {float(vert.max()):.1f}")
    print(f"max subsidence (most negative): {float(vert.min()):.1f} mm/yr")
    print(f"wrote {out_tif.with_suffix('.npy')}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("write-cfg", help="write the MintPy config for an AOI")
    c.add_argument("--aoi", default="metro-manila")
    c.add_argument("--ref-lat", type=float, default=None, help="stable reference point lat (default: auto)")
    c.add_argument("--ref-lon", type=float, default=None, help="stable reference point lon (default: auto)")

    v = sub.add_parser("to-vertical", help="convert MintPy LOS velocity.h5 to vertical")
    v.add_argument("--vel", required=True, help="MintPy velocity.h5 (LOS)")
    v.add_argument("--geom", required=True, help="MintPy geometryGeo.h5 (incidenceAngle)")
    v.add_argument("--out", required=True, help="output raster path")

    args = ap.parse_args()
    if args.cmd == "write-cfg":
        print(f"wrote {write_cfg(args.aoi, args.ref_lat, args.ref_lon)}")
    elif args.cmd == "to-vertical":
        _to_vertical_raster(Path(args.vel), Path(args.geom), Path(args.out))


if __name__ == "__main__":
    main()
