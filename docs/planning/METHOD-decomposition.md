# LOS vs vertical decomposition - method study (2026-06-17)

What InSAR actually measures, why "subsidence in mm/yr" is not directly what comes out of the pipeline, and the decision for v1.

## What InSAR measures: line-of-sight, not vertical

InSAR phase gives displacement along the radar line-of-sight (LOS), the direction from the ground to the satellite. The true ground motion is a 3D vector d = (dE, dN, dU) (east, north, up). The sensor only sees its projection onto the LOS unit vector:

  d_LOS = dU * cos(theta) - sin(theta) * (east-west horizontal term) + (north-south term, ~0)

where theta is the radar incidence angle. Two consequences that matter here:

1. Vertical sensitivity is cos(theta). Sentinel-1 IW incidence runs ~29 degrees (near range) to ~46 degrees (far range), ~39 degrees mid-swath. So cos(theta) is ~0.69 to 0.87, about 0.78 mid-swath. Pure vertical sinking shows up in LOS at roughly 78% of its true size mid-swath. You must divide by cos(theta) to get true vertical.

2. North-south motion is nearly invisible. Sentinel-1 flies a near-polar orbit (heading ~10-12 degrees off north), so north-south displacement projects almost entirely into the along-track (azimuth) direction, which interferometric phase cannot see. InSAR is sensitive to vertical and east-west, blind to north-south.

## Single-geometry LOS to "pseudo-vertical" (the v1 method)

If you assume motion is purely vertical (dE = dN = 0), then:

  dU = d_LOS / cos(theta)

One track (one viewing geometry) is enough. This is valid when motion is genuinely vertical-dominant, which is exactly the case for:
- Aquifer-compaction subsidence (groundwater extraction) - the dominant PH cause.
- Delta / sediment compaction.
- Reclamation-fill settlement.

All the Regime 1 and 2 cities in CITIES.md fall here. Most published PH subsidence figures effectively rest on this assumption. So v1 = descending-track LOS, convert to vertical with cos(theta), state the vertical-dominant assumption plainly on the methodology page.

## Why and when you need full decomposition

A single geometry cannot separate vertical from horizontal: a pixel moving down looks similar to one moving away in range. If real horizontal motion exists, single-track LOS is biased and misread as wrong subsidence. To resolve it, combine two look directions:

- Ascending and descending passes see the same ground from opposite sides.
- Two LOS measurements (d_LOS_asc, d_LOS_desc) give two equations. Solving (least squares, assuming dN ~ 0) yields vertical (dU) and east-west (dE) separately.
- North-south still needs extra data (azimuth pixel-offset / MAI, or GNSS).

You need this when horizontal motion is plausible:
- Landslides / slope creep (downslope motion is largely horizontal) - Baguio, Regime 3.
- Fault-adjacent creep (e.g., near the West Valley Fault through Metro Manila) - a v2 refinement, not required for the subsidence-flood story.

## Cost consequence (this is the real tradeoff)

HyP3 emits LOS interferograms; MintPy outputs an LOS velocity field. To get vertical:
- LOS-only (v1): one HyP3 stack per AOI, scale by cos(theta). Half the credits, half the processing.
- Full decomposition: two stacks per AOI (ascending + descending), co-registered and combined. Doubles HyP3 credits and adds a co-registration/resampling step. With the 8,000 credits/month free quota and a 10-year stack, this materially slows the city rollout.

So decomposition is not free rigor; it roughly doubles the per-city cost. Spend it only where the physics demands it.

## Decision

- v1: descending-track LOS to pseudo-vertical via cos(theta), for all Regime 1 / 2 lowland cities. State the vertical-dominant assumption. This matches the published PH subsidence literature and fits the credit budget.
- v2 (optional refinement): add the ascending track for true 2D decomposition on fault-adjacent AOIs (Metro Manila / West Valley Fault) to separate any horizontal creep, and to tighten vertical estimates.
- Baguio / Regime 3: decomposition-required and coherence-poor; treat as a separate slope-motion showcase, not part of the v1 subsidence-flood map.

## Error sources to disclose on the methodology page

Atmospheric phase delay (tropospheric water vapor), phase-unwrapping errors, DEM error, choice of reference point (must sit on stable ground), and the vertical-dominant assumption itself. Standard InSAR caveats; list them so the measurement is honest.
