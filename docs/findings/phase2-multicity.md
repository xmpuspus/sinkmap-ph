# Phase 2-3: multi-city subsidence + flood overlay (2026-06-20)

Five validation metros run through the v1 pipeline (Sentinel-1 descending SBAS,
2016-2025, ~40 quarterly scenes / ~77 pairs each, HyP3 + MintPy, LOS -> pseudo-
vertical). Every rate is compared to the published anchor (Aslan et al. 2024).
Reported as measurement, not blame; flood overlap is coincidence, not causation.

## Subsidence validation

| City | Anchor mm/yr | Measured (robust) mm/yr | Ratio | Reliable px | Confidence | Verdict |
|---|---|---|---|---|---|---|
| Metro Manila / Bulacan | 109 | 72 (peak) | 0.66 | ~340k | high | **GO** |
| Cebu / Mandaue | 11 | 10.1 | 0.91 | 22,911 | high | **GO** |
| Iloilo | 9 | 9.8 | 1.09 | 13,750 | high | **GO** |
| Legazpi | 29 | - | - | 0 | - | NO-GO (coherence) |
| Davao | 38 | - | - | 37 @0.7 | - | coherence-limited |

Robust rate = the 1%-most-subsiding boundary (a single-pixel max overstates a
sparse field). Metro Manila uses its single-pixel max (72), which is itself a
~750-px cluster, not an outlier.

### Verified GO cities

- **Metro Manila / Bulacan-Pampanga belt: 72 mm/yr**, peak at lat 15.177 / lon
  120.983 (inland Bulacan/Pampanga/Candaba), confirmed inland and reference-
  invariant. See metro-manila-v1.md.
- **Cebu / Mandaue: 10.1 mm/yr** general subsidence (matches the 11 anchor), PLUS
  a localized **~35 mm/yr cluster** (35 px) at the southern Cebu coast
  (Talisay / South Road Properties reclamation zone) that sits above the
  groundwater anchor. Reference on stable 104 m ground (coh 0.96).
- **Iloilo: 9.8 mm/yr** (matches the 9 anchor near-exactly), flat coastal city
  with good urban coherence. Reference on 72 m ground (coh 0.97).

### Coherence-limited cities (honest non-results, not forced numbers)

- **Legazpi**: raw HyP3 frame coherence is fine (max 0.98), but the small, flat,
  vegetated Bicol coastal AOI subset is decorrelated (per-interferogram mean
  coherence ~0.02; maskConnComp empty). No reliable reference, no velocity.
- **Davao**: AOI is upland-dominated (median 145 m, 22% above 300 m; Mt Apo
  foothills) with sparse urban persistent scatterers - only 37 px exceed temporal
  coherence 0.7. A provisional 0.55-threshold field gave an implausible ~100 mm/yr
  from reference bias + decorrelation; not reported as a measurement.

### Method-applicability finding (the real lesson)

The quarterly / 200-day descending SBAS reproduces dense-urban subsidence at high
confidence (Metro Manila, Cebu, Iloilo) but is coherence-limited for vegetated or
upland AOIs (Legazpi, Davao). Those need PS-InSAR (persistent scatterers), a
short-baseline dense network, or a tighter urban-core AOI - a clear v1.1 path, not
a failure of the validated cities.

## Flood overlay (subsidence x NOAH 25-yr flood hazard, Var >= 2 = >=0.5 m depth)

| City | high-subsidence in flood zone | all ground in flood zone | enrichment |
|---|---|---|---|
| Metro Manila | 41% (>20 mm/yr) | 8.4% | ~5x |
| Cebu / Mandaue | 18% (>10 mm/yr) | 2.0% | ~9x |
| Iloilo | 0.3% (>5 mm/yr) | 0.6% | none |

- Metro Manila and Cebu: fast-sinking ground is several times more likely to be
  flood-prone than the background rate - the subsidence-amplifies-flooding signal.
- Iloilo: no preferential coincidence with the NOAH baseline. Caveat: the NOAH
  25-yr high-depth area inside the Iloilo grid is tiny (0.5 km2), so this is
  inconclusive, not evidence of absence - Iloilo's chronic "new normal" flooding
  may be drainage/tidal, outside a return-period depth model.

### Derived Sentinel-1 event flood extents (observed, independent of InSAR)

Carina + habagat (Jul 2024, Metro Manila) 12.1 km2; 2025 SW monsoon 12.4 km2;
Kristine/Trami (Oct 2024, Bicol) 1.5 km2 (only 2 post-event S1 scenes -> a lower
bound, under-sampled).

## Credits / data

HyP3: 7,230 -> 4,160 credits (3,070 spent on the 4 metros; ~770/city). All raw
products deleted after processing (clipped products + velocity + vertical kept).
subset.lalo mis-crops variable-extent HyP3 products (placed Cebu 73 km off-AOI);
fixed by gdal pre-clip to a common AOI grid (clip_products in velocity.py).
