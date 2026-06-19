# Subsidence-PH - project scope (v1, 2026-06-17)

Working name only. Final name TBD pending conflict-check (candidates: lubog-ph, sink-ph, ground-ph). Project home: ~/Desktop/subsidence-ph/.

## One-line thesis

Metro Manila and other Philippine cities are sinking, measured from space with Sentinel-1 InSAR time-series, and the fastest-sinking ground coincides with where recent floods hit hardest. Subsidence is a hidden multiplier of the flood problem that drainage and flood-control spending does not touch.

## Framing (neutral, per research-tone rule)

Hero is a declarative measurement: "Ground is subsiding up to ~N mm/yr in [areas], 2017-2026, from Sentinel-1 InSAR." Method on a methodology page. The flood layer is presented as observed spatial coincidence, with an explicit disclaimer that subsidence is one of several flood drivers and correlation is not causation. No DPWH-takedown headline, no "wasted billions" hero. The data carries the point.

## What gets measured / detected

- Vertical ground velocity (mm/yr) across each AOI, from a Sentinel-1 SLC stack (2017-2026) processed to an SBAS/time-series displacement field.
- Per-pixel displacement time-series (not just a single rate) so the deliverable can show the sinking accelerating over the period.
- Recent flood extents for 2-3 major events, derived from Sentinel-1 SAR (pre vs post water masking) and cross-checked against Copernicus GFM.
- Spatial correlation between subsidence hotspots and (a) recent flood extents and (b) the Project NOAH flood-prone baseline.

## Pillars

### A. Subsidence engine (the hard core)

- Pipeline: ASF HyP3 on-demand Sentinel-1 InSAR (SBAS multi-burst stack, free 8,000 credits/month on an Earthdata login) -> MintPy for time-series inversion -> vertical velocity raster. LiCSAR/LiCSBAS is NOT usable (no PH frames). Source: https://hyp3-docs.asf.alaska.edu/guides/insar_product_guide/ , https://github.com/insarlab/MintPy
- Why this is feasible at all: cities are high-coherence for InSAR (buildings are persistent scatterers), so urban subsidence is one of the cleaner InSAR targets.
- Line-of-sight to vertical: LOCKED for v1. Descending-track LOS converted to pseudo-vertical via cos(incidence), stating the vertical-dominant assumption (valid for aquifer/delta/reclamation subsidence). Full ascending+descending decomposition is a v2 refinement for fault-adjacent AOIs and is required only for slope/landslide cases (Baguio). Full rationale and the cost tradeoff in METHOD-decomposition.md.
- Reference point: anchor the stack on stable bedrock ground (e.g., higher-elevation Rizal/Antipolo) so rates are relative to something not moving.

### B. Validation (Metro Manila first)

- No public downloadable PH subsidence raster exists to diff against. Validate against published numbers and points instead:
  - Reproduce the known Bulacan / CAMANAVA hotspot magnitude (~100-125 mm/yr) and location reported in the 2014-2020 literature. Agreement in sign, location, and order of magnitude is the pass condition.
  - Optional point check: NAMRIA PAGeNet CORS GNSS stations give independent vertical rates where co-located with a coherent InSAR pixel.
- Validation is a GO/NO-GO gate: if Phase 0 cannot reproduce the documented Metro Manila / Bulacan hotspot, stop and reassess before scaling.

### C. Flood corroboration

- Recent flood extents (derive own, transparent + repeatable): Sentinel-1 GRD in GEE, VV/VH to dB, speckle filter, threshold + pre/post change detection, mask permanent water with JRC Global Surface Water. UN-SPIDER recipe: https://un-spider.org/advisory-support/recommended-practices/recommended-practice-google-earth-engine-flood-mapping
  - Target events: Typhoon Carina + habagat (Jul 2024, Metro Manila + Pampanga, Marikina overflow); Typhoon Kristine/Trami (Oct 2024, Bicol, Camarines Sur 36/37 cities); 2025 monsoon (Wipha/Co-may, Jul 2025).
  - Cross-check own masks against Copernicus Global Flood Monitoring (GFM) GeoTIFF for the same dates. https://docs.openeo.cloud/usecases/gfm/
- Flood-prone baseline: Project NOAH hazard polygons (5/25/100-yr return periods), downloadable as shapefile/PMTiles via the BetterGov data portal. https://data.bettergov.ph/datasets/22
- Correlation output: quantify overlap, e.g. "X% of high-subsidence area (> threshold mm/yr) falls inside flood-prone zones / observed flood extent," plus side-by-side maps. State it as coincidence with disclaimer.

### D. Web deliverable

- Reuse the shake-exposure-ph rendering stack: web map + PMTiles + the glow layer, plus building footprints (Overture / Microsoft Open Buildings, free for PH) for an exposure read (how many buildings sit on fast-sinking ground).
- Layers (toggle + time slider): subsidence velocity, displacement time-series animation, recent flood extents per event, NOAH flood-prone baseline, building exposure.
- Methodology page: full pipeline, assumptions (LOS->vertical, reference point), validation results, the correlation disclaimer.

## Phasing (de-risked)

- Phase 0 - spike + gate (~1 week, the make-or-break): one Metro Manila/Bulacan frame end to end through HyP3 + MintPy. Reproduce the documented ~100-125 mm/yr hotspot. GO/NO-GO before any further investment. This IS the "validate in Metro Manila" step and the technical de-risk in one.
- Phase 1: full Metro Manila + Bulacan + Pampanga velocity + displacement time-series + validation writeup.
- Phase 2: flood corroboration (derive event flood extents, NOAH baseline, overlay + correlation stats).
- Phase 3: tiered city rollout per CITIES.md. P1 = the four other published-rate metros (Davao, Legazpi, Cebu/Mandaue, Iloilo) for cheap validation; P2 = exploratory delta/flood cities (Dagupan, Butuan, Cotabato, Cagayan de Oro, General Santos, Tacloban, Bacolod, Naga-Bicol) for new measurements; P3 stretch = Baguio slope-motion showcase + Cavite uplift nuance.
- Phase 4: web map + methodology page + ship.

## Honest risks

- InSAR learning curve (MintPy: unwrapping, coherence thresholds, reference point) is the dominant risk. Mitigated by the Phase 0 gate. Budget 10-20h of reading before clean output.
- HyP3 credit quota (8,000/month) is tight for a large multi-year stack; one AOI at a time.
- LOS-to-vertical decomposition adds complexity; v1 may state the vertical-dominant assumption rather than do full ascending+descending decomposition.
- Flood correlation is coincidence, not proof of causation; subsidence is one driver among rainfall, drainage, tides, reclamation. Disclaimer is mandatory.
- AlphaEarth embeddings do NOT help here (annual, and subsidence needs interferometric phase). They are only useful for an optional land-cover context layer.

## Tech reuse

shake-exposure-ph (building footprints, PMTiles, glow rendering, web map), floodwatch-ph (flood arc + hazard layers), plot.ph (time-series viz), personal GEE service account (leaves-ph .ee-key.json, GCP poised-honor-217909) for the flood-extent derivation.

## Decisions locked (2026-06-17)

1. Extension cities: tiered list in CITIES.md (5 validation-anchor metros + up to 8 exploratory delta/flood cities + Baguio/Cavite stretch). Not just 2-3.
2. LOS vs vertical: v1 is descending-track LOS to pseudo-vertical via cos(incidence); decomposition deferred to v2 / Baguio. See METHOD-decomposition.md.
3. Time window: 2016-2026, a clean 10-year horizon, subsampled to ~quarterly (~40 scenes/AOI) to hold coherence and fit HyP3 credits while still showing non-linear acceleration.

## Still open

- Final project name (conflict-check first): lubog-ph, sink-ph, ground-ph, others.
- Exact Sentinel-1 frames/tracks per AOI (resolved in Phase 0 via ASF search API).
