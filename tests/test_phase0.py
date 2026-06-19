"""Phase 0 unit tests: the math and registry that gate the project.

These run without any InSAR data, credentials, or network. They lock the LOS->
vertical conversion, the GO/NO-GO gate band, the SBAS pairing, and the AOI
registry invariants.
"""

from __future__ import annotations

import math

from pipeline import aoi as aoi_registry
from pipeline.insar.submit_hyp3 import build_pairs
from pipeline.insar.validate import gate
from pipeline.insar.velocity import los_to_vertical


def test_los_to_vertical_mid_swath():
    # at 39 deg incidence, cos ~0.777, so vertical = los / 0.777
    assert math.isclose(los_to_vertical(77.7, 39.0), 77.7 / math.cos(math.radians(39.0)))
    # pure vertical recovered larger than its LOS projection
    assert los_to_vertical(10.0, 39.0) > 10.0


def test_los_to_vertical_rejects_grazing():
    try:
        los_to_vertical(10.0, 90.0)
    except ValueError:
        return
    raise AssertionError("expected ValueError at 90 deg incidence")


def test_gate_pass_band():
    # Metro Manila anchor is 109 mm/yr; 98 is within factor-of-2 -> GO
    assert gate(98.0, 109.0)["verdict"] == "GO"
    # an order of magnitude low -> NO-GO
    assert gate(12.0, 109.0)["verdict"] == "NO-GO"
    # too high also fails the band
    assert gate(400.0, 109.0)["verdict"] == "NO-GO"


def test_build_pairs_short_baseline():
    scenes = [{"scene": f"S{i}", "date": f"2016-{m:02d}-01"} for i, m in enumerate([1, 4, 7, 10], 1)]
    pairs = build_pairs(scenes, connections=2, max_days=200)
    # each scene links forward to <=2 within 200 days; no self/backward pairs
    assert all(a != b for a, b in pairs)
    assert len(pairs) >= 3
    # first scene (Jan) connects to Apr and Jul (both <=200d), not Oct (>200d via... 273d)
    first = [b for a, b in pairs if a == "S1"]
    assert "S2" in first and "S3" in first


def test_registry_invariants():
    aois = aoi_registry.all_aois()
    assert any(a.id == "metro-manila" and a.tier == 0 for a in aois)
    # validation anchors all carry a published rate; exploratory ones do not
    for a in aoi_registry.validation_anchors():
        assert a.published_rate_mm_yr_max is not None
    # Baguio is the slope-motion regime needing decomposition
    baguio = aoi_registry.get("baguio")
    assert baguio.regime == 3 and baguio.decomposition == "needs_decomposition"
    # bbox is well-formed (min < max) for every AOI
    for a in aois:
        lon0, lat0, lon1, lat1 = a.bbox
        assert lon0 < lon1 and lat0 < lat1
