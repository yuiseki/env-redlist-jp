---
license: cc-by-4.0
language:
- ja
- en
pretty_name: Red List of Japan, 5th edition (Ministry of the Environment)
task_categories:
- tabular-classification
tags:
- biodiversity
- red-list
- threatened-species
- conservation
- japan
- species
size_categories:
- 1K<n<10K
configs:
- config_name: vascular_plants
  data_files: parquet/5th/vascular_plants.parquet
  default: true
- config_name: bryophytes
  data_files: parquet/5th/bryophytes.parquet
- config_name: algae
  data_files: parquet/5th/algae.parquet
- config_name: lichens
  data_files: parquet/5th/lichens.parquet
- config_name: fungi
  data_files: parquet/5th/fungi.parquet
- config_name: birds
  data_files: parquet/5th/birds.parquet
- config_name: reptiles
  data_files: parquet/5th/reptiles.parquet
- config_name: amphibians
  data_files: parquet/5th/amphibians.parquet
---

# env-redlist-jp

The 5th Red List of Japan (環境省 第５次レッドリスト), published by the
Ministry of the Environment, Nature Conservation Bureau. A Red List assigns
each wild species of Japan that is at risk an extinction-risk category (EX,
EW, CR, EN, VU, NT, DD, LP). The Ministry publishes one CSV per taxon on its
Ikimono Log site; this dataset keeps those CSVs byte for byte and gives each
taxon a Parquet subset beside them.

CC BY 4.0, as stated on the source page, with credit to the Ministry of the
Environment (see Licence).

## Versions

The 5th edition replaces the 4th edition and its revisions (Red List 2015 to
2020), but it is being published taxon by taxon:

| batch | published | taxa | press release |
|---|---|---|---|
| plants and fungi | 2025-03-18 | vascular plants, bryophytes, algae, lichens, fungi | https://www.env.go.jp/press/press_04578.html |
| animals, first batch | 2026-03-17 | birds, reptiles, amphibians | https://www.env.go.jp/press/press_03312.html |

The other animals (mammals, fishes, insects, molluscs and other
invertebrates) are not in the 5th edition yet; the source page says they will
follow from fiscal 2026, and until then their latest list is Red List 2020
(marine species: the marine Red List of 2017). Those older lists are on the
same page but are not here, because the page states no licence for them.

There is one version, `5th`. A later batch of the 5th edition would be added
under it as new subsets.

## Subsets

| subset | rows | columns | raw file | encoding | header rows |
|---|---:|---:|---|---|---:|
| `vascular_plants` (維管束植物) | 2,222 | 4 | `raw/5th/redlist2025_ikansoku.csv` | cp932 | 1 |
| `bryophytes` (蘚苔類) | 289 | 4 | `raw/5th/redlist2025_sentairui.csv` | cp932 | 1 |
| `algae` (藻類) | 178 | 4 | `raw/5th/redlist2025_sorui.csv` | cp932 | 1 |
| `lichens` (地衣類) | 153 | 4 | `raw/5th/redlist2025_chiirui.csv` | UTF-8 with BOM | 1 |
| `fungi` (菌類) | 110 | 4 | `raw/5th/redlist2025_kinrui.csv` | cp932 | 1 |
| `birds` (鳥類) | 170 | 178 | `raw/5th/redlist2026_birds.csv` | UTF-8 with BOM | 3 |
| `reptiles` (爬虫類) | 63 | 178 | `raw/5th/redlist2026_reptiles.csv` | UTF-8 with BOM | 3 |
| `amphibians` (両生類) | 77 | 178 | `raw/5th/redlist2026_amphibian.csv` | UTF-8 with BOM | 3 |

One row is one listed species, subspecies or local population. Rows keep the
order of the CSV. All raw files use CRLF line endings.
`raw/5th/MANIFEST.json` gives each file's URL, size, sha256, Last-Modified,
fetch time, encoding and record count (header rows included).

## Columns and types

The column names are the Japanese names the source writes. In the Parquet the
type comes from the column's name, never from inference: the 0 or 1 columns of
the 2026 files are INTEGER, and every other column is the text of the CSV,
unchanged.

### 2025 files (plants and fungi)

| column | type | content |
|---|---|---|
| `カテゴリー` | VARCHAR | category in Japanese with the abbreviation in brackets, e.g. `絶滅危惧Ⅱ類（VU）` |
| `分類群` | VARCHAR | taxon, the same on every row of a file (e.g. `維管束植物`) |
| `和名` | VARCHAR | Japanese name |
| `学名` | VARCHAR | scientific name |

### 2026 files (birds, reptiles, amphibians)

The three files have the same 178 columns and the same three header rows. Row
1 numbers the columns 1 to 178, row 2 names a group, row 3 names the column.
They are flattened into one name per column by this rule:

- `<row 2>_<row 3>` when row 2 is not empty, e.g. `5thRL_学名`,
  `RL2020_カテゴリー`, `国土地域区分_都市地域`;
- `<row 3>` alone when row 2 is empty, which happens only for the last
  column, `不明`.

Row 1 is dropped from the names after checking that it holds each column's
position. The flattened names are unique, also when compared without case.
The original three rows are listed in full below and are kept in each
Parquet file's key-value metadata as `source_header_rows` (a JSON array of
three arrays).

| columns (0-based) | group (row 2) | names (row 3) | type |
|---|---|---|---|
| 0 to 8 | `5thRL` | `掲載No.` (listing id, e.g. `BI0001`, `RE0001`, `AM0001`), `分科会名` (working group), `カテゴリーJPN`, `カテゴリーENG`, `目名` (order), `科名` (family), `和名`, `学名`, `判定基準` (criteria) | VARCHAR |
| 9 to 35 | `RL2020`, `RL2019`, `RL2018`, `RL2017`, `RL2015`, `4thRL`, `3rdRL`, `2ndRL`, `1stRL` | `和名`, `学名`, `カテゴリー` for each earlier edition | VARCHAR |
| 36 to 121 | `生息・生育環境区分（...）`, eight groups: land (mountains and hills; plains and coasts) and sea (coastal; open ocean), each with a middle and a fine class | habitat classes, e.g. `森林`, `干潟`, `サンゴ礁` | INTEGER, 0 or 1 |
| 40, 57, 61, 90, 95, 107, 111, 121 | the same groups | `その他自由記述` (other, free text) | VARCHAR |
| 122 to 129 | `国土地域区分` | eight regions, e.g. `奥山自然地域`, `都市地域`, `不明` | INTEGER, 0 or 1 |
| 130 to 175 | `存続を脅かす要因（現在）` | current threats, e.g. `森林伐採`, `気候変動`, `違法採集` | INTEGER, 0 or 1 |
| 176 | `存続を脅かす要因（現在）` | `その他自由記述` | VARCHAR |
| 177 | (empty) | `不明` | INTEGER, 0 or 1 |

That is 133 INTEGER columns and 45 VARCHAR columns. Column 177 has no group
in the source; it sits after the threat columns and may mean "threat
unknown", but the file does not say so, so the name is kept as `不明` and no
group is invented for it.

<details>
<summary>The three header rows of the 2026 files, column by column</summary>

| # | row 1 | row 2 (group) | row 3 (name) | column in the Parquet | type |
|---:|---|---|---|---|---|
| 0 | 1 | 5thRL | 掲載No. | `5thRL_掲載No.` | VARCHAR |
| 1 | 2 | 5thRL | 分科会名 | `5thRL_分科会名` | VARCHAR |
| 2 | 3 | 5thRL | カテゴリーJPN | `5thRL_カテゴリーJPN` | VARCHAR |
| 3 | 4 | 5thRL | カテゴリーENG | `5thRL_カテゴリーENG` | VARCHAR |
| 4 | 5 | 5thRL | 目名 | `5thRL_目名` | VARCHAR |
| 5 | 6 | 5thRL | 科名 | `5thRL_科名` | VARCHAR |
| 6 | 7 | 5thRL | 和名 | `5thRL_和名` | VARCHAR |
| 7 | 8 | 5thRL | 学名 | `5thRL_学名` | VARCHAR |
| 8 | 9 | 5thRL | 判定基準 | `5thRL_判定基準` | VARCHAR |
| 9 | 10 | RL2020 | 和名 | `RL2020_和名` | VARCHAR |
| 10 | 11 | RL2020 | 学名 | `RL2020_学名` | VARCHAR |
| 11 | 12 | RL2020 | カテゴリー | `RL2020_カテゴリー` | VARCHAR |
| 12 | 13 | RL2019 | 和名 | `RL2019_和名` | VARCHAR |
| 13 | 14 | RL2019 | 学名 | `RL2019_学名` | VARCHAR |
| 14 | 15 | RL2019 | カテゴリー | `RL2019_カテゴリー` | VARCHAR |
| 15 | 16 | RL2018 | 和名 | `RL2018_和名` | VARCHAR |
| 16 | 17 | RL2018 | 学名 | `RL2018_学名` | VARCHAR |
| 17 | 18 | RL2018 | カテゴリー | `RL2018_カテゴリー` | VARCHAR |
| 18 | 19 | RL2017 | 和名 | `RL2017_和名` | VARCHAR |
| 19 | 20 | RL2017 | 学名 | `RL2017_学名` | VARCHAR |
| 20 | 21 | RL2017 | カテゴリー | `RL2017_カテゴリー` | VARCHAR |
| 21 | 22 | RL2015 | 和名 | `RL2015_和名` | VARCHAR |
| 22 | 23 | RL2015 | 学名 | `RL2015_学名` | VARCHAR |
| 23 | 24 | RL2015 | カテゴリー | `RL2015_カテゴリー` | VARCHAR |
| 24 | 25 | 4thRL | 和名 | `4thRL_和名` | VARCHAR |
| 25 | 26 | 4thRL | 学名 | `4thRL_学名` | VARCHAR |
| 26 | 27 | 4thRL | カテゴリー | `4thRL_カテゴリー` | VARCHAR |
| 27 | 28 | 3rdRL | 和名 | `3rdRL_和名` | VARCHAR |
| 28 | 29 | 3rdRL | 学名 | `3rdRL_学名` | VARCHAR |
| 29 | 30 | 3rdRL | カテゴリー | `3rdRL_カテゴリー` | VARCHAR |
| 30 | 31 | 2ndRL | 和名 | `2ndRL_和名` | VARCHAR |
| 31 | 32 | 2ndRL | 学名 | `2ndRL_学名` | VARCHAR |
| 32 | 33 | 2ndRL | カテゴリー | `2ndRL_カテゴリー` | VARCHAR |
| 33 | 34 | 1stRL | 和名 | `1stRL_和名` | VARCHAR |
| 34 | 35 | 1stRL | 学名 | `1stRL_学名` | VARCHAR |
| 35 | 36 | 1stRL | カテゴリー | `1stRL_カテゴリー` | VARCHAR |
| 36 | 37 | 生息・生育環境区分（陸域（山地・丘陵）中区分） | 高標高地 | `生息・生育環境区分（陸域（山地・丘陵）中区分）_高標高地` | INTEGER |
| 37 | 38 | 生息・生育環境区分（陸域（山地・丘陵）中区分） | 中標高地 | `生息・生育環境区分（陸域（山地・丘陵）中区分）_中標高地` | INTEGER |
| 38 | 39 | 生息・生育環境区分（陸域（山地・丘陵）中区分） | 低標高地 | `生息・生育環境区分（陸域（山地・丘陵）中区分）_低標高地` | INTEGER |
| 39 | 40 | 生息・生育環境区分（陸域（山地・丘陵）中区分） | その他 | `生息・生育環境区分（陸域（山地・丘陵）中区分）_その他` | INTEGER |
| 40 | 41 | 生息・生育環境区分（陸域（山地・丘陵）中区分） | その他自由記述 | `生息・生育環境区分（陸域（山地・丘陵）中区分）_その他自由記述` | VARCHAR |
| 41 | 42 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 裸地 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_裸地` | INTEGER |
| 42 | 43 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 森林 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_森林` | INTEGER |
| 43 | 44 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 草地 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_草地` | INTEGER |
| 44 | 45 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 田地・畑地 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_田地・畑地` | INTEGER |
| 45 | 46 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 耕作放棄地 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_耕作放棄地` | INTEGER |
| 46 | 47 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 農業用水路 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_農業用水路` | INTEGER |
| 47 | 48 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 湿地・湿原・細流 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_湿地・湿原・細流` | INTEGER |
| 48 | 49 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 砂地・風衝地 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_砂地・風衝地` | INTEGER |
| 49 | 50 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 岩壁・ガレ場（石灰岩地等） | `生息・生育環境区分（陸域（山地・丘陵）細区分）_岩壁・ガレ場（石灰岩地等）` | INTEGER |
| 50 | 51 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 洞窟・地下浅層・地下水域 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_洞窟・地下浅層・地下水域` | INTEGER |
| 51 | 52 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 河川源流域 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_河川源流域` | INTEGER |
| 52 | 53 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 河川上流域 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_河川上流域` | INTEGER |
| 53 | 54 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 河川中流域 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_河川中流域` | INTEGER |
| 54 | 55 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | ため池・池沼 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_ため池・池沼` | INTEGER |
| 55 | 56 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | 湖・ダム湖 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_湖・ダム湖` | INTEGER |
| 56 | 57 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | その他 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_その他` | INTEGER |
| 57 | 58 | 生息・生育環境区分（陸域（山地・丘陵）細区分） | その他自由記述 | `生息・生育環境区分（陸域（山地・丘陵）細区分）_その他自由記述` | VARCHAR |
| 58 | 59 | 生息・生育環境区分（陸域（平野・海岸等）中区分） | 平地部 | `生息・生育環境区分（陸域（平野・海岸等）中区分）_平地部` | INTEGER |
| 59 | 60 | 生息・生育環境区分（陸域（平野・海岸等）中区分） | 海岸部 | `生息・生育環境区分（陸域（平野・海岸等）中区分）_海岸部` | INTEGER |
| 60 | 61 | 生息・生育環境区分（陸域（平野・海岸等）中区分） | その他 | `生息・生育環境区分（陸域（平野・海岸等）中区分）_その他` | INTEGER |
| 61 | 62 | 生息・生育環境区分（陸域（平野・海岸等）中区分） | その他自由記述 | `生息・生育環境区分（陸域（平野・海岸等）中区分）_その他自由記述` | VARCHAR |
| 62 | 63 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 裸地 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_裸地` | INTEGER |
| 63 | 64 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 森林 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_森林` | INTEGER |
| 64 | 65 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 草地 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_草地` | INTEGER |
| 65 | 66 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 田地・畑地 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_田地・畑地` | INTEGER |
| 66 | 67 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 耕作放棄地 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_耕作放棄地` | INTEGER |
| 67 | 68 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 湿地・湿原 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_湿地・湿原` | INTEGER |
| 68 | 69 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 住宅地 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_住宅地` | INTEGER |
| 69 | 70 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 商業・工業施設 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_商業・工業施設` | INTEGER |
| 70 | 71 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 市街緑地 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_市街緑地` | INTEGER |
| 71 | 72 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 砂地・礫地 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_砂地・礫地` | INTEGER |
| 72 | 73 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 河川中流域 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_河川中流域` | INTEGER |
| 73 | 74 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 河川下流域 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_河川下流域` | INTEGER |
| 74 | 75 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 河口域 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_河口域` | INTEGER |
| 75 | 76 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | ワンド | `生息・生育環境区分（陸域（平野・海岸等）細区分）_ワンド` | INTEGER |
| 76 | 77 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 農業用水路 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_農業用水路` | INTEGER |
| 77 | 78 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 小河川 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_小河川` | INTEGER |
| 78 | 79 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | ため池・池沼 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_ため池・池沼` | INTEGER |
| 79 | 80 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 潟・湖・ダム湖 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_潟・湖・ダム湖` | INTEGER |
| 80 | 81 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 地下水域 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_地下水域` | INTEGER |
| 81 | 82 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 井戸 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_井戸` | INTEGER |
| 82 | 83 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 洞窟・地下浅層 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_洞窟・地下浅層` | INTEGER |
| 83 | 84 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 砂浜・礫浜 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_砂浜・礫浜` | INTEGER |
| 84 | 85 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 海崖・岩浜・岩礁（磯） | `生息・生育環境区分（陸域（平野・海岸等）細区分）_海崖・岩浜・岩礁（磯）` | INTEGER |
| 85 | 86 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 汽水域 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_汽水域` | INTEGER |
| 86 | 87 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 塩沼地・塩性湿地・河口干潟(マングローブ湿地を含む) | `生息・生育環境区分（陸域（平野・海岸等）細区分）_塩沼地・塩性湿地・河口干潟(マングローブ湿地を含む)` | INTEGER |
| 87 | 88 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 潟・汽水湖 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_潟・汽水湖` | INTEGER |
| 88 | 89 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | 陸封潮溜まり（アンキアライン池・洞窟） | `生息・生育環境区分（陸域（平野・海岸等）細区分）_陸封潮溜まり（アンキアライン池・洞窟）` | INTEGER |
| 89 | 90 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | その他 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_その他` | INTEGER |
| 90 | 91 | 生息・生育環境区分（陸域（平野・海岸等）細区分） | その他自由記述 | `生息・生育環境区分（陸域（平野・海岸等）細区分）_その他自由記述` | VARCHAR |
| 91 | 92 | 生息・生育環境区分（海域（沿岸）中区分） | 潮間帯 | `生息・生育環境区分（海域（沿岸）中区分）_潮間帯` | INTEGER |
| 92 | 93 | 生息・生育環境区分（海域（沿岸）中区分） | 表層 | `生息・生育環境区分（海域（沿岸）中区分）_表層` | INTEGER |
| 93 | 94 | 生息・生育環境区分（海域（沿岸）中区分） | 中深層以深 | `生息・生育環境区分（海域（沿岸）中区分）_中深層以深` | INTEGER |
| 94 | 95 | 生息・生育環境区分（海域（沿岸）中区分） | その他 | `生息・生育環境区分（海域（沿岸）中区分）_その他` | INTEGER |
| 95 | 96 | 生息・生育環境区分（海域（沿岸）中区分） | その他自由記述 | `生息・生育環境区分（海域（沿岸）中区分）_その他自由記述` | VARCHAR |
| 96 | 97 | 生息・生育環境区分（海域（沿岸）細区分） | 海面 | `生息・生育環境区分（海域（沿岸）細区分）_海面` | INTEGER |
| 97 | 98 | 生息・生育環境区分（海域（沿岸）細区分） | 漂泳界(水柱環境) | `生息・生育環境区分（海域（沿岸）細区分）_漂泳界(水柱環境)` | INTEGER |
| 98 | 99 | 生息・生育環境区分（海域（沿岸）細区分） | 岩礁（磯） | `生息・生育環境区分（海域（沿岸）細区分）_岩礁（磯）` | INTEGER |
| 99 | 100 | 生息・生育環境区分（海域（沿岸）細区分） | 藻場 | `生息・生育環境区分（海域（沿岸）細区分）_藻場` | INTEGER |
| 100 | 101 | 生息・生育環境区分（海域（沿岸）細区分） | アマモ場 | `生息・生育環境区分（海域（沿岸）細区分）_アマモ場` | INTEGER |
| 101 | 102 | 生息・生育環境区分（海域（沿岸）細区分） | サンゴ礁 | `生息・生育環境区分（海域（沿岸）細区分）_サンゴ礁` | INTEGER |
| 102 | 103 | 生息・生育環境区分（海域（沿岸）細区分） | 干潟 | `生息・生育環境区分（海域（沿岸）細区分）_干潟` | INTEGER |
| 103 | 104 | 生息・生育環境区分（海域（沿岸）細区分） | 砂底・礫底 | `生息・生育環境区分（海域（沿岸）細区分）_砂底・礫底` | INTEGER |
| 104 | 105 | 生息・生育環境区分（海域（沿岸）細区分） | 泥底 | `生息・生育環境区分（海域（沿岸）細区分）_泥底` | INTEGER |
| 105 | 106 | 生息・生育環境区分（海域（沿岸）細区分） | 洞窟 | `生息・生育環境区分（海域（沿岸）細区分）_洞窟` | INTEGER |
| 106 | 107 | 生息・生育環境区分（海域（沿岸）細区分） | その他 | `生息・生育環境区分（海域（沿岸）細区分）_その他` | INTEGER |
| 107 | 108 | 生息・生育環境区分（海域（沿岸）細区分） | その他自由記述 | `生息・生育環境区分（海域（沿岸）細区分）_その他自由記述` | VARCHAR |
| 108 | 109 | 生息・生育環境区分（海域（外洋）中区分） | 表層 | `生息・生育環境区分（海域（外洋）中区分）_表層` | INTEGER |
| 109 | 110 | 生息・生育環境区分（海域（外洋）中区分） | 中深層以深 | `生息・生育環境区分（海域（外洋）中区分）_中深層以深` | INTEGER |
| 110 | 111 | 生息・生育環境区分（海域（外洋）中区分） | その他 | `生息・生育環境区分（海域（外洋）中区分）_その他` | INTEGER |
| 111 | 112 | 生息・生育環境区分（海域（外洋）中区分） | その他自由記述 | `生息・生育環境区分（海域（外洋）中区分）_その他自由記述` | VARCHAR |
| 112 | 113 | 生息・生育環境区分（海域（外洋）細区分） | 海面 | `生息・生育環境区分（海域（外洋）細区分）_海面` | INTEGER |
| 113 | 114 | 生息・生育環境区分（海域（外洋）細区分） | 漂泳界(水柱環境) | `生息・生育環境区分（海域（外洋）細区分）_漂泳界(水柱環境)` | INTEGER |
| 114 | 115 | 生息・生育環境区分（海域（外洋）細区分） | 岩底 | `生息・生育環境区分（海域（外洋）細区分）_岩底` | INTEGER |
| 115 | 116 | 生息・生育環境区分（海域（外洋）細区分） | 砂底・礫底 | `生息・生育環境区分（海域（外洋）細区分）_砂底・礫底` | INTEGER |
| 116 | 117 | 生息・生育環境区分（海域（外洋）細区分） | 泥底 | `生息・生育環境区分（海域（外洋）細区分）_泥底` | INTEGER |
| 117 | 118 | 生息・生育環境区分（海域（外洋）細区分） | 洞窟 | `生息・生育環境区分（海域（外洋）細区分）_洞窟` | INTEGER |
| 118 | 119 | 生息・生育環境区分（海域（外洋）細区分） | 熱水噴出孔 | `生息・生育環境区分（海域（外洋）細区分）_熱水噴出孔` | INTEGER |
| 119 | 120 | 生息・生育環境区分（海域（外洋）細区分） | 冷水湧出帯 | `生息・生育環境区分（海域（外洋）細区分）_冷水湧出帯` | INTEGER |
| 120 | 121 | 生息・生育環境区分（海域（外洋）細区分） | その他 | `生息・生育環境区分（海域（外洋）細区分）_その他` | INTEGER |
| 121 | 122 | 生息・生育環境区分（海域（外洋）細区分） | その他自由記述 | `生息・生育環境区分（海域（外洋）細区分）_その他自由記述` | VARCHAR |
| 122 | 123 | 国土地域区分 | 奥山自然地域 | `国土地域区分_奥山自然地域` | INTEGER |
| 123 | 124 | 国土地域区分 | 里地里山・田園地域 | `国土地域区分_里地里山・田園地域` | INTEGER |
| 124 | 125 | 国土地域区分 | 都市地域 | `国土地域区分_都市地域` | INTEGER |
| 125 | 126 | 国土地域区分 | 河川・湿地地域 | `国土地域区分_河川・湿地地域` | INTEGER |
| 126 | 127 | 国土地域区分 | 沿岸域 | `国土地域区分_沿岸域` | INTEGER |
| 127 | 128 | 国土地域区分 | 海洋域 | `国土地域区分_海洋域` | INTEGER |
| 128 | 129 | 国土地域区分 | 島嶼地域 | `国土地域区分_島嶼地域` | INTEGER |
| 129 | 130 | 国土地域区分 | 不明 | `国土地域区分_不明` | INTEGER |
| 130 | 131 | 存続を脅かす要因（現在） | 森林伐採 | `存続を脅かす要因（現在）_森林伐採` | INTEGER |
| 131 | 132 | 存続を脅かす要因（現在） | 湖沼開発 | `存続を脅かす要因（現在）_湖沼開発` | INTEGER |
| 132 | 133 | 存続を脅かす要因（現在） | 河川開発 | `存続を脅かす要因（現在）_河川開発` | INTEGER |
| 133 | 134 | 存続を脅かす要因（現在） | 海岸開発 | `存続を脅かす要因（現在）_海岸開発` | INTEGER |
| 134 | 135 | 存続を脅かす要因（現在） | 海砂採取 | `存続を脅かす要因（現在）_海砂採取` | INTEGER |
| 135 | 136 | 存続を脅かす要因（現在） | 湿地開発 | `存続を脅かす要因（現在）_湿地開発` | INTEGER |
| 136 | 137 | 存続を脅かす要因（現在） | 圃場整備 | `存続を脅かす要因（現在）_圃場整備` | INTEGER |
| 137 | 138 | 存続を脅かす要因（現在） | 草地開発 | `存続を脅かす要因（現在）_草地開発` | INTEGER |
| 138 | 139 | 存続を脅かす要因（現在） | 石灰採掘 | `存続を脅かす要因（現在）_石灰採掘` | INTEGER |
| 139 | 140 | 存続を脅かす要因（現在） | 洞窟の消失や環境悪化 | `存続を脅かす要因（現在）_洞窟の消失や環境悪化` | INTEGER |
| 140 | 141 | 存続を脅かす要因（現在） | ゴルフ場 | `存続を脅かす要因（現在）_ゴルフ場` | INTEGER |
| 141 | 142 | 存続を脅かす要因（現在） | スキー場 | `存続を脅かす要因（現在）_スキー場` | INTEGER |
| 142 | 143 | 存続を脅かす要因（現在） | 土地造成 | `存続を脅かす要因（現在）_土地造成` | INTEGER |
| 143 | 144 | 存続を脅かす要因（現在） | 交通インフラ建設 | `存続を脅かす要因（現在）_交通インフラ建設` | INTEGER |
| 144 | 145 | 存続を脅かす要因（現在） | ダム・河川工作物建設 | `存続を脅かす要因（現在）_ダム・河川工作物建設` | INTEGER |
| 145 | 146 | 存続を脅かす要因（現在） | 発電施設建設 | `存続を脅かす要因（現在）_発電施設建設` | INTEGER |
| 146 | 147 | 存続を脅かす要因（現在） | 水質汚濁 | `存続を脅かす要因（現在）_水質汚濁` | INTEGER |
| 147 | 148 | 存続を脅かす要因（現在） | 水温変化 | `存続を脅かす要因（現在）_水温変化` | INTEGER |
| 148 | 149 | 存続を脅かす要因（現在） | 農薬汚染/化学物質汚染 | `存続を脅かす要因（現在）_農薬汚染/化学物質汚染` | INTEGER |
| 149 | 150 | 存続を脅かす要因（現在） | 感染症/病原菌 | `存続を脅かす要因（現在）_感染症/病原菌` | INTEGER |
| 150 | 151 | 存続を脅かす要因（現在） | 大気汚染 | `存続を脅かす要因（現在）_大気汚染` | INTEGER |
| 151 | 152 | 存続を脅かす要因（現在） | 捕獲・狩猟/園芸採取 | `存続を脅かす要因（現在）_捕獲・狩猟/園芸採取` | INTEGER |
| 152 | 153 | 存続を脅かす要因（現在） | 食用・薬用採取 | `存続を脅かす要因（現在）_食用・薬用採取` | INTEGER |
| 153 | 154 | 存続を脅かす要因（現在） | 違法採集 | `存続を脅かす要因（現在）_違法採集` | INTEGER |
| 154 | 155 | 存続を脅かす要因（現在） | 混獲・錯誤捕獲 | `存続を脅かす要因（現在）_混獲・錯誤捕獲` | INTEGER |
| 155 | 156 | 存続を脅かす要因（現在） | シカ食害 | `存続を脅かす要因（現在）_シカ食害` | INTEGER |
| 156 | 157 | 存続を脅かす要因（現在） | その他動物食害 | `存続を脅かす要因（現在）_その他動物食害` | INTEGER |
| 157 | 158 | 存続を脅かす要因（現在） | 捕食（外来種による） | `存続を脅かす要因（現在）_捕食（外来種による）` | INTEGER |
| 158 | 159 | 存続を脅かす要因（現在） | 捕食（在来種による） | `存続を脅かす要因（現在）_捕食（在来種による）` | INTEGER |
| 159 | 160 | 存続を脅かす要因（現在） | 競争/競合（外来種による） | `存続を脅かす要因（現在）_競争/競合（外来種による）` | INTEGER |
| 160 | 161 | 存続を脅かす要因（現在） | 競争/競合（在来種による） | `存続を脅かす要因（現在）_競争/競合（在来種による）` | INTEGER |
| 161 | 162 | 存続を脅かす要因（現在） | 交雑（外来種による） | `存続を脅かす要因（現在）_交雑（外来種による）` | INTEGER |
| 162 | 163 | 存続を脅かす要因（現在） | 交雑（在来種による) | `存続を脅かす要因（現在）_交雑（在来種による)` | INTEGER |
| 163 | 164 | 存続を脅かす要因（現在） | 宿主の減少 | `存続を脅かす要因（現在）_宿主の減少` | INTEGER |
| 164 | 165 | 存続を脅かす要因（現在） | 人の踏みつけ | `存続を脅かす要因（現在）_人の踏みつけ` | INTEGER |
| 165 | 166 | 存続を脅かす要因（現在） | 交通事故 | `存続を脅かす要因（現在）_交通事故` | INTEGER |
| 166 | 167 | 存続を脅かす要因（現在） | 人工構造物への衝突 | `存続を脅かす要因（現在）_人工構造物への衝突` | INTEGER |
| 167 | 168 | 存続を脅かす要因（現在） | 光害 | `存続を脅かす要因（現在）_光害` | INTEGER |
| 168 | 169 | 存続を脅かす要因（現在） | 管理放棄 | `存続を脅かす要因（現在）_管理放棄` | INTEGER |
| 169 | 170 | 存続を脅かす要因（現在） | 遷移進行・植生変化/自然遷移 | `存続を脅かす要因（現在）_遷移進行・植生変化/自然遷移` | INTEGER |
| 170 | 171 | 存続を脅かす要因（現在） | 基質・基物の減少及び消失 | `存続を脅かす要因（現在）_基質・基物の減少及び消失` | INTEGER |
| 171 | 172 | 存続を脅かす要因（現在） | 自然災害 | `存続を脅かす要因（現在）_自然災害` | INTEGER |
| 172 | 173 | 存続を脅かす要因（現在） | 気候変動 | `存続を脅かす要因（現在）_気候変動` | INTEGER |
| 173 | 174 | 存続を脅かす要因（現在） | 局所分布 | `存続を脅かす要因（現在）_局所分布` | INTEGER |
| 174 | 175 | 存続を脅かす要因（現在） | 近親交配 | `存続を脅かす要因（現在）_近親交配` | INTEGER |
| 175 | 176 | 存続を脅かす要因（現在） | その他 | `存続を脅かす要因（現在）_その他` | INTEGER |
| 176 | 177 | 存続を脅かす要因（現在） | その他自由記述 | `存続を脅かす要因（現在）_その他自由記述` | VARCHAR |
| 177 | 178 | (empty) | 不明 | `不明` | INTEGER |

</details>

## Using it with DuckDB

```sql
-- birds by 5th-edition category, straight off the Hub
SELECT "5thRL_カテゴリーENG" AS category, count(*) AS species
FROM 'hf://datasets/yuiseki/env-redlist-jp/parquet/5th/birds.parquet'
GROUP BY ALL ORDER BY species DESC;

-- birds whose category changed since Red List 2020 ('－' = not listed then)
SELECT "5thRL_和名", "RL2020_カテゴリー", "5thRL_カテゴリーENG"
FROM 'hf://datasets/yuiseki/env-redlist-jp/parquet/5th/birds.parquet'
WHERE "RL2020_カテゴリー" <> "5thRL_カテゴリーENG";

-- vascular plants: the category text as written
SELECT カテゴリー, count(*)
FROM 'hf://datasets/yuiseki/env-redlist-jp/parquet/5th/vascular_plants.parquet'
GROUP BY ALL ORDER BY ALL;
```

Column names that start with a digit or hold brackets need double quotes in
SQL.

## Things to know

No value was normalised. The points below describe what the source writes, so
that a user who wants to compare or group values can decide how to.

Categories are written differently in the 2025 and 2026 files:

| category | 2025 `カテゴリー` | 2026 `5thRL_カテゴリーJPN` | 2026 `5thRL_カテゴリーENG` |
|---|---|---|---|
| EX | `絶滅（EX）` | `絶滅` | `EX` |
| EW | `野生絶滅（EW）` | (none listed) | |
| CR | `絶滅危惧ⅠＡ類（CR）` | `絶滅危惧IA類` | `CR` |
| EN | `絶滅危惧ⅠB類（EN）` | `絶滅危惧IB類` | `EN` |
| VU | `絶滅危惧Ⅱ類（VU）` | `絶滅危惧II類` | `VU` |
| NT | `準絶滅危惧（NT）` | `準絶滅危惧` | `NT` |
| DD | `情報不足（DD）` | `情報不足` | `DD` |
| LP | (none listed) | `絶滅のおそれのある地域個体群` | `LP` |

- The 2025 files use the Roman numeral characters Ⅰ (U+2160) and Ⅱ (U+2161),
  full-width brackets （） and, inside the same column, a full-width Ａ
  (U+FF21) in `ⅠＡ` but an ASCII B in `ⅠB`. Each file uses each spelling
  consistently; there is one spelling per category across the five files.
- The 2026 files write the numerals with ASCII letters (`I`, `II`) and put the
  abbreviation in its own column, `5thRL_カテゴリーENG`.
- A text match on `カテゴリー` therefore has to use the exact characters. To
  group 2025 and 2026 together, take the abbreviation (the letters inside the
  brackets in 2025, `5thRL_カテゴリーENG` in 2026).
- The earlier-edition `カテゴリー` columns of the 2026 files hold
  abbreviations only. `1stRL_カテゴリー` (the 1991 Red Data Book) uses that
  edition's own system: `Ex`, `E`, `V`, `R`, and `LP` in amphibians. One bird
  (ダイトウウグイス) has `EX／DD` in `RL2015_カテゴリー`, with a full-width
  slash (U+FF0F).

Two different dashes mean two different things in the 2026 files:

- `－` (U+FF0D, full-width hyphen-minus) in the earlier-edition columns means
  the species was not listed in that edition.
- `―` (U+2015, horizontal bar) in the `その他自由記述` columns means nothing was
  written.

No field in any file is empty.

`5thRL_判定基準` mixes two kinds of code: criteria such as `A2`, `B2ab`,
`C2a(i)`, `D2` (several separated by a space, sometimes joined with `+`), and
circled numbers `①` to `④`. Two rows use `A2 ＋付加的事情` with a full-width
plus. The meaning of each code is in the Ministry's assessment criteria, which
are not part of this dataset.

Names:

- Two bryophyte scientific names end with a space (`Lewinskya iwatsukii `,
  `Buckia vaucheri `). They are kept.
- One vascular plant is written `Utricularia ｘ japonica`, with a full-width
  ｘ (U+FF58) for the hybrid sign.
- Three lichen names have a diaeresis (`Cladonia koyaënsis`, `Pyxine cocoës`,
  `Lobaria kazawaënsis`). The `?` that replaces such letters in older lichen
  lists on the same page does not occur in the 5th edition.
- Seven bryophyte and one lichen Japanese names carry another name in
  full-width brackets, e.g. `ユリゴケ（タイワンユリゴケ）`.
- A local population (LP) is named with its place, e.g.
  `大東諸島のオガサワラヤモリ`. The earlier-edition names of the same
  population may differ (`東京都のトウキョウサンショウウオ` in the 2nd
  edition, `東京都のトウキョウサンショウウオ個体群` in the 1st).
- Scientific names change between editions in the same row (e.g. `Porzana
  cinerea brevipes` in RL2020, `Poliolimnas cinereus brevipes` in the 5th
  edition). The row links them; the names are as each edition wrote them.
- `5thRL_分科会名` is `爬虫類・両生類` in both the reptile and the amphibian
  file, which were assessed by one working group.

Counts compared with the press releases:

- Plants and fungi match the 2025 press release: vascular plants 2,222,
  bryophytes 289, algae 178, lichens 153, fungi 110 (2,952 in all).
- Birds: 170 rows, as the 2026 press release says ("鳥類は計170種が掲載").
- Reptiles and amphibians: the files have 63 and 77 rows, 140 together. The
  2026 press release gives 138 for reptiles and amphibians together. This is
  unresolved. Two reptile rows are local populations (LP), and 140 minus 2 is
  138, so the press release may count LP separately; that was not confirmed
  against the release's own breakdown.

The source page states file sizes that do not match the files (birds "CSV 543
KB" for 142,742 bytes; reptiles "CSV 472 KB" for 62,787; amphibians "CSV 478
KB" for 69,170). `MANIFEST.json` keeps both.

## Checked before upload

`scripts/02_verify.py` in the source repository checks:

- every raw file against `MANIFEST.json`: size, sha256, that it decodes in the
  recorded encoding, and its record count read with Python's csv module;
- for each subset: the Parquet has as many rows as the raw file has data
  records by the csv module, and the pinned count above;
- the column names are the flattened header of the raw file, in order;
- every column has the type its name gives;
- every value of the Parquet equals the raw value (integers compared as their
  text), and a sha256 over all values is the same on both sides;
- the header rows kept in the Parquet metadata equal the raw header rows;
- a plain DuckDB, with only its built-in extensions, opens every file;
- no row group carries a bloom filter.

All checks passed with DuckDB 1.5.6.

## Licence

The source page, いきものログ「レッドリスト・レッドデータブック」
(https://ikilog.biodic.go.jp/Rdb/booklist, read on 2026-10-03, and checked
again by the download script when the files were fetched on 2026-10-04 UTC),
says in its section 「第５次レッドリストについて（令和7年～）」, directly above the
table of the eight CSV files:

> なお、以下のレッドリスト（CSV版）は、クリエイティブ・コモンズ 表示 4.0 国際ライセンス（CC BY 4.0）の下で公表されています。

("The following Red Lists (CSV versions) are published under the Creative
Commons Attribution 4.0 International licence (CC BY 4.0).") The e-Gov data
portal lists the same eight files with `license_id` `cc-by-4.0`.

Credit, as CC BY 4.0 asks:

> 出典：環境省 第５次レッドリスト（いきものログ https://ikilog.biodic.go.jp/Rdb/booklist）、CC BY 4.0。Parquet は yuiseki/env-redlist-jp が CSV から変換。

Source: Ministry of the Environment, Japan, 5th Red List (Ikimono Log,
https://ikilog.biodic.go.jp/Rdb/booklist), CC BY 4.0. The Parquet files were
converted from the CSVs by yuiseki/env-redlist-jp and are not published by the
Ministry.

What was changed: the files under `raw/5th/` are the Ministry's CSVs,
unchanged. The Parquet was made from them: decoded from cp932 or UTF-8 into
UTF-8, the three header rows of the 2026 files flattened into one name per
column (the rows are kept in the file metadata and above), the 0 or 1 columns
of the 2026 files typed as INTEGER. No value was changed. `LICENSE` beside
this file says the same.

The earlier editions on the same page (1991 to Red List 2020, the marine Red
List) are not here: the page states no licence for them.

## Citation

環境省 (2025) 第５次レッドリスト（植物・菌類）. 環境省 (2026)
第５次レッドリスト（鳥類、爬虫類・両生類）. いきものログ,
https://ikilog.biodic.go.jp/Rdb/booklist

Ministry of the Environment, Japan (2025, 2026). The 5th Red List of Japan.
https://ikilog.biodic.go.jp/Rdb/booklist
