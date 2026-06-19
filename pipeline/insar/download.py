"""Phase 0: poll the HyP3 batch and download finished InSAR products.

Run after submit_hyp3. HyP3 processes for 1-7 days. This finds the submitted
jobs by name, reports progress, and downloads + unzips the finished products
into data/insar/<aoi>/hyp3_products/, which is what MintPy reads (see
pipeline.insar.velocity).

    python -m pipeline.insar.download --aoi metro-manila           # status + grab whatever is ready
    python -m pipeline.insar.download --aoi metro-manila --watch   # block until all done, then download
"""

from __future__ import annotations

import argparse
import zipfile
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aoi", default="metro-manila")
    ap.add_argument("--watch", action="store_true", help="block and poll until all jobs finish")
    args = ap.parse_args()

    from pipeline.insar._edl import hyp3_client

    hyp3 = hyp3_client()
    batch = hyp3.find_jobs(name=f"sinkmap-{args.aoi}")
    if len(batch) == 0:
        raise SystemExit(f"no HyP3 jobs named sinkmap-{args.aoi}. Run submit_hyp3 first.")

    counts = Counter(j.status_code for j in batch)
    print(f"{len(batch)} jobs for {args.aoi}: {dict(counts)}")

    if args.watch and not batch.complete():
        print("watching until all jobs finish (HyP3 queues 1-7 days)...")
        batch = hyp3.watch(batch)

    succeeded = [j for j in batch if j.succeeded()]
    if not succeeded:
        print("nothing finished yet. Re-run later, or use --watch to block.")
        return

    out = REPO_ROOT / "data" / "insar" / args.aoi / "hyp3_products"
    out.mkdir(parents=True, exist_ok=True)

    downloaded = []
    for j in succeeded:
        downloaded += j.download_files(out)

    unzipped = 0
    for f in downloaded:
        f = Path(f)
        if f.suffix == ".zip":
            with zipfile.ZipFile(f) as z:
                z.extractall(out)
            unzipped += 1

    print(f"downloaded {len(downloaded)} products ({unzipped} unzipped) to {out}")
    print("next: install MintPy (conda), then "
          "`python -m pipeline.insar.velocity write-cfg --aoi {a} --ref-lat <stable> --ref-lon <stable>`, "
          "`smallbaselineApp.py <cfg>`, then velocity.py to-vertical, then validate."
          .format(a=args.aoi))


if __name__ == "__main__":
    main()
