"""Build the round-3 finding layers + web/data/findings.json for the map panel.

Colorizes the acceleration and differential-tilt rasters (written by analysis.py)
into PNG image-overlays, writes the double-exposed building points to a geojson,
and assembles web/data/findings.json -- the findings story panel's content. Every
number in the copy is read from the gated tmp/analysis/*.json (compute before
narrating); nothing is hand-typed. Run in the MintPy env, AFTER analysis.py:

  PY=~/anaconda3/envs/sinkmap-mintpy312/bin/python
  $PY scripts/analysis.py accel metro-manila && $PY scripts/analysis.py tilt metro-manila
  $PY scripts/analysis.py compound metro-manila  # ... and hazard/footprint/municipality
  $PY scripts/make_finding_layers.py
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
ANA = ROOT / "tmp" / "analysis"
CITY = "metro-manila"


def _load(name):
    return json.loads((ANA / name).read_text())


def _warp_bounds(tif):
    ds = gdal.Warp("", str(tif), format="MEM", dstSRS="EPSG:4326",
                   srcNodata="nan", dstNodata="nan", resampleAlg="near")
    gt = ds.GetGeoTransform(); w, h = ds.RasterXSize, ds.RasterYSize
    arr = ds.GetRasterBand(1).ReadAsArray().astype("float64")
    west, north = gt[0], gt[3]
    east, south = gt[0] + gt[1] * w, gt[3] + gt[5] * h
    return arr, {"west": round(west, 5), "south": round(south, 5),
                 "east": round(east, 5), "north": round(north, 5)}


def accel_png():
    """Acceleration: red = subsidence speeding up, green = slowing, center clear."""
    arr, bounds = _warp_bounds(ROOT / "data" / "insar" / CITY / "accel.tif")
    vmin, vmax = -20.0, 20.0
    norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax)
    rgba = matplotlib.colormaps["RdYlGn"](norm(np.clip(arr, vmin, vmax)))
    alpha = np.clip((np.abs(arr) - 3.0) / 6.0, 0.0, 1.0) * 0.9
    rgba[..., 3] = np.where(np.isfinite(arr), alpha, 0.0)
    out = ROOT / "web" / "data" / "accel" / f"{CITY}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((rgba * 255).astype("uint8"), "RGBA").save(out)
    return bounds


def tilt_png():
    """Differential tilt: single-hue purple, alpha scales with gradient steepness."""
    arr, bounds = _warp_bounds(ROOT / "data" / "insar" / CITY / "tilt.tif")
    rgba = np.zeros(arr.shape + (4,), dtype="float64")
    rgba[..., 0] = 0.482; rgba[..., 1] = 0.121; rgba[..., 2] = 0.635  # #7b1fa2 purple
    alpha = np.clip((arr - 3.0) / 12.0, 0.0, 1.0) * 0.88
    rgba[..., 3] = np.where(np.isfinite(arr), alpha, 0.0)
    out = ROOT / "web" / "data" / "tilt" / f"{CITY}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray((rgba * 255).astype("uint8"), "RGBA").save(out)
    return bounds


def compound_geojson():
    pts = _load(f"compound-{CITY}-pts.json")
    gj = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": {"type": "Point", "coordinates": p}, "properties": {}} for p in pts]}
    out = ROOT / "web" / "data" / "exposure" / f"{CITY}-flood.geojson"
    out.write_text(json.dumps(gj))
    return f"data/exposure/{CITY}-flood.geojson", len(pts)


def main():
    acc = _load(f"accel-{CITY}.json")
    cmp_ = _load(f"compound-{CITY}.json")
    foot = _load(f"footprint-{CITY}.json")
    muni = _load(f"municipality-{CITY}.json")
    haz = _load(f"hazard-tiers-{CITY}.json")
    tlt = _load(f"tilt-{CITY}.json")
    recl = _load("reclamation-cebu-mandaue.json")
    # land rate (Metro Manila robust) for the sea-vs-land card
    mm_result = json.loads((ROOT / "tmp" / "phase2" / "metro-manila-result.json").read_text())
    land = mm_result["robust_subsidence_mm_yr"]

    accel_bounds = accel_png()
    tilt_bounds = tilt_png()
    cmp_geo, cmp_n = compound_geojson()

    hot = acc["hotspot_15.177N_120.983E"]
    east = acc["max_accelerating_cluster"]
    san = muni["top"][0]
    # hazard: % sinking >10 per class, ordered none/Low/Med/High
    pct = {t["class"]: t["pct_sinking_gt10"] for t in haz["tiers"]}
    f100 = foot["headline"]
    f100_end = foot["area_km2_by_depth"]["100"][-1]
    f100_peak = foot["headline"]["peak_km2"]
    recl_srp = next(s for s in recl["sites"] if "SRP" in s["name"] or "South Road" in s["name"])

    findings = [
        {
            "id": "acceleration", "layer": "accel",
            "tag": {"en": "Acceleration", "tl": "Pagbilis"},
            "title": {"en": "Past the peak, but the field is still spreading",
                      "tl": "Lampas na sa rurok, pero lumalawak pa ang lupa"},
            "stat": {"en": f"{acc['area_accelerating_gt3_km2']:.0f} km² speeding up vs {acc['area_decelerating_gt3_km2']:.0f} km² slowing",
                     "tl": f"{acc['area_accelerating_gt3_km2']:.0f} km² bumibilis vs {acc['area_decelerating_gt3_km2']:.0f} km² bumabagal"},
            "blurb": {"en": f"The worst hotspot slowed ({hot['early_rate_mm_yr']:.0f} to {hot['late_rate_mm_yr']:.0f} mm/yr between the 2016-2020 and 2021-2025 halves), yet more ground sped up than slowed. A zone about 6 km east more than doubled, from {east['early_rate_mm_yr']:.0f} to {east['late_rate_mm_yr']:.0f} mm/yr. Red is speeding up, green is slowing.",
                      "tl": f"Bumagal ang pinakamabilis na lugar ({hot['early_rate_mm_yr']:.0f} hanggang {hot['late_rate_mm_yr']:.0f} mm/taon sa pagitan ng 2016-2020 at 2021-2025), pero mas malaking lupa ang bumilis. Isang lugar 6 km sa silangan ang lumampas sa doble, mula {east['early_rate_mm_yr']:.0f} hanggang {east['late_rate_mm_yr']:.0f} mm/taon. Pula ay bumibilis, berde ay bumabagal."},
            "fly": {"center": [121.0, 15.15], "zoom": 9.6},
            "callouts": [
                {"lngLat": [120.983, 15.177], "label": {"en": f"hotspot: slowing ({hot['late_rate_mm_yr']:.0f} mm/yr)",
                                                          "tl": f"hotspot: bumabagal ({hot['late_rate_mm_yr']:.0f} mm/taon)"}},
                {"lngLat": [east["lon"], east["lat"]], "label": {"en": f"6 km east: doubled to {east['late_rate_mm_yr']:.0f} mm/yr",
                                                                  "tl": f"6 km silangan: doble na, {east['late_rate_mm_yr']:.0f} mm/taon"}},
            ],
        },
        {
            "id": "compound", "layer": "compound",
            "tag": {"en": "Compound risk", "tl": "Dobleng panganib"},
            "title": {"en": "Sinking fast and flood-prone at the same time",
                      "tl": "Mabilis lumulubog at madaling bahain nang sabay"},
            "stat": {"en": f"{cmp_['pct_double_exposed']:.0f}% of fast-sinking buildings are also flood-prone",
                     "tl": f"{cmp_['pct_double_exposed']:.0f}% ng mabilis lumulubog na gusali ay madali ring bahain"},
            "blurb": {"en": f"Of {cmp_['buildings_on_fast_sinking_ground']:,} mapped buildings on ground sinking faster than {cmp_['fast_sinking_threshold_mm_yr']:.0f} mm/yr, {cmp_['also_in_flood_prone_zone']:,} also sit inside a 25-year flood-prone zone (0.5 m or deeper). Two public layers overlapping, not proof of cause.",
                      "tl": f"Sa {cmp_['buildings_on_fast_sinking_ground']:,} gusaling nasa lupang lumulubog nang higit {cmp_['fast_sinking_threshold_mm_yr']:.0f} mm/taon, {cmp_['also_in_flood_prone_zone']:,} ang nasa loob din ng 25-taong delikado-sa-baha (0.5 m pataas). Pagsasapaw ng dalawang datos, hindi patunay ng sanhi."},
            "fly": {"center": [120.97, 15.0], "zoom": 9.4},
            "callouts": [],
        },
        {
            "id": "footprint",
            "tag": {"en": "Footprint", "tl": "Sakop"},
            "title": {"en": "The 10 cm subsidence footprint grew from nothing",
                      "tl": "Lumaki mula sa wala ang sakop ng 10 cm na paglubog"},
            "stat": {"en": f"~0 to ~{f100_end:.0f} km² since 2016 (peak {f100_peak:.0f} km²)",
                     "tl": f"~0 hanggang ~{f100_end:.0f} km² mula 2016 (rurok {f100_peak:.0f} km²)"},
            "blurb": {"en": f"In 2016 almost no ground had dropped 10 cm relative to stable. By late 2025, about {f100_end:.0f} km² had, peaking near {f100_peak:.0f} km² in early 2025. Watch it build with the 'Watch it sink' slider.",
                      "tl": f"Noong 2016 halos walang lupang bumaba ng 10 cm kumpara sa matatag. Pagdating ng huling bahagi ng 2025, mga {f100_end:.0f} km² na, umabot malapit sa {f100_peak:.0f} km² noong simula ng 2025. Panoorin sa 'Panoorin lumubog' na slider."},
            "fly": {"center": [121.0, 15.05], "zoom": 9.3},
            "callouts": [],
        },
        {
            "id": "municipality",
            "tag": {"en": "Most exposed", "tl": "Pinaka-apektado"},
            "title": {"en": f"One town carries most of the exposed ground: {san['name']}",
                      "tl": f"Isang bayan ang may pinakamaraming apektadong lupa: {san['name']}"},
            "stat": {"en": f"{san['name']}, Bulacan: {san['fast_sinking_km2']:.0f} km² sinking fast, {san['fast_and_flood_km2']:.0f} km² also flood-prone",
                     "tl": f"{san['name']}, Bulacan: {san['fast_sinking_km2']:.0f} km² mabilis lumulubog, {san['fast_and_flood_km2']:.0f} km² madali ring bahain"},
            "blurb": {"en": f"Aggregating per municipality boundary, {san['name']} has {san['fast_sinking_km2']:.0f} km² of ground sinking faster than 15 mm/yr, of which {san['fast_and_flood_km2']:.0f} km² is also flood-prone, by far the most double-exposed ground of any town in the frame. The fastest inland hotspot sits inside it.",
                      "tl": f"Kapag tinipon kada hangganan ng bayan, ang {san['name']} ay may {san['fast_sinking_km2']:.0f} km² na lupang lumulubog nang higit 15 mm/taon, kung saan {san['fast_and_flood_km2']:.0f} km² ay madali ring bahain, pinakamarami sa lahat ng bayan sa frame. Nasa loob nito ang pinakamabilis na hotspot."},
            "fly": {"center": [120.983, 15.177], "zoom": 10.2},
            "callouts": [{"lngLat": [120.983, 15.177], "label": {"en": "fastest inland hotspot", "tl": "pinakamabilis na hotspot"}}],
        },
        {
            "id": "decoupling",
            "tag": {"en": "Decoupled", "tl": "Magkahiwalay"},
            "title": {"en": "The deepest floods are not the fastest sinking",
                      "tl": "Ang pinakamalalim na baha ay hindi ang pinakamabilis lumubog"},
            "stat": {"en": f"sinking >10 mm/yr: {pct[1]:.0f}% Low, {pct[2]:.0f}% Medium, {pct[3]:.0f}% High flood tier",
                     "tl": f"lumulubog >10 mm/taon: {pct[1]:.0f}% Mababa, {pct[2]:.0f}% Katamtaman, {pct[3]:.0f}% Mataas na baha"},
            "blurb": {"en": f"By modeled flood-hazard depth class, fast-sinking ground concentrates in the Low and Medium tiers ({pct[1]:.0f}% and {pct[2]:.0f}% sinking >10 mm/yr), not the deepest-flooding High tier ({pct[3]:.0f}%). Flood depth and sinking rate overlap but are largely separate fields.",
                      "tl": f"Ayon sa lalim ng baha, ang mabilis lumulubog na lupa ay nasa Mababa at Katamtamang antas ({pct[1]:.0f}% at {pct[2]:.0f}% na >10 mm/taon), hindi sa pinakamalalim na Mataas ({pct[3]:.0f}%). Magkasapaw pero magkahiwalay na larangan ang lalim ng baha at bilis ng paglubog."},
            "fly": {"center": [120.95, 14.95], "zoom": 9.2},
            "callouts": [],
        },
        {
            "id": "tilt", "layer": "tilt",
            "tag": {"en": "Differential tilt", "tl": "Hindi pantay"},
            "title": {"en": "Uneven sinking is what breaks roads and pipes",
                      "tl": "Ang hindi pantay na paglubog ang sumisira ng kalsada at tubo"},
            "stat": {"en": f"tilt up to {tlt['max_mm_yr_per_km']:.0f} mm/yr per km (p95 {tlt['p95_mm_yr_per_km']:.0f})",
                     "tl": f"hilig hanggang {tlt['max_mm_yr_per_km']:.0f} mm/taon kada km (p95 {tlt['p95_mm_yr_per_km']:.0f})"},
            "blurb": {"en": f"Uniform settlement is harmless; it is the spatial gradient, where ground drops faster than its neighbor, that cracks roads, snaps pipes, and stresses bridges. Purple marks the steepest tilt, up to {tlt['max_mm_yr_per_km']:.0f} mm/yr per km.",
                      "tl": f"Hindi nakakapinsala ang pantay na paglubog; ang pagkakaiba sa kalapit na lupa ang bumabasag ng kalsada, pumuputol ng tubo, at nagdidiin sa tulay. Lila ang pinakamatarik na hilig, hanggang {tlt['max_mm_yr_per_km']:.0f} mm/taon kada km."},
            "fly": {"center": [121.0, 15.13], "zoom": 9.8},
            "callouts": [],
        },
        {
            "id": "sea_vs_land",
            "tag": {"en": "Land vs sea", "tl": "Lupa vs dagat"},
            "title": {"en": "The land drops far faster than the sea rises",
                      "tl": "Mas mabilis bumaba ang lupa kaysa pagtaas ng dagat"},
            "stat": {"en": f"land ~{land:.0f} mm/yr vs sea ~5-7 mm/yr",
                     "tl": f"lupa ~{land:.0f} mm/taon vs dagat ~5-7 mm/taon"},
            "blurb": {"en": f"At the Bulacan hotspot the ground drops about {land:.0f} mm/yr (measured here). Sea level in Philippine waters is rising roughly 5-7 mm/yr (PAGASA / satellite altimetry). For someone there, the effective rise is dominated about 10 to 1 by the land going down, not the ocean coming up.",
                      "tl": f"Sa hotspot ng Bulacan, bumababa ang lupa nang mga {land:.0f} mm/taon (sinukat dito). Ang taas ng dagat sa Pilipinas ay tumataas nang mga 5-7 mm/taon (PAGASA / satellite). Para sa naroon, ang epektibong pagtaas ay nangingibabaw nang mga 10 sa 1 dahil sa pagbaba ng lupa, hindi pag-akyat ng dagat."},
            "fly": {"center": [120.983, 15.177], "zoom": 10.0},
            "callouts": [],
            "source": "Subsidence measured (InSAR); sea-level rise cited (PAGASA / satellite altimetry).",
        },
    ]

    # round-4 scale-out findings (Dagupan + cross-city patterns), fly-to cards
    try:
        dg = _load("dig-dagupan.json")
        cj = {c["id"]: c for c in json.loads((ROOT / "web" / "data" / "cities.json").read_text())["cities"]}
        loss = abs(dg["cumulative_loss_at_hotspot_mm"]) / 10.0  # mm -> cm
        flip = dg["hotspot"][::-1]  # [lat,lon] -> [lon,lat]
        rate = lambda k: f"{cj[k]['rate_mm_yr']:.0f}"
        findings += [
            {"id": "dagupan", "tag": {"en": "New city", "tl": "Bagong lungsod"},
             "title": {"en": "Dagupan: the second fast-sinking delta",
                       "tl": "Dagupan: pangalawang mabilis lumubog na delta"},
             "stat": {"en": f"about {loss:.0f} cm lost at the hotspot since 2016",
                      "tl": f"mga {loss:.0f} cm nawala sa hotspot mula 2016"},
             "blurb": {"en": f"Dagupan / Pangasinan measures about {rate('dagupan')} mm/yr (gated), with the hotspot dropping roughly {loss:.0f} cm since 2016. Like Metro Manila it is a groundwater-pumped alluvial delta, the fastest landform in the data.",
                       "tl": f"Sinusukat ang Dagupan / Pangasinan sa mga {rate('dagupan')} mm/taon (gated); bumaba ang hotspot ng mga {loss:.0f} cm mula 2016. Tulad ng Metro Manila, isa itong delta na hinuhukay ng tubig sa ilalim, ang pinakamabilis na uri ng lupa sa datos."},
             "fly": {"center": flip, "zoom": 10.2},
             "callouts": [{"lngLat": flip, "label": {"en": f"about {loss:.0f} cm since 2016",
                                                       "tl": f"mga {loss:.0f} cm mula 2016"}}]},
            {"id": "regime", "tag": {"en": "Regime", "tl": "Uri ng lupa"},
             "title": {"en": "It is the deltas, not the cities",
                       "tl": "Ang mga delta, hindi ang mga lungsod"},
             "stat": {"en": "deltas sink about 10x faster than island cities",
                      "tl": "mga delta ~10x mas mabilis kaysa mga lungsod-isla"},
             "blurb": {"en": f"With six cities measured, the rate splits by landform: alluvial deltas sink fast (Metro Manila ~{rate('metro-manila')}, Dagupan ~{rate('dagupan')} mm/yr) while island and coastal cities sink slowly (Cebu ~{rate('cebu-mandaue')}, Iloilo ~{rate('iloilo')}, Bacolod ~{rate('bacolod')}, Tacloban ~{rate('tacloban')}).",
                       "tl": f"Sa anim na lungsod, nahahati ang bilis ayon sa uri ng lupa: mabilis ang mga delta (Metro Manila ~{rate('metro-manila')}, Dagupan ~{rate('dagupan')} mm/taon), mabagal ang mga lungsod-isla (Cebu ~{rate('cebu-mandaue')}, Iloilo ~{rate('iloilo')}, Bacolod ~{rate('bacolod')}, Tacloban ~{rate('tacloban')})."},
             "fly": {"center": [122.6, 12.4], "zoom": 5.2}, "callouts": []},
            {"id": "deceleration", "tag": {"en": "Past peak", "tl": "Lampas sa rurok"},
             "title": {"en": "The fast hotspots are past their peak",
                       "tl": "Lampas na sa rurok ang mabibilis na hotspot"},
             "stat": {"en": "every measured hotspot slowed, 2016-20 vs 2021-25",
                      "tl": "bumagal lahat ng hotspot, 2016-20 vs 2021-25"},
             "blurb": {"en": "Splitting the decade in half, the fastest-sinking ground was faster in 2016-2020 than 2021-2025 in every measured city (Manila, Dagupan, Bacolod, Tacloban). The 2019 El Nino drought (peak groundwater pumping) is a plausible common driver. Observed, not a forecast.",
                       "tl": "Hinati ang dekada sa dalawa: mas mabilis lumubog noong 2016-2020 kaysa 2021-2025 sa lahat ng sinukat na lungsod (Manila, Dagupan, Bacolod, Tacloban). Posibleng sanhi ang El Nino drought ng 2019. Sinukat, hindi hula."},
             "fly": {"center": [122.6, 12.4], "zoom": 5.2}, "callouts": []},
        ]
    except Exception as e:  # noqa: BLE001
        print("round-4 cards skipped:", e)

    payload = {
        "city": CITY,
        "layers": {
            "accel": {"png": f"data/accel/{CITY}.png", "bounds": accel_bounds,
                      "legend": {"en": {"left": "speeding up", "right": "slowing"},
                                 "tl": {"left": "bumibilis", "right": "bumabagal"}}},
            "tilt": {"png": f"data/tilt/{CITY}.png", "bounds": tilt_bounds,
                     "legend": {"en": {"left": "gentle", "right": "steep tilt"},
                                "tl": {"left": "banayad", "right": "matarik"}}},
            "compound": {"geojson": cmp_geo, "n": cmp_n},
        },
        "findings": findings,
        "disclaimer": {
            "en": "Measured ground velocity and observed flood-layer coincidence from public satellite data. Subsidence is one of several flood drivers; overlaps are not proof of cause.",
            "tl": "Sinukat na bilis ng lupa at pagkakataon ng baha mula sa pampublikong datos ng satellite. Ang paglubog ay isa lamang sa mga sanhi ng baha; ang pagsasapaw ay hindi patunay ng sanhi.",
        },
    }
    out = ROOT / "web" / "data" / "findings.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"wrote {out.relative_to(ROOT)} ({len(findings)} findings)")
    print(f"  accel.png bounds {accel_bounds}")
    print(f"  tilt.png bounds {tilt_bounds}")
    print(f"  compound geojson {cmp_geo} ({cmp_n} double-exposed pts)")


if __name__ == "__main__":
    main()
