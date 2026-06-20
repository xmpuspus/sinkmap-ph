"""Compute-before-narrating analysis for the round-3 subsidence findings.

Pure math on the MintPy time-series / velocity rasters. No web output here: this
module computes and gates the numbers, prints them, and writes detailed JSON to
tmp/analysis/. The web layer builder (make_finding_layers.py) imports these same
functions so the map numbers are never hand-typed.

Subsidence rates are RELATIVE (no GNSS tie). Every per-period or per-zone number
is differential: the quantity of interest minus the area's stable baseline, so a
reference/atmosphere drift that is common to the scene cancels. Run in the MintPy
env:

  ~/anaconda3/envs/sinkmap-mintpy312/bin/python scripts/analysis.py accel metro-manila
  ~/anaconda3/envs/sinkmap-mintpy312/bin/python scripts/analysis.py all metro-manila
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import h5py
from osgeo import gdal, osr

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "tmp" / "analysis"
OUT.mkdir(parents=True, exist_ok=True)

PX_KM2 = (80.0 * 80.0) / 1e6  # one 80 m pixel in km2


def _run(aoi_id):
    return ROOT / "data" / "insar" / aoi_id / "mintpy_run"


def _decimal_years(dates):
    out = []
    for d in dates:
        dt = datetime.strptime(d[:8], "%Y%m%d")
        start = datetime(dt.year, 1, 1)
        frac = (dt - start).days / (366.0 if dt.year % 4 == 0 else 365.0)
        out.append(dt.year + frac)
    return np.array(out)


def load_city(aoi_id):
    """Return vertical time-series (mm, T,H,W), decimal years, reliable mask, geotransform, epsg."""
    run = _run(aoi_id)
    with h5py.File(run / "velocity.h5") as f:
        a = dict(f.attrs)
    with h5py.File(run / "inputs" / "geometryGeo.h5") as f:
        inc = f["incidenceAngle"][:].astype("float64")
    with h5py.File(run / "timeseries.h5") as f:
        ts = f["timeseries"][:].astype("float64") * 1000.0  # LOS mm
        dates = [d.decode() if isinstance(d, bytes) else str(d) for d in f["date"][:]]
    with h5py.File(run / "maskTempCoh.h5") as f:
        mask = f["mask"][:].astype(bool)
    cosi = np.cos(np.radians(inc))
    cosi[cosi < 0.2] = np.nan
    vert = ts / cosi  # LOS -> pseudo-vertical (mm), subsidence negative
    gt = (float(a["X_FIRST"]), float(a["X_STEP"]), 0.0,
          float(a["Y_FIRST"]), 0.0, float(a["Y_STEP"]))
    return vert, _decimal_years(dates), dates, mask, gt, int(a["EPSG"])


def _pixel_rate(t, Y):
    """Vectorized OLS slope (mm/yr) of Y (T,H,W) against times t (T,). NaN-safe per pixel."""
    tbar = t.mean()
    dt = (t - tbar)[:, None, None]
    num = np.nansum(dt * (Y - np.nanmean(Y, axis=0)), axis=0)
    den = np.nansum((dt * np.ones_like(Y)) * dt, axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return num / den


def _save_tif(arr, gt, epsg, path):
    drv = gdal.GetDriverByName("GTiff")
    L, W = arr.shape
    ds = drv.Create(str(path), W, L, 1, gdal.GDT_Float32)
    ds.SetGeoTransform(gt)
    srs = osr.SpatialReference(); srs.ImportFromEPSG(epsg); ds.SetProjection(srs.ExportToWkt())
    b = ds.GetRasterBand(1); b.SetNoDataValue(float("nan")); b.WriteArray(arr.astype("float32"))
    ds.FlushCache()


def _sample(arr, gt, epsg, lat, lon):
    """Sample arr (in its native UTM grid) at a lat/lon by transforming to UTM."""
    srs_ll = osr.SpatialReference(); srs_ll.ImportFromEPSG(4326)
    srs_utm = osr.SpatialReference(); srs_utm.ImportFromEPSG(epsg)
    srs_ll.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    srs_utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ct = osr.CoordinateTransformation(srs_ll, srs_utm)
    x, y, _ = ct.TransformPoint(lon, lat)
    j = int((x - gt[0]) / gt[1]); i = int((y - gt[3]) / gt[5])
    if 0 <= i < arr.shape[0] and 0 <= j < arr.shape[1]:
        return float(arr[i, j]) if np.isfinite(arr[i, j]) else None, (i, j)
    return None, (i, j)


def _latlon_of(gt, epsg, i, j):
    srs_utm = osr.SpatialReference(); srs_utm.ImportFromEPSG(epsg)
    srs_ll = osr.SpatialReference(); srs_ll.ImportFromEPSG(4326)
    srs_utm.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    srs_ll.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    ct = osr.CoordinateTransformation(srs_utm, srs_ll)
    x = gt[0] + (j + 0.5) * gt[1]; y = gt[3] + (i + 0.5) * gt[5]
    lon, lat, _ = ct.TransformPoint(x, y)
    return round(lat, 4), round(lon, 4)


def accel(aoi_id, split_year=2021):
    """Per-pixel acceleration map: late-half rate minus early-half rate (mm/yr change).

    Each half's per-pixel vertical rate is referenced to that half's own spatial
    median over reliable pixels (so a reference that itself drifts at different
    speeds in the two halves cancels). Negative accel = sinking faster (speeding
    up); positive = slowing. Writes a UTM GeoTIFF for the colorizer.
    """
    vert, years, dates, mask, gt, epsg = load_city(aoi_id)
    early = years < split_year
    late = years >= split_year
    r_early = _pixel_rate(years[early], vert[early])
    r_late = _pixel_rate(years[late], vert[late])
    # reference each half to its own reliable-area median (differential)
    r_early -= np.nanmedian(r_early[mask])
    r_late -= np.nanmedian(r_late[mask])
    accel_arr = np.where(mask, r_late - r_early, np.nan)
    # edge-trim a 2 px frame (warp/decorrelation fringe)
    accel_arr[:2, :] = np.nan; accel_arr[-2:, :] = np.nan
    accel_arr[:, :2] = np.nan; accel_arr[:, -2:] = np.nan
    r_early_m = np.where(mask, r_early, np.nan)
    r_late_m = np.where(mask, r_late, np.nan)

    valid = np.isfinite(accel_arr)
    n = int(valid.sum())
    # the inland hotspot (finding #1 location) should be DECELERATING
    hot_lat, hot_lon = 15.177, 120.983
    hot_accel, hot_ij = _sample(accel_arr, gt, epsg, hot_lat, hot_lon)
    hot_early, _ = _sample(r_early_m, gt, epsg, hot_lat, hot_lon)
    hot_late, _ = _sample(r_late_m, gt, epsg, hot_lat, hot_lon)
    # where is subsidence ACCELERATING the most (most-negative accel cluster)?
    # smooth lightly so we report a cluster centroid, not a single noisy pixel
    from scipy.ndimage import uniform_filter
    filled = np.where(valid, accel_arr, 0.0)
    cnt = uniform_filter(valid.astype("float64"), size=5)
    sm = uniform_filter(filled, size=5)
    sm = np.where(cnt > 0.5, sm / np.maximum(cnt, 1e-6), np.nan)
    sm = np.where(valid, sm, np.nan)
    i_acc, j_acc = np.unravel_index(np.nanargmin(sm), sm.shape)
    acc_lat, acc_lon = _latlon_of(gt, epsg, i_acc, j_acc)
    acc_early = float(r_early_m[i_acc, j_acc]) if np.isfinite(r_early_m[i_acc, j_acc]) else None
    acc_late = float(r_late_m[i_acc, j_acc]) if np.isfinite(r_late_m[i_acc, j_acc]) else None
    # areas
    accelerating = np.nansum(accel_arr < -3.0) * PX_KM2   # speeding up > 3 mm/yr
    decelerating = np.nansum(accel_arr > 3.0) * PX_KM2
    res = {
        "aoi": aoi_id, "finding": "acceleration",
        "split_year": split_year,
        "reliable_px": n,
        "hotspot_15.177N_120.983E": {
            "early_rate_mm_yr": round(hot_early, 1) if hot_early is not None else None,
            "late_rate_mm_yr": round(hot_late, 1) if hot_late is not None else None,
            "accel_mm_yr": round(hot_accel, 1) if hot_accel is not None else None,
        },
        "max_accelerating_cluster": {
            "lat": acc_lat, "lon": acc_lon,
            "accel_mm_yr_smoothed": round(float(sm[i_acc, j_acc]), 1),
            "early_rate_mm_yr": round(acc_early, 1) if acc_early is not None else None,
            "late_rate_mm_yr": round(acc_late, 1) if acc_late is not None else None,
        },
        "area_accelerating_gt3_km2": round(float(accelerating), 1),
        "area_decelerating_gt3_km2": round(float(decelerating), 1),
        "accel_p5_mm_yr": round(float(np.nanpercentile(accel_arr, 5)), 1),
        "accel_p95_mm_yr": round(float(np.nanpercentile(accel_arr, 95)), 1),
        "note": "Negative = subsidence speeding up; positive = slowing. Each half "
                "referenced to its own reliable-area median (differential).",
    }
    tif = ROOT / "data" / "insar" / aoi_id / "accel.tif"
    _save_tif(accel_arr, gt, epsg, tif)
    res["accel_tif"] = str(tif.relative_to(ROOT))
    (OUT / f"accel-{aoi_id}.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return res


# --- shared 4326 helpers (match make_web_layers display datum) -------------

def vertical_4326(aoi_id):
    """vertical.tif -> EPSG:4326, area-median subtracted (the map display datum).
    Returns (arr, gt) where gt[0]=west lon, gt[3]=north lat."""
    ds = gdal.Warp("", str(ROOT / "data" / "insar" / aoi_id / "vertical.tif"),
                   format="MEM", dstSRS="EPSG:4326", srcNodata="nan", dstNodata="nan")
    arr = ds.GetRasterBand(1).ReadAsArray().astype("float64")
    arr = arr - np.nanmedian(arr)
    return arr, ds.GetGeoTransform()


def _sample4326(arr, gt, lat, lon):
    j = int((lon - gt[0]) / gt[1]); i = int((lat - gt[3]) / gt[5])
    if 0 <= i < arr.shape[0] and 0 <= j < arr.shape[1] and np.isfinite(arr[i, j]):
        return float(arr[i, j])
    return None


def _buffer_stats(arr, gt, lat, lon, radius_km):
    """Median/mean subsidence of finite pixels within radius_km of (lat,lon)."""
    H, W = arr.shape
    yy, xx = np.mgrid[0:H, 0:W]
    plat = gt[3] + (yy + 0.5) * gt[5]; plon = gt[0] + (xx + 0.5) * gt[1]
    dy = (plat - lat) * 111.0
    dx = (plon - lon) * 111.0 * np.cos(np.radians(lat))
    within = (dx * dx + dy * dy) <= radius_km * radius_km
    vals = arr[within & np.isfinite(arr)]
    if vals.size == 0:
        return None
    return {"n_px": int(vals.size), "median_mm_yr": round(float(np.median(vals)), 1),
            "mean_mm_yr": round(float(vals.mean()), 1), "min_mm_yr": round(float(vals.min()), 1)}


HAZARD_SHPS = {
    "metro-manila": ["bulacan-25yr/Bulacan_Flood_25year.shp",
                     "pampanga-25yr/Pampanga_Flood_25year.shp",
                     "mm-25yr/MetroManila_Flood_25year.shp"],
    "iloilo": ["iloilo-25yr/Iloilo_Flood_25year.shp"],
}


def _rasterize_hazard(aoi_id, gt, shape):
    """Burn NOAH 25-yr flood class (1 Low / 2 Med / 3 High; higher wins) onto the
    4326 vertical grid. Returns an int8 class array (0 = no mapped hazard)."""
    H, W = shape
    drv = gdal.GetDriverByName("MEM")
    target = drv.Create("", W, H, 1, gdal.GDT_Byte)
    target.SetGeoTransform(gt)
    srs = osr.SpatialReference(); srs.ImportFromEPSG(4326); target.SetProjection(srs.ExportToWkt())
    from osgeo import ogr
    for shp in HAZARD_SHPS.get(aoi_id, []):
        path = ROOT / "data" / "hazard" / "unzipped" / shp
        if not path.exists():
            continue
        for cls in (1, 2, 3):  # draw ascending so the highest class wins on overlap
            vds = ogr.Open(str(path)); lyr = vds.GetLayer()
            lyr.SetAttributeFilter(f"Var = {cls}")
            gdal.RasterizeLayer(target, [1], lyr, burn_values=[cls])
    return target.GetRasterBand(1).ReadAsArray()


def hazard_tiers(aoi_id):
    """Mean subsidence by NOAH flood-hazard class. Tests whether the ground that
    floods deepest is also the ground that sinks fastest (compounding), or not."""
    arr, gt = vertical_4326(aoi_id)
    hz = _rasterize_hazard(aoi_id, gt, arr.shape)
    finite = np.isfinite(arr)
    tiers = []
    names = {0: "no mapped hazard", 1: "Low (0.1-0.5 m)", 2: "Medium (0.5-1.5 m)", 3: "High (>1.5 m)"}
    for cls in (0, 1, 2, 3):
        sel = finite & (hz == cls)
        v = arr[sel]
        if v.size == 0:
            continue
        tiers.append({"class": cls, "label": names[cls], "area_km2": round(v.size * PX_KM2, 1),
                      "mean_subsidence_mm_yr": round(float(v.mean()), 1),
                      "median_subsidence_mm_yr": round(float(np.median(v)), 1),
                      "pct_sinking_gt10": round(float((v <= -10).mean() * 100), 1)})
    res = {"aoi": aoi_id, "finding": "hazard_tiers", "tiers": tiers,
           "disclaimer": "Observed spatial coincidence only. NOAH is a modeled "
                         "return-period flood-hazard layer; subsidence is one of "
                         "several flood drivers. Not evidence of causation."}
    (OUT / f"hazard-tiers-{aoi_id}.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return res


def compound_exposure(aoi_id, thresh):
    """Of the buildings already on fast-sinking ground, how many also sit in a
    flood-prone (>=0.5 m, 25-yr) zone -- the double-exposed count."""
    arr, gt = vertical_4326(aoi_id)
    hz = _rasterize_hazard(aoi_id, gt, arr.shape)
    gj = json.loads((ROOT / "web" / "data" / "exposure" / f"{aoi_id}.geojson").read_text())
    pts = [f["geometry"]["coordinates"] for f in gj["features"]]
    both, flood_pts = 0, []
    for lon, lat in pts:
        j = int((lon - gt[0]) / gt[1]); i = int((lat - gt[3]) / gt[5])
        if 0 <= i < hz.shape[0] and 0 <= j < hz.shape[1] and hz[i, j] >= 2:
            both += 1; flood_pts.append([round(lon, 5), round(lat, 5)])
    res = {"aoi": aoi_id, "finding": "compound_exposure",
           "buildings_on_fast_sinking_ground": len(pts),
           "fast_sinking_threshold_mm_yr": thresh,
           "also_in_flood_prone_zone": both,
           "pct_double_exposed": round(both / len(pts) * 100, 1) if pts else 0.0,
           "double_exposed_pts": flood_pts,
           "disclaimer": "Spatial coincidence of two independent public layers "
                         "(InSAR subsidence + NOAH flood hazard), not causation."}
    res.pop("double_exposed_pts")  # keep summary JSON small; pts go to a geojson in the layer builder
    (OUT / f"compound-{aoi_id}.json").write_text(json.dumps(res, indent=2))
    (OUT / f"compound-{aoi_id}-pts.json").write_text(json.dumps(flood_pts))
    print(json.dumps(res, indent=2))
    return res


# reclamation sites (public knowledge; coordinates are the made-ground footprints)
RECLAMATION = {
    "cebu-mandaue": [{"name": "South Road Properties (SRP), Cebu City", "lat": 10.2786, "lon": 123.8951, "r_km": 1.2},
                     {"name": "measured coastal peak (Talisay/SRP belt)", "lat": 10.2625, "lon": 123.8693, "r_km": 1.0}],
    "iloilo": [{"name": "Iloilo Business Park (Mandurriao reclamation)", "lat": 10.7139, "lon": 122.5486, "r_km": 1.0},
               {"name": "measured coastal peak", "lat": 10.7676, "lon": 122.5127, "r_km": 1.0}],
}


def reclamation(aoi_id):
    """Subsidence on named engineered/reclaimed ground vs the city-wide baseline."""
    arr, gt = vertical_4326(aoi_id)
    city_median = 0.0  # arr is already median-referenced, so the city baseline is 0
    city_p10 = round(float(np.nanpercentile(arr, 10)), 1)  # typical "fast" city ground
    sites = []
    for s in RECLAMATION.get(aoi_id, []):
        st = _buffer_stats(arr, gt, s["lat"], s["lon"], s["r_km"])
        if st:
            sites.append({**s, **st,
                          "x_vs_city_median": "n/a (city baseline ~0 mm/yr)",
                          "faster_than_city_p10_by_mm_yr": round(st["median_mm_yr"] - city_p10, 1)})
    res = {"aoi": aoi_id, "finding": "reclamation",
           "city_baseline_mm_yr": city_median, "city_p10_mm_yr": city_p10, "sites": sites,
           "note": "Rates are differential vs the city-wide median (0 by construction). "
                   "Reclamation coordinates are public made-ground footprints."}
    (OUT / f"reclamation-{aoi_id}.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return res


def footprint(aoi_id, depths=(50, 100, 200)):
    """How the subsidence footprint grew: area exceeding a cumulative-displacement
    depth at each acquisition since 2016 (relative to the area median each date)."""
    vert, years, dates, mask, gt, epsg = load_city(aoi_id)
    base = vert[0]
    series = {d: [] for d in depths}
    out_dates = []
    for i in range(len(dates)):
        cum = (vert[i] - base)
        cum = cum - np.nanmedian(cum[mask])
        cum = np.where(mask, cum, np.nan)
        out_dates.append(f"{dates[i][:4]}-{dates[i][4:6]}")
        for d in depths:
            series[d].append(round(float(np.nansum(cum <= -d) * PX_KM2), 1))
    res = {"aoi": aoi_id, "finding": "footprint", "dates": out_dates,
           "area_km2_by_depth": {str(d): series[d] for d in depths},
           "note": "Area whose ground dropped more than the given depth since "
                   "2016-01, relative to the reliable-area median at each date."}
    # headline: growth of the >100 mm footprint
    f100 = series[100]
    res["headline"] = {"depth_mm": 100, "start": f"{out_dates[0]}={f100[0]} km2",
                       "end": f"{out_dates[-1]}={f100[-1]} km2",
                       "peak_km2": max(f100)}
    (OUT / f"footprint-{aoi_id}.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return res


def tilt(aoi_id):
    """Differential-tilt field: magnitude of the spatial gradient of the vertical
    velocity (mm/yr per km), smoothed ~400 m. Uniform settlement is benign; this
    gradient is the mechanism that cracks roads and snaps pipes. Writes a UTM tif."""
    from scipy.ndimage import uniform_filter
    run = _run(aoi_id)
    with h5py.File(run / "velocity.h5") as f:
        vel = f["velocity"][:].astype("float64") * 1000.0  # LOS mm/yr
        a = dict(f.attrs)
    with h5py.File(run / "inputs" / "geometryGeo.h5") as f:
        inc = f["incidenceAngle"][:].astype("float64")
    with h5py.File(run / "maskTempCoh.h5") as f:
        mask = f["mask"][:].astype(bool)
    cosi = np.cos(np.radians(inc)); cosi[cosi < 0.2] = np.nan
    v = np.where(mask, vel / cosi, np.nan)
    px_km = abs(float(a["X_STEP"])) / 1000.0  # 0.08 km
    filled = np.where(np.isfinite(v), v, 0.0)
    cnt = uniform_filter(np.isfinite(v).astype("float64"), size=5)
    sm = uniform_filter(filled, size=5) / np.maximum(cnt, 1e-6)
    sm = np.where(cnt > 0.5, sm, np.nan)
    gy, gx = np.gradient(sm)
    grad = np.sqrt(gy * gy + gx * gx) / px_km  # mm/yr per km
    grad = np.where(np.isfinite(v), grad, np.nan)
    grad[:2, :] = np.nan; grad[-2:, :] = np.nan; grad[:, :2] = np.nan; grad[:, -2:] = np.nan
    gt = (float(a["X_FIRST"]), float(a["X_STEP"]), 0.0, float(a["Y_FIRST"]), 0.0, float(a["Y_STEP"]))
    epsg = int(a["EPSG"])
    tif = ROOT / "data" / "insar" / aoi_id / "tilt.tif"
    _save_tif(grad, gt, epsg, tif)
    res = {"aoi": aoi_id, "finding": "tilt",
           "p50_mm_yr_per_km": round(float(np.nanpercentile(grad, 50)), 1),
           "p95_mm_yr_per_km": round(float(np.nanpercentile(grad, 95)), 1),
           "max_mm_yr_per_km": round(float(np.nanmax(grad)), 1),
           "tilt_tif": str(tif.relative_to(ROOT)),
           "note": "Gradient magnitude of vertical velocity, smoothed ~400 m. "
                   "Differential settlement, not absolute rate."}
    (OUT / f"tilt-{aoi_id}.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return res


def municipality(aoi_id, thresh=15.0):
    """Rank cities/municipalities by area of fast-sinking ground (and fast+flood).

    Pulls admin_level=6 boundaries from OSM (Overpass -> .osm -> OGR multipolygons),
    aggregates per OSM relation id (never per name: PH place names repeat), and
    rasterizes each onto the subsidence grid. Degrades to a skip on fetch failure
    rather than fabricating a name."""
    import tempfile, urllib.request, urllib.parse
    from osgeo import ogr
    arr, gt = vertical_4326(aoi_id)
    H, W = arr.shape
    south = gt[3] + H * gt[5]; west = gt[0]; north = gt[3]; east = gt[0] + W * gt[1]
    hz = _rasterize_hazard(aoi_id, gt, arr.shape)
    q = (f'[out:xml][timeout:180];relation["admin_level"="6"]["boundary"="administrative"]'
         f'({south},{west},{north},{east});(._;>;);out;')
    req = urllib.request.Request("https://overpass-api.de/api/interpreter",
                                 data=urllib.parse.urlencode({"data": q}).encode(),
                                 headers={"User-Agent": "sinkmap.ph/1.0 (civic subsidence map)"})
    try:
        raw = urllib.request.urlopen(req, timeout=200).read()
    except Exception as e:  # noqa: BLE001
        print(f"municipality: Overpass fetch failed ({e}); skipping (no fabrication)")
        return None
    tmp = Path(tempfile.mkdtemp()) / "admin.osm"
    tmp.write_bytes(raw)
    gdal.SetConfigOption("OSM_USE_CUSTOM_INDEXING", "NO")
    vds = ogr.Open(str(tmp))
    if vds is None:
        print("municipality: OGR could not open OSM; skipping"); return None
    lyr = vds.GetLayerByName("multipolygons")
    fast = np.isfinite(arr) & (arr <= -thresh)
    rows = {}
    fidx = 0
    for feat in lyr:
        ot = feat.GetField("other_tags") or ""
        al = feat.GetField("admin_level")
        if al != "6" and '"admin_level"=>"6"' not in ot:
            continue
        name = feat.GetField("name") or f"rel{feat.GetFID()}"
        geom = feat.GetGeometryRef()
        if geom is None:
            continue
        # rasterize this one polygon to a mask
        fidx += 1
        drv = gdal.GetDriverByName("MEM"); tg = drv.Create("", W, H, 1, gdal.GDT_Byte)
        tg.SetGeoTransform(gt)
        srs = osr.SpatialReference(); srs.ImportFromEPSG(4326); tg.SetProjection(srs.ExportToWkt())
        mds = ogr.GetDriverByName("Memory").CreateDataSource("m")
        ml = mds.CreateLayer("m", srs, ogr.wkbMultiPolygon)
        f2 = ogr.Feature(ml.GetLayerDefn()); f2.SetGeometry(geom.Clone()); ml.CreateFeature(f2)
        gdal.RasterizeLayer(tg, [1], ml, burn_values=[1])
        inside = tg.GetRasterBand(1).ReadAsArray().astype(bool)
        fa = float(np.sum(fast & inside) * PX_KM2)
        ff = float(np.sum(fast & inside & (hz >= 2)) * PX_KM2)
        key = feat.GetFID()
        rows[key] = {"name": name, "fast_sinking_km2": round(fa, 2),
                     "fast_and_flood_km2": round(ff, 2)}
    ranked = sorted(rows.values(), key=lambda r: r["fast_sinking_km2"], reverse=True)
    ranked = [r for r in ranked if r["fast_sinking_km2"] > 0][:8]
    res = {"aoi": aoi_id, "finding": "municipality", "fast_sinking_threshold_mm_yr": thresh,
           "admin_level": 6, "top": ranked,
           "disclaimer": "Per-polygon aggregation (OSM relation id). Coincidence of "
                         "public layers, not causation."}
    (OUT / f"municipality-{aoi_id}.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))
    return res


THRESH = {"metro-manila": 15.0, "cebu-mandaue": 8.0, "iloilo": 6.0}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "accel"
    aoi = sys.argv[2] if len(sys.argv) > 2 else "metro-manila"
    if cmd == "accel":
        accel(aoi)
    elif cmd == "hazard":
        hazard_tiers(aoi)
    elif cmd == "compound":
        compound_exposure(aoi, THRESH.get(aoi, 10.0))
    elif cmd == "reclamation":
        reclamation(aoi)
    elif cmd == "footprint":
        footprint(aoi)
    elif cmd == "tilt":
        tilt(aoi)
    elif cmd == "municipality":
        municipality(aoi, THRESH.get(aoi, 15.0))
    else:
        print(f"unknown command {cmd}")
