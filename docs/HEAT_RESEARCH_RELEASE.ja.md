# 暑熱研究のPR統合境界

統合準備日: 2026-10-15。研究・資料確認の基準日は **2026-09-09** のまま。
新しい実測値の取得、制度の最新性調査、追加のFurnace実験は行っていない。

## 二つのレーン

| レーン | 同梱内容 | 主張できないこと |
|---|---|---|
| `heat_institution_v01` | 既存保護を同条件に固定した合成実験。開発1,280、評価10,240 arm-seasons。72条件と8対照 | 現実の保護効果、臨床安全性、Nash均衡、全国効果。総合勝者なし |
| `heat_public_audit_v01` | 公的8資料の保存・転記監査、公開死亡19事例の時計項目充足、費用経路の整理 | 現場の保護到達率、代表的応答時間、最終費用負担。実測較正はBLOCKED |

合成実験の解釈は [結果記録](HEAT_INSTITUTION_V01_RESULTS.ja.md)、公開資料監査の
入口は [成果物README](../artifacts/heat_public_audit_v01/README.md)。後者のHTMLは
リポジトリ同梱のスナップショットで、Webサイトの運用・公開ではない。
私的な会話、労働者の個票、現場別の賃金台帳は含めていない。

## 検証の接続

既存 `.github/workflows/verify.yml` に別の `heat` ジョブを追加した。
Ubuntu/Python 3.10・3.13 と Windows/Python 3.13 で、新レーンのテスト、
両合成出力の再生、公開監査の再構成、配布物のハッシュを検査する。
Windowsの新ジョブはGit BashからネイティブPythonを起動し、各ステップを
単一コマンドにして失敗を伝播させる。既存のPowerShell検証は変更しない。

旧61ファイルのrelease manifestは、その対象集合・主張上限を維持し、
**CIファイルのバイト数とハッシュだけ**を更新する。旧モデル、結果、receipt、
論文のハッシュは変えない。`make verify` 単独は旧レーンの検証であって、
暑熱レーンの検証を包含しない。新レーンは個別receiptと上記CIで別に確認する。
同じtree内のハッシュは内部整合性の検査であり、外部の根拠はreview済みGit commit。

ローカルでの追試（リポジトリのrootから）:

```sh
(cd experiments/heat_institution_v01 && python3 -m unittest -v test_run)
(cd experiments/heat_public_audit_v01 && python3 -m unittest -v test_run test_publication)
python3 experiments/heat_institution_v01/run.py verify --out artifacts/heat_institution_v01/development --replay --processes 2
python3 experiments/heat_institution_v01/run.py verify --out artifacts/heat_institution_v01/evaluation --replay --processes 2
python3 experiments/heat_public_audit_v01/run.py --out artifacts/heat_public_audit_v01/analysis-r02 --verify --input-revision r02
make verify
```

原資料はPDFだけでなくHTMLも原バイトを保持する。HTMLに含まれるCRLFをGitに
正規化させないため、原資料ディレクトリに限定した属性を設定した。
初回のHTML梱包失敗とr01入力、最終r02入力・出力、9月9日の検証記録を残す。
過去の「未push／未merge」等は当時の記録であり、後日のPR状態を表すものではない。

## 公開前の破壊テストと修正

初期実装では、同じ入力ハッシュの出力を再利用すると、出力内のsymlink先を
上書きできた。またreceiptの `calibration` を `READY` に変えても検証が通った。
使い捨ての合成ファイルで両方を再現した。研究成果物への改変・破壊は行っていない。

現行runnerは新規ディレクトリのみに発行し、symlinkを解決する前に祖先まで検査する。
発行前に一時領域で再構成検証し、既存ファイルは排他的作成で拒否する。
receiptの形式・時刻・較正ゲート・セル実行数・実行方法を厳密に照合し、JSONの
指数オーバーフローも拒否する。SQL接続も確実に閉じる。

修正前のr02の4入力は `history/r02_inputs/` に原バイトのまま保存した。
`--input-revision r02 --verify` は固定された旧receiptを、保存入力と現行の検証処理で
読み取り専用に再生する。旧runner自体は実行しない。元のHTML、ノートブック、
監査出力、receiptは変更しない。現行runnerで新規生成する場合は5入力を固定する。
OS自体やファイルシステムを乗っ取った並行書換えに対する隔離機構は主張しない。

## Mergeの条件

現行headに対するPRレビューの指摘を検討し、必要な回帰テストと修正を行う。
既存・新規のCIがすべて成功したheadだけをmergeする。
PR・CI・mergeの事実はGitHubの記録で確認し、ここで先取りして完了とは書かない。
実装・CI・mergeが完了しても、実測値が未取得という研究上のゲートは解除しない。
