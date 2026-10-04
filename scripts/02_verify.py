#!/usr/bin/env python3
"""Check the raw files against MANIFEST.json, then the Parquet against the raw files.

Raw, for each file under data/raw/<version>/: size and sha256 must match, it
must decode in the encoding the manifest records, and the csv module must read
the number of records the manifest records. Zip and gzip files, if any appear,
are tested to the end.

Parquet, for each table of scripts/03_export_parquet.py (data/parquet/5th/):
  - its rows equal the data records the csv module reads from the raw file,
    and the pinned count
  - the column names are the flattened header of the raw file, in order
  - every column has the type column_type gives its name
  - every value equals the raw value (integers compared as their text), and a
    sha256 over all values is the same on both sides
  - the source header rows in the key-value metadata equal the raw header rows
  - a plain DuckDB, with no extension loaded, opens it
  - no row group carries a bloom filter

Prints one ok/FAIL line per check and exits 1 on any failure.

    uv run python scripts/02_verify.py
"""

import csv
import gzip
import hashlib
import importlib.util
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PQ = ROOT / "data" / "parquet"
EXPECTED_ROWS = {
    "vascular_plants": 2222, "bryophytes": 289, "algae": 178, "lichens": 153,
    "fungi": 110, "birds": 170, "reptiles": 63, "amphibians": 77,
}  # fmt: skip

_spec = importlib.util.spec_from_file_location("export", ROOT / "scripts" / "03_export_parquet.py")
export = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(export)


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


def values_digest(rows) -> str:
    h = hashlib.sha256()
    for r in rows:
        h.update("\x1f".join(r).encode())
        h.update(b"\x1e")
    return h.hexdigest()


def check_parquet() -> int:
    import duckdb

    failures = 0

    def ok(cond: bool, what: str) -> None:
        nonlocal failures
        print(("ok   " if cond else "FAIL ") + what)
        failures += not cond

    manifest = json.loads((RAW / export.VERSION / "MANIFEST.json").read_text())["files"]
    con = duckdb.connect()
    con.execute("set memory_limit = '8GB'")
    for table, (fname, nhead) in export.TABLES.items():
        p = PQ / export.VERSION / f"{table}.parquet"
        if not p.exists():
            ok(False, f"{table}: {p.relative_to(ROOT)} missing")
            continue
        q = export._q(str(p))
        header, names, raw = export.read_source(
            RAW / export.VERSION / fname, manifest[fname]["encoding"], nhead
        )
        rel = con.sql(f"select * from {q}")
        rows = rel.fetchall()
        ok(len(rows) == len(raw) == EXPECTED_ROWS[table],
           f"{table}: {len(rows):,} rows, {len(raw):,} in {fname} by the csv module")  # fmt: skip
        ok(rel.columns == names, f"{table}: {len(names)} column names as flattened from the CSV")
        wrong = {
            c: t for c, t in zip(rel.columns, map(str, rel.types), strict=True)
            if t != export.column_type(c)
        }  # fmt: skip
        ok(not wrong, f"{table}: every column has its type ({wrong or 'as the rule gives'})")
        as_text = [[v if isinstance(v, str) else str(v) for v in r] for r in rows]
        a, b = values_digest(raw), values_digest(as_text)
        ok(as_text == raw and a == b, f"{table}: every value as in the CSV (sha256 {b[:16]})")
        meta = dict(
            con.sql(f"select decode(key), decode(value) from parquet_kv_metadata({q})").fetchall()
        )
        ok(json.loads(meta.get("source_header_rows", "null")) == header,
           f"{table}: {len(header)} source header row(s) kept in the metadata")  # fmt: skip
        plain = duckdb.connect()
        n = plain.sql(f"select count(*) from {q}").fetchone()[0]
        extra = plain.sql(
            "select count(*) from duckdb_extensions() "
            "where loaded and install_mode <> 'STATICALLY_LINKED'"
        ).fetchone()[0]
        ok(n == len(raw) and extra == 0,
           f"{table}: a plain DuckDB opens it (only built-in extensions loaded)")  # fmt: skip
        bloom = con.sql(
            f"select count(*) filter (where bloom_filter_offset is not null) from parquet_metadata({q})"
        ).fetchone()[0]
        ok(bloom == 0, f"{table}: no bloom filters")
    return failures


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
    failures += check_parquet()
    print(f"{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
