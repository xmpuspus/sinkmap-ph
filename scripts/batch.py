"""Batch InSAR runner: drive multiple AOIs from recon to submission, resumable.

Wraps the existing Phase-0 modules (pipeline.insar.search / submit_hyp3 / _edl)
with credit planning and a state file so a fleet of cities can be launched and
resumed. Recon and planning need no auth and spend nothing; submit spends HyP3
credits (10/pair, GAMMA) and queues 1-7 days. Download + MintPy come later (the
HyP3 queue is days), so this stops after submission and records state.

  # plan only (no auth, no spend): recon + credit estimate within a budget
  .venv/bin/python scripts/batch.py plan --budget 4000 dagupan bacolod cagayan-de-oro
  # submit the cities that fit the budget (spends credits)
  .venv/bin/python scripts/batch.py submit --budget 4000 dagupan bacolod cagayan-de-oro
  # poll submitted jobs
  .venv/bin/python scripts/batch.py status

State: data/insar/batch_state.json  (per-AOI: queued/reconned/submitted/...).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from pipeline.insar import search as search_mod  # noqa: E402
from pipeline.insar.submit_hyp3 import build_pairs  # noqa: E402

STATE = ROOT / "data" / "insar" / "batch_state.json"
CREDITS_PER_PAIR = 10  # INSAR_GAMMA 20x4 looks
CONNECTIONS, MAX_DAYS = 3, 200


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state():
    return json.loads(STATE.read_text()) if STATE.exists() else {"aois": {}}


def save_state(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2))


def recon(aoi_id, refresh=False):
    """Ensure data/insar/<aoi>/scenes.json exists (ASF search, no auth). Returns
    {scenes, pairs, credits, track}."""
    sj = ROOT / "data" / "insar" / aoi_id / "scenes.json"
    if sj.exists() and not refresh:
        data = json.loads(sj.read_text())
    else:
        data = search_mod.search(aoi_id, "2016-01-01", "2026-01-01", "DESCENDING")
        sj.parent.mkdir(parents=True, exist_ok=True)
        sj.write_text(json.dumps(data, indent=2))
    subsampled = data.get("scenes_subsampled", [])
    pairs = build_pairs(subsampled, CONNECTIONS, MAX_DAYS)
    return {"scenes": len(subsampled), "pairs": len(pairs),
            "credits": len(pairs) * CREDITS_PER_PAIR, "track": data.get("chosen_track"),
            "date_min": subsampled[0]["date"] if subsampled else None,
            "date_max": subsampled[-1]["date"] if subsampled else None}


def plan(aoi_ids, budget):
    """Recon each AOI; greedily select (in the given priority order) what fits."""
    rows, picked, spent = [], [], 0
    for aid in aoi_ids:
        r = recon(aid)
        fits = (spent + r["credits"]) <= budget and r["pairs"] > 0
        if fits:
            picked.append(aid); spent += r["credits"]
        rows.append({"aoi": aid, **r, "fits_budget": fits})
        flag = "PICK" if fits else ("skip-budget" if r["pairs"] else "skip-no-scenes")
        print(f"{aid:18} track {str(r['track']):>4}  {r['scenes']:>3} scenes  "
              f"{r['pairs']:>3} pairs  ~{r['credits']:>4} cr  {r['date_min']}..{r['date_max']}  [{flag}]")
    print(f"\nselected {len(picked)} AOIs, ~{spent} credits of {budget} budget: {', '.join(picked)}")
    return rows, picked, spent


def submit(aoi_ids, budget):
    import hyp3_sdk
    from pipeline.insar._edl import hyp3_client
    rows, picked, spent = plan(aoi_ids, budget)
    if not picked:
        print("nothing fits the budget; submitting nothing."); return
    hyp3 = hyp3_client()
    have = hyp3.check_credits()
    if have is not None and have < spent:
        raise SystemExit(f"plan needs ~{spent} credits but only {have} available; narrow the list.")
    st = load_state()
    for aid in picked:
        sj = ROOT / "data" / "insar" / aid / "scenes.json"
        data = json.loads(sj.read_text())
        pairs = build_pairs(data["scenes_subsampled"], CONNECTIONS, MAX_DAYS)
        batch = hyp3_sdk.Batch()
        for ref, sec in pairs:
            batch += hyp3.submit_insar_job(ref, sec, name=f"sinkmap-{aid}",
                                           include_dem=True, include_look_vectors=True)
        (sj.parent / "hyp3_batch.json").write_text(
            json.dumps([j.to_dict() for j in batch.jobs], indent=2, default=str))
        st["aois"][aid] = {"state": "submitted", "n_jobs": len(batch),
                           "job_name": f"sinkmap-{aid}", "submitted_at": _now(),
                           "track": data.get("chosen_track")}
        save_state(st)
        print(f"submitted {len(batch):>3} jobs for {aid} (sinkmap-{aid})")
    rem = hyp3.check_credits()
    print(f"\ndone. remaining credits: {rem}. Jobs queue 1-7 days; "
          f"resume with `scripts/batch.py status`, then download + MintPy.")


def process(aoi_ids):
    """Download finished HyP3 products, then run the MintPy -> vertical -> gate
    chain (pipeline/insar/process.py) per AOI. Resumable: download skips what is
    already local; process overwrites. Run in/with the MintPy env on PATH for the
    process step (it shells the MintPy-env python itself)."""
    import subprocess
    mp = str(Path.home() / "anaconda3" / "envs" / "sinkmap-mintpy312" / "bin" / "python")
    st = load_state()
    for aid in aoi_ids:
        print(f"=== {aid}: download ===", flush=True)
        subprocess.run([".venv/bin/python", "-m", "pipeline.insar.download",
                        "--aoi", aid, "--watch"], cwd=str(ROOT))
        print(f"=== {aid}: MintPy + gate ===", flush=True)
        rc = subprocess.run([mp, "pipeline/insar/process.py", aid], cwd=str(ROOT)).returncode
        res = ROOT / "tmp" / "phase2" / f"{aid}-result.json"
        st["aois"].setdefault(aid, {})["state"] = "processed" if rc == 0 else "process-failed"
        if res.exists():
            st["aois"][aid]["result"] = json.loads(res.read_text())
        save_state(st)


def status():
    from pipeline.insar._edl import hyp3_client
    st = load_state()
    if not st["aois"]:
        print("no submitted batches in state."); return
    hyp3 = hyp3_client()
    for aid, info in st["aois"].items():
        if info.get("state") != "submitted":
            print(f"{aid:18} {info.get('state')}"); continue
        jobs = hyp3.find_jobs(name=info["job_name"])
        done = sum(1 for j in jobs if j.succeeded())
        run = sum(1 for j in jobs if j.running())
        fail = sum(1 for j in jobs if j.failed())
        print(f"{aid:18} {len(jobs)} jobs: {done} succeeded, {run} running, {fail} failed")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("cmd", choices=["plan", "submit", "status", "recon", "process"])
    ap.add_argument("aois", nargs="*")
    ap.add_argument("--budget", type=int, default=4000, help="HyP3 credit budget")
    args = ap.parse_args()
    if args.cmd == "recon":
        for a in args.aois:
            print(a, recon(a, refresh=True))
    elif args.cmd == "plan":
        plan(args.aois, args.budget)
    elif args.cmd == "submit":
        submit(args.aois, args.budget)
    elif args.cmd == "process":
        process(args.aois)
    elif args.cmd == "status":
        status()


if __name__ == "__main__":
    main()
