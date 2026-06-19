"""Shared Earth Engine init for sinkmap.ph flood-extent derivation.

InSAR (subsidence) runs on ASF HyP3 + MintPy, NOT Earth Engine. This helper is
only for the flood pillar (pipeline/flood), which derives Sentinel-1 flood
extents in GEE.

Auth sources, in order (mirrors the leaves-ph pattern):
    1. Service-account key at SINKMAP_EE_KEY (env var pointing to a JSON file).
    2. Service-account key at <repo>/.ee-key.json (gitignored).
    3. Interactive credentials at ~/.config/earthengine/credentials.

Use the personal civic-project service account (e.g. the leaves-ph key, GCP
project poised-honor-217909). Never a work / Boost GCP project.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_initialised = False


def init() -> None:
    """Initialise Earth Engine. Idempotent."""
    global _initialised
    if _initialised:
        return

    import ee

    env_key = os.environ.get("SINKMAP_EE_KEY")
    if env_key and Path(env_key).exists():
        _init_service_account(env_key)
        _initialised = True
        return

    repo_key = REPO_ROOT / ".ee-key.json"
    if repo_key.exists():
        _init_service_account(str(repo_key))
        _initialised = True
        return

    interactive = Path.home() / ".config" / "earthengine" / "credentials"
    if interactive.exists():
        ee.Initialize()
        _initialised = True
        return

    raise RuntimeError(
        "Earth Engine not authenticated. Run `earthengine authenticate`, or set "
        "SINKMAP_EE_KEY to a service-account JSON, or place one at .ee-key.json. "
        "Use a personal civic-project account, never a work GCP project."
    )


def _init_service_account(key_path: str) -> None:
    import ee

    with open(key_path) as f:
        key = json.load(f)
    credentials = ee.ServiceAccountCredentials(key["client_email"], key_path)
    ee.Initialize(credentials)
