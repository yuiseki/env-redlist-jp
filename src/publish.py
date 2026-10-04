#!/usr/bin/env python3
"""Push the card, the raw files and the Parquet to the Hugging Face Hub.

The raw CSVs go up unchanged, after their sha256 is checked against
data/raw/<version>/MANIFEST.json. Every Parquet file under data/parquet/ must
be declared as a subset in the card's configs, or nothing is sent.

    uv run python src/publish.py             # dry run: list the files and their size
    uv run python src/publish.py --push
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "yuiseki/env-redlist-jp"
DATA = ROOT / "data"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def declared(card: str) -> dict[str, str]:
    """config_name -> data_files, from the card's YAML front matter."""
    front = card.split("\n---\n", 1)[0] + "\n"
    return dict(re.findall(r"- config_name: '?([^'\n]+)'?\n  data_files: (\S+)\n", front))


def files_to_push() -> list[str]:
    card = (DATA / "README.md").read_text(encoding="utf-8")
    configs = declared(card)
    files = ["README.md", "LICENSE", "provenance.yaml"]
    parquet = sorted(p.relative_to(DATA).as_posix() for p in (DATA / "parquet").rglob("*.parquet"))
    if not parquet:
        raise SystemExit("no Parquet under data/parquet/; run scripts/03_export_parquet.py")
    missing = [p for p in parquet if p not in configs.values()]
    if missing:
        raise SystemExit(f"the card does not declare these files as subsets: {missing}")
    absent = [f for f in configs.values() if f not in parquet]
    if absent:
        raise SystemExit(f"the card declares files that do not exist: {absent}")
    for mpath in sorted((DATA / "raw").glob("*/MANIFEST.json")):
        d = mpath.parent
        for name, m in json.loads(mpath.read_text())["files"].items():
            if sha256(d / name) != m["sha256"]:
                raise SystemExit(f"raw/{d.name}/{name} is not the file in its manifest")
            files.append(f"raw/{d.name}/{name}")
        files.append(f"raw/{d.name}/MANIFEST.json")
    return files + parquet


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()

    files = files_to_push()
    total = sum((DATA / f).stat().st_size for f in files)
    print(a.repo)
    for f in files:
        print(f"  {(DATA / f).stat().st_size:>9,}  {f}")
    print(f"  {len(files)} files, {total:,} bytes ({total / 1e6:.2f} MB)")
    if not a.push:
        print("\ndry run. pass --push to upload")
        return 0

    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(a.repo, repo_type="dataset", exist_ok=True, private=False)
    api.upload_folder(
        folder_path=str(DATA), repo_id=a.repo, repo_type="dataset", allow_patterns=files
    )
    print(f"\npushed to https://huggingface.co/datasets/{a.repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
