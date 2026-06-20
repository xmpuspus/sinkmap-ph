"""Build the web map's velocity layers + city summary from the MintPy outputs.

For each validated city: reproject vertical.tif to EPSG:4326, colorize it with a
diverging ramp (subsidence red, stable white, uplift blue; NaN transparent), and
write a PNG image-overlay + its lat/lon bounds. Also emit web/data/cities.json
(measured rate, verdict, confidence, flood-overlap stat, bounds) which the
single-file frontend reads. Run in the MintPy env (gdal + matplotlib):

  ~/anaconda3/envs/sinkmap-mintpy312/bin/python scripts/make_web_layers.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.colors as mcolors
from osgeo import gdal
from PIL import Image

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parent.parent
VMIN, VMAX = -60.0, 20.0  # shared diverging range (mm/yr): <=-60 deep red ... +20 blue
DEADBAND, FADE = 4.0, 6.0  # |v|<4 mm/yr transparent (stable); full color by |v|=10

GO_CITIES = ["metro-manila", "cebu-mandaue", "iloilo"]
LIMITED = {"legazpi": "coherence-limited (vegetated coastal AOI)",
           "davao": "coherence-limited (upland AOI)"}


def colorize(aoi_id):
    """vertical.tif -> EPSG:4326 -> RdBu PNG (NaN transparent). Returns bounds."""
    src = ROOT / "data" / "insar" / aoi_id / "vertical.tif"
    ds = gdal.Warp("", str(src), format="MEM", dstSRS="EPSG:4326",
                   srcNodata="nan", dstNodata="nan", resampleAlg="near")
    gt = ds.GetGeoTransform()
    w, h = ds.RasterXSize, ds.RasterYSize
    arr = ds.GetRasterBand(1).ReadAsArray().astype("float64")
    # Display datum = the measured-area median (standard for relative InSAR with no
    # GNSS tie): most ground is the stable baseline, so the bulk reads stable and
    # only differential motion colors. Metro Manila's piedmont reference is itself
    # moving ~7 mm/yr vs the delta; without this the whole delta would read "rising".
    # The validation gate keeps the piedmont datum (see findings); this only affects
    # the map's color centering.
    arr = arr - np.nanmedian(arr)
    west, north = gt[0], gt[3]
    east, south = gt[0] + gt[1] * w, gt[3] + gt[5] * h

    norm = mcolors.TwoSlopeNorm(vmin=VMIN, vcenter=0.0, vmax=VMAX)
    cmap = matplotlib.colormaps["RdBu"]  # low (subsidence) -> red, high (uplift) -> blue
    rgba = cmap(norm(np.clip(arr, VMIN, VMAX)))
    # Fade near-zero velocities to transparent: InSAR is relative, and a small
    # offset from the reference (within ~a few mm/yr) is effectively stable, not
    # real uplift. Color only ground that is measurably moving so stable areas
    # read as stable (uncolored basemap), sinking as red, rising as blue.
    mag = np.abs(arr)
    alpha = np.clip((mag - DEADBAND) / FADE, 0.0, 1.0) * 0.92
    rgba[..., 3] = np.where(np.isfinite(arr), alpha, 0.0)
    out = ROOT / "web" / "data" / "velocity" / f"{aoi_id}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((rgba * 255).astype("uint8"), "RGBA").save(out)
    return {"west": round(west, 5), "south": round(south, 5),
            "east": round(east, 5), "north": round(north, 5)}


def _warp_arr_to_4326(arr, gt, epsg):
    """Put a numpy array on a UTM MEM raster, warp to EPSG:4326, return array."""
    drv = gdal.GetDriverByName("MEM")
    L, W = arr.shape
    src = drv.Create("", W, L, 1, gdal.GDT_Float32)
    src.SetGeoTransform(gt)
    from osgeo import osr
    srs = osr.SpatialReference(); srs.ImportFromEPSG(epsg); src.SetProjection(srs.ExportToWkt())
    b = src.GetRasterBand(1); b.SetNoDataValue(float("nan")); b.WriteArray(arr.astype("float32"))
    dst = gdal.Warp("", src, format="MEM", dstSRS="EPSG:4326", srcNodata="nan", dstNodata="nan")
    return dst.GetRasterBand(1).ReadAsArray().astype("float64")


def _rgba_png(arr, vmin, vmax, deadband, out):
    norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax)
    rgba = matplotlib.colormaps["RdBu"](norm(np.clip(arr, vmin, vmax)))
    alpha = np.clip((np.abs(arr) - deadband) / (deadband * 1.6), 0.0, 1.0) * 0.92
    rgba[..., 3] = np.where(np.isfinite(arr), alpha, 0.0)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((rgba * 255).astype("uint8"), "RGBA").save(out)


def sink_lapse(aoi_id, nframes=8):
    """Export cumulative-vertical-displacement frames (the 'watch it sink' view).

    Reads the MintPy time-series, takes the cumulative motion since the first
    acquisition at ~nframes evenly-spaced dates, converts LOS->vertical, centers
    on the area median, colorizes (same red-sink/blue-rise ramp), and writes one
    PNG per frame. Returns [{date, png}] for the frontend slider.
    """
    import h5py
    run = ROOT / "data" / "insar" / aoi_id / "mintpy_run"
    with h5py.File(run / "velocity.h5") as f:
        a = dict(f.attrs)
    with h5py.File(run / "inputs" / "geometryGeo.h5") as f:
        inc = f["incidenceAngle"][:]
    with h5py.File(run / "timeseries.h5") as f:
        ts = f["timeseries"][:] * 1000.0  # m -> mm (LOS)
        dates = [d.decode() if isinstance(d, bytes) else str(d) for d in f["date"][:]]
    gt = (float(a["X_FIRST"]), float(a["X_STEP"]), 0.0, float(a["Y_FIRST"]), 0.0, float(a["Y_STEP"]))
    epsg = int(a["EPSG"])
    cosi = np.cos(np.radians(inc))
    idx = sorted(set(np.linspace(0, len(dates) - 1, nframes).round().astype(int)))
    # color scale from the final cumulative frame (robust 1% subsidence)
    final = _warp_arr_to_4326((ts[idx[-1]] - ts[0]) / cosi, gt, epsg)
    final = final - np.nanmedian(final)
    span = max(20.0, float(-np.nanpercentile(final, 1)))
    vmin, vmax = -span, span * 0.4
    hot = np.isfinite(final) & (final <= -span * 0.5)  # the fastest-sinking area, for the readout
    frames = []
    for k, i in enumerate(idx):
        disp = _warp_arr_to_4326((ts[i] - ts[0]) / cosi, gt, epsg)
        disp = disp - np.nanmedian(disp)
        out = ROOT / "web" / "data" / "lapse" / aoi_id / f"{k:02d}.png"
        _rgba_png(disp, vmin, vmax, deadband=max(8.0, span * 0.12), out=out)
        cum = float(np.nanmedian(disp[hot])) if hot.any() else 0.0  # hotspot cumulative since 2016 (mm)
        frames.append({"date": f"{dates[i][:4]}-{dates[i][4:6]}",
                       "png": f"data/lapse/{aoi_id}/{k:02d}.png", "cum_mm": round(cum)})
    print(f"{aoi_id}: {len(frames)} sink-lapse frames, scale +/-{span:.0f} mm, "
          f"hotspot cumulative {frames[-1]['cum_mm']} mm by {frames[-1]['date']}")
    return frames


def main():
    # carry over exposure fields (added by make_exposure.py) so a rebuild here
    # does not wipe them; they only change when exposure is recomputed.
    prev = {}
    cj = ROOT / "web" / "data" / "cities.json"
    if cj.exists():
        for c in json.loads(cj.read_text()).get("cities", []):
            prev[c["id"]] = {k: c[k] for k in
                             ("buildings_on_sinking_ground", "buildings_threshold_mm_yr", "exposure_geojson")
                             if k in c}
    cities = []
    for aoi_id in GO_CITIES:
        res = json.loads((ROOT / "tmp" / "phase2" / f"{aoi_id}-result.json").read_text()) \
            if (ROOT / "tmp" / "phase2" / f"{aoi_id}-result.json").exists() else {}
        ov_path = ROOT / "web" / "data" / "overlay" / f"{aoi_id}-25yr.json"
        ov = json.loads(ov_path.read_text()) if ov_path.exists() else {}
        bounds = colorize(aoi_id)
        rate = res.get("robust_subsidence_mm_yr") or res.get("max_subsidence_mm_yr")
        cities.append({
            "id": aoi_id,
            "bounds": bounds,
            "center": [round((bounds["west"] + bounds["east"]) / 2, 4),
                       round((bounds["south"] + bounds["north"]) / 2, 4)],
            "rate_mm_yr": rate,
            "peak_mm_yr": res.get("peak_subsidence_mm_yr"),
            "anchor_mm_yr": res.get("published_anchor_mm_yr"),
            "ratio": res.get("ratio") or res.get("robust_ratio"),
            "confidence": res.get("confidence", "high"),
            "verdict": res.get("verdict", "GO"),
            "flood_pct_high_sub": ov.get("pct_high_subsidence_in_flood_zone"),
            "flood_pct_background": ov.get("pct_all_reliable_ground_flood_prone"),
            "png": f"data/velocity/{aoi_id}.png",
            "lapse": sink_lapse(aoi_id),
            **prev.get(aoi_id, {}),
        })
        print(f"{aoi_id}: rate {rate} mm/yr, bounds {bounds}")
    payload = {
        "vmin": VMIN, "vmax": VMAX,
        "cities": cities,
        "coherence_limited": [{"id": k, "note": v} for k, v in LIMITED.items()],
    }
    (ROOT / "web" / "data" / "cities.json").write_text(json.dumps(payload, indent=2))
    print(f"wrote web/data/cities.json ({len(cities)} mapped cities)")


if __name__ == "__main__":
    main()
