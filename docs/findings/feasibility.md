# Scale-out feasibility: which PH cities the current method can measure

Computed by `scripts/feasibility.py` (no HyP3 credits spent). For every candidate AOI it reads built-up fraction, flat-built fraction (built AND slope < 10 deg, the coherent ground a descending SBAS can anchor on), slope, elevation, and vegetation from public Earth Engine layers (ESA WorldCover v200 10 m, SRTM 30 m), then labels feasibility for the current quarterly/descending-SBAS method.

## The discriminator and its calibration

Flat-built fraction separates the five cities whose outcome is already known (docs/findings/phase2-multicity.md): the three that validated (Metro Manila 0.44, Cebu 0.34, Iloilo 0.28) all sit at or above 0.28; the two that failed (Davao 0.13 upland, Legazpi 0.11 vegetated) sit at or below 0.13. The GO threshold is set at **0.20**, inside that 0.15-wide gap with margin. The scorer reproduces all five known outcomes (5/5).

## Result: 124 AOIs scored (15 registry + 109 OSM cities)

- **GO-now (20)**: a dense, flat urban core the current method can anchor on. Run these first.
- **tighter-AOI (5)**: works once the AOI is clipped to the built-up core (drop the vegetated/steep surroundings).
- **PS-needed (82)**: sparse-urban or vegetated; the current SBAS will decorrelate. Needs persistent-scatterer InSAR.
- **terrain-hard (17)**: upland or steep; needs ascending+descending decomposition plus PS.

### GO-now (run with today's pipeline)

| City (OSM population) | flat-built | mean slope / % >300 m | why |
|---|---|---|---|
| Cavite coast (uplift nuance) | 0.67 | 1° / 0% >300m | dense flat urban core (current method) |
| Muntinlupa | 0.59 | 2° / 0% >300m | dense flat urban core (current method) |
| Santa Rosa | 0.52 | 1° / 0% >300m | dense flat urban core (current method) |
| San Pedro | 0.52 | 2° / 0% >300m | dense flat urban core (current method) |
| Biñan | 0.51 | 2° / 0% >300m | dense flat urban core (current method) |
| Cabuyao | 0.46 | 1° / 0% >300m | dense flat urban core (current method) |
| Metro Manila + Bulacan + Pampanga belt | 0.44 | 2° / 0% >300m | dense flat urban core (current method) |
| Carmona | 0.42 | 2° / 0% >300m | dense flat urban core (current method) |
| General Trias | 0.39 | 1° / 0% >300m | dense flat urban core (current method) |
| Talisay | 0.37 | 4° / 2% >300m | dense flat urban core (current method) |
| Metro Cebu / Mandaue | 0.34 | 6° / 11% >300m | dense flat urban core (current method) |
| Dasmariñas | 0.32 | 2° / 0% >300m | dense flat urban core (current method) |
| Angeles | 0.32 | 2° / 0% >300m | dense flat urban core (current method) |
| Antipolo | 0.30 | 6° / 4% >300m | dense flat urban core (current method) |
| Iloilo City | 0.28 | 2° / 0% >300m | dense flat urban core (current method) |
| Calamba | 0.28 | 3° / 6% >300m | dense flat urban core (current method) |
| Cagayan de Oro | 0.26 | 4° / 4% >300m | dense flat urban core (current method) |
| Bacolod / Negros | 0.24 | 1° / 0% >300m | dense flat urban core (current method) |
| Zamboanga City | 0.23 | 3° / 2% >300m | dense flat urban core (current method) |
| Mabalacat | 0.22 | 3° / 0% >300m | dense flat urban core (current method) |

### tighter-AOI (clip to the urban core, then run)

| City (OSM population) | flat-built | mean slope / % >300 m | why |
|---|---|---|---|
| Tacloban / Leyte | 0.19 | 4° / 0% >300m | clip to the urban core, then current method |
| Dagupan / Pangasinan | 0.18 | 1° / 0% >300m | clip to the urban core, then current method |
| General Santos | 0.18 | 2° / 0% >300m | clip to the urban core, then current method |
| Batangas City | 0.17 | 3° / 1% >300m | clip to the urban core, then current method |
| Naga (Camarines Sur, Bicol) | 0.15 | 1° / 0% >300m | clip to the urban core, then current method |

### terrain-hard (needs ascending+descending + PS)

| City (OSM population) | flat-built | mean slope / % >300 m | why |
|---|---|---|---|
| Baguio City (slope-motion showcase) | 0.20 | 12° / 100% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Metro Davao | 0.13 | 4° / 16% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Lipa | 0.12 | 4° / 51% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Olongapo | 0.11 | 8° / 7% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Iligan | 0.09 | 7° / 7% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Tagaytay | 0.07 | 7° / 60% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Marawi | 0.05 | 5° / 100% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Kidapawan | 0.03 | 4° / 42% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Valencia | 0.03 | 4° / 81% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Mati | 0.03 | 8° / 14% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Tayabas | 0.03 | 6° / 35% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Tabuk | 0.03 | 6° / 17% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Malaybalay | 0.02 | 10° / 100% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Catbalogan | 0.02 | 6° / 5% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Gingoog | 0.02 | 6° / 22% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Dapitan | 0.01 | 8° / 4% >300m | upland/relief, little flat urban (needs asc+desc + PS) |
| Canlaon | 0.00 | 11° / 90% >300m | upland/relief, little flat urban (needs asc+desc + PS) |

### PS-needed (82)

The bulk. Examples: Trece Martires, Santo Tomas, Tanauan, Dumaguete, Legazpi (Bicol), Tarlac City, Puerto Princesa, Naga, Cabanatuan, Roxas City, Tuguegarao, Balanga, and others. Most are small or component cities with low built-up fraction and high vegetation; persistent-scatterer InSAR (or simply being too small to anchor an areal SBAS) is the limiter.

## Caveats (state these)

- This predicts radar **coherence feasibility** for one method, not whether subsidence exists. A PS-needed city is not a city that is not sinking.
- OSM and WorldCover **under-count built-up area** in small cities, so the PS-needed bucket is inflated by genuinely-small towns, not only hard ones.
- OSM-sourced AOIs use an approximate centroid-buffer box; the 15 registry AOIs use curated boxes.
- Calibrated on five labeled cities; the 0.20 threshold has margin but more validated grounds would sharpen it.
- GO-now is a pre-screen, not a guarantee: each city still runs through HyP3 + MintPy and must pass the GO/NO-GO gate before any number is shown.

## What this says about scale-out

About **20 cities are immediately reachable** with the validated method, plus 5 with tighter AOIs: the dense flat cores of the Mega Manila sprawl (Dasmarinas, Binan, Santa Rosa, Cabuyao, San Pedro, Muntinlupa, General Trias) and the flat coastal HUCs (Zamboanga, Cagayan de Oro, Bacolod, Iloilo, Cebu, Angeles). These are Phase A. Reaching the 82+17 vegetated, small, or upland cities (Baguio, Tagaytay, Marawi, Iligan, Olongapo, and most component cities) needs the PS-InSAR upgrade (Phase B). Anchor-free validation is required for all of them, since only five PH cities have a published rate.


Disclaimer: feasibility indicators from public land-cover and terrain data. A label is a processing-method prediction, not a statement about ground motion.
