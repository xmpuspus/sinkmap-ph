# sinkmap.ph

[![License: MIT (code) / CC-BY-4.0 (data)](https://img.shields.io/badge/license-MIT%20%2F%20CC--BY--4.0-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![InSAR: Sentinel-1 HyP3 + MintPy](https://img.shields.io/badge/InSAR-Sentinel--1%20HyP3%20%2B%20MintPy-success.svg)](docs/findings/metro-manila-v1.md)
[![Validated: 3 metros vs Aslan 2024](https://img.shields.io/badge/validated-3%20metros%20vs%20Aslan%202024-success.svg)](docs/findings/phase2-multicity.md)
[![e2e: 88 checks](https://img.shields.io/badge/e2e-88%20checks-success.svg)](tests/e2e.sh)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](README.md)

> **sinkmap.ph** is the measured record of how fast the ground is sinking under
> Philippine cities, from open Sentinel-1 satellite radar, 2016-2025, shown next to
> where the floods actually hit. Seven cities are measured across Luzon, the Visayas,
> and Mindanao. Three reproduce their published rates within a factor of two (Metro
> Manila/Bulacan ~72 mm/yr vs ~109, Cebu ~10 vs 11, Iloilo ~10 vs 9); four more are
> coverage-gated with no published anchor (Dagupan ~20, Cavite ~6, Bacolod ~4, Tacloban ~3).
> The fastest sinking in Metro Manila is **inland** in the Bulacan/Pampanga lowland,
> not the coast, and Dagupan has lost about 35 cm at its hotspot since 2016. A
> single-file MapLibre map carries a velocity layer, a 2016-2025 "watch it sink"
> slider, toggleable flood extents, a building-exposure read, a surprising-findings
> panel, and a methodology page, with the coincidence-not-causation disclaimer
> throughout.

[![sinkmap.ph walkthrough](docs/demo.gif)](https://sinkmap-ph.vercel.app)

<sub>Real recording of the live map ([sinkmap-ph.vercel.app](https://sinkmap-ph.vercel.app),
via `scripts/record_demo.py`): the nationwide overview, the surprising-findings panel
(the acceleration layer with on-map callouts), a measured-city card (Dagupan, ~20
mm/yr, coverage-gated), "watch it sink" accumulating 2016-2025 displacement on Metro
Manila (the readout climbs to ~325 mm), and a recent Sentinel-1 flood extent toggled
on. The apex **sinkmap.ph** goes live once its dot.ph A record points to Vercel.</sub>

**Status: validated, with a working map of seven cities.** Three metros reproduce
their published rates within a factor of two; four more (no published anchor) are
measured and coverage-gated, spanning Luzon, the Visayas, and Mindanao:

| City | Measured (2016-2025) | Published (Aslan 2024) |
| --- | --- | --- |
| Metro Manila / Bulacan | ~72 mm/yr | ~109 mm/yr |
| Cebu / Mandaue | ~10 mm/yr | 11 mm/yr |
| Iloilo | ~10 mm/yr | 9 mm/yr |
| Dagupan / Pangasinan | ~20 mm/yr (peak field ~35; ~35 cm lost since 2016) | no published rate |
| Bacolod / Negros | ~4 mm/yr | no published rate |
| Cavite coast (Manila Bay) | ~6 mm/yr (reclamation, peak ~17) | no published rate |
| Tacloban / Leyte | ~3 mm/yr (marginal coverage) | no published rate |

Dagupan, Cavite, Bacolod, and Tacloban have no Aslan anchor, so the map shows them with a
"measured (coverage-gated)" badge, not "validated". A scale-out feasibility scorer
(`scripts/feasibility.py`) ranks ~120 PH cities for the current method, and a burst-
InSAR test showed burst is 10x cheaper but cannot measure a regional subsidence
bowl from a single burst (Manila burst 7.6 vs GAMMA 72), so the scale-out stays on
full-scene GAMMA. See `docs/findings/`.

The fastest sinking in Metro Manila is inland in the Bulacan/Pampanga lowland
(around 15.18 deg N), consistent with the published maximum location, and it holds
up under a stable reference and a tropospheric correction. Cebu also shows a
localized faster-sinking cluster (~35 mm/yr) at the southern coast, consistent with
reclamation. Three cities (Legazpi, Davao, Cagayan de Oro) are **coherence-limited** over small
vegetated or upland areas and are reported as honest non-results, not forced
numbers; they would need persistent-scatterer InSAR or a tighter urban area.

Where the sinking ground meets flood-prone ground (NOAH 25-year hazard): in Metro
Manila 41% of high-subsidence ground is flood-prone against 8% of all measured
ground (about 5x); in Cebu 18% against 2% (about 9x); Iloilo shows no preferential
coincidence. Full write-ups in `docs/findings/`. The map is a single-file MapLibre
site with a velocity layer, a 2016-2025 "watch it sink" time slider, toggleable
flood extents, and a building-exposure read (OSM buildings on fast-sinking ground:
~1,900 in Metro Manila above 15 mm/yr, ~560 in Cebu, ~410 in Iloilo). A
**surprising-findings panel** flies to and overlays the computed patterns:
an acceleration map (the worst hotspot slowed from -96 to -79 mm/yr while a zone
6 km east doubled, and 294 km2 sped up vs 244 km2 slowed), a differential-tilt
layer (up to 70 mm/yr per km), the double-exposed buildings (46% of fast-sinking
buildings are also flood-prone), and the most-exposed town (San Miguel, Bulacan).
Every number is computed by `scripts/analysis.py` and baked into
`web/data/findings.json`, not hand-typed. `make serve`, then `web/index.html`.

## What this measures

This measures **subsidence rate**: how fast the ground is moving down, in mm/yr,
from interferometric phase. It does not predict which buildings will flood, does
not assign blame, and issues no per-building verdict. Where the sinking ground
meets a flood is a question for engineers and hydrologists on the ground. The map
shows the rate and where recent floods reached.

Subsidence is one driver of flooding among rainfall, drainage, tides,
reclamation, and sea-level rise. The flood overlay is shown as observed spatial
coincidence, not as proof of cause.

## What the radar actually shows

InSAR measures the *relative* vertical motion of ground that stays coherent between
satellite passes. Dense urban fabric (buildings, pavement) holds that coherence and
gives a clean rate; vegetation, open water, and steep terrain decorrelate. That
boundary is the honest core of this project:

- It works where the literature's fastest PH subsidence is, the flat dense Metro
  Manila / Bulacan / Pampanga lowland, and reproduces it (~72 mm/yr, inland). The
  peak location is reference-invariant, so the "inland, not coastal" finding holds
  regardless of the reference pixel.
- It is **coherence-limited** over the small vegetated Legazpi coastal area and the
  upland Davao AOI: too few coherent pixels for a trustworthy rate, so none is
  reported there rather than a forced number. The raw frames are fine; the AOI
  subsets decorrelate. They would need persistent-scatterer InSAR or a tighter
  urban area.
- Rates are relative (InSAR has no absolute datum on its own). The map colors each
  city relative to its own area median, so stable ground reads stable and only
  ground that is measurably moving is painted; the validation rates use a stable
  bedrock-piedmont reference. Both are stated in `docs/findings/`.
- The flood overlay **varies**: strong in Metro Manila and Cebu (fast-sinking ground
  several times more likely to be flood-prone than background), absent in Iloilo.
  Not every city fits the thesis, and the map says so.

## What's in this repo

- **`pipeline/insar/`**: the Phase 0 InSAR pipeline. `search.py` finds the
  Sentinel-1 SLC stack for an AOI from the ASF archive (public, no auth) and
  picks one coherent descending track, quarterly-subsampled. `submit_hyp3.py`
  builds a short-baseline (SBAS) pair network and submits it to ASF HyP3 for
  on-demand InSAR (needs an Earthdata login). `velocity.py` writes the MintPy
  config and converts the resulting line-of-sight velocity to pseudo-vertical
  via `cos(incidence)`. `validate.py` is the GO/NO-GO gate against the published
  anchor.
- **`pipeline/cities.json` + `pipeline/aoi.py`**: the AOI registry. The source of
  truth for each city's bbox, dry-run tier, physical regime, and the published
  subsidence rate used for validation.
- **`pipeline/flood/`**, **`pipeline/overlay/`**: `flood_extent.py` derives a
  Sentinel-1 pre/post flood extent in Earth Engine and exports it as a map overlay;
  `overlap.py` rasterizes NOAH flood-hazard onto the velocity grid and computes the
  subsidence x flood-zone statistic with the coincidence disclaimer baked in.
- **`scripts/`**: build the web layers from the MintPy outputs. `make_web_layers.py`
  renders the velocity + "watch it sink" frames and `cities.json`; `make_flood_layers.py`
  exports the flood overlays; `make_exposure.py` counts OSM buildings on fast-sinking
  ground; `record_sink_lapse.py` records the demo GIF from the live map.
- **`web/`**: the single-file MapLibre map (`index.html`) with the velocity layer,
  the 2016-2025 time slider, flood toggles, building-exposure glow, EN/TL copy, and
  `methodology.html`. `serve.py` is Range-capable for local serving.
- **`docs/findings/`**: the per-phase write-ups (Metro Manila v1, the multi-city
  results, the flood overlay), separating verified results from provisional ones.
- **`docs/planning/`**: the locked spec (`SCOPE.md`, `CITIES.md`,
  `METHOD-decomposition.md`, `BUILD-PROMPT.md`).
- **`tests/`**: pytest over the LOS->vertical math, the GO/NO-GO gate band, the SBAS
  pairing, and the AOI registry invariants; plus `e2e.sh`, a 88-check behavioral
  suite that drives the live map (loading, the sink-lapse slider/play, the flood
  toggles, exposure, place cards, the surprising-findings panel with its
  acceleration / tilt / compound-exposure layers and callouts, EN/TL). Run
  `make e2e` (or `make e2e BASE=https://sinkmap-ph.vercel.app`).

## What this is not

- Not a flood forecast or an evacuation tool. It is a slow-measurement map of
  ground motion, not a real-time warning.
- Not a per-building risk verdict. Subsidence rate is a regional field; what
  happens to any one structure is an engineering question.
- Not a damage map. It measures the ground moving, not buildings failing.
- Not a claim of cause. Subsidence coinciding with floods is shown as
  coincidence; rainfall, drainage, tides, and sea level all contribute.

## Method, in one line

Descending-track Sentinel-1 LOS velocity from an SBAS time-series, converted to
vertical under a stated vertical-dominant assumption (valid for aquifer, delta,
and reclamation subsidence). Full ascending+descending decomposition is reserved
for slope-motion cases. See `docs/planning/METHOD-decomposition.md`.

## Quickstart (Phase 0, runnable now)

```bash
make venv

# Verify the Sentinel-1 stack for an AOI (no credentials needed):
make search AOI=metro-manila

# Inspect the SBAS pair plan and credit footprint (no submission):
make dry-run AOI=metro-manila

# Submit to HyP3 (needs an Earthdata login in ~/.netrc):
.venv/bin/python -m pipeline.insar.submit_hyp3 --aoi metro-manila

# After MintPy produces a vertical velocity raster, run the gate:
make validate AOI=metro-manila VALUE=-105   # or RASTER=path/to/vertical.npy

make test
```

Build the web layers from the MintPy outputs and serve the map locally:

```bash
# render the velocity + sink-lapse PNGs and cities.json (MintPy env, has gdal):
~/anaconda3/envs/sinkmap-mintpy312/bin/python scripts/make_web_layers.py
# count OSM buildings on fast-sinking ground (exposure glow + place-card stat):
~/anaconda3/envs/sinkmap-mintpy312/bin/python scripts/make_exposure.py
# derive the flood-extent overlays (GEE, personal key):
SINKMAP_EE_KEY=~/Desktop/leaves-ph/.ee-key.json .venv/bin/python scripts/make_flood_layers.py

make serve     # Range-capable server on :8788, then open web/index.html
make e2e       # 88-check behavioral suite against the running map
```

![sinkmap.ph watching Metro Manila sink, 2016-2025](docs/sink-lapse.gif)

*Real recording of the map (`scripts/record_sink_lapse.py`): the Bulacan/Pampanga
hotspot accumulating ground motion across the decade.*

## Roadmap (honest "not yet")

- **Richer building exposure.** The current exposure read uses OSM footprints via
  Overpass; a complete count would use Microsoft / Google Open Buildings or Overture
  for PH (denser coverage than OSM in some areas).
- **Legazpi and Davao.** Coherence-limited under this areal SBAS method; would need
  persistent-scatterer InSAR or a tighter urban AOI.
- **Metro Manila coastal CAMANAVA.** The current grid covers the inland Bulacan belt;
  full coastal coverage needs additional southern Sentinel-1 frames.
- **Exploratory cities** (Dagupan, Butuan, Cotabato, and others with no published
  rate) and the **ascending+descending decomposition** remain future work.

## Data and responsible use

All inputs are publicly licensed (Copernicus Sentinel-1, NASA/ASF, ESA, JRC,
Project NOAH, Microsoft/Google/Overture building footprints). Code is MIT; derived
data is CC-BY-4.0. Full attribution in `NOTICE`.

> All data sourced from public records. sinkmap.ph computes statistical
> indicators only. Specific allegations, if any, require independent
> investigation and corroboration.
