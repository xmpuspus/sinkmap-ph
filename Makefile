.PHONY: venv search dry-run submit status download test e2e validate serve clean

PY := .venv/bin/python
AOI ?= metro-manila

venv:
	python3 -m venv .venv && .venv/bin/pip install -q -U pip && .venv/bin/pip install -q -r requirements.txt

# Phase 0 recon: find the Sentinel-1 descending SLC stack (no auth needed).
search:
	$(PY) -m pipeline.insar.search --aoi $(AOI) --start 2016-01-01 --end 2026-01-01 --direction DESCENDING

# Inspect the SBAS pair plan + credit footprint without submitting.
dry-run:
	$(PY) -m pipeline.insar.submit_hyp3 --aoi $(AOI) --dry-run

# Submit the SBAS stack to HyP3 (needs EARTHDATA_TOKEN in env/.env). Spends credits.
submit:
	$(PY) -m pipeline.insar.submit_hyp3 --aoi $(AOI)

# Check job status and download whatever has finished.
status:
	$(PY) -m pipeline.insar.download --aoi $(AOI)

# Block until all jobs finish, then download + unzip products for MintPy.
download:
	$(PY) -m pipeline.insar.download --aoi $(AOI) --watch

# Gate check against the published anchor (pass a computed value or a raster).
validate:
	$(PY) -m pipeline.insar.validate --aoi $(AOI) $(if $(VALUE),--value $(VALUE),--raster $(RASTER))

test:
	$(PY) -m pytest tests/ -q

# Behavioral e2e for the web map (run `make serve` first; needs agent-browser).
# Test the live site with: make e2e BASE=https://sinkmap-ph.vercel.app
BASE ?= http://localhost:8788
e2e:
	zsh tests/e2e.sh $(BASE)

serve:
	$(PY) web/serve.py

clean:
	rm -rf .venv data/insar/*/hyp3_products mintpy_run __pycache__ .pytest_cache
