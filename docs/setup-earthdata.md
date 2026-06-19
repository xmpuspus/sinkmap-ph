# NASA Earthdata + ASF HyP3 setup

sinkmap.ph's subsidence pipeline (Phase 0) submits Sentinel-1 InSAR jobs to ASF
HyP3, which authenticates with a NASA Earthdata Login. The flood pillar uses
Google Earth Engine instead (see the leaves-ph `docs/setup-gee.md`); this doc is
only for the InSAR side. There is no credential to inherit from other projects;
this is a one-time, free setup.

## One-time Earthdata Login

1. Register a free account at https://urs.earthdata.nasa.gov/ (about 2 minutes).
2. In your Earthdata profile, under Applications -> Authorized Apps, authorize
   "Alaska Satellite Facility Data Access" (HyP3/Vertex downloads need it).

## ~/.netrc (what asf_search and hyp3_sdk read)

Create `~/.netrc` with your Earthdata credentials and lock it down:

```bash
cat >> ~/.netrc <<'EOF'
machine urs.earthdata.nasa.gov
    login YOUR_EARTHDATA_USERNAME
    password YOUR_EARTHDATA_PASSWORD
EOF
chmod 600 ~/.netrc
```

Both `asf_search` and `hyp3_sdk.HyP3()` pick this up with no further config. The
search step (`pipeline.insar.search`) needs no auth at all; only submission does.

## HyP3 account and credits

The first `hyp3.submit_insar_job(...)` auto-provisions a free HyP3 account. The
free tier carries a monthly credit allotment (about 8,000 credits/month at time
of writing). Each InSAR pair costs credits, so a full 10-year SBAS stack can take
1-2 months of the free allotment. Confirm current per-job cost against
https://hyp3-docs.asf.alaska.edu/using/credits/ and submit one AOI at a time.

## MintPy (separate, conda)

The time-series inversion (`pipeline.insar.velocity`) runs MintPy, which is not
pip-friendly (it pulls ISCE, GDAL, h5py). Install via conda/mamba per
https://github.com/insarlab/MintPy. MintPy itself needs no Earthdata login; it
reads the HyP3 products you already downloaded.

## Verify the chain

```bash
make search AOI=metro-manila          # no auth; should report the 325-scene track
make dry-run AOI=metro-manila         # no auth; should report 77 SBAS pairs
.venv/bin/python -m pipeline.insar.submit_hyp3 --aoi metro-manila   # needs ~/.netrc
```

## Troubleshooting

- 401 / "Unauthorized" on submit or download: check `~/.netrc` is `chmod 600` and
  the "Alaska Satellite Facility Data Access" app is authorized in your profile.
- "Quota exceeded" / out of credits: wait for the monthly reset or submit fewer
  pairs; one AOI at a time.
- Search works but submit fails: search needs no auth, submit does. The failure
  is the Earthdata login, not the query.
