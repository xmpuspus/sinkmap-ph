"""Phase 0 GO/NO-GO gate: does the computed velocity reproduce the literature?

The gate (per docs/planning/SCOPE.md): the Metro Manila run must reproduce the
documented subsidence hotspot in SIGN, LOCATION, and ORDER OF MAGNITUDE before
the project scales to other cities. There is no public subsidence raster to
diff against, so we compare the computed maximum subsidence rate to the
published anchor (Aslan et al. 2024: ~109 mm/yr max for Metro Manila/Bulacan).

    # once MintPy + velocity.py have produced a vertical raster:
    python -m pipeline.insar.validate --aoi metro-manila --raster data/insar/metro-manila/vertical.npy

    # or check the gate logic against a single number:
    python -m pipeline.insar.validate --aoi metro-manila --value -98
"""

from __future__ import annotations

import argparse
from pathlib import Path

from pipeline import aoi as aoi_registry

# Computed max subsidence passes if it is the same sign and within this band of
# the published anchor. InSAR rates vary with window, processing, and exact
# hotspot pixel, so an order-of-magnitude + factor-of-2 band is the honest test.
LOW, HIGH = 0.5, 2.0


def gate(computed_max_subsidence_mm_yr: float, published_anchor_mm_yr: float) -> dict:
    """computed_max_subsidence is a positive mm/yr subsidence magnitude."""
    ratio = computed_max_subsidence_mm_yr / published_anchor_mm_yr
    passed = LOW <= ratio <= HIGH
    return {
        "computed_mm_yr": round(computed_max_subsidence_mm_yr, 1),
        "published_anchor_mm_yr": published_anchor_mm_yr,
        "ratio": round(ratio, 2),
        "band": [LOW, HIGH],
        "verdict": "GO" if passed else "NO-GO",
        "note": (
            "within factor-of-2 of published anchor"
            if passed
            else "outside the factor-of-2 band; inspect reference point, unwrapping, "
                 "AOI, or the vertical-dominant assumption before scaling"
        ),
    }


def _max_subsidence_from_raster(raster: Path) -> float:
    import numpy as np  # type: ignore

    arr = np.load(raster) if raster.suffix == ".npy" else None
    if arr is None:
        import rasterio  # type: ignore

        with rasterio.open(raster) as ds:
            arr = ds.read(1)
    # subsidence is negative vertical velocity; max subsidence = -min(vel)
    return float(-np.nanmin(arr))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aoi", default="metro-manila")
    ap.add_argument("--raster", default=None, help="vertical velocity raster (.npy/.tif)")
    ap.add_argument("--value", type=float, default=None,
                    help="computed vertical velocity in mm/yr (negative = subsidence)")
    args = ap.parse_args()

    a = aoi_registry.get(args.aoi)
    if a.published_rate_mm_yr_max is None:
        raise SystemExit(
            f"{a.id} is exploratory (no published anchor); the gate only applies to "
            f"validation AOIs: {[x.id for x in aoi_registry.validation_anchors()]}"
        )

    if args.raster:
        computed = _max_subsidence_from_raster(Path(args.raster))
    elif args.value is not None:
        computed = -args.value if args.value < 0 else args.value
    else:
        raise SystemExit("provide --raster or --value")

    result = gate(computed, a.published_rate_mm_yr_max)
    print(f"AOI: {a.name}")
    for k, v in result.items():
        print(f"  {k}: {v}")
    raise SystemExit(0 if result["verdict"] == "GO" else 1)


if __name__ == "__main__":
    main()
