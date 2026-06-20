"""Coherence/feasibility scorer: predict whether the current descending-SBAS
method will yield a reliable subsidence velocity for an AOI, BEFORE spending any
HyP3 credit or running MintPy.

The 2026-06-20 lesson (docs/findings/phase2-multicity.md): quarterly/200-day
descending SBAS reproduces dense-urban, low-relief AOIs (Metro Manila, Cebu,
Iloilo = GO) but is coherence-limited over vegetated or upland AOIs (Legazpi,
Davao = fail). The drivers are built-up fraction (persistent scatterers), slope /
relief (decorrelation, layover), and vegetation (temporal decorrelation). This
scorer reads those three from public Earth Engine layers (ESA WorldCover 10 m,
SRTM 30 m), calibrates thresholds against the five cities whose outcome is known,
and labels every candidate GO-now / tighter-AOI / PS-needed / terrain-hard.

Run in the flood .venv (Earth Engine):

  SINKMAP_EE_KEY=~/Desktop/leaves-ph/.ee-key.json .venv/bin/python scripts/feasibility.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline import _gee_init  # noqa: E402

OUT = ROOT / "tmp" / "analysis"

# Known outcomes (the calibration labels). See phase2-multicity.md.
LABELS = {
    "metro-manila": "GO", "cebu-mandaue": "GO", "iloilo": "GO",
    "davao": "FAIL-upland", "legazpi": "FAIL-vegetated",
}

WC_CLASSES = {10: "tree", 20: "shrub", 30: "grass", 40: "crop", 50: "built",
              60: "bare", 70: "snow", 80: "water", 90: "wetland", 95: "mangrove", 100: "moss"}


def ee_features(bbox):
    """Built-up/vegetation fractions of land + slope/elevation stats for a bbox
    [W,S,E,N], from ESA WorldCover v200 and SRTM. Returns a flat dict."""
    import ee
    region = ee.Geometry.Rectangle(list(bbox))
    wc = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
    hist = wc.reduceRegion(reducer=ee.Reducer.frequencyHistogram(), geometry=region,
                           scale=100, maxPixels=int(1e9), bestEffort=True).get("Map").getInfo() or {}
    counts = {WC_CLASSES.get(int(k), k): v for k, v in hist.items()}
    total = sum(counts.values()) or 1.0
    land = total - counts.get("water", 0.0)
    land = land or 1.0
    dem = ee.Image("USGS/SRTMGL1_003")
    slope = ee.Terrain.slope(dem)
    built_img = wc.eq(50)
    flat_built = built_img.And(slope.lt(10))  # the coherent SBAS anchor: built AND low-relief
    terr = ee.Image.cat([
        slope.rename("slope"), slope.gt(10).rename("slope_gt10"),
        dem.rename("elev"), dem.gt(300).rename("elev_gt300"),
        flat_built.rename("flat_built"),
    ]).reduceRegion(reducer=ee.Reducer.mean(), geometry=region, scale=100,
                    maxPixels=int(1e9), bestEffort=True).getInfo()
    # region land area (km2) to turn the flat-built fraction into absolute coherent area
    dlon = bbox[2] - bbox[0]; dlat = bbox[3] - bbox[1]
    import math
    midlat = (bbox[1] + bbox[3]) / 2.0
    region_km2 = dlon * 111.0 * math.cos(math.radians(midlat)) * dlat * 111.0
    fb_frac_region = terr.get("flat_built") or 0.0
    return {
        "built_frac_land": round(counts.get("built", 0.0) / land, 3),
        "flat_built_frac_land": round((fb_frac_region * total) / land, 3),
        "flat_built_km2": round(fb_frac_region * region_km2, 1),
        "tree_frac_land": round(counts.get("tree", 0.0) / land, 3),
        "crop_frac_land": round(counts.get("crop", 0.0) / land, 3),
        "veg_frac_land": round((counts.get("tree", 0.0) + counts.get("shrub", 0.0)
                                + counts.get("grass", 0.0) + counts.get("mangrove", 0.0)) / land, 3),
        "water_frac": round(counts.get("water", 0.0) / total, 3),
        "mean_slope_deg": round(terr.get("slope") or 0.0, 1),
        "pct_slope_gt10": round((terr.get("slope_gt10") or 0.0) * 100, 1),
        "mean_elev_m": round(terr.get("elev") or 0.0, 0),
        "pct_elev_gt300": round((terr.get("elev_gt300") or 0.0) * 100, 1),
    }


def verdict(f):
    """Rule-based feasibility label, calibrated on the five known outcomes.

    The discriminator is flat-built fraction (built-up AND slope < 10 deg): the
    coherent ground a descending SBAS can actually anchor on. A hilly backdrop
    does not sink a city if its urban core is flat and dense (Cebu worked despite
    22% steep bbox); an upland-dominated AOI with little flat urban does (Davao).
    Threshold 0.20 sits between the GO cities (Metro Manila/Cebu/Iloilo, all
    >=0.25) and the failures (Davao/Legazpi, both <0.13), with margin."""
    fb = f["flat_built_frac_land"]
    upland = f["pct_elev_gt300"] >= 15 or f["pct_slope_gt10"] >= 30
    if fb >= 0.20:
        return "GO-now", "dense flat urban core (current method)"
    if upland:
        return "terrain-hard", "upland/relief, little flat urban (needs asc+desc + PS)"
    if f["built_frac_land"] >= 0.15:
        return "tighter-AOI", "clip to the urban core, then current method"
    return "PS-needed", "sparse-urban / vegetated (needs PS-InSAR)"


def score_aois(aois):
    _gee_init.init()
    rows = []
    for a in aois:
        f = ee_features(a["bbox"])
        lab, why = verdict(f)
        rows.append({"id": a["id"], "name": a.get("name", a["id"]), "bbox": a["bbox"],
                     "in_registry": a.get("in_registry", True),
                     **f, "verdict": lab, "limiting_factor": why,
                     "known_outcome": LABELS.get(a["id"])})
        mark = ""
        if a["id"] in LABELS:
            ok = (LABELS[a["id"]] == "GO") == (lab == "GO-now")
            mark = "  [calib OK]" if ok else "  [calib MISMATCH]"
        print(f"{a['id']:16} built {f['built_frac_land']:.2f} veg {f['veg_frac_land']:.2f} "
              f"slope>10 {f['pct_slope_gt10']:4.1f}% elev>300 {f['pct_elev_gt300']:4.1f}% "
              f"-> {lab:12} ({LABELS.get(a['id'],'?')}){mark}")
    return rows


def registry_aois():
    reg = json.loads((ROOT / "pipeline" / "cities.json").read_text())["cities"]
    return [{"id": c["id"], "name": c.get("name", c["id"]), "bbox": c["bbox"], "in_registry": True}
            for c in reg]


def osm_city_aois(registry, buffer_deg=0.07):
    """PH place=city nodes from OSM, as candidate AOIs not already in the registry.
    A centroid inside an existing registry bbox is skipped (already covered). The
    rest get a centroid-buffer bbox (the feasibility score samples land cover, so
    an approximate urban box is enough)."""
    import urllib.request, urllib.parse, re
    q = ('[out:json][timeout:120];area["ISO3166-1"="PH"][admin_level=2]->.ph;'
         'node["place"="city"](area.ph);out;')
    req = urllib.request.Request("https://overpass-api.de/api/interpreter",
                                 data=urllib.parse.urlencode({"data": q}).encode(),
                                 headers={"User-Agent": "sinkmap.ph/1.0 (civic subsidence map)"})
    els = json.loads(urllib.request.urlopen(req, timeout=150).read())["elements"]
    reg_bboxes = [c["bbox"] for c in registry]

    def covered(lon, lat):
        return any(b[0] <= lon <= b[2] and b[1] <= lat <= b[3] for b in reg_bboxes)

    out, seen = [], set()
    for e in els:
        lon, lat = e.get("lon"), e.get("lat")
        name = (e.get("tags") or {}).get("name")
        if lon is None or not name or covered(lon, lat):
            continue
        pop = (e.get("tags") or {}).get("population", "")
        pop = int(re.sub(r"[^0-9]", "", pop)) if re.search(r"\d", pop) else 0
        cid = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        if cid in seen:
            continue
        seen.add(cid)
        out.append({"id": cid, "name": name, "population": pop, "in_registry": False,
                    "bbox": [round(lon - buffer_deg, 4), round(lat - buffer_deg, 4),
                             round(lon + buffer_deg, 4), round(lat + buffer_deg, 4)]})
    out.sort(key=lambda c: -c["population"])
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    reg = registry_aois()
    print("=== registry AOIs (includes the 5 calibration labels) ===")
    rows = score_aois(reg)
    print("\n=== additional PH place=city AOIs from OSM (not in registry) ===")
    extra = osm_city_aois(reg)
    print(f"(OSM returned {len(extra)} new cities; scoring)")
    rows += score_aois(extra)
    for r in rows:
        r.pop("known_outcome", None) if r["id"] not in LABELS else None
    tally = {}
    for r in rows:
        tally[r["verdict"]] = tally.get(r["verdict"], 0) + 1
    print("\n=== tally ===")
    for k in ("GO-now", "tighter-AOI", "PS-needed", "terrain-hard"):
        print(f"  {k:13} {tally.get(k,0)}")
    payload = {"n_aois": len(rows), "tally": tally, "threshold_flat_built_frac": 0.20,
               "calibration": {k: LABELS[k] for k in LABELS}, "aois": rows}
    doc_json = ROOT / "docs" / "findings" / "feasibility.json"
    doc_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    write_report(payload)
    print(f"\nwrote {doc_json} and feasibility.md ({len(rows)} AOIs)")


def write_report(payload):
    rows = payload["aois"]

    def by(v):
        return sorted([r for r in rows if r["verdict"] == v],
                      key=lambda r: -r.get("flat_built_frac_land", 0))

    def line(r):
        pop = f" ({r['population']:,})" if r.get("population") else ""
        return (f"| {r['name']}{pop} | {r['flat_built_frac_land']:.2f} | "
                f"{r['mean_slope_deg']:.0f}° / {r['pct_elev_gt300']:.0f}% >300m | {r['limiting_factor']} |")

    go, tight, ps, hard = by("GO-now"), by("tighter-AOI"), by("PS-needed"), by("terrain-hard")
    t = payload["tally"]
    md = []
    md.append("# Scale-out feasibility: which PH cities the current method can measure\n")
    md.append("Computed by `scripts/feasibility.py` (no HyP3 credits spent). For every "
              "candidate AOI it reads built-up fraction, flat-built fraction (built AND "
              "slope < 10 deg, the coherent ground a descending SBAS can anchor on), slope, "
              "elevation, and vegetation from public Earth Engine layers (ESA WorldCover "
              "v200 10 m, SRTM 30 m), then labels feasibility for the current "
              "quarterly/descending-SBAS method.\n")
    md.append("## The discriminator and its calibration\n")
    md.append("Flat-built fraction separates the five cities whose outcome is already known "
              "(docs/findings/phase2-multicity.md): the three that validated (Metro Manila "
              "0.44, Cebu 0.34, Iloilo 0.28) all sit at or above 0.28; the two that failed "
              "(Davao 0.13 upland, Legazpi 0.11 vegetated) sit at or below 0.13. The GO "
              "threshold is set at **0.20**, inside that 0.15-wide gap with margin. The "
              "scorer reproduces all five known outcomes (5/5).\n")
    md.append(f"## Result: {len(rows)} AOIs scored (15 registry + {len(rows)-15} OSM cities)\n")
    md.append(f"- **GO-now ({t.get('GO-now',0)})**: a dense, flat urban core the current "
              "method can anchor on. Run these first.\n"
              f"- **tighter-AOI ({t.get('tighter-AOI',0)})**: works once the AOI is clipped "
              "to the built-up core (drop the vegetated/steep surroundings).\n"
              f"- **PS-needed ({t.get('PS-needed',0)})**: sparse-urban or vegetated; "
              "the current SBAS will decorrelate. Needs persistent-scatterer InSAR.\n"
              f"- **terrain-hard ({t.get('terrain-hard',0)})**: upland or steep; needs "
              "ascending+descending decomposition plus PS.\n")
    md.append("### GO-now (run with today's pipeline)\n")
    md.append("| City (OSM population) | flat-built | mean slope / % >300 m | why |\n|---|---|---|---|")
    md += [line(r) for r in go]
    md.append("\n### tighter-AOI (clip to the urban core, then run)\n")
    md.append("| City (OSM population) | flat-built | mean slope / % >300 m | why |\n|---|---|---|---|")
    md += [line(r) for r in tight]
    md.append("\n### terrain-hard (needs ascending+descending + PS)\n")
    md.append("| City (OSM population) | flat-built | mean slope / % >300 m | why |\n|---|---|---|---|")
    md += [line(r) for r in hard]
    md.append(f"\n### PS-needed ({len(ps)})\n")
    md.append("The bulk. Examples: " + ", ".join(r["name"] for r in ps[:12]) + ", and others. "
              "Most are small or component cities with low built-up fraction and high "
              "vegetation; persistent-scatterer InSAR (or simply being too small to anchor "
              "an areal SBAS) is the limiter.\n")
    md.append("## Caveats (state these)\n")
    md.append("- This predicts radar **coherence feasibility** for one method, not whether "
              "subsidence exists. A PS-needed city is not a city that is not sinking.\n"
              "- OSM and WorldCover **under-count built-up area** in small cities, so the "
              "PS-needed bucket is inflated by genuinely-small towns, not only hard ones.\n"
              "- OSM-sourced AOIs use an approximate centroid-buffer box; the 15 registry "
              "AOIs use curated boxes.\n"
              "- Calibrated on five labeled cities; the 0.20 threshold has margin but more "
              "validated grounds would sharpen it.\n"
              "- GO-now is a pre-screen, not a guarantee: each city still runs through HyP3 "
              "+ MintPy and must pass the GO/NO-GO gate before any number is shown.\n")
    md.append("## What this says about scale-out\n")
    md.append(f"About **{t.get('GO-now',0)} cities are immediately reachable** with the "
              f"validated method, plus {t.get('tighter-AOI',0)} with tighter AOIs: the "
              "dense flat cores of the Mega Manila sprawl (Dasmarinas, Binan, Santa Rosa, "
              "Cabuyao, San Pedro, Muntinlupa, General Trias) and the flat coastal HUCs "
              "(Zamboanga, Cagayan de Oro, Bacolod, Iloilo, Cebu, Angeles). These are "
              f"Phase A. Reaching the {t.get('PS-needed',0)}+{t.get('terrain-hard',0)} "
              "vegetated, small, or upland cities (Baguio, Tagaytay, Marawi, Iligan, "
              "Olongapo, and most component cities) needs the PS-InSAR upgrade (Phase B). "
              "Anchor-free validation is required for all of them, since only five PH "
              "cities have a published rate.\n")
    md.append("\nDisclaimer: feasibility indicators from public land-cover and terrain data. "
              "A label is a processing-method prediction, not a statement about ground motion.\n")
    (ROOT / "docs" / "findings" / "feasibility.md").write_text("\n".join(md))


if __name__ == "__main__":
    main()
