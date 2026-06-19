"""Building-exposure read: how many buildings sit on fast-sinking ground.

For each validated city, find the fast-sinking sub-area from the velocity raster,
pull OSM building footprints there via Overpass (centroids; the documented
User-Agent + `out center;` pattern), sample the median-referenced vertical
velocity at each building, and count those on ground sinking faster than a
threshold. Writes the count into web/data/cities.json and a small GeoJSON of the
fast-sinking building points for an optional glow layer. Run in the MintPy env
(gdal):

  ~/anaconda3/envs/sinkmap-mintpy312/bin/python scripts/make_exposure.py [city ...]
"""
from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from osgeo import gdal
from pyproj import Transformer

gdal.UseExceptions()
ROOT = Path(__file__).resolve().parent.parent
THRESH = {"metro-manila": 15.0, "cebu-mandaue": 8.0, "iloilo": 6.0}  # mm/yr "fast-sinking"
OVERPASS = "https://overpass-api.de/api/interpreter"


def _median_ref_4326(aoi_id):
    """vertical.tif warped to EPSG:4326, median-subtracted (display datum). Returns (arr, gt)."""
    ds = gdal.Warp("", str(ROOT / "data" / "insar" / aoi_id / "vertical.tif"),
                   format="MEM", dstSRS="EPSG:4326", srcNodata="nan", dstNodata="nan")
    arr = ds.GetRasterBand(1).ReadAsArray().astype("float64")
    arr = arr - np.nanmedian(arr)
    return arr, ds.GetGeoTransform()


def _sample(arr, gt, lon, lat):
    j = int((lon - gt[0]) / gt[1]); i = int((lat - gt[3]) / gt[5])
    if 0 <= i < arr.shape[0] and 0 <= j < arr.shape[1]:
        v = arr[i, j]
        return float(v) if np.isfinite(v) else None
    return None


def _sink_bbox(arr, gt, thr):
    """lat/lon bbox of pixels sinking faster than thr (bounds the Overpass query)."""
    ys, xs = np.where(np.isfinite(arr) & (arr <= -thr))
    if len(ys) == 0:
        return None
    lons = gt[0] + (xs + 0.5) * gt[1]; lats = gt[3] + (ys + 0.5) * gt[5]
    return [float(lats.min()), float(lons.min()), float(lats.max()), float(lons.max())]  # S,W,N,E


def _overpass_buildings(bbox_swne):
    q = (f"[out:json][timeout:120];(way[\"building\"]({bbox_swne[0]},{bbox_swne[1]},{bbox_swne[2]},{bbox_swne[3]});"
         f"relation[\"building\"]({bbox_swne[0]},{bbox_swne[1]},{bbox_swne[2]},{bbox_swne[3]}););out center;")
    req = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": q}).encode(),
                                 headers={"User-Agent": "sinkmap.ph/1.0 (civic subsidence map)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())["elements"]


def main():
    cities_path = ROOT / "web" / "data" / "cities.json"
    data = json.loads(cities_path.read_text())
    want = sys.argv[1:] or [c["id"] for c in data["cities"]]
    for c in data["cities"]:
        if c["id"] not in want:
            continue
        thr = THRESH.get(c["id"], 10.0)
        arr, gt = _median_ref_4326(c["id"])
        sb = _sink_bbox(arr, gt, thr)
        if sb is None:
            print(f"{c['id']}: no pixels sinking > {thr} mm/yr"); continue
        els = _overpass_buildings(sb)
        pts, on_sink = [], 0
        for e in els:
            ctr = e.get("center") or ({"lat": e.get("lat"), "lon": e.get("lon")} if e.get("lat") else None)
            if not ctr:
                continue
            v = _sample(arr, gt, ctr["lon"], ctr["lat"])
            if v is not None and v <= -thr:
                on_sink += 1
                pts.append([round(ctr["lon"], 5), round(ctr["lat"], 5)])
        c["buildings_on_sinking_ground"] = on_sink
        c["buildings_threshold_mm_yr"] = thr
        gj = {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": p}, "properties": {}} for p in pts]}
        (ROOT / "web" / "data" / "exposure" / f"{c['id']}.geojson").parent.mkdir(parents=True, exist_ok=True)
        (ROOT / "web" / "data" / "exposure" / f"{c['id']}.geojson").write_text(json.dumps(gj))
        c["exposure_geojson"] = f"data/exposure/{c['id']}.geojson"
        print(f"{c['id']}: {len(els)} OSM buildings queried, {on_sink} on ground sinking > {thr} mm/yr")
        time.sleep(2)  # be polite to Overpass
    cities_path.write_text(json.dumps(data, indent=2))
    print("updated web/data/cities.json")


if __name__ == "__main__":
    main()
