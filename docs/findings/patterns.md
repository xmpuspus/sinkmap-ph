# Surprising patterns in the data (2026-06-20)

Findings computed from the v1 velocity rasters and MintPy time-series (Metro
Manila, Cebu, Iloilo). Each is backed by a number; caveats are stated. Subsidence
rates are relative; the "hotspot vs stable" temporal numbers are differential
(hotspot mean minus stable-area mean) so common-mode atmospheric/reference drift
cancels.

## 1. Manila's subsidence is past its peak, not accelerating

The Bulacan hotspot rate by period (differential, mm/yr): **2016-19 ~51, 2019-22
~62 (peak), 2022-25 ~43** -- the most recent years are the *slowest* of the decade.
The full-period rate (~72) also sits below the 2014-2020 literature value (~109),
consistent with a slowdown. The project plan assumed the deliverable would "show it
accelerating"; the data shows the opposite. The 2019-2022 peak coincides with the
2019 El Nino drought (drought -> more groundwater pumping -> faster sinking is a
plausible mechanism), but causation is not proven from InSAR alone.

## 2. The fastest-sinking ground is rural farmland, not the dense city

The Manila hotspot is at ~15.18 N, the inland Candaba / Bulacan-Pampanga floodplain
(rice and fishponds), and carries only **~24 OSM buildings/km2** on ground sinking
faster than 15 mm/yr (79 km2). A dense PH metro core runs ~3,000-8,000 buildings/km2.
The "cities are sinking" headline is half wrong: the worst sinking is under farmland
and aquaculture drawing groundwater, not under the skyline. (Caveat: OSM under-maps
rural buildings, so 24/km2 is a floor; the conclusion holds because the location is
agricultural floodplain and the density is 2+ orders of magnitude below urban.)

## 3. Nearly half a meter, gone in a decade

The Manila hotspot lost **~459 mm** of elevation 2016-2025 relative to stable ground
-- close to half a meter in ten years at the peak.

## 4. Engineered coast sinks ~3.5x faster than the natural city

Cebu's general subsidence is ~10 mm/yr (matching the published anchor), but its
southern-coast reclamation cluster reaches **~35 mm/yr** -- newly made ground
settling about 3.5x faster than the city it extends.

## 5. Subsidence is a concentrated aggravator of flooding, not the main cause

Both directions of the overlap matter. Fast-sinking ground is **5-9x more likely**
than average to be flood-prone (Manila 41% vs 8% background; Cebu 20% vs 2%). But it
is only **17% of all flood-prone ground** in Manila (10% in Cebu). So subsidence
sharply worsens flooding where it occurs, yet most flood-prone ground is not sinking
fast -- subsidence is a sharp local amplifier, not the dominant driver.

## 6. The thesis fails where you'd most expect it: Iloilo

Iloilo, where "flooding is the new normal," validated as sinking (~10 mm/yr) but
shows **no preferential flood coincidence** (0.3% vs 0.6% background). Its chronic
flooding is drainage/tidal, outside a return-period depth model. The poster-child
flood city is the one where subsidence is not the flood story.

## 7. The big aquifer is slowing; the small cities hold steady

Manila (a vast groundwater system) is past peak / decelerating, but **Cebu
(-14.3 -> -14.1 mm/yr) and Iloilo (-7.6 -> -7.0)** are essentially dead-linear across
the decade. The scale of the aquifer tracks whether the rate is changing at all.

## Candidate, not trusted

A small, consistent wet/dry oscillation appears across all three cities (the ground
reads slightly more sunk in the wet season, ~2-3 mm), but it cannot be cleanly
separated from residual seasonal tropospheric delay, so it is not reported as real
ground "breathing."

## More patterns (2026-06-20, round 2)

### 8. The land sinks far faster than the sea rises
Sea level in PH waters is rising roughly 5-7 mm/yr (PAGASA / satellite altimetry).
At the Bulacan hotspot the ground drops ~72 mm/yr. So the effective sea-level rise
for someone there is dominated ~10:1 by the land going down, not the ocean coming
up. (Subsidence measured here; SLR cited.)

### 9. It is the uneven sinking that breaks things
Differential subsidence (the spatial gradient of the velocity, smoothed ~400 m):
Metro Manila p95 ~27 mm/yr per km (locally steeper). Cebu ~7, Iloilo ~9. Uniform
settlement is benign; this differential tilt is the mechanism that cracks roads,
snaps pipes, and stresses bridges. Computed from the velocity raster gradient.

### 10. A regional footprint, not a few dots (Metro Manila)
Area sinking faster than 5 mm/yr: ~269 km2 (larger than Quezon City, ~166 km2);
faster than 10 mm/yr: ~139 km2; faster than 20: ~48 km2. Central Luzon's
subsidence is a regional field, not isolated hotspots.

### 11. Cebu and Iloilo are pinpoint, not regional
By contrast, Cebu has only ~5 km2 sinking >5 mm/yr and Iloilo ~3 km2, concentrated
on reclaimed/coastal ground. Same phenomenon, two scales: regional in the Central
Luzon aquifer, pinpoint in the island cities.

## More patterns (2026-06-20, round 3)

Computed by scripts/analysis.py on the Metro Manila MintPy time-series / velocity
raster. The per-period rates and per-zone rates are differential (each referenced
to the area's own reliable-pixel median), so a reference or atmosphere drift that
is common to the scene cancels. Flood overlap is observed coincidence of two
public layers (InSAR + NOAH), never causation.

### 12. The peak is past, but the field is still spreading
Finding #1 is true only at the single worst hotspot. Splitting the decade in half
and fitting a per-pixel rate to each, the inland Bulacan hotspot (15.177 N) slowed
from **-96 mm/yr (2016-2020) to -79 (2021-2025)** (+17 slower) -- but **more
ground sped up than slowed down**: 294 km2 accelerated by >3 mm/yr vs 244 km2
decelerated (robust across cuts: 203 vs 151 km2 at >5 mm/yr, 67 vs 59 at >10). A
zone ~6 km east of the hotspot (15.171 N, 121.036 E) **doubled its rate, from -18
to -46 mm/yr** (accel -28). So "Manila past peak" is a statement about the peak,
not the field: the Central Luzon subsidence kept widening and intensifying around
the edges through 2021-2025. Acceleration is spatially scattered (126 small
clusters, largest 0.7 km2), not one blob. Map layer: web/data/accel/.

### 13. Nearly half the most-exposed buildings face both hazards at once
Of the **1,881** OSM buildings already on fast-sinking ground (>15 mm/yr), **871
(46%)** also sit inside a NOAH 25-yr flood-prone zone (>=0.5 m). Double-exposed:
sinking fast AND modeled flood-prone. (OSM under-maps rural buildings, so 1,881 is
a floor; the 46% double-exposure rate is the headline, not the count.) Coincidence
of two independent public layers, not causation.

### 14. Flood depth and sinking rate are only loosely coupled
By NOAH 25-yr flood-hazard class, the share of ground sinking faster than 10 mm/yr
is **12% (no mapped hazard), 31% (Low 0.1-0.5 m), 30% (Medium 0.5-1.5 m), 17%
(High >1.5 m)**. Fast-sinking ground concentrates in the Low/Medium tiers, not the
deepest-flooding High tier. Median subsidence by tier: +0.1 / -0.5 / -2.2 / +0.9
mm/yr. So the ground modeled to flood deepest is not the fastest-sinking; the two
risks overlap but are largely separate fields. Caveat: High-hazard zones (active
river floodways) have the lowest InSAR coverage (0.20 reliable vs 0.49 for
no-hazard ground), so the High-tier read is on its drier reliable subset.

### 15. The 10 cm subsidence footprint grew from nothing to ~230 km2
Area whose ground has dropped more than 100 mm (10 cm) since 2016-01 (relative to
the reliable-area median each date): **~0 km2 in 2016 -> ~228 km2 by Oct 2025**,
peaking ~311 km2 in early 2025. The >5 cm footprint reached ~337 km2, the >20 cm
footprint ~102 km2. Seasonal scatter is present (atmospheric), but the decade
trend is strong, near-monotonic growth. The subsidence is not just deep at a
point; its measurable footprint widened across Central Luzon.

### 16. One Bulacan town carries most of the exposed ground: San Miguel
Aggregating fast-sinking pixels per OSM municipality boundary (admin_level 6, by
relation id -- PH place names repeat), **San Miguel, Bulacan** has **43.4 km2** of
ground sinking >15 mm/yr, of which **16.8 km2 is also flood-prone** -- by far the
most double-exposed ground of any town in the frame (next: San Ildefonso 1.6 km2,
Meycauayan 0.4). The fastest-sinking inland hotspot sits inside San Miguel's
footprint. (Doña Remedios Trinidad shows 21.6 km2 fast-sinking but ~0 flood-prone
and is upland/forested, where coherence is weaker -- treated as secondary.)

## More patterns (2026-06-20, round 4 -- multi-city scale-out)

Computed by scripts/dig_newcities.py on the first three scale-out cities (Dagupan,
Bacolod, Tacloban), processed through the lean pipeline with the median-datum fix.
Median datum throughout (reference-invariant). Rates are differential.

### 17. Dagupan is the second fast-sinking delta: ~35 cm gone at the hotspot in a decade
Dagupan / Pangasinan (a long-documented subsidence delta) measures **~20 mm/yr
robust (gated, temporal-coherence >= 0.7)**, with the hotspot at 16.02 N, 120.33 E
reaching ~33-40 mm/yr on the fuller reliable mask and **~352 mm (35 cm) of
cumulative subsidence since 2016**. The >5 cm footprint grew from ~0 to ~30 km2,
the >10 cm footprint to ~24 km2. After Metro Manila (72), Dagupan is the fastest
of the six measured cities -- and like Manila it is a groundwater-pumped alluvial
delta, not a dense urban core. (It first read -2.8 mm/yr from a reference-datum
bug: auto-reference landed on subsiding delta ground, where there is no stable
high reference. The area-median datum recovers the real rate. See batch-status.md.)

### 18. The deceleration is not just Manila -- it shows in every new city
Splitting the decade in half, the fastest-sinking ground was faster in 2016-2020
than 2021-2025 in all three new cities, matching finding #1: Dagupan hotspot
-43 -> -31 mm/yr (slowed 12), Bacolod -14 -> -1 (slowed 13), Tacloban -7 -> -4
(slowed 4). Across Dagupan more ground decelerated (29 km2) than accelerated
(10 km2). The 2019 El Nino drought (peak groundwater pumping) is a plausible
common driver -- the early half spans the drought pulse, the late half is
post-drought -- so this may be "the drought pulse passed" rather than a permanent
turn. Half-period rates are noisier than the full-period; reported as a multi-city
pattern, not a forecast. (The slow island cities Cebu/Iloilo stayed near-linear,
finding #7; the deceleration is a property of the fast hotspots.)

### 19. It is the deltas, not the cities: a 10x regime split
With six cities measured, the rate splits by landform, not by how built-up a place
is. The big alluvial / groundwater deltas sink fast -- Metro Manila / Bulacan ~72,
Dagupan ~20 mm/yr -- while the island and coastal-fill cities sink slowly -- Cebu
~10, Iloilo ~10, Bacolod ~4, Tacloban ~3. An order of magnitude separates delta
subsidence from island-city subsidence. (Extends finding #11's regional-vs-pinpoint
split into a landform regime: the fast PH subsidence is a delta-aquifer story.)

## Candidate, not headline (round 3)

- **Reclamation is not uniformly fast.** At the flagship made-ground sites
  themselves the 1 km-buffer median is modest: Cebu South Road Properties -1.3
  mm/yr, Iloilo Business Park -2.0. The fast coastal subsidence sits on adjacent
  older ground (Cebu Talisay belt: 1 km median -9.8, min -34.6, consistent with
  finding #4's ~35 mm/yr cluster). "Reclamation" alone does not predict the rate;
  fill age, compaction, and drainage do. Stated as nuance, not a takedown of any
  named development.
- **Tilt field (layer recompute).** The differential-tilt layer (web/data/tilt/)
  uses a smoothed-then-gradient method giving Metro Manila p50 5.2, p95 17.5, max
  70 mm/yr per km. This refines the round-2 finding #9 estimate (p95 ~27, computed
  with a different smoothing window); both are differential-gradient measures, the
  layer uses the consistent recompute.
