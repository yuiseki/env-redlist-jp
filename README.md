# env-redlist-jp

A reproducible copy of the CSV files of the 5th Red List of Japan's Ministry of the Environment (環境省 第５次レッドリスト).

The Red List assigns an extinction-risk category (EX, EW, CR, EN, VU, NT, DD, LP) to wild species in Japan, one CSV per taxon. The 5th edition is being published taxon by taxon:

- plants and fungi (vascular plants, bryophytes, algae, lichens, fungi), published 2025-03-18, files under `redlist2025/` on the server;
- birds, reptiles and amphibians, published 2026-03-17, files under `redlist2026/`.

The 2025 files have four columns (category, taxon group, Japanese name, scientific name) and one header line. The 2026 files have 178 columns and three header lines (column numbers, column groups, column names): the 5th-edition assessment, the names and categories of the same species in every earlier edition, habitat classes, regions and threats. Files are kept byte for byte as served. Their encoding differs from file to file (cp932 or UTF-8 with a BOM) and is recorded in the manifest.

Earlier editions (1991 to Red List 2020, the marine Red List) are on the same page but are not collected here, because no licence is stated for them. The Red Data Book texts (PDF) are not collected either.

## Source

- Listing page: <https://ikilog.biodic.go.jp/Rdb/booklist> (いきものログ, section 「第５次レッドリストについて（令和7年～）」). The download script reads the CSV links from that section only.
- Press releases: <https://www.env.go.jp/press/press_04578.html> (2025-03-18), <https://www.env.go.jp/press/press_03312.html> (2026-03-17).
- Publisher: Ministry of the Environment, Nature Conservation Bureau.

## Licence

The listing page states that the 5th Red List CSV files are published under the Creative Commons Attribution 4.0 International licence (CC BY 4.0, <https://creativecommons.org/licenses/by/4.0/>). Credit the source, for example: 環境省 第５次レッドリスト (いきものログ https://ikilog.biodic.go.jp/Rdb/booklist), CC BY 4.0.

## How to run

```sh
uv run python scripts/01_download.py   # fetch into data/raw/5th/
uv run python scripts/02_verify.py     # re-check hashes, encodings and record counts
uv run python -m pytest                # unit tests for the page parsing
```

`01_download.py` stops if the 5th-edition section or its CC BY 4.0 sentence is missing from the page. It skips files already in the manifest with a matching sha256, so running it again only fetches files that are new or changed. Requests are sequential and at least 1.5 seconds apart.

## Layout

```
scripts/01_download.py        fetch the CSVs listed in the 5th-edition section
scripts/02_verify.py          verify every file against its manifest
tests/                        unit tests; fixtures trimmed from the real page and files
data/raw/5th/                 the CSV files as served (not in git)
data/raw/5th/MANIFEST.json    per file: url, bytes, sha256, last_modified, fetched_at,
                              taxon, stated_size (as written on the page), release_date,
                              press_release, encoding, csv_records
```

`csv_records` counts every record the `csv` module reads, header lines included. The sizes written on the listing page (`stated_size`) do not match the real sizes for several files; `bytes` is the size actually served.
