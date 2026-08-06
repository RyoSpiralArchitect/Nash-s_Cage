# Nash's Cage / RVCIM 日本語クイックスタート

このリポジトリは現在 **F0 の構造実験**です。実行できることは、理論が正しいことや現実の政策効果を示すこととは別です。まずは「どの仮定が、どの挙動を生むか」を再現可能な形で観察するための小さな実験装置として扱います。

## 1. 最短で動かす

必要なのは Python 3.10 以上だけです。

```bash
git clone https://github.com/RyoSpiralArchitect/Nash-s_Cage.git
cd Nash-s_Cage
make verify
```

`make verify` は次をまとめて行います。

1. Python ソースの compile check
2. 標準ライブラリだけで動く unit test
3. 4 arm の小規模 smoke experiment
4. 生成物の SHA-256 receipt 検証

`make` がない環境では、次でも確認できます。

```bash
python3 -m py_compile simulation/__init__.py simulation/__main__.py simulation/rvcim_sim.py
python3 -m unittest discover -s simulation/tests -v
python3 -m simulation smoke \
  --config simulation/configs/minimal.json \
  --episodes 4 --seed 101 --out .tmp/smoke
python3 -m simulation verify --receipt .tmp/smoke/receipt.json
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

## 4. 原稿ソースを通常ファイルへ展開する

軽量な main branch では、大きな Python / TeX ソースを hash 付き payload として保持しています。編集可能な通常ファイルへ展開するには:

```bash
make materialize
```

この処理は payload のサイズと SHA-256 を検証してから展開します。

## 5. アップロード原本 PDF と完全版を復元する

```bash
make restore-release
```

これで次が作業ツリーへ復元されます。

- アップロードされた v0.1 PDF と TeX
- 実行可能性・容易性を補強した v0.2 PDF と TeX
- `references.bib`
- 完全な simulator source
- 64 episode の reference artifact

復元処理は同じ GitHub リポジトリ内の archive branch を読み、圧縮 archive の SHA-256、path traversal、アップロード原本 PDF / TeX の SHA-256 を検証します。GitHub Actions や TeX 環境は不要です。

`make` を使わない場合:

```bash
python3 tools/restore_release.py --overwrite
```

## 6. PDF を自分で再ビルドする

`latexmk`、Biber、必要な TeX package がある環境では:

```bash
make paper
```

既存 PDF を読むだけなら `make restore-release` のほうが速いです。

## 7. Windows

Command Prompt / PowerShell では:

```bat
rvcim.cmd explain
rvcim.cmd smoke --config simulation\configs\minimal.json --episodes 4 --seed 101 --out .tmp\smoke
```

完全版の復元:

```bat
py tools\restore_release.py --overwrite
```

## 8. 数字の読み方

`irreversible_entry_rate` が低い、`min_hidden_cr` が高い、`false_negative_trigger_rate` が低い、といった差は、現在の正規化された toy assumptions の内部での差です。現実の気候リスク、制度効果、政策順位を推定してはいません。

次の段階 F1 では、対象を狭く固定し、観測データ、parameter provenance、out-of-sample test、alternative mechanism、失敗条件を明示して初めて calibration の話へ進みます。
