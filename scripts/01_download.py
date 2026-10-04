#!/usr/bin/env python3
"""Fetch the CSV files of the Ministry of the Environment's 5th Red List.

The list of files is read from the section "第５次レッドリストについて" of
the Ikimono Log page https://ikilog.biodic.go.jp/Rdb/booklist . That section
says its CSV files are published under CC BY 4.0; the script refuses to run if
the sentence is gone. Earlier editions on the same page are not taken, since
no licence is stated for them.

The version is the edition, not a fetch date: the files live under
data/raw/5th/. The 5th edition is published taxon by taxon (plants and fungi
in 2025-03 under redlist2025/, birds, reptiles and amphibians in 2026-03 under
redlist2026/); a later batch on the page is picked up by running this again.

Each file is kept as served and accepted only if it has the Content-Length the
server states. data/raw/5th/MANIFEST.json records, per file, its URL, size,
sha256, Last-Modified, fetch time, the taxon and the size the page states, the
date of the press release for its year, its text encoding (cp932 or UTF-8
with a BOM) and the number of CSV records (header lines included; the 2026
files have three header lines, the 2025 files one). A file whose name is in
the manifest and whose sha256 still matches is not fetched again.

    uv run python scripts/01_download.py
"""

import csv
import hashlib
import io
import json
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION = "5th"
OUT = ROOT / "data" / "raw" / VERSION
PAGE_URL = "https://ikilog.biodic.go.jp/Rdb/booklist"
SECTION_PREFIX = "第５次レッドリスト"
UA = "env-redlist-jp/1 (+https://github.com/yuiseki/env-redlist-jp)"
DELAY = 1.5


class _SectionParser(HTMLParser):
    """Collect the text and links between the 5th-edition h3 and the next h3."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.heading: str | None = None
        self.in_h3 = False
        self.h3_text = ""
        self.inside = False
        self.done = False
        self.text: list[str] = []
        self.cell = ""  # text of the current <td>/<th>
        self.row_cells: list[str] = []
        self.href: str | None = None
        self.link_text = ""
        # (href, link text, cells of the row before the link)
        self.links: list[tuple[str, str, list[str]]] = []

    def handle_starttag(self, tag, attrs):
        if self.done:
            return
        if tag == "h3":
            self.in_h3, self.h3_text = True, ""
            return
        if not self.inside:
            return
        if tag == "tr":
            self.row_cells = []
        elif tag in ("td", "th"):
            self.cell = ""
        elif tag == "a":
            self.href = dict(attrs).get("href")
            self.link_text = ""

    def handle_endtag(self, tag):
        if self.done:
            return
        if tag == "h3" and self.in_h3:
            self.in_h3 = False
            title = self.h3_text.strip()
            if self.inside:
                self.done = True
            elif title.startswith(SECTION_PREFIX):
                self.inside, self.heading = True, title
            return
        if not self.inside:
            return
        if tag in ("td", "th"):
            self.row_cells.append(self.cell.strip())
        elif tag == "a" and self.href:
            self.links.append((self.href, self.link_text.strip(), list(self.row_cells)))
            self.href = None

    def handle_data(self, data):
        if self.done:
            return
        if self.in_h3:
            self.h3_text += data
        elif self.inside:
            self.text.append(data)
            self.cell += data
            if self.href:
                self.link_text += data


def parse_date(text: str) -> str | None:
    """'令和7(2025)年3月18日' -> '2025-03-18', using the western year in brackets."""
    m = re.search(r"[(（](\d{4})[)）]年(\d{1,2})月(\d{1,2})日", text)
    if not m:
        return None
    y, mo, d = (int(g) for g in m.groups())
    return f"{y:04d}-{mo:02d}-{d:02d}"


def parse_fifth_section(html: str, base_url: str) -> dict:
    """Return the heading, licence sentence, press releases and CSV files of the section."""
    p = _SectionParser()
    p.feed(html)
    p.close()
    if p.heading is None:
        raise ValueError(f"no h3 starting with {SECTION_PREFIX} on the page")
    text = "".join(p.text)
    sentences = [s.strip() for s in re.split(r"(?<=。)", text) if "CC BY 4.0" in s]
    if not sentences:
        raise ValueError("the 5th-edition section no longer states CC BY 4.0")

    press, files = [], []
    for href, label, cells in p.links:
        url = urllib.parse.urljoin(base_url, href)
        if "/press/" in url:
            press.append({"url": url, "date": parse_date(label)})
        elif urllib.parse.urlparse(url).path.lower().endswith(".csv"):
            size = re.search(r"\[(CSV[^\]]*?)\s*\]", label)
            files.append(
                {
                    "name": Path(urllib.parse.urlparse(url).path).name,
                    "url": url,
                    "taxon": cells[-1] if cells else "",
                    "stated_size": size.group(1) if size else None,
                }
            )
    if not files:
        raise ValueError("no CSV links in the 5th-edition section")
    names = [f["name"] for f in files]
    if len(set(names)) != len(names):
        raise ValueError(f"duplicate file names in the section: {names}")

    by_year = {r["date"][:4]: r for r in press if r["date"]}
    for f in files:
        m = re.search(r"redlist(\d{4})", f["url"])
        r = by_year.get(m.group(1)) if m else None
        f["release_date"] = r["date"] if r else None
        f["press_release"] = r["url"] if r else None
    return {
        "heading": p.heading,
        "licence_statement": sentences[0],
        "press_releases": press,
        "files": files,
    }


def detect_encoding(data: bytes) -> str:
    """'utf-8-sig' when there is a BOM, else 'utf-8' if it decodes, else 'cp932'."""
    if data.startswith(b"\xef\xbb\xbf"):
        data[3:].decode("utf-8")
        return "utf-8-sig"
    for enc in ("utf-8", "cp932"):
        try:
            data.decode(enc)
        except UnicodeDecodeError:
            continue
        return enc
    raise ValueError("neither UTF-8 nor cp932")


def count_rows(data: bytes, encoding: str) -> int:
    """Number of CSV records (header lines included), as the csv module reads them."""
    text = data.decode(encoding)
    return sum(1 for _ in csv.reader(io.StringIO(text, newline="")))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def fetch(url: str, dest: Path) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=300) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
        length = r.headers.get("Content-Length")
        lm = r.headers.get("Last-Modified", "")
    got = tmp.stat().st_size
    if length is not None and got != int(length):
        tmp.unlink()
        raise SystemExit(f"{url}: got {got} bytes, the server stated {length}")
    tmp.replace(dest)
    return {
        "url": url,
        "bytes": got,
        "sha256": sha256(dest),
        "last_modified": lm,
        "fetched_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def main() -> int:
    section = parse_fifth_section(get(PAGE_URL).decode("utf-8"), PAGE_URL)
    OUT.mkdir(parents=True, exist_ok=True)
    mpath = OUT / "MANIFEST.json"
    manifest = json.loads(mpath.read_text()) if mpath.exists() else {"files": {}}
    manifest["source"] = {
        "page": PAGE_URL,
        "section": section["heading"],
        "licence": "CC BY 4.0",
        "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "licence_statement": section["licence_statement"],
        "press_releases": section["press_releases"],
    }
    fetched = 0
    for f in section["files"]:
        dest = OUT / f["name"]
        old = manifest["files"].get(f["name"])
        if old and old["url"] == f["url"] and dest.exists() and sha256(dest) == old["sha256"]:
            continue
        time.sleep(DELAY)
        entry = fetch(f["url"], dest)
        data = dest.read_bytes()
        enc = detect_encoding(data)
        entry |= {
            "taxon": f["taxon"],
            "stated_size": f["stated_size"],
            "release_date": f["release_date"],
            "press_release": f["press_release"],
            "encoding": enc,
            "csv_records": count_rows(data, enc),
        }
        manifest["files"][f["name"]] = entry
        fetched += 1
        print(
            f"{VERSION}/{f['name']}: {entry['bytes']:,} bytes, {enc}, {entry['csv_records']} records"
        )
    mpath.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
    print(f"fetched {fetched}, already present {len(section['files']) - fetched}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
