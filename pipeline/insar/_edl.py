"""Earthdata Login token auth for the InSAR (ASF/HyP3) track.

The token lives in EARTHDATA_TOKEN (env var, or the repo .env which is
gitignored). It authenticates both asf_search (search/download) and the HyP3
API (job submission). hyp3_sdk's constructor only exposes username/password,
but the HyP3 API accepts the EDL bearer token on the session Authorization
header (verified against GET /user -> 200), so we inject it there.

Generate or refresh a token at https://urs.earthdata.nasa.gov/profile. Tokens
are ~60-day; see docs/setup-earthdata.md.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load_token() -> str:
    """EARTHDATA_TOKEN from the environment, falling back to the repo .env."""
    tok = os.environ.get("EARTHDATA_TOKEN")
    if tok:
        return tok.strip()
    env = REPO_ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            s = line.strip()
            if s.startswith("EARTHDATA_TOKEN=") and not s.startswith("#"):
                return s.split("=", 1)[1].strip()
    raise SystemExit(
        "No EARTHDATA_TOKEN in env or .env. Generate one at "
        "https://urs.earthdata.nasa.gov/profile (see docs/setup-earthdata.md)."
    )


def hyp3_client():
    """A hyp3_sdk.HyP3 client authenticated with the EDL bearer token.

    hyp3_sdk.HyP3.__init__ authenticates eagerly via
    hyp3_sdk.util.get_authenticated_session (netrc / EDL OAuth) and raises if it
    finds no username/password, so we cannot construct it and then inject a
    header. Instead we replace that session factory with one that returns a
    bearer-token session. The HyP3 API accepts the EDL token on the
    Authorization header (verified against GET /user -> 200), and this keeps the
    SDK's job-spec builders (submit_insar_job, etc.).
    """
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    import hyp3_sdk
    import hyp3_sdk.util as hyp3_util

    token = load_token()

    def _token_session(username=None, password=None, *args, **kwargs):
        s = requests.Session()
        s.headers.update({"Authorization": f"Bearer {token}"})
        # The SDK's normal session carries a urllib3 Retry; a plain Session does
        # not, so a stalled request hangs forever (it hung find_jobs for 5 min).
        # Add retries + a default timeout so calls fail fast and recover.
        retry = Retry(total=5, backoff_factor=1.0,
                      status_forcelist=[429, 500, 502, 503, 504], allowed_methods=None)
        adapter = HTTPAdapter(max_retries=retry)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _orig_request = s.request

        def _request(method, url, **kw):
            kw.setdefault("timeout", 60)
            return _orig_request(method, url, **kw)

        s.request = _request
        return s

    hyp3_util.get_authenticated_session = _token_session
    return hyp3_sdk.HyP3(prompt=False)


# Note on ASF downloads: pipeline.insar.search uses asf.geo_search, which needs
# no auth. HyP3 fetches its input SLCs server-side, and HyP3 output products are
# downloaded with the token-authed HyP3 session (batch.download_files()). So no
# asf_search session auth is on the critical path. asf_search's auth_with_token
# rejects this EDL user token ("Invalid/Expired") even though HyP3 accepts it; if
# an authenticated ASF Vertex download is ever needed, use EDL username/password
# for that call specifically.
