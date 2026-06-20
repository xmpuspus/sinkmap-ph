# Scale-out plan: from 6 cities to national coverage

Three tiers, set by what the data and the method actually allow (measured this
session, not assumed). The feasibility scorer (docs/findings/feasibility.md) says
~20 cities are reachable with the current areal-SBAS method; the rest need
persistent scatterers. The cost lever splits by region.

## Tier 1 -- ARIA-GUNW, credit-free, Luzon

ASF/JPL publish ARIA-S1-GUNW (pre-made unwrapped interferograms) that MintPy
ingests directly via its built-in `prep_aria` (no HyP3 credits, no full-scene
download of SLCs). Coverage over the Philippines, measured by `asf_search`:

| AOI | ARIA-GUNW products | covered |
|---|---|---|
| Metro Manila | 7,638 | yes |
| Cavite coast | 5,699 | yes |
| Dagupan | 3,852 | yes |
| Baguio | 2,258 | yes |
| Legazpi | 1,259 | yes |
| Naga (Bicol) | 861 | yes |
| Cebu, Iloilo, Bacolod, Tacloban (Visayas) | 0 | no |
| Cagayan de Oro, Davao, General Santos, Butuan, Cotabato (Mindanao) | 0 | no |

**ARIA covers Luzon, not the Visayas or Mindanao.** That is still most of the
reachable GO-now list (the NCR sprawl, Dagupan, Angeles, Batangas, Naga, etc.) and
the two fastest deltas. Recipe per Luzon city, no credits:

```bash
# in the sinkmap-aria env (aria-tools on conda-forge)
ariaDownload.py --bbox "S N W E" --start 20160101 --end 20260101 -o Download
ariaTSsetup.py -f "products/*.nc" --bbox "S N W E"          # build the stack
# then in the MintPy env
prep_aria.py -s stack/ -d DEM/SRTM_3arcsec.dem -i incidenceAngle/*.vrt ...
smallbaselineApp.py sinkmap.cfg
# then pipeline/insar/process.py-style adaptive_vertical + anchor_free_gate
```

## Tier 2 -- HyP3 GAMMA, credit-funded, Visayas + Mindanao

The island and Mindanao cities have no ARIA coverage, so they stay on the
validated HyP3 full-scene GAMMA path (scripts/batch.py + lean_fetch +
process.py), ~770 credits/city, ~10/month on the free tier. This is the method
already validated on Cebu/Iloilo and used for the 6 live cities. Burst InSAR was
tested as a 10x-cheaper option and rejected for regional bowls (Manila burst 7.6
vs GAMMA 72; see batch-status.md) -- it only works for pinpoint coastal cities.

## Tier 3 -- PS-InSAR (Phase B), the ~100 cities the current method cannot reach

The feasibility scorer flags ~82 PS-needed + ~17 terrain-hard cities: small,
vegetated, or upland places (Baguio interior, Tagaytay, Marawi, Iligan, Olongapo,
most component cities) where areal SBAS decorrelates. These need **persistent-
scatterer InSAR**: instead of averaging a coherent area, track individual stable
point reflectors (building corners, rock, infrastructure) that stay coherent even
in a noisy scene.

- **Tool**: StaMPS (MATLAB, the reference PS implementation) or a Python PS stack
  (e.g. the PS module in newer MiaplPy / MintPy-PS). StaMPS needs MATLAB; MiaplPy
  is the open-source path and reuses the same ISCE/HyP3 stacks we already build.
- **Inputs**: the same Sentinel-1 SLC stacks (or ARIA for Luzon). No new data.
- **Steps**: SLC coregistration -> PS candidate selection (amplitude dispersion)
  -> phase analysis on the PS network -> velocity -> same median-datum +
  anchor-free gate.
- **Effort**: weeks, not a session. It is the genuine unlock for "all major
  cities," and the harness (registry, gate, lean fetch, web layers) is built to
  plug it in. Validate it the same way burst was: reproduce a known city
  (Cebu/Iloilo) on PS before trusting a new one.

## Sequence

1. Wire ARIA for Luzon (Tier 1): unlimited credit-free cities where it counts.
2. Spend the monthly HyP3 free allotment on the Visayas/Mindanao GO-now cities
   (Tier 2): Bacolod and Tacloban already done; add Zamboanga, General Santos,
   the rest.
3. Stand up MiaplPy PS (Tier 3) and validate on a known city before scaling to
   the vegetated/upland ~100.
