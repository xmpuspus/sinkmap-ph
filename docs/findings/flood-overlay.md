# Subsidence x flood overlay (Phase 3, 2026-06-20)

Observed spatial coincidence between fast-sinking ground and flood-prone ground.
This is correlation, NOT causation: subsidence is one of several flood drivers
(rainfall, drainage capacity, tides, reclamation, sea-level rise). The overlap
is reported with that disclaimer everywhere it appears.

## Verified (Metro Manila / Bulacan-Pampanga belt)

Subsidence layer: the v1 vertical velocity raster (vertical.tif, EPSG:32651,
80 m, reliable pixels only). Flood-prone layer: Project NOAH 25-year flood-hazard
polygons for Bulacan + Pampanga (Var depth class 1 Low / 2 Medium / 3 High),
rasterized onto the subsidence grid. "High subsidence" = sinking faster than
20 mm/yr.

- High-subsidence area: 35.5 km2. Flood-prone area (Var>=2, >=0.5 m, 25-yr)
  within the grid: 83.0 km2. Overlap: 14.5 km2.
- **41% of high-subsidence ground lies in flood-prone (>=0.5 m, 25-yr) zones**,
  vs **8.4%** of all reliable ground in the same frame. Fast-sinking ground is
  about 5x more likely to be flood-prone than the background rate.
- Robust to choices: at a stricter 40 mm/yr subsidence cut, 42% (essentially
  unchanged); against any-depth hazard (Var>=1), 63.5% vs 11.9% background.
- Mean subsidence inside the coinciding zone: -40.5 mm/yr.
- Output: web/data/overlay/metro-manila-25yr.json (carries the disclaimer).

## Derived Sentinel-1 event flood extents (observed, independent of InSAR)

Pre/post VH backscatter change detection in Earth Engine (UN-SPIDER recipe),
permanent-water (JRC) and slope masked. Areas are calibration-stage:

- Typhoon Carina + habagat (Jul 2024, Metro Manila): 12.1 km2.
- 2025 SW monsoon (Wipha/Co-may, Jul 2025, Metro Manila): 12.4 km2.
- Typhoon Kristine/Trami (Oct 2024, Bicol): 1.5 km2 -- CAVEAT: only 2 Sentinel-1
  scenes in the post window, so the peak extent is under-sampled; treat as a
  lower bound, not the full flood.

## Provisional / caveats (state on the methodology page)

- NOAH hazard is a MODELED return-period flood-prone layer, not an observed
  extent. The headline statistic uses it as the flood-prone baseline.
- The NOAH Bulacan/Pampanga layers cover lat <= ~15.27 N; the subsidence grid's
  far-north fringe (15.28-15.33 N) is outside them (Nueva Ecija/Tarlac layers
  exist if that fringe is needed). The subsidence peak (15.177 N) is covered.
- The S1 event-extent km2 are change-detection starting points (fixed dB
  thresholds), sensitive to overpass timing; the spatial pattern matters more
  than the absolute area.
- Subsidence rate is relative to the assumed-stable Sierra Madre piedmont
  reference (see metro-manila-v1.md).

## Pending (gated on Phase 2 HyP3 + MintPy)

Per-city overlap for Davao, Legazpi, Cebu/Mandaue, Iloilo runs once each city's
v1 subsidence raster exists. NOAH hazard for those provinces is already fetched
(data/hazard/). Same statistic, same disclaimer.
