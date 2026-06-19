# sinkmap.ph

The measured record of how the ground under Philippine cities is sinking, built
from open satellite data, shown next to where the floods actually hit. It uses
Sentinel-1 InSAR time-series to map land-subsidence rate (mm/yr) over 2016-2026,
validates against published rates for Metro Manila and other metros, and
overlays recent flood extents to show where the sinking and the flooding line up.
Repository: sinkmap-ph.

**Status: Phase 0 (gate not yet passed).** The InSAR pipeline is built and the
Sentinel-1 stack is verified: a 325-scene descending stack (relative orbit 32,
frames 540-546) covers Metro Manila and Bulacan continuously from 2016-01-06 to
2025-12-26. No subsidence rate is published here yet. The Phase 0 gate, running
that stack through HyP3 + MintPy and reproducing the documented ~100-125 mm/yr
Bulacan/CAMANAVA hotspot, is the next step and decides whether the project
scales. Numbers appear only after the gate passes.

## What this measures

This measures **subsidence rate**: how fast the ground is moving down, in mm/yr,
from interferometric phase. It does not predict which buildings will flood, does
not assign blame, and issues no per-building verdict. Where the sinking ground
meets a flood is a question for engineers and hydrologists on the ground. The map
shows the rate and where recent floods reached.

Subsidence is one driver of flooding among rainfall, drainage, tides,
reclamation, and sea-level rise. The flood overlay is shown as observed spatial
coincidence, not as proof of cause.

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
- **`pipeline/flood/`**, **`pipeline/overlay/`**: the flood-extent derivation
  (Sentinel-1 in Earth Engine) and the subsidence x flood correlation (Phase 2).
- **`web/`**: the static MapLibre + PMTiles map (`serve.py` is Range-capable for
  local PMTiles).
- **`docs/planning/`**: the locked spec (`SCOPE.md`, `CITIES.md`,
  `METHOD-decomposition.md`, `BUILD-PROMPT.md`).

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

## Data and responsible use

All inputs are publicly licensed (Copernicus Sentinel-1, NASA/ASF, ESA, JRC,
Project NOAH, Microsoft/Google/Overture building footprints). Code is MIT; derived
data is CC-BY-4.0. Full attribution in `NOTICE`.

> All data sourced from public records. sinkmap.ph computes statistical
> indicators only. Specific allegations, if any, require independent
> investigation and corroboration.
