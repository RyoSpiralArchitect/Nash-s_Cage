# 改稿v0.4の検証・点検記録

2026-11-10 JST。ローカル検証であり、外部査読・実証確認とは区別する。

## 論文と設計の点検

- 旧稿の「訂正可能性」と重複するため、新発見ではなく待機中の行使条件の具体化と明記。
- 行使可能性を成功結果で定義する循環、実現した待機時間での事後条件付け、
  追加資源・未来情報による優位、名目的な権利と実行の混同を点検し、禁止事項を本文と設計へ記載。
- 規範の正当性、F0の記録識別、現実の因果効果、戦略的均衡の四つを分離。
  行使可能経路でも無改善・悪化・他者への押し出しを許す。次期試験は未実装・未凍結・未実行。
- 自己点検であり、別エージェントの独立レビューや外部査読を実施したとはしない。

## 実施済みの確認

- Tectonic 0.17.0で36ページのPDFを生成。全ページを画像化して一覧確認し、
  PDF頁18・19（訂正可能性・待機権限）、24（COP31）、26（次試験）を拡大確認。
  引き継いだ構成図の二つの箱の重なりをv0.4だけで修正し、再生成した。
- 文献55キー（全55引用）、ラベル66件の重複・未定義なし。
  最終TeXログで未解決参照・引用、欠落文字、overfull/underfull boxは検出されなかった。
  inputencを無視する通知、shell escape無効、BibTeX代替バックエンドの警告は残る。
  最初のビルドで見つかった文献URLの改頁時注釈警告は、書誌項目を途中改頁しない設定で解消。
- `make verify`成功：67ファイルの整合性、7群212テスト、従来のsmoke、
  reference・feasibility・sustained・powerの凍結fixture検証と再生。
- 前のexecutability-twins専用27テスト成功、保存済み全列挙のhash検証成功。
  この改稿では全列挙を新たに回さず、`audit.py`で保存出力を独立集計し`RECOUNT_MATCH`を確認。
  36,864世界、147,456 arm-worlds、143,484 class×contrast行、18要約、14例示組を照合。
- 旧稿TeX・PDF・書誌と、実験7入力・既存出力は保存。抽選結果は実験データや科学的出典へ入れていない。

## 再現用コマンド

```sh
make verify
python3 -B -m unittest discover -s experiments/executability_twins_v01 -p 'test_*.py' -v
python3 -B experiments/executability_twins_v01/run.py verify --out artifacts/executability_twins_v01/enumeration_20261104
python3 -B docs/research/2026-11-04-executability-twins/audit.py artifacts/executability_twins_v01/enumeration_20261104
```

通常のTeX環境では`make paper`。このホストでは`paper/`から次を実行した。

```sh
/Applications/ChatGPT.app/Contents/Resources/tectonic/tectonic -X compile \
  --outdir ../.tmp/paper-v04 --outfmt pdf --keep-logs --keep-intermediates \
  --untrusted nashs_cage_rvcim_v0_4.tex
```

生成したPDFを新設のv0.4に複製してmanifestを更新した。エンジンや作成時刻の異なるビルドとの
PDFバイト同一性は要求しない。原稿の独立した正しさ・出典の真正性を証明する検査ではない。

## 公開対象の別展開での確認

ステージ済みGit tree `2f8e9dedaa63f8237d298c1b6892dc5cf03b7571` を空の一時ディレクトリへ展開し、
`make verify`、専用27テスト、保存済み全列挙のhash検証、独立集計を再実行して全て成功。
同じ展開からTectonicで再生成し、手元の最終PDFと36ページすべての抽出本文が一致した。
抽出本文一致はPDFバイト一致や描画の完全同一性を意味しない。
この確認後は本検証記録だけを追記した。

公開対象のMarkdown 17ファイル、ローカルリンク先123件が存在。リモートURLと見出しfragmentの全件自動検証ではない。
既存の論文関連8ファイルは基点manifestとhash一致。`git diff --cached --check`成功。
最終PDFの構成図も拡大画像で重なり解消を確認した。
