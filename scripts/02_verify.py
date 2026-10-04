#!/usr/bin/env python3
"""Check every file under data/raw/<version>/ against its MANIFEST.json.

For each file: size and sha256 must match, it must decode in the encoding the
manifest records, and the csv module must read the number of records the
manifest records. Zip and gzip files, if any appear, are tested to the end.
Prints one ok/FAIL line per file and exits 1 on any failure.

    uv run python scripts/02_verify.py
"""

import csv
import gzip
import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def check(path: Path, entry: dict) -> str | None:
    if not path.exists():
        return "missing"
    if path.stat().st_size != entry["bytes"]:
        return f"size {path.stat().st_size} != {entry['bytes']}"
    if sha256(path) != entry["sha256"]:
        return "sha256 mismatch"
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            bad = z.testzip()
        if bad:
            return f"bad zip member {bad}"
    if path.suffix == ".gz":
        with gzip.open(path) as g:
            while g.read(1 << 20):
                pass
    if path.suffix == ".csv":
        try:
            text = path.read_bytes().decode(entry["encoding"])
        except UnicodeDecodeError as e:
            return f"not {entry['encoding']}: {e}"
        n = sum(1 for _ in csv.reader(io.StringIO(text, newline="")))
        if n != entry["csv_records"]:
            return f"{n} records != {entry['csv_records']}"
    return None


def main() -> int:
    failures = 0
    manifests = sorted(RAW.glob("*/MANIFEST.json"))
    if not manifests:
        print("FAIL no manifest under data/raw/")
        return 1
    for mpath in manifests:
        d = mpath.parent
        files = json.loads(mpath.read_text())["files"]
        listed = set(files)
        for name, entry in sorted(files.items()):
            err = check(d / name, entry)
            if err:
                failures += 1
                print(f"FAIL {d.name}/{name}: {err}")
            else:
                extra = (
                    f", {entry['encoding']}, {entry['csv_records']} records"
                    if "encoding" in entry
                    else ""
                )
                print(f"ok   {d.name}/{name}: {entry['bytes']:,} bytes{extra}")
        for p in sorted(d.iterdir()):
            if p.name != "MANIFEST.json" and p.name not in listed:
                failures += 1
                print(f"FAIL {d.name}/{p.name}: not in the manifest")
    print(f"{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
