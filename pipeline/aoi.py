"""AOI registry loader for sinkmap.ph.

Reads pipeline/cities.json (the source of truth for areas of interest, their
coarse bboxes, dry-run tiers, and the published subsidence rates used for
validation). bbox is [min_lon, min_lat, max_lon, max_lat].
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

_REGISTRY = Path(__file__).resolve().parent / "cities.json"


@dataclass(frozen=True)
class AOI:
    id: str
    name: str
    bbox: Tuple[float, float, float, float]
    tier: int
    regime: int
    flood_severity: str
    published_rate_mm_yr_max: Optional[float]
    published_source: Optional[str]
    decomposition: str
    notes: str

    def wkt(self) -> str:
        """bbox as a WKT POLYGON for ASF / GEE intersect queries."""
        lon0, lat0, lon1, lat1 = self.bbox
        return (
            f"POLYGON(({lon0} {lat0},{lon1} {lat0},"
            f"{lon1} {lat1},{lon0} {lat1},{lon0} {lat0}))"
        )

    @property
    def is_exploratory(self) -> bool:
        return self.published_rate_mm_yr_max is None


def _load() -> List[AOI]:
    data = json.loads(_REGISTRY.read_text())
    out = []
    for c in data["cities"]:
        out.append(
            AOI(
                id=c["id"],
                name=c["name"],
                bbox=tuple(c["bbox"]),  # type: ignore[arg-type]
                tier=c["tier"],
                regime=c["regime"],
                flood_severity=c["flood_severity"],
                published_rate_mm_yr_max=c["published_rate_mm_yr_max"],
                published_source=c["published_source"],
                decomposition=c["decomposition"],
                notes=c["notes"],
            )
        )
    return out


def all_aois() -> List[AOI]:
    return _load()


def get(aoi_id: str) -> AOI:
    for a in _load():
        if a.id == aoi_id:
            return a
    raise KeyError(f"unknown AOI id: {aoi_id!r}. Known: {[a.id for a in _load()]}")


def by_tier(tier: int) -> List[AOI]:
    return [a for a in _load() if a.tier == tier]


def validation_anchors() -> List[AOI]:
    """AOIs with a published rate to validate against."""
    return [a for a in _load() if a.published_rate_mm_yr_max is not None]
