import importlib.util
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"


def load(name: str):
    path = HERE.parent / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"mod_{name}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dl = load("01_download")
PAGE = (FIXTURES / "booklist_5th.html").read_text(encoding="utf-8")


def test_section_has_the_eight_csv_files_and_nothing_from_2020():
    s = dl.parse_fifth_section(PAGE, dl.PAGE_URL)
    names = [f["name"] for f in s["files"]]
    assert names == [
        "redlist2026_birds.csv",
        "redlist2026_reptiles.csv",
        "redlist2026_amphibian.csv",
        "redlist2025_ikansoku.csv",
        "redlist2025_sentairui.csv",
        "redlist2025_sorui.csv",
        "redlist2025_chiirui.csv",
        "redlist2025_kinrui.csv",
    ]


def test_urls_are_absolute_and_taxa_and_stated_sizes_come_from_the_row():
    s = dl.parse_fifth_section(PAGE, dl.PAGE_URL)
    birds = s["files"][0]
    assert birds["url"] == (
        "https://ikilog.biodic.go.jp/rdbdata/files/redlist2026/redlist2026_birds.csv"
    )
    assert birds["taxon"] == "鳥類"
    assert birds["stated_size"] == "CSV 543 KB"
    assert s["files"][-1]["taxon"] == "菌類"


def test_licence_sentence_is_found_in_the_section():
    s = dl.parse_fifth_section(PAGE, dl.PAGE_URL)
    assert "CC BY 4.0" in s["licence_statement"]
    assert s["heading"].startswith("第５次レッドリスト")


def test_press_releases_and_their_dates():
    s = dl.parse_fifth_section(PAGE, dl.PAGE_URL)
    assert s["press_releases"] == [
        {"url": "https://www.env.go.jp/press/press_04578.html", "date": "2025-03-18"},
        {"url": "https://www.env.go.jp/press/press_03312.html", "date": "2026-03-17"},
    ]


def test_each_file_gets_the_press_release_of_its_directory_year():
    s = dl.parse_fifth_section(PAGE, dl.PAGE_URL)
    by_name = {f["name"]: f for f in s["files"]}
    assert by_name["redlist2025_kinrui.csv"]["release_date"] == "2025-03-18"
    assert by_name["redlist2026_birds.csv"]["release_date"] == "2026-03-17"


def test_missing_section_is_an_error():
    with pytest.raises(ValueError):
        dl.parse_fifth_section("<html><h3>レッドリスト2020について</h3></html>", dl.PAGE_URL)


def test_section_without_licence_sentence_is_an_error():
    page = PAGE.replace("CC BY 4.0", "")
    with pytest.raises(ValueError):
        dl.parse_fifth_section(page, dl.PAGE_URL)


def test_wareki_date():
    assert dl.parse_date("報道発表資料（令和7(2025)年3月18日）") == "2025-03-18"
    assert dl.parse_date("報道発表資料") is None


def test_encoding_utf8_bom():
    assert dl.detect_encoding("﻿カテゴリー,学名\r\n".encode()) == "utf-8-sig"


def test_encoding_cp932():
    assert dl.detect_encoding("カテゴリー,学名\r\n".encode("cp932")) == "cp932"


def test_encoding_utf8_without_bom_is_named_as_such():
    assert dl.detect_encoding("カテゴリー,学名\n".encode()) == "utf-8"


def test_encoding_undecodable_is_an_error():
    with pytest.raises(ValueError):
        dl.detect_encoding(b"\x81\x7f\xff\xfe\x80")


def test_count_rows_handles_quoted_newlines_and_crlf():
    data = 'a,b\r\n1,"x\r\ny"\r\n2,z\r\n'.encode("cp932")
    assert dl.count_rows(data, "cp932") == 3


@pytest.mark.parametrize(
    ("fixture", "encoding", "rows"),
    [
        ("redlist2025_kinrui_head.csv", "cp932", 6),
        ("redlist2025_chiirui_head.csv", "utf-8-sig", 6),
    ],
)
def test_real_heads(fixture, encoding, rows):
    data = (FIXTURES / fixture).read_bytes()
    assert dl.detect_encoding(data) == encoding
    assert dl.count_rows(data, encoding) == rows
