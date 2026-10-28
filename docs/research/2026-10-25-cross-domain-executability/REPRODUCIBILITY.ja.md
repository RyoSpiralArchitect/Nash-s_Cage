# 再現手順と検証範囲

## 保存内容

- [入力契約](../../../experiments/cross_domain_audit_v01/CONTRACT.ja.md)：全件取得前に固定。
  メタデータ、FEMAの標本1行と行数は先に確認している。正式な事前登録ではない。
- [取得プログラム](../../../experiments/cross_domain_audit_v01/fetch.py)：公式APIのみ。既存の保存先へ上書きしない。
- [取得manifest](../../../artifacts/cross_domain_audit_v01/snapshot_20261025/manifest.json)：9応答のURL・取得時刻・元バイト数・ハッシュ。
- [オフライン集計](../../../experiments/cross_domain_audit_v01/analyze.py)：取得済み本文のハッシュを確認してから集計。
- [日付・重複・欠測のテスト](../../../experiments/cross_domain_audit_v01/test_analyze.py)：9テスト。
- [独立検算](../../../experiments/cross_domain_audit_v01/verify.rb)：元の圧縮API本文からRubyで再計算。Pythonの集計関数を使わない。
- [集計結果](../../../artifacts/cross_domain_audit_v01/analysis_20261025/summary.json)、
  [宣言ごとのCSV](../../../artifacts/cross_domain_audit_v01/analysis_20261025/fema_declarations.csv)、
  [国・年・指標ごとのCSV](../../../artifacts/cross_domain_audit_v01/analysis_20261025/world_bank_series.csv)。
- [集計receipt](../../../artifacts/cross_domain_audit_v01/analysis_20261025/receipt.json)、
  [独立検算receipt](../../../artifacts/cross_domain_audit_v01/verification_20261025.json)。

取得：2026-10-25 06:55 JST頃（2026-10-24 21:55 UTC）。取得時刻と対象年を混同しない。
世界銀行の応答に記載された最終更新日は2026-10-08。FEMA各行の`lastRefresh`は原応答に残した。
保存データと集計は約2 MiB。Python標準ライブラリ、curl、Ruby標準ライブラリのみを使用。
モデル呼出し・Furnace・GPU・新規シミュレーションはない。

## 保存データから再計算する

リポジトリ直下で実行。`--out` は未使用のディレクトリ名にする。

```sh
python3 -m unittest discover -s experiments/cross_domain_audit_v01 -p 'test_*.py' -v
python3 experiments/cross_domain_audit_v01/analyze.py \
  --snapshot artifacts/cross_domain_audit_v01/snapshot_20261025 \
  --out artifacts/cross_domain_audit_v01/analysis_replay
ruby experiments/cross_domain_audit_v01/verify.rb \
  artifacts/cross_domain_audit_v01/snapshot_20261025 \
  artifacts/cross_domain_audit_v01/analysis_replay
```

再取得には`fetch.py --out`で別の新規保存先を与える。更新される公式APIなので、後日の再取得は
今回と同じ数値になる保証がない。今回の再現は保存済み本文から行う。
一部取得で失敗した保存先は、不完全な証拠として残し、完成manifestのないものを集計しない。

## 確認済み

1. FEMA 29,471行、ID重複なし。宣言IDで1,542宣言に縮約。分析に用いた宣言内定数の競合なし。
2. 各宣言の開始→申請→宣言の日差の算術整合。欠測を0にせず、負値を保存。
3. 全体・21種別・25年の各日差の分母、欠測、負値、0、最小・最大、四分位・90%点を別実装で照合。
4. 世界銀行は100セルの完全な国×年×指標格子。重複なし、欠測なし。8つの比較窓平均と有効年数を独立照合。
5. 独立照合は1,578項目で一致。ただし同じ原資料の再計算であり、原資料の正しさへの独立証拠ではない。
6. 9つの人工的な境界テストが成功。これは監査コードの検査であり、新しい実世界・合成政策実験ではない。
7. 保存本文から別ディレクトリへ再計算し、集計JSON・2つのCSVが元の出力とバイト単位で一致した。
   再計算用コピーは`.tmp/cross_domain_audit_v01/analysis_replay/`に置いた。

本文ではなく、対話内の図・出典表示用に[限定した表示データ](../../../artifacts/cross_domain_audit_v01/inline_payloads/chart.json)も生成した。
元の年次値は丸めずに表示へ渡し、欠測を補完しない。図の2本の系列は加算できない。

主な保存ハッシュ（SHA-256）：

| 対象 | SHA-256 |
|---|---|
| 取得manifest | `a68eb408f35e02b334dacb3a6c38d65959c4da72e072692a368654526bac08f3` |
| 入力契約 | `309f54e3da24b282101816defba5297480f87a9b834c2c03abb10719d8a3fc38` |
| summary.json | `43d845ca55900707eb893120ce039320dc3ef43fa2c49f429cbe088a65fcda7f` |
| FEMA宣言CSV | `49e3bdd14e34800a8b73bef04b8bce06ce611e17e450e6fcd308833e35d7b682` |
| 世界銀行系列CSV | `7d564c3a778ea0e2a219d04d08134fb7f688e4d99eac1757296dabf42f04ad92` |

## 未確認・不適切な用途

- FEMAの3ページを原子的な同時点のデータベース取引として取得したわけではない。
  ページごとの件数とIDは照合したが、同件数のまま行が入れ替わる等の更新を完全には排除できない。
- 異常な申請日を元の申請文書で訂正できていない。原値を事実上の処理時間と断定しない。
- 申請・宣言は入金や保護の開始ではない。被害・未申請者の全分母はない。
- 比率は政府の現金残高でも、適応予算の因果的な圧迫でもない。
- 文献の結果を再推定したわけではない。要旨までしか読めなかった文献は台帳で区別した。
- 上記は2026-10-25時点の検証記録であり、その時点ではローカルの未コミット変更だった。
  その後の公開・検証範囲は[2026-10-28改稿記録](../2026-10-28-manuscript-v03/README.ja.md)へ分ける。
