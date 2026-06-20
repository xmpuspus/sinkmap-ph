"""Stream-fetch + clip HyP3 products one at a time, never hoarding the raw
full-frame GAMMA bundles. Per product: download the ~200 MB zip to a temp dir,
extract only the 5 bands MintPy uses, clip them to the AOI grid into clipped/,
delete the temp. Peak disk stays well under 1 GB; the kept clipped/ is ~70 MB
per city, versus ~16 GB for the full unzipped products.

Runs in the MintPy env (needs gdal + hyp3_sdk). Resumable: a product already
clipped is skipped.

  ~/anaconda3/envs/sinkmap-mintpy312/bin/python pipeline/insar/lean_fetch.py <aoi>
"""
from __future__ import annotations

import glob
import math
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

TYPES = ["unw_phase", "corr", "dem", "lv_theta", "lv_phi"]  # the bands MintPy reads


def _aoi_grid(aoi_id, res=80):
    """The common AOI UTM grid clip_products uses (subset.lalo mis-crops HyP3)."""
    from pyproj import Transformer
    from pipeline import aoi as reg
    lon0, lat0, lon1, lat1 = reg.get(aoi_id).bbox
    cen = (lon0 + lon1) / 2.0
    epsg = 32600 + int((cen + 180) // 6) + 1
    inv = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
    pts = [inv.transform(x, y) for x in (lon0, lon1) for y in (lat0, lat1)]
    es = [p[0] for p in pts]; ns = [p[1] for p in pts]
    e0, e1 = math.floor(min(es) / res) * res, math.ceil(max(es) / res) * res
    n0, n1 = math.floor(min(ns) / res) * res, math.ceil(max(ns) / res) * res
    return e0, n0, e1, n1, epsg, res


def fetch_clip(aoi_id):
    from osgeo import gdal
    from pipeline.insar._edl import hyp3_client
    gdal.UseExceptions()
    e0, n0, e1, n1, epsg, res = _aoi_grid(aoi_id)
    dst = ROOT / "data" / "insar" / aoi_id / "clipped"
    dst.mkdir(parents=True, exist_ok=True)
    hyp3 = hyp3_client()
    jobs = [j for j in hyp3.find_jobs(name=f"sinkmap-{aoi_id}") if j.succeeded()]
    print(f"[{aoi_id}] {len(jobs)} succeeded jobs; streaming fetch+clip", flush=True)
    done = 0
    for j in jobs:
        pname = j.files[0]["filename"][:-4]  # strip .zip
        od = dst / pname
        if od.exists() and glob.glob(str(od / "*_unw_phase.tif")):
            done += 1; continue  # already clipped (resumable)
        with tempfile.TemporaryDirectory(dir=str(ROOT / "tmp")) as tmp:
            tmp = Path(tmp)
            for f in j.download_files(tmp):
                f = Path(f)
                if f.suffix != ".zip":
                    continue
                with zipfile.ZipFile(f) as z:
                    members = [m for m in z.namelist()
                               if any(m.endswith(f"_{t}.tif") for t in TYPES) or m.endswith(".txt")]
                    z.extractall(tmp, members)
                f.unlink()  # drop the zip immediately
            od.mkdir(parents=True, exist_ok=True)
            for t in TYPES:
                ins = glob.glob(str(tmp / "**" / f"*_{t}.tif"), recursive=True)
                if ins:
                    gdal.Warp(str(od / Path(ins[0]).name), ins[0],
                              outputBounds=(e0, n0, e1, n1), xRes=res, yRes=res,
                              dstSRS=f"EPSG:{epsg}", resampleAlg="near")
            for meta in glob.glob(str(tmp / "**" / "*.txt"), recursive=True):
                shutil.copy(meta, od / Path(meta).name)
        done += 1
        if done % 10 == 0 or done == len(jobs):
            print(f"[{aoi_id}] {done}/{len(jobs)} clipped", flush=True)
    mb = sum(f.stat().st_size for f in dst.rglob("*") if f.is_file()) // (1024 * 1024)
    print(f"[{aoi_id}] done: {done} products in {dst} (~{mb} MB kept)", flush=True)
    return dst


if __name__ == "__main__":
    fetch_clip(sys.argv[1] if len(sys.argv) > 1 else "cavite-coast")
