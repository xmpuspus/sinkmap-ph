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
