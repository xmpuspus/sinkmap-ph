# What sinkmap.ph found

A plain-English summary of the measured results, for a general audience. Every
number comes from open Sentinel-1 satellite radar (2016-2025) processed with
HyP3 and MintPy, and is gated before it is shown. This measures how fast the
ground is moving down. It is not a forecast and assigns no blame; where sinking
ground meets a flood is a question for engineers on the ground.

## The headline results

**The fastest-sinking ground is rural farmland, not the city skyline.** The worst
subsidence in the Metro Manila region is inland, in the Bulacan/Pampanga lowland
(rice fields and fishponds drawing groundwater), at about 72 mm a year, not under
the dense coastal city. "Cities are sinking" is half the story; the worst of it is
under farmland and aquaculture.

**Dagupan has lost about 35 cm of ground at its hotspot in a decade.** Dagupan,
Pangasinan, is the second fastest-sinking place measured, around 20 mm a year,
with its worst spot down roughly 35 centimeters since 2016. Like Metro Manila, it
is a river delta pumped for groundwater.

**It is the deltas, not the cities.** Across six measured cities the rate splits by
landform, not by how built-up a place is. River deltas sink fast (Metro Manila ~72,
Dagupan ~20 mm/yr); island and coastal cities sink about ten times slower (Cebu ~10,
Iloilo ~10, Bacolod ~4, Tacloban ~3).

**The fast sinking is past its peak.** Splitting the decade in half, every fast
hotspot was sinking faster in 2016-2020 than in 2021-2025. The 2019 El Nino
drought (when groundwater pumping peaks) is a plausible common cause. This is an
observed slowdown, not a prediction that it will keep slowing.

**The land drops far faster than the sea rises.** At the Bulacan hotspot the ground
falls about 72 mm a year; sea level in Philippine waters rises about 5-7 mm a year.
For people there, the effective rise is dominated roughly ten to one by the land
going down, not the ocean coming up.

**Sinking and flooding overlap, sharply but locally.** Of the buildings already on
fast-sinking ground in the Metro Manila region, nearly half (46%) also sit in a
modeled 25-year flood zone. Fast-sinking ground is several times more likely to be
flood-prone than average, but it is still a minority of all flood-prone ground, so
sinking is a sharp local amplifier of flooding, not its main cause.

## What the map does not claim

- It does not predict which buildings will flood, and issues no per-building verdict.
- Flood overlap is observed spatial coincidence, not proof of cause. Flooding has
  many drivers: rainfall, drainage, tides, reclamation, and sea-level rise.
- Rates are relative (radar has no absolute datum on its own) and are shown
  against each city's own stable ground.
- Two cities (Legazpi, Davao) are too decorrelated for a reliable rate with this
  method and are reported as honest non-results, not forced numbers.

## Data and method

All data is from public sources: Copernicus Sentinel-1 (ESA), HyP3 (NASA/ASF),
MintPy, JRC Global Surface Water, Project NOAH flood-hazard maps, and Aslan et al.
2024 for the validation anchors. Three of the six cities reproduce their published
subsidence rates within a factor of two; the other three have no published anchor
and are shown as coverage-gated measurements. Full write-ups and the methodology
page are in this repository and at sinkmap.ph. Code is MIT; derived data CC-BY-4.0.
