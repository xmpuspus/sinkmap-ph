"""Phase 3: subsidence x flood-zone overlap statistic.

Quantifies how much of the fast-sinking ground coincides with flood-prone
ground. This is OBSERVED SPATIAL COINCIDENCE, not causation: subsidence is one
of several flood drivers (rainfall, drainage, tides, reclamation, sea level),
and the overlap is reported with that disclaimer.

Two flood layers can be overlaid against the subsidence velocity raster:
  - NOAH return-period flood-hazard polygons (the flood-prone baseline; Var
    field = 1 Low / 2 Medium / 3 High depth class), EPSG:4326 shapefiles.
  - a derived Sentinel-1 event flood-extent raster (observed extent of one
    event), aligned to the subsidence grid.

The subsidence raster (vertical.tif from velocity.py) is EPSG:32651 (UTM 51N),
80 m, negative = subsidence, NaN where unreliable. Everything is rasterized onto
that grid so the overlap is computed pixel-for-pixel over the shared extent.

    python -m pipeline.overlay.overlap \\
        --subsidence data/insar/metro-manila/vertical.tif \\
        --hazard data/hazard/unzipped/bulacan-25yr/*.shp data/hazard/unzipped/pampanga-25yr/*.shp \\
        --threshold 20 --hazard-class 2
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

DISCLAIMER = (
    "Observed spatial coincidence only. Subsidence is one of several flood "
    "drivers (rainfall, drainage capacity, tides, reclamation, sea-level rise); "
    "this overlap is not evidence of causation."
)


def _grid_from_tif(path):
    from osgeo import gdal  # type: ignore

    gdal.UseExceptions()
    ds = gdal.Open(str(path))
    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()
    w, h = ds.RasterXSize, ds.RasterYSize
    band = ds.GetRasterBand(1)
    arr = band.ReadAsArray()
    nodata = band.GetNoDataValue()
    ds = None
    return arr, gt, proj, w, h, nodata


def rasterize_hazard(shapefiles, gt, proj, w, h, bbox_4326=None):
    """Burn NOAH hazard polygons (Var class) onto the subsidence grid.

    Each shapefile is clipped to the AOI bbox, reprojected to the grid CRS, and
    rasterized with the Var attribute. Multiple shapefiles (e.g. neighbouring
    provinces) are combined by taking the per-pixel maximum hazard class.
    """
    from osgeo import gdal, osr  # type: ignore

    gdal.UseExceptions()
    import numpy as np

    out = np.zeros((h, w), dtype="uint8")
    for shp in shapefiles:
        # clip to bbox (in source CRS 4326) then reproject to grid CRS
        clip = gdal.VectorTranslate(
            "/vsimem/clip.shp", str(shp),
            spatFilter=bbox_4326, spatSRS="EPSG:4326",
            dstSRS=proj, reproject=True,
        )
        clip = None
        mem = gdal.GetDriverByName("MEM").Create("", w, h, 1, gdal.GDT_Byte)
        mem.SetGeoTransform(gt)
        mem.SetProjection(proj)
        gdal.Rasterize(mem, "/vsimem/clip.shp", attribute="Var",
                       allTouched=False)
        band = mem.GetRasterBand(1).ReadAsArray()
        out = np.maximum(out, band.astype("uint8"))
        mem = None
        gdal.Unlink("/vsimem/clip.shp")
    return out


def compute_overlap(subsidence_tif, hazard_class_raster, threshold_mm=20.0,
                    hazard_min_class=2):
    """Overlap stats between high-subsidence pixels and flood-prone pixels.

    threshold_mm: subsidence faster than this (mm/yr, magnitude) is "high".
    hazard_min_class: NOAH Var class >= this counts as flood-prone (2 = >=0.5 m).
    """
    import numpy as np

    vert, gt, proj, w, h, nodata = _grid_from_tif(subsidence_tif)
    px_km2 = abs(gt[1] * gt[5]) / 1e6  # pixel area in km2

    reliable = np.isfinite(vert)
    if nodata is not None and not np.isnan(nodata):
        reliable &= vert != nodata
    high_sub = reliable & (vert <= -abs(threshold_mm))
    flood = hazard_class_raster >= hazard_min_class
    overlap = high_sub & flood

    high_sub_km2 = int(high_sub.sum()) * px_km2
    flood_km2 = int((flood & reliable).sum()) * px_km2
    overlap_km2 = int(overlap.sum()) * px_km2

    pct_high_sub_in_flood = (100.0 * overlap.sum() / high_sub.sum()) if high_sub.sum() else None
    # baseline: what fraction of ALL reliable ground is flood-prone? (so the
    # overlap can be read against the background rate, not in a vacuum)
    pct_all_ground_flood = (100.0 * (flood & reliable).sum() / reliable.sum()) if reliable.sum() else None

    sub_in_flood = vert[overlap]
    sub_out_flood = vert[high_sub & ~flood]
    return {
        "threshold_mm_yr": abs(threshold_mm),
        "hazard_min_class": hazard_min_class,
        "reliable_area_km2": round(int(reliable.sum()) * px_km2, 1),
        "high_subsidence_area_km2": round(high_sub_km2, 1),
        "flood_prone_area_km2": round(flood_km2, 1),
        "overlap_area_km2": round(overlap_km2, 1),
        "pct_high_subsidence_in_flood_zone": round(pct_high_sub_in_flood, 1) if pct_high_sub_in_flood is not None else None,
        "pct_all_reliable_ground_flood_prone": round(pct_all_ground_flood, 1) if pct_all_ground_flood is not None else None,
        "mean_subsidence_in_flood_mm_yr": round(float(np.nanmean(sub_in_flood)), 1) if sub_in_flood.size else None,
        "disclaimer": DISCLAIMER,
    }


def _bbox_from_grid(gt, w, h, proj):
    """AOI bbox in EPSG:4326 (minlon,minlat,maxlon,maxlat) for clipping."""
    from osgeo import osr  # type: ignore

    xs = [gt[0], gt[0] + gt[1] * w]
    ys = [gt[3], gt[3] + gt[5] * h]
    src = osr.SpatialReference(); src.ImportFromWkt(proj)
    dst = osr.SpatialReference(); dst.ImportFromEPSG(4326)
    dst.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ct = osr.CoordinateTransformation(src, dst)
    corners = [ct.TransformPoint(x, y)[:2] for x in xs for y in ys]
    lons = [c[0] for c in corners]; lats = [c[1] for c in corners]
    return [min(lons), min(lats), max(lons), max(lats)]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--subsidence", required=True, help="vertical velocity GeoTIFF")
    ap.add_argument("--hazard", nargs="+", required=True, help="NOAH hazard shapefile(s)")
    ap.add_argument("--threshold", type=float, default=20.0, help="subsidence mm/yr magnitude = 'high'")
    ap.add_argument("--hazard-class", type=int, default=2, help="NOAH Var >= this is flood-prone (2=>=0.5m)")
    ap.add_argument("--out", default=None, help="write the stats JSON here")
    args = ap.parse_args()

    _, gt, proj, w, h, _ = _grid_from_tif(args.subsidence)
    bbox = _bbox_from_grid(gt, w, h, proj)
    haz = rasterize_hazard(args.hazard, gt, proj, w, h, bbox_4326=bbox)
    res = compute_overlap(args.subsidence, haz, args.threshold, args.hazard_class)
    res["subsidence_grid_bbox_4326"] = [round(x, 4) for x in bbox]
    res["hazard_sources"] = [str(s) for s in args.hazard]

    print(json.dumps(res, indent=2))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(res, indent=2))
        print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
