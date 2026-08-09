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

1. release manifest と実行 closure 全体の hash / provenance / symlink / LF 検証
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
python3 -m unittest -v simulation.tests.test_rvcim_sim
python3 -m unittest -v tools.tests.test_verify_release
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

## 3. 完全な 4 arm 実験（使い捨て出力）

```bash
make experiment
```

直接指定する場合:

```bash
python3 -m simulation run \
  --config simulation/configs/minimal.json \
  --episodes 64 \
  --seed 7 \
  --out .tmp/experiment \
  --overwrite
```

通常の `make experiment` は `.tmp/experiment` だけに書き込み、commit 済みの `artifacts/reference_run` は変更しません。reference fixture の更新は、モデルまたは設定の意図的変更を review した maintainer が `make refresh-reference` で明示的に行い、差分と manifest を確認します。

既存出力directoryの置換には、filesystemのatomic directory exchangeが必要です。Linux / macOSでは対応filesystem上で安全に置換します。Windowsまたは非対応filesystemでは `--overwrite` を拒否して既存の検証済み出力を残すため、新しい出力pathを指定してください。新規directoryへの生成は全対応platformで利用できます。

主な出力:

- `summary.csv`: arm ごとの集約値
- `episodes.csv`: episode ごとの結果
- `trace.csv`: step trace
- `comparison.md`: 人間向け比較表
- `resolved_config.json`: 実際に使われた設定
- `receipt.json`: command、環境情報、claim boundary、ファイル hash

## 4. 原稿と provenance

Python、TeX、bibliography、PDF、reference artifact はすべて通常ファイルとして同梱されています。展開処理や別 branch からの復元は不要です。

現在 checkout される v0.1 の file identity:

- `paper/nashs_cage_rvcim_v0_1.tex`: `6f0d0d7f47df6bdb38ff41bca32b5b5108d7254f07825b069349e53f2c3ad5b7`
- `paper/nashs_cage_rvcim_v0_1.pdf`: `4ded46a5fee179182f40f671ab1345453dceda8e534b713eee775d628cf65d2e`

v0.1 は operator-attested な preserved upload として記録されています。TeX には利用可能な Git history anchor がありますが、PDF を元 upload と独立に結び付ける history anchor は利用できません。v0.2 は、壊れた bootstrap 表現から過去のバイト列を復元したものではありません。v0.1 と現在の executable contract から 2026-08-07 に再生成したと operator が attest した版であり、過去に存在した可能性のある別の v0.2 とのバイト一致は主張しません。

`RELEASE_MANIFEST.json` が検証するのは checkout 内の整合性です。manifest、verifier、対象ファイルが同じ tree にあるため、その hash 自体が過去の出自を自己証明するわけではありません。外部 anchor は review 済み Git commit（および別途保存された署名や archive がある場合はそれら）です。

manifest だけを検証する場合:

```bash
make verify-release
```

## 5. PDF を自分で再ビルドする

`latexmk`、XeLaTeX、BibTeX、必要な TeX package がある環境では:

```bash
make paper
```

既存 PDF はそのまま読めます。`make paper` の出力先は `.tmp/paper/nashs_cage_rvcim_v0_2.pdf` で、commit 済みの v0.1 / v0.2 PDF を上書きしません。manifest の hash は同一 tree 内にある現在の PDF identity を示しますが、TeX からの build lineage を単独で証明するものではありません。TeX engine、package、font、生成時 metadata が異なるローカル再 build に同一 hash は要求しません。

## 6. Windows

Command Prompt / PowerShell では:

```bat
rvcim.cmd explain
rvcim.cmd smoke --config simulation\configs\minimal.json --episodes 4 --seed 101 --out .tmp\smoke
```

## 7. 数字の読み方

`irreversible_entry_rate` が低い、`min_hidden_cr` が高い、`false_negative_trigger_rate` が低い、といった差は、現在の正規化された toy assumptions の内部での差です。現実の気候リスク、制度効果、政策順位を推定してはいません。

次の段階 F1 では、対象を狭く固定し、観測データ、parameter provenance、out-of-sample test、alternative mechanism、失敗条件を明示して初めて calibration の話へ進みます。
