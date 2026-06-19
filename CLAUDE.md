# sinkmap.ph (repo: sinkmap-ph) - working notes

Civic-tech tool: land-subsidence InSAR map of PH cities (mm/yr, 2016-2026),
overlaid on recent flood extents. Sibling to shake-exposure-ph (lindol.ph);
mirror its layout and conventions. Domain sinkmap.ph. Born 2026-06-17 from the
"detect the invisible" remote-sensing brainstorm.

## Stance (locked, non-negotiable)

SUBSIDENCE RATE only. The map shows measured ground velocity (mm/yr) and observed
flood coincidence. No per-building flood/damage verdict, no blame, no forecast.
Correlation, not causation: subsidence is one flood driver among rainfall,
drainage, tides, reclamation, sea level. Hero is a declarative measurement, never
a takedown, and never a "vs published figure X" delta in the hero (other figures
go in a neutral references list). Positive framing (say what each surface IS).
Plain English, short sentences, no em-dashes, no AI-jargon, no eng-bro verbs.
Public-record disclaimer block on README and the methodology page. Compute before
narrating: no subsidence number appears anywhere until it is actually computed
and gated.

## Layout

- `pipeline/insar/` - search.py (ASF stack, no auth), submit_hyp3.py (SBAS ->
  HyP3, needs Earthdata), velocity.py (MintPy cfg + LOS->vertical), validate.py
  (GO/NO-GO gate vs published anchor).
- `pipeline/cities.json` + `aoi.py` - AOI registry, source of truth (bbox, tier,
  regime, published rate). Edit the JSON, not the code.
- `pipeline/_gee_init.py` - Earth Engine auth for the flood pillar only (personal
  service account; never a work GCP project).
- `pipeline/flood/`, `pipeline/overlay/` - Phase 2.
- `web/` - static MapLibre/PMTiles map; serve.py is Range-capable (port 8788).
- `docs/planning/` - the locked spec (SCOPE, CITIES, METHOD-decomposition,
  BUILD-PROMPT). Read these before changing direction; do not re-derive.

## Decisions locked (2026-06-17)

- HyP3 (ASF) + MintPy for InSAR. NOT LiCSAR/LiCSBAS (no PH frames; LiCSAR is
  Alpine-Himalayan only). HyP3 free 8,000 credits/month, Earthdata login.
- 2016-2026 (10yr), quarterly subsample (~40 scenes/AOI). Verified: Metro Manila
  descending = relative orbit 32, 325 scenes, frames 540-546, 2016-01..2025-12.
- v1 = descending LOS -> pseudo-vertical via cos(incidence), vertical-dominant
  assumption stated. Ascending+descending decomposition is v2 / Baguio only;
  it doubles HyP3 credits per AOI. See docs/planning/METHOD-decomposition.md.
- Validation anchors (Aslan et al. 2024): Metro Manila/Bulacan ~109, Davao 38,
  Legazpi 29, Cebu/Mandaue 11, Iloilo 9 mm/yr. Gate = reproduce within factor-of-2.

## Commands

```bash
make venv                                 # 3.9 venv + Phase 0 deps
make search AOI=metro-manila              # verify the S1 stack (no auth)
make dry-run AOI=metro-manila             # SBAS pair plan + credit note
make validate AOI=metro-manila VALUE=-105 # gate check (or RASTER=...)
make test                                 # pytest (Phase 0 math + registry)
make serve                                # Range-capable dev server, web/
```

Python is 3.9 here: `from __future__ import annotations` everywhere; no runtime
`X | Y` unions outside annotations (matches shake-exposure-ph).

## Gotchas inherited from lindol (do not relearn)

- PMTiles needs HTTP Range; serve via web/serve.py, never bare http.server.
- Aggregate per polygon, never per municipality name (PH names repeat across
  provinces).
- Overpass needs a User-Agent and `out center;`.
- CDN scripts in index head carry SRI hashes; recompute on version bump.
- agent-browser e2e: poll `window.__diag.ready` via eval; object-literal args do
  not survive eval; map style has no glyphs endpoint (labels are HTML markers).
- Pin committed dataset values in e2e as intentional regression pins; update with
  the data, never loosen.

## Phase 0 gate (the make-or-break)

One Metro Manila / Bulacan AOI end to end: search -> HyP3 SBAS -> download ->
MintPy SBAS -> LOS velocity -> cos(incidence) vertical -> validate against the
~109 mm/yr anchor (factor-of-2 band). GO/NO-GO before scaling. The HyP3 step
needs an Earthdata login and queues 1-7 days; MintPy needs a conda install and
10-20h of tuning (unwrapping, coherence, reference point on stable ground).

## Conventions

- Commits: simple messages, no `feat:`/`fix:` prefixes, no AI attribution.
- No em-dashes, no AI-jargon in any user-visible copy.
- New numbers need a source or are not shown.
