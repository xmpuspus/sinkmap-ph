# Metro Manila v1 subsidence finding (2026-06-20)

Land subsidence rate for the Metro Manila + Bulacan + Pampanga belt, measured
from Sentinel-1 descending InSAR (77 SBAS pairs, 2016-2025), MintPy time-series,
converted to pseudo-vertical under the vertical-dominant assumption. This is the
v1 hardening of the Phase 0 gate result, with the qualifiers from v0 addressed.

## Verified

- Max subsidence: **72.1 mm/yr** (on reliable pixels: maskTempCoh, edge-excluded;
  72.6 mm/yr unmasked over the full grid). Relative to a stable reference on the
  Sierra Madre piedmont.
- Gate vs published anchor (Aslan et al. 2024, ~109 mm/yr max for Metro
  Manila/Bulacan): **ratio 0.66 -> GO** (factor-of-2 band). Correct sign,
  location, and order of magnitude.
- Location of the fastest-sinking ground: **lat 15.177, lon 120.983**, the inland
  Bulacan/Pampanga/Candaba lowland (groundwater-extraction delta). The worst-0.5%
  subsidence cluster is 100% inland (lat >= 15.0), median 15.168 N; 0% on the
  coast. The peak is NOT the coastal CAMANAVA zone.
- The inland peak **survived the v1 hardening**: a verified-stable bedrock-piedmont
  reference (replacing the v0 auto pixel that sat on low alluvium) and a
  tropospheric correction (replacing v0's no correction). It did not relocate.
- Robustness: the peak **location is reference-invariant** (the reference choice
  only shifts the whole field by a constant; the spatial pattern that defines the
  hotspot does not move). So "fastest subsidence is inland Bulacan/Pampanga" holds
  regardless of the exact reference pixel.

## Method (changes from v0)

- Reference point: `mintpy.reference.yx = 600, 376` = lat 14.8996, lon 121.1620,
  elevation 298 m on the Sierra Madre piedmont, coherence 0.93, inside
  maskConnComp (the unwrapping-reliability mask `reference_point` enforces), 5x5
  neighborhood fully in-mask. The auto minCoherence pixel (~156 m alluvium) and a
  higher 803 m bedrock pixel (masked OUT, forested -> unreliable unwrapping) were
  both rejected. 298 m is the highest defensibly-stable ground InSAR still
  unwraps here.
- Troposphere: `mintpy.troposphericDelay.method = height_correlation` (polyOrder 1,
  looks 8, minCorrelation 0.1). Empirical phase-vs-elevation fit; needs no CDS/ERA5
  key. v0 ran no tropospheric correction.
- Grid: EPSG:32651 (UTM 51N), 80 m, lat 14.728..15.331, lon 120.878..121.189.

## Provisional / qualifiers (state on the methodology page)

- Absolute magnitude is relative to an *assumed*-stable piedmont reference; no
  co-located GNSS/CORS benchmark is available on stable ground inside the frame to
  pin the absolute datum. The 72 mm/yr is "relative to the Sierra Madre piedmont."
- `height_correlation` removes the topography-correlated phase component; in the
  flat delta the subsidence is not topo-correlated so the risk of removing real
  signal is low, but the rate may be slightly conservative, and elevation-correlated
  motion near the eastern fringe could be partly absorbed. Turbulent wet-season
  tropospheric noise is not removed by this method.
- Coastal CAMANAVA / Manila Bay (~14.7-14.9 N) sits at the masked southern edge of
  this grid (low temporal coherence + edge), so this v1 measures the inland Bulacan/
  Pampanga belt well but does NOT characterize the coastal hotspot. Capturing it
  needs S1 frames extending further south (a v1.1 item), not a config change.
- Single descending track; vertical-dominant assumption (valid for aquifer/delta
  subsidence; see docs/planning/METHOD-decomposition.md). No asc+desc decomposition.

## Artifacts

- `data/insar/metro-manila/vertical.tif` (georeferenced, masked, UTM 51N) and
  `vertical.npy`.
- `data/insar/metro-manila/mintpy_run/velocity.h5` (LOS) + `timeseries.h5`.
- Config: `data/insar/metro-manila/sinkmap_metro-manila.txt`.
- Diagnosis notes: `tmp/phase1/{subset,reference,troposphere}.md`.
