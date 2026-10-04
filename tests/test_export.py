import importlib.util
from pathlib import Path

import duckdb
import pytest

_spec = importlib.util.spec_from_file_location(
    "export", Path(__file__).parents[1] / "scripts" / "03_export_parquet.py"
)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)


@pytest.mark.parametrize(
    ("name", "sql"),
    [
        ("生息・生育環境区分（陸域（山地・丘陵）細区分）_森林", "INTEGER"),
        ("生息・生育環境区分（海域（外洋）中区分）_その他", "INTEGER"),
        ("国土地域区分_都市地域", "INTEGER"),
        ("国土地域区分_不明", "INTEGER"),
        ("存続を脅かす要因（現在）_気候変動", "INTEGER"),
        ("不明", "INTEGER"),
        ("生息・生育環境区分（陸域（山地・丘陵）細区分）_その他自由記述", "VARCHAR"),
        ("存続を脅かす要因（現在）_その他自由記述", "VARCHAR"),
        ("5thRL_掲載No.", "VARCHAR"),
        ("5thRL_カテゴリーENG", "VARCHAR"),
        ("RL2020_カテゴリー", "VARCHAR"),
        ("1stRL_学名", "VARCHAR"),
        ("カテゴリー", "VARCHAR"),
        ("学名", "VARCHAR"),
        ("a_column_nobody_knows", "VARCHAR"),
    ],
)
def test_column_type(name, sql):
    assert m.column_type(name) == sql


def test_flatten_joins_group_and_name_and_keeps_a_lone_name():
    rows = [
        ["1", "2", "3"],
        ["5thRL", "国土地域区分", ""],
        ["掲載No.", "不明", "不明"],
    ]
    assert m.flatten(rows) == ["5thRL_掲載No.", "国土地域区分_不明", "不明"]


def test_flatten_one_header_row_is_kept_as_is():
    assert m.flatten([["カテゴリー", "分類群", "和名", "学名"]]) == [
        "カテゴリー",
        "分類群",
        "和名",
        "学名",
    ]


def test_flatten_refuses_a_column_number_out_of_place():
    with pytest.raises(ValueError, match="column 2"):
        m.flatten([["1", "3"], ["a", "a"], ["x", "y"]])


@pytest.mark.parametrize(
    "names",
    [["和名", "和名"], ["abc", "ABC"], ["", "x"]],
)
def test_names_that_clash_or_are_empty_stop_the_build(names):
    with pytest.raises(ValueError):
        m.check_names(names)


def _rel(tmp_path, names, rows):
    f = tmp_path / "t.csv"
    m.write_work_csv(f, names, rows)
    return duckdb.connect().sql(m.select_sql(f, "t.csv", names))


NAMES = [
    "5thRL_掲載No.",
    "国土地域区分_都市地域",
    "不明",
    "存続を脅かす要因（現在）_その他自由記述",
]


def test_values_are_typed_and_text_stays_as_written(tmp_path):
    rel = _rel(tmp_path, NAMES, [["BI0001", "1", "0", "―"], ["BI0002", "0", "1", ' a, b"c ']])
    assert rel.types == ["VARCHAR", "INTEGER", "INTEGER", "VARCHAR"]
    assert rel.fetchall() == [("BI0001", 1, 0, "―"), ("BI0002", 0, 1, ' a, b"c ')]


def test_an_empty_text_value_stays_an_empty_string(tmp_path):
    rel = _rel(tmp_path, ["学名", "和名"], [["", "x"]])
    assert rel.fetchall() == [("", "x")]


@pytest.mark.parametrize("bad", ["2", "", "１", "1.0", " 1", "-"])
def test_a_value_that_is_not_0_or_1_stops_the_build(tmp_path, bad):
    with pytest.raises(duckdb.Error, match=r"t\.csv: 国土地域区分_都市地域 is not 0 or 1: "):
        _rel(tmp_path, NAMES, [["BI0001", bad, "0", "―"]]).fetchall()


def test_read_source_flattens_the_2026_layout(tmp_path):
    f = tmp_path / "s.csv"
    f.write_bytes(
        "\ufeff1,2,3\r\n5thRL,国土地域区分,\r\n掲載No.,不明,不明\r\nBI0001,1,0\r\n".encode()
    )
    header, names, rows = m.read_source(f, "utf-8-sig", 3)
    assert header[1] == ["5thRL", "国土地域区分", ""]
    assert names == ["5thRL_掲載No.", "国土地域区分_不明", "不明"]
    assert rows == [["BI0001", "1", "0"]]


def test_read_source_decodes_cp932_and_refuses_a_short_row(tmp_path):
    f = tmp_path / "s.csv"
    f.write_bytes("カテゴリー,和名\r\n絶滅危惧ⅠＡ類（CR）,ア\r\n".encode("cp932"))
    _, names, rows = m.read_source(f, "cp932", 1)
    assert names == ["カテゴリー", "和名"] and rows == [["絶滅危惧ⅠＡ類（CR）", "ア"]]
    f.write_bytes("カテゴリー,和名\r\n絶滅（EX）\r\n".encode("cp932"))
    with pytest.raises(ValueError, match="1 fields"):
        m.read_source(f, "cp932", 1)
