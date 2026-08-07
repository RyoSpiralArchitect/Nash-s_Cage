# Nash's Cage / RVCIM 日本語クイックスタート

このリポジトリは現在 **F0 の構造実験**です。実行できることは、理論が正しいことや現実の政策効果を示すこととは別です。まずは「どの仮定が、どの挙動を生むか」を再現可能な形で観察するための小さな実験装置として扱います。

## 1. 最短で動かす

必要なのは Python 3.10 以上と Make です。Python verifier と simulator 自体に third-party package はありません。

```bash
git clone https://github.com/RyoSpiralArchitect/Nash-s_Cage.git
cd Nash-s_Cage
make verify
```

`make verify` は次をまとめて行います。

1. release manifest と全必須ファイルの hash / provenance 検証
2. Python ソースの compile check
3. simulator と release verifier の unit test
4. 4 arm の小規模 smoke experiment と receipt 検証
5. commit 済み reference receipt の検証
6. 64 episode reference command の再実行と deterministic output 5 ファイルの byte 比較

`make` がない環境では、同じ full verification を次で実行できます。

```bash
python3 tools/verify_release.py --root . --manifest RELEASE_MANIFEST.json
python3 -m py_compile simulation/__init__.py simulation/__main__.py simulation/rvcim_sim.py
python3 -m py_compile tools/verify_release.py tools/verify_reference_replay.py
python3 -m unittest discover -s simulation/tests -v
python3 -m unittest discover -s tools/tests -v
python3 -m simulation smoke \
  --config simulation/configs/minimal.json \
  --episodes 4 --seed 101 --out .tmp/smoke
python3 -m simulation verify --receipt .tmp/smoke/receipt.json
python3 -m simulation verify --receipt artifacts/reference_run/receipt.json
python3 tools/verify_reference_replay.py \
  --root . --reference-dir artifacts/reference_run
```

## 2. モデル境界を先に読む

```bash
./rvcim explain
```

または:

```bash
python3 -m simulation explain
```

ここには F0 の claim boundary、主要な状態変数、論文とコードの対応関係が表示されます。

## 3. 完全な 4 arm 実験

```bash
make experiment
```

直接指定する場合:

```bash
python3 -m simulation run \
  --config simulation/configs/minimal.json \
  --episodes 64 \
  --seed 7 \
  --out artifacts/reference_run \
  --overwrite
```

主な出力:

- `summary.csv`: arm ごとの集約値
- `episodes.csv`: episode ごとの結果
- `trace.csv`: step trace
- `comparison.md`: 人間向け比較表
- `resolved_config.json`: 実際に使われた設定
- `receipt.json`: command、環境情報、claim boundary、ファイル hash

## 4. 原稿と provenance

Python、TeX、bibliography、PDF、reference artifact はすべて通常ファイルとして同梱されています。展開処理や別 branch からの復元は不要です。

保存された v0.1 の原本 identity:

- `paper/nashs_cage_rvcim_v0_1.tex`: `6f0d0d7f47df6bdb38ff41bca32b5b5108d7254f07825b069349e53f2c3ad5b7`
- `paper/nashs_cage_rvcim_v0_1.pdf`: `4ded46a5fee179182f40f671ab1345453dceda8e534b713eee775d628cf65d2e`

v0.2 は、壊れた bootstrap 表現から過去のバイト列を復元したものではありません。保存された v0.1 と現在の executable contract から 2026-08-07 に再生成した版であり、過去に存在した可能性のある別の v0.2 とのバイト一致は主張しません。この境界と全必須ファイルの SHA-256 / size は `RELEASE_MANIFEST.json` に記録されています。

manifest だけを検証する場合:

```bash
make verify-release
```

## 5. PDF を自分で再ビルドする

`latexmk`、XeLaTeX、BibTeX、必要な TeX package がある環境では:

```bash
make paper
```

既存 PDF はそのまま読めます。`make paper` の出力先は `.tmp/paper/nashs_cage_rvcim_v0_2.pdf` で、commit 済みの v0.1 / v0.2 PDF を上書きしません。manifest の hash は検証済み PDF の identity です。TeX engine、package、font、生成時 metadata が異なるローカル再 build に同一 hash は要求しません。

## 6. Windows

Command Prompt / PowerShell では:

```bat
rvcim.cmd explain
rvcim.cmd smoke --config simulation\configs\minimal.json --episodes 4 --seed 101 --out .tmp\smoke
```

## 7. 数字の読み方

`irreversible_entry_rate` が低い、`min_hidden_cr` が高い、`false_negative_trigger_rate` が低い、といった差は、現在の正規化された toy assumptions の内部での差です。現実の気候リスク、制度効果、政策順位を推定してはいません。

次の段階 F1 では、対象を狭く固定し、観測データ、parameter provenance、out-of-sample test、alternative mechanism、失敗条件を明示して初めて calibration の話へ進みます。
