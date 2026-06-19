# Build prompt: sinkmap.ph (end to end)

Paste this into a fresh session at ~/Desktop/subsidence-ph/ to build the project from empty repo to shipped site. It assumes the three spec docs already in this folder.

---

You are building **sinkmap.ph**, a civic-tech web map: the measured record of how the ground under Philippine cities is sinking, built from open satellite data, shown next to where the floods actually hit. It measures land-subsidence velocity (mm/yr) from Sentinel-1 InSAR time-series over 2016-2026, validates against published rates in Metro Manila and other metros, extends to exploratory cities, and overlays recent flood extents to show the spatial coincidence. Repo name: `sinkmap-ph`. Domain: `sinkmap.ph`.

## Read first (the spec is already written)

In this folder:
- `SCOPE.md` - the four pillars, phasing, the locked decisions (HyP3+MintPy InSAR, 2016-2026, LOS-only v1), honest risks.
- `CITIES.md` - the extension-city dry run: three physical regimes, the tiered city list, validation anchors, the processing/credit dry-run, sequence.
- `METHOD-decomposition.md` - the LOS vs vertical study and the v1 decision.

Do not re-derive these. Build to them.

## Clone the conventions from these repos (read them, mirror them)

- **`~/Desktop/shake-exposure-ph/` (lindol.ph) is the primary template.** Sinkmap is its sibling: a computed measurement plus a static MapLibre/PMTiles map, not a trained classifier. Mirror its layout (`pipeline/`, `web/` single-file frontend, `data/`, `scripts/`, `docs/`, `tests/`), its civic stance, its `web/serve.py` (PMTiles needs HTTP Range, stdlib http.server corrupts tiles), its `scripts/record_demo.py` + `scripts/record_lapse_demo.py` recording pattern, its `tests/e2e.sh` behavioral checks, its `window.__diag.ready` hook, its EN/TL copy dicts, its `og-card.png`, and its Vercel-Blob path for PMTiles over 100MB. Read its `CLAUDE.md` gotchas section in full and inherit every relevant one.
- **`~/Desktop/solar-map-ph/` (SolarMap.PH)** for README tone and structure (badge row, one-line hero blockquote, hero GIF with a real-recording caption that names the exact command, "What's in this repo" dir-by-dir, "What this is not", "Privacy and responsible use", the public-record disclaimer block), the `Makefile` + `pyproject.toml` + pinned `requirements.txt` + `CITATION.cff` + `MODEL_CARD.md` discipline, and the data-honesty stance in its `CLAUDE.md`.
- **`~/Desktop/leaves-ph/`** for the Earth Engine pipeline pattern and the personal GEE service-account wiring (`*_EE_KEY` env var pointing at the leaves-ph `.ee-key.json`, GCP project `poised-honor-217909`; SA-key-first with interactive fallback). Personal account only, never a work/Boost GCP project.

## Locked stance (non-negotiable, like lindol's EXPOSURE-only line)

- **SUBSIDENCE RATE only.** The map shows measured ground velocity (mm/yr) and observed flood coincidence. It does NOT predict which buildings will flood, does NOT assign blame, does NOT issue per-building verdicts. "What happens to any one place is a question for engineers and hydrologists on the ground."
- **Vertical-dominant assumption** stated plainly on the methodology page (descending-track LOS scaled by cos(incidence); see METHOD-decomposition.md).
- **Correlation, not causation.** Subsidence is one flood driver among rainfall, drainage, tides, reclamation, sea level. The flood overlay is shown as spatial coincidence with that disclaimer visible near the result.
- **Hero is a declarative measurement**, never a takedown: "The ground around [area] is subsiding up to N mm/yr, 2016-2026, from Sentinel-1 InSAR." No "DPWH wasted billions" framing. No "vs published figure X" deltas in the hero. Other figures go in a neutral references list.
- **Positive framing** (say what each surface IS). **Plain English, short sentences, no em-dashes, no AI-jargon, no eng-bro verbs.** Conservative civic-tech language throughout. Public-record disclaimer block on README and the About/methodology page.

## Repo layout to create (mirror lindol)

```
sinkmap-ph/
  README.md  CLAUDE.md  LICENSE(MIT)  NOTICE(data licenses)  CITATION.cff
  Makefile  pyproject.toml  requirements.txt(pinned)
  pipeline/
    insar/        # HyP3 submission + MintPy time-series -> velocity raster (per AOI)
    flood/        # GEE Sentinel-1 pre/post water-masking flood extents + GFM cross-check
    overlay/      # subsidence x flood-extent x NOAH-baseline correlation + building exposure
    cities.json   # AOI registry (bbox, track, published-rate anchor, tier) - source of truth
    run.py  paths.py
  web/
    index.html    # single-file vanilla JS, MapLibre GL + PMTiles, EN/TL dicts, __diag.ready
    methodology.html
    serve.py      # dev server WITH HTTP Range (port e.g. 8788)
    data/         # per-city velocity tiles, flood layers, exposure, cities.json mirror
    og-card.png   # 1200x630 real screenshot
  scripts/
    record_demo.py        # Playwright walkthrough -> webm -> docs/demo.gif (ffmpeg)
    record_sink_lapse.py  # "watch it sink": 2016-2026 displacement accumulating + flood events
  docs/           # demo.gif, sink-lapse.gif, methodology figures, verify/ screenshots
  tests/          # e2e.sh behavioral (agent-browser, __diag.ready), pytest for pipeline math
```

## Build order

**Setup (step 0).** Rename this folder to match the project: `mv ~/Desktop/subsidence-ph ~/Desktop/sinkmap-ph`, then `cd ~/Desktop/sinkmap-ph && git init`. The four spec docs (SCOPE/CITIES/METHOD/BUILD-PROMPT) stay in the repo as planning material (move them under `docs/planning/` once the layout exists). Then scaffold the layout below.

**Phase 0 - the gate (do this before anything else).** One Metro Manila / Bulacan AOI end to end: ASF Vertex SBAS search -> HyP3 on-demand InSAR (free 8,000 credits/month, Earthdata login) -> MintPy SBAS time-series -> descending-track LOS velocity -> cos(incidence) to pseudo-vertical. Must reproduce the documented ~100-125 mm/yr Bulacan/CAMANAVA hotspot in location and order of magnitude. GO/NO-GO. If it can't reproduce, stop and reassess the pipeline before scaling. Budget 10-20h on MintPy (unwrapping, coherence threshold, reference point on stable ground).

**Phase 1 - validation metros.** Run the four other published-rate metros (Davao 38, Legazpi 29, Cebu/Mandaue 11, Iloilo 9 mm/yr per Aslan et al. 2024). Each is a free validation check. Write the validation results into a methodology section.

**Phase 2 - flood corroboration.** In GEE, derive Sentinel-1 flood extents for Carina+habagat (Jul 2024), Kristine/Trami (Oct 2024), 2025 monsoon: VV/VH to dB, Refined Lee filter, pre/post change threshold, JRC permanent-water mask. Cross-check against Copernicus GFM GeoTIFF. Pull Project NOAH flood-hazard polygons (BetterGov data portal) as the baseline. Compute the overlay statistic ("X% of high-subsidence area sits inside flood-prone / observed-flood zones"). State it as coincidence with disclaimer.

**Phase 3 - exploratory cities + exposure.** Dagupan, Butuan, Cotabato, Cagayan de Oro, General Santos, Tacloban, Bacolod, Naga-Bicol (these have NO published rate; the build produces the first measurement, label them as such). Add a building-exposure read using Microsoft/Google Open Buildings or Overture footprints: how many buildings sit on fast-sinking ground (reuse the shake-exposure-ph PMTiles glow + place-card pattern).

**Phase 4 - frontend + ship.** Single-file `web/index.html`: MapLibre + PMTiles velocity layer (a diverging ramp, sinking vs stable vs uplift, so Cavite's uplift shows honestly), a **time slider** that animates the 2016-2026 displacement (the "watch it sink" view, modeled on lindol's "watch it grow"), recent flood-extent toggles, the NOAH baseline, the building-exposure glow, a place card per city/point answering in whole-band words, EN/TL copy, `window.__diag.ready`. Methodology page with full pipeline, the vertical-dominant assumption, validation results, error sources, and the correlation disclaimer. Record `docs/demo.gif` (walkthrough) and `docs/sink-lapse.gif` ("watch it sink") with the Playwright+ffmpeg scripts. Write the README (badges, hero GIF + real-recording caption naming the command, "What this measures", the locked stance, "What's in this repo", "What this is not", "Privacy and responsible use", disclaimer block, quickstart, methodology link). Then deploy.

## Demo GIF recipe (mirror shake-exposure-ph exactly)

Playwright async, headless chromium, `record_video_dir`, viewport ~1000x760. A `CHOREO` async-JS string drives the real map: wait for `window.__diag.ready===true`, then open the time slider and step the displacement frames holding each ~1.2s (the sink-lapse), or run the walkthrough (search a city, place card opens with its mm/yr rate, toggle the flood overlay, zoom to a building). Then ffmpeg webm -> gif (two-pass palette). Caption every GIF as a real recording and name the command, like lindol does. Real recordings only, never mockups.

## Deploy (mirror lindol's verified path)

- Vercel project, **rootDirectory = `web`**, git-connected to `github.com/xmpuspus/sinkmap-ph` so a push to main produces a production deploy. Verify `githubCommitSha == HEAD`.
- Velocity/flood PMTiles over GitHub's 100MB cap go to **Vercel Blob** (stable URLs via the @vercel/blob SDK with `addRandomSuffix:false`; the CLI ignores the flag). Frontend reads a `TILES_HOST` var, empty falls back to local.
- **sinkmap.ph apex** via dot.ph: dot.ph parks fresh apexes on ParkLogic, so set the A record to `76.76.21.21` (Vercel) and prove with `curl --resolve sinkmap.ph:443:76.76.21.21 https://sinkmap.ph/` before declaring it live. Never trust the local resolver. After deploy, fingerprint live content (a build-unique string), not just HTTP 200.

## Gotchas to inherit (from lindol CLAUDE.md, paid for already)

PMTiles needs HTTP Range (use `web/serve.py`, never bare http.server). Aggregate per polygon, never per municipality name (PH names repeat across provinces). Overpass needs a User-Agent and `out center;`. CDN scripts in index head carry SRI hashes; recompute on version bump. agent-browser e2e: poll `window.__diag.ready` via eval, object-literal args do not survive eval. Map style has no glyphs endpoint, so on-map labels are HTML markers not symbol layers. Pin committed dataset values in e2e as intentional regression pins; update with the data, never loosen.

## Data + licensing

Code MIT (`LICENSE`). Data CC-BY-4.0. `NOTICE` carries every source license (Copernicus Sentinel-1, ESA, JRC Global Surface Water, Project NOAH/UP, Microsoft/Google Open Buildings or Overture, Copernicus GFM, NASA/ASF HyP3). `CITATION.cff`. Public-record disclaimer block on README and methodology page. GEE auth via the personal leaves-ph service account only, never a work GCP project.

## Definition of done

Phase 0 hotspot reproduced and documented; at least Metro Manila + the four validation metros mapped with their rates cross-checked; flood overlay computed for the three recent events with the correlation statistic; single-file map deployed to sinkmap.ph with the time-slider sink-lapse, flood toggles, exposure glow, EN/TL, place card, methodology page; both GIFs recorded from the real map; README + disclaimers + NOTICE + CITATION complete; e2e.sh green with regression pins; live apex fingerprinted.
