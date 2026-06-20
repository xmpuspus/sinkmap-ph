# Scale-out batch: launch status and the resumable pipeline

This is the Phase-A scale-out in motion: the feasibility scorer
(docs/findings/feasibility.md) picked the reachable cities, and the batch harness
(`scripts/batch.py`) launched the highest-value ones into HyP3. Land subsidence is
not produced until each city's stack finishes processing and passes the gate; this
file records what is queued versus done. Compute before narrating: no new city's
rate appears on the map until it is processed and gated.

## What launched (2026-06-20)

Five cities submitted to ASF HyP3 (Sentinel-1 descending SBAS, 2016-2025,
quarterly, ~77 pairs each, INSAR_GAMMA with DEM + look vectors), within the 4,160
remaining credits. A deliberate Luzon / Visayas / Mindanao spread:

| City | Track | Pairs (jobs) | Feasibility | Why this one |
|---|---|---|---|---|
| Dagupan / Pangasinan | 32 | 77 | tighter-AOI | Known delta subsidence; high civic value |
| Cavite coast | 32 | 77 | GO-now | Manila Bay reclamation, adjacent to the NCR field |
| Bacolod / Negros | 134 | 76 | GO-now | Distinct Visayas HUC, flat coastal |
| Cagayan de Oro | 61 | 77 | GO-now | Mindanao HUC, flood-prone |
| Tacloban / Leyte | 61 | 77 | tighter-AOI | Storm-surge city, coastal Eastern Visayas |

Recon confirmed every target has a full decade-long descending stack (40 quarterly
scenes), so scene availability is not the limiter in the Philippines (coherence is,
which the feasibility scorer screens for).

## Status: QUEUED, not done

Verified server-side right after submission: 384 jobs accepted, **0 failed**,
Dagupan and Cavite coast already running, the rest pending in the HyP3 queue.
HyP3 jobs take 1-7 days. Nothing is downloaded or processed yet. The honest state
lives in `data/insar/batch_state.json` and on the HyP3 server (jobs named
`sinkmap-<city>`, recoverable by name even without the local state file).

Resume, once the queue finishes:

```bash
.venv/bin/python scripts/batch.py status          # poll succeeded/running/failed
# then, per city: download products -> MintPy SBAS -> velocity -> vertical
#   auto-reference + anchor-free gate are automated (pipeline/insar/autoref.py)
```

## The pipeline, end to end (what is automated now)

1. **Feasibility pre-screen** (`scripts/feasibility.py`): GO-now / tighter-AOI /
   PS-needed / terrain-hard, no credits spent. Calibrated 5/5 on known outcomes.
2. **Recon + credit plan** (`scripts/batch.py plan`): ASF search, SBAS pair count,
   credit estimate, greedy selection within a budget. No auth.
3. **Submit** (`scripts/batch.py submit`): HyP3 SBAS jobs, state recorded.
4. **Download + MintPy** (existing `pipeline.insar.*`): after the queue clears.
5. **Auto-reference** (`pipeline/insar/autoref.py`): picks the highest stable
   coherent ground for the reference point. Verified to land on the same
   piedmont regime as the hand-picked Metro Manila / Cebu / Iloilo references
   (the velocity field is reference-invariant, so the exact pixel only shifts a
   constant). This removes the per-city reference-tuning that did not scale.
6. **Anchor-free gate** (`pipeline/insar/autoref.py`): GO / MARGINAL / NO-GO from
   reliable-pixel count and temporal coherence, since only five PH cities have a
   published rate to check against. Reproduces all five known outcomes exactly
   (Metro Manila / Cebu / Iloilo GO with 154k / 22,911 / 13,750 reliable px;
   Davao 37 px and Legazpi 0 px NO-GO). Ascending+descending agreement is the
   stronger gate and is a v2 add.

## Credits and what is next

~3,840 of 4,160 credits used on these five. The free allotment resets monthly
(8,000), so the next batch (General Santos, Naga, the Mega Manila sprawl cities,
the rest of the GO-now list) goes next cycle. The ~100 PS-needed / terrain-hard
cities (docs/findings/feasibility.md) still need the PS-InSAR upgrade (Phase B);
this harness is what they plug into. The credit-free path to remove the ceiling
entirely is ARIA-S1-GUNW ingestion (needs ARIA-tools installed; not yet wired).
