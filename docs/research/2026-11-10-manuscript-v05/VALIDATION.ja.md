# v0.5検証記録

2026-11-10 JST。以下は整合性・再現性の検査であり、独立した理論検証や実証ではない。

## 作業木で確認済み

- `make verify`: 成功。70ファイルのrelease closure、212単体テスト、smoke、旧fixtureの再生を確認。
- 待機試験の別lane: 26テスト成功。登録・8入力・全出力の検証と全列挙の同一コード再生が成功。
- 保存イベントをモデル非importの`audit.py`で独立再集計し、既存`recount.json`とバイト一致。
  18,432世界、55,296 arm-worlds、49,608 class-contrast rows、51 witness pairs。
- 待機試験のモデル・入力・結果を変更していない。再集計は独立な世界生成器ではない。
- 新稿のTeX・PDF・専用書誌を追加。過去稿v0.1–v0.4のmanifest記録は不変。
- Tectonic 0.17.0でビルド成功。37 PDFページ（無番号の表紙＋本文36ページ）。
  最終TeX passには未解決引用・参照、missing character、overfull/underfull boxなし。
  inputenc無視、shell escape無効、biblatexのBibTeX fallbackという既知警告は残る。
  初回passの目次生成前にはoverfull警告が出たが、最終passでは解消した。
- 全37ページの縮小画像を確認し、要旨・待機結果・結論を拡大点検。数値表・改ページ・文字の欠けを確認。
  未定義だったHypothesisの相互参照表示を新稿のみに追加し、解消を確認。
- `git diff --check`: 成功。

## 公開前後の検証

- staged tree `6a6b3bf9d8175299a146ede34a80ba641db8cabe`を一時ディレクトリへGit archiveで書き出し、
  `make verify`と待機試験の全出力再生を再確認した。
- クリーン書き出しの新稿をTectonicで再構築し、保存PDFと全37ページの抽出テキストが一致。
  PDF全体のバイト同一性を主張する検査ではない。
- 新規・更新Markdown 10文書のローカルリンク56件に欠落なし。
- PRのCIとfresh-eyeレビューの状態はPRおよびレビュー記録で区別する。

保存済み全列挙のreceipt SHA-256:
`508a3829f1d6528534b5cb1c74e446f0ff8e290552a396b93ea9904826d325ed`

登録SHA-256:
`a59505a4c4ba81ddaf15349aea82ac5348f0fae9ae1f93b899f359f6409cdff4`
