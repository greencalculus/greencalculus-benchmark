#!/usr/bin/env python3
"""Upload the built configs to the HuggingFace Hub.

Requires HF_TOKEN in the environment (see ~/.gc-secrets).

The guard below is the point of this file. CI protects git from the held-out
set; nothing protects an upload, and an upload is exactly how it would leak —
one careless push and a public pre-registration becomes unhonourable.
"""
import json, os, sys
from pathlib import Path

REPO = "greencalculus/emission-factor-benchmark"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def guard():
    """Refuse to upload if anything carries a held-out id, or if the private
    file has somehow landed inside the upload directory."""
    hp = ROOT / "holdout.json"
    if not hp.exists():
        sys.exit("holdout.json not found — cannot verify the upload is clean. "
                 "Clone greencalculus/benchmark-holdout first.")
    banned = {q["id"] for q in json.loads(hp.read_text(encoding="utf-8"))["questions"]}

    stray = [p for p in HERE.rglob("*") if p.name in ("holdout.json", "holdout-manifest.json")]
    if stray:
        sys.exit(f"held-out artefacts inside the upload dir: {stray}")

    checked = 0
    for f in (HERE / "data").rglob("train.jsonl"):
        for line in f.read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            for k in ("id", "question_id"):
                if r.get(k) in banned:
                    sys.exit(f"HELD-OUT LEAK in {f.name}: {r[k]}")
            checked += 1
    print(f"  guard: {checked} rows checked, 0 held-out ids, no stray files")
    return checked


def main():
    # The guard runs FIRST and needs no credentials, so --dry-run is a real
    # test of the thing that matters rather than a test of whether a token
    # happens to be loaded.
    n = guard()
    if "--dry-run" in sys.argv:
        print(f"  dry run — {n} rows would upload to {REPO}")
        return

    tok = os.environ.get("HF_TOKEN")
    if not tok:
        sys.exit("HF_TOKEN is not set. Add it to ~/.gc-secrets and open a new shell.")
    try:
        from huggingface_hub import HfApi
    except ImportError:
        sys.exit("pip install huggingface_hub")

    api = HfApi(token=tok)
    api.create_repo(REPO, repo_type="dataset", exist_ok=True, private=False)
    api.upload_folder(
        folder_path=str(HERE), repo_id=REPO, repo_type="dataset",
        # push.py and build.py live in the benchmark repo, not the dataset repo.
        ignore_patterns=["*.py", "__pycache__/*"],
        commit_message="Emission-factor benchmark: 3,299 rows across 5 configs",
    )
    print(f"  pushed → https://huggingface.co/datasets/{REPO}")


if __name__ == "__main__":
    main()
