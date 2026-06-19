# Extension cities - dry run (2026-06-17)

Per-city feasibility pass for the subsidence-PH build. Every subsidence rate is cited; cities with no published rate are marked exploratory (the build would produce the first measurement, not validate an existing one). Do not present exploratory cities as having known rates.

## The three physical regimes (this is the key finding)

Not every PH city "sinks" for the same reason, and the project's thesis (subsidence amplifies flooding) only cleanly fits one regime. The dry run sorts every city into:

- Regime 1 - Aquifer / delta subsidence in flat flood-prone lowlands. Vertical-dominant motion, good InSAR coherence (buildings = persistent scatterers), and the sinking directly worsens flooding. THIS IS THE CORE OF THE PROJECT.
- Regime 2 - Reclamation / coastal fill settlement. A distinct cause inside Regime 1: engineered new ground at sea level that settles fast. Still vertical-dominant. Good sub-story (Manila Bay, Mandaue).
- Regime 3 - Slope / landslide deformation in steep terrain. Horizontal (downslope) motion, poor coherence under vegetation, NOT a flooding story, and it breaks the simple LOS-to-vertical conversion. Baguio is the example. Different project; showcase only.

The regime also decides the method: Regimes 1 and 2 are vertical-dominant, so single-track LOS scaled by cos(incidence) is defensible for v1. Regime 3 needs full ascending+descending decomposition. See METHOD-decomposition.md.

## City table

Primary validation source for the documented rates: Aslan et al. 2024, "Ground subsidence in major Philippine metropolitan cities from 2014 to 2020," Sentinel-1 InSAR + GNSS. https://www.sciencedirect.com/science/article/pii/S1569843224004618

| City / AOI | Subsidence (published) | Cause | Flood | Setting | InSAR terrain | Regime | Validation |
|---|---|---|---|---|---|---|---|
| Metro Manila + Bulacan + Pampanga | ~109 mm/yr max (Bulacan), avg ~11 | Groundwater | HIGH (chronic) | Coastal delta lowland | Flat-urban (good) | 1 (+2 reclaim) | Direct (study + multiple papers) |
| Metro Davao | 38 mm/yr max | Groundwater | MEDIUM | Riverine + some upland | Mixed | 1 | Direct (study) |
| Legazpi (Bicol) | 29 mm/yr max | Groundwater, urbanization | MED-HIGH (typhoon) | Coastal urban | Flat-urban (good) | 1 | Direct (study) |
| Metro Cebu / Mandaue | 11 mm/yr max | Groundwater + reclamation | MED-HIGH | Coastal urban | Flat-urban (good) | 1 + 2 | Direct (study) |
| Iloilo City | 9 mm/yr max | Groundwater | MED-HIGH ("new normal") | Coastal lowland | Flat-urban (good) | 1 | Direct (study) |
| Dagupan / Pangasinan | Qualitative only (no mm/yr found) | Fishpond + aquifer depletion, tidal | HIGH (chronic tidal) | River-delta | Flat-urban (good) | 1 | Exploratory |
| Butuan / Agusan basin | None published | (delta compaction suspected) | HIGH (chronic) | River delta + marsh | Flat-urban (good) | 1 | Exploratory |
| Cotabato City / Mindanao R | None published (tectonic noted) | (delta/marsh suspected) | HIGH (36/37 villages, Paeng) | Liguasan marsh basin | Flat-urban (good) | 1 | Exploratory |
| Cagayan de Oro | None published | (riverine; landslide nearby) | MED-HIGH | Riverine + upland | Mixed | 1 (partial) | Exploratory |
| General Santos | None published | unknown | MEDIUM | Coastal lowland | Flat-urban (good) | 1 | Exploratory |
| Tacloban / Leyte | None published | storm-surge focus | MED-HIGH | Coastal urban | Flat-urban (good) | 1 | Exploratory |
| Bacolod / Negros | None published | unknown | MEDIUM | Coastal urban | Flat-urban (good) | 1 | Exploratory |
| Naga, CAMARINES SUR (Bicol) | None published | unknown | MED-HIGH | Coastal lowland | Flat-urban (good) | 1 | Exploratory |
| Naga, CEBU (different city) | >50 mm cumulative 2014-18 | Quarrying + groundwater | n/a | - | Flat-urban | 1 | Direct (PS-InSAR paper) |
| Cavite coast (Bacoor/Kawit) | UPLIFT in fishpond zones | consolidation/recharge | MEDIUM | Coastal lowland | Flat-urban | counter-signal | Direct (study) |
| Baguio City | 0.1-0.4 m/yr slope settlement; 140 mm Jul-Sep 2024 | Landslides, rainfall | LOW (flash/landslide) | Steep mountain ~1500 m | Steep-vegetated (poor) | 3 | Showcase only |
| Zamboanga City | None | unknown | LOW-MED (no recent events found) | Coastal urban | Flat-urban | - | Skip v1 |

Note the Naga disambiguation: the published >50 mm subsidence is Naga City in CEBU (quarrying-driven), NOT Naga in Bicol (the flood-prone one). Keep them separate.

## What the dry run implies

- Five metros come with a published 2014-2020 rate (Manila/Bulacan/Pampanga, Davao, Legazpi, Cebu/Mandaue, Iloilo). These are validation anchors: our 2016-2026 run should reproduce the location and order of magnitude, then extend the timeline. Cheap credibility.
- The exploratory delta/marsh cities (Dagupan, Butuan, Cotabato, CDO, GenSan, Tacloban, Bacolod, Naga-Bicol) are where the project produces NEW measurements. Higher value, higher uncertainty. They are all flat-urban/delta lowland, so InSAR coherence should hold, and all chronically flood, so the subsidence-flood overlay is meaningful if a signal exists.
- Baguio is the honest "wherever has limits" case: different physics (landslide, not aquifer), poor coherence under vegetation, horizontal motion that single-track LOS cannot resolve, and no flood-thesis tie. Include only as a separate "the method also sees slope motion" tile, clearly flagged, or defer.
- Cavite is a useful nuance: it shows UPLIFT, not subsidence, so the map honestly shows where ground is rising too, not only a doom narrative.

## Processing dry run (no execution)

Path is HyP3 (on-demand Sentinel-1 SBAS InSAR) + MintPy, one AOI at a time. Descending track as default geometry for v1.

- Frames/tracks per AOI: resolved at run time via the ASF search API. Metro Manila (verified 2026-06-17): descending relative orbit 32, frames 540-546, 325 scenes 2016-2025, 40 after quarterly subsample, 77 SBAS pairs.
- Scenes: 2016-2026 subsampled (target ~quarterly, ~40 scenes/AOI) keeps coherence via short baselines while fitting credits. Dense enough for a robust velocity and to show non-linear acceleration.
- Credits (corrected against the live HyP3 /costs table, 2026-06-17): INSAR_GAMMA is 10 credits/pair at 20x4 looks (15 at 10x2), NOT the ~600-800 an early estimate guessed. ~77 SBAS pairs = ~770 credits, well inside the 8,000/month free allotment, so one AOI fits in a single month with room to spare. INSAR_ISCE_BURST is 1 credit/pair if you want it cheaper.
- Calendar: HyP3 queue 1-7 days per batch + MintPy inversion. Expect ~1-2 weeks elapsed per AOI after the first.

## Suggested sequence

- P0 (gate): Metro Manila / Bulacan. Must reproduce the ~100+ mm/yr hotspot. GO/NO-GO.
- P1: the four other published-rate metros (Davao, Legazpi, Cebu/Mandaue, Iloilo). Each validates against a known number and builds the national picture fast.
- P2: exploratory delta/flood cities (Dagupan, Butuan, Cotabato, Cagayan de Oro, General Santos, Tacloban, Bacolod, Naga-Bicol). New findings, overlay against recent floods.
- P3 (stretch): Baguio slope-motion showcase (needs decomposition), Cavite uplift nuance.

This gives "many cities" honestly: 5 validation anchors + up to 8 exploratory + 1 stretch, not a hand-wave.
