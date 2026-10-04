#!/usr/bin/env python3
"""Turn each CSV of the 5th Red List into a Parquet file, one per taxon.

Each file is decoded in the encoding its MANIFEST.json records (cp932 or UTF-8
with a BOM) and read with Python's csv module. The 2025 files (plants and
fungi) have one header row, kept as the column names. The 2026 files (birds,
reptiles, amphibians) have three: column numbers 1 to 178, a column group, and
a column name. They are flattened into one name per column:

    group + "_" + name    when the group (row 2) is not empty
    name                  when it is empty (only the last column, 不明)

and the first row must hold the column's position (1, 2, ...), or the run
stops. The three rows are kept in the dataset card and in the Parquet's
key-value metadata (source_header_rows, JSON).

The type of a column comes from its flattened name, never from inference: the
habitat, region and threat columns of the 2026 files (names starting with
生息・生育環境区分, 国土地域区分_ or 存続を脅かす要因（現在）_, and the last
column 不明) are INTEGER, except their free-text columns (ending in
_その他自由記述). The source writes these as 0 or 1; any other value stops the
run with an error naming the file, the column and the value. Every other
column is the text of the CSV, unchanged: no category, bracket, numeral or
dash is normalised, and an empty field stays an empty string.

Rows keep the order of the CSV. Files are written with zstd and no bloom
filters to data/parquet/5th/<table>.parquet.

    uv run python scripts/03_export_parquet.py
"""

import csv
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "5th"
RAW = ROOT / "data" / "raw" / VERSION
OUT = ROOT / "data" / "parquet" / VERSION
WORK = ROOT / "data" / "work" / VERSION

# subset name -> (file, header rows)
TABLES = {
    "vascular_plants": ("redlist2025_ikansoku.csv", 1),
    "bryophytes": ("redlist2025_sentairui.csv", 1),
    "algae": ("redlist2025_sorui.csv", 1),
    "lichens": ("redlist2025_chiirui.csv", 1),
    "fungi": ("redlist2025_kinrui.csv", 1),
    "birds": ("redlist2026_birds.csv", 3),
    "reptiles": ("redlist2026_reptiles.csv", 3),
    "amphibians": ("redlist2026_amphibian.csv", 3),
}

FLAG_PREFIXES = ("生息・生育環境区分", "国土地域区分_", "存続を脅かす要因（現在）_")
FLAG_NAMES = ("不明",)
FREE_TEXT_SUFFIX = "_その他自由記述"


def column_type(name: str) -> str:
    if name.endswith(FREE_TEXT_SUFFIX):
        return "VARCHAR"
    if name in FLAG_NAMES or name.startswith(FLAG_PREFIXES):
        return "INTEGER"
    return "VARCHAR"


def flatten(header_rows: list[list[str]]) -> list[str]:
    """One name per column from the header rows (see the module docstring)."""
    if len(header_rows) == 1:
        return list(header_rows[0])
    numbers, groups, names = header_rows
    out = []
    for i, (num, group, name) in enumerate(zip(numbers, groups, names, strict=True)):
        if num != str(i + 1):
            raise ValueError(f"column {i + 1}: the number row holds {num!r}")
        out.append(f"{group}_{name}" if group else name)
    return out


def check_names(names: list[str]) -> None:
    """DuckDB matches names without case; a clash or an empty name stops the run."""
    seen: dict[str, str] = {}
    for n in names:
        if not n:
            raise ValueError("an empty column name")
        if n.lower() in seen:
            raise ValueError(f"column {n!r} clashes with {seen[n.lower()]!r}")
        seen[n.lower()] = n


def read_source(path: Path, encoding: str, header_rows: int):
    """(header rows, flattened names, data rows), every row as wide as the header."""
    text = path.read_bytes().decode(encoding)
    rows = list(csv.reader(io.StringIO(text, newline="")))
    header, data = rows[:header_rows], rows[header_rows:]
    names = flatten(header)
    check_names(names)
    for i, r in enumerate(data, start=header_rows + 1):
        if len(r) != len(names):
            raise ValueError(f"{path.name}: record {i} has {len(r)} fields, not {len(names)}")
    return header, names, data


def write_work_csv(path: Path, names: list[str], rows: list[list[str]]) -> None:
    """UTF-8, every field quoted, so DuckDB keeps empty strings as they are."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL, lineterminator="\n")
        w.writerow(names)
        w.writerows(rows)


def _q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def _ident(s: str) -> str:
    return '"' + s.replace('"', '""') + '"'


def _expr(source: str, name: str) -> str:
    c = _ident(name)
    if column_type(name) == "VARCHAR":
        return c
    msg = _q(f"{source}: {name} is not 0 or 1: ")
    return (
        f"case when regexp_full_match({c}, '[01]') then cast({c} as integer) "
        f"else error({msg} || coalesce({c}, 'NULL')) end"
    )


def select_sql(work: Path, source: str, names: list[str]) -> str:
    cols = "{" + ", ".join(f"{_q(n)}: 'VARCHAR'" for n in names) + "}"
    src = (
        f"read_csv({_q(str(work))}, header = true, columns = {cols}, delim = ',', "
        "quote = '\"', escape = '\"', allow_quoted_nulls = false, strict_mode = true, "
        "auto_detect = false)"
    )
    sel = ", ".join(f"{_expr(source, n)} as {_ident(n)}" for n in names)
    return f"select {sel} from {src}"


def main() -> int:
    import duckdb

    manifest = json.loads((RAW / "MANIFEST.json").read_text())["files"]
    con = duckdb.connect()
    con.execute("set memory_limit = '8GB'")
    OUT.mkdir(parents=True, exist_ok=True)
    for table, (fname, nhead) in TABLES.items():
        entry = manifest[fname]
        header, names, rows = read_source(RAW / fname, entry["encoding"], nhead)
        if len(rows) + nhead != entry["csv_records"]:
            raise SystemExit(
                f"{fname}: {len(rows) + nhead} records, manifest says {entry['csv_records']}"
            )
        work = WORK / f"{table}.csv"
        write_work_csv(work, names, rows)
        p = OUT / f"{table}.parquet"
        meta = json.dumps(header, ensure_ascii=False)
        con.execute(
            f"copy ({select_sql(work, fname, names)}) to {_q(str(p))} "
            "(format parquet, compression zstd, write_bloom_filter false, "
            f"kv_metadata {{source_file: {_q(fname)}, source_header_rows: {_q(meta)}}})"
        )
        got = con.sql(f"select count(*) from {_q(str(p))}").fetchone()[0]
        if got != len(rows):
            raise SystemExit(f"{table}: {got} rows written, the CSV has {len(rows)}")
        work.unlink()
        n_int = sum(column_type(n) == "INTEGER" for n in names)
        print(f"{table}: {got:,} rows, {len(names)} columns ({n_int} INTEGER), "
              f"{p.stat().st_size:,} bytes", flush=True)  # fmt: skip
    for d in (WORK, WORK.parent):
        if d.exists() and not any(d.iterdir()):
            d.rmdir()
    return 0


if __name__ == "__main__":
    sys.exit(main())
