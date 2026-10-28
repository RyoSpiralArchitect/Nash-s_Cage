# 異分野資料台帳

確認日：2026-10-25 JST。採用した9文献、継承したUNEP資料、2系統の公式データ。
検索結果の要約やニュースを独立の証拠として重複計上しない。
以下は読めた範囲の記録であり、全論文の査読・再現ではない。

## 探索の方針

語の類似だけでなく、(a)先行負担を動かす介入、(b)域外への押し出し、(c)既存制度の有効な応答、
(d)現物供給、(e)長期の残余被害、(f)政治的な選定、を別々に探した。
検索語の例：`Federal Quickpay faster payment employment`、`Time versus State insurance Kenya`、
`hurricanes social insurance fiscal cost`、`Katrina individual tax returns`、
`financial networks systemic risk`、`input specificity natural disasters production networks`、
`sovereign disaster finance liquidity risk layering`、`tropical cyclones long term mortality`、
`political economy FEMA disaster payments`。
系統的な検索式・網羅的な採否フローはない。刊行版・著者所属機関・公式提供者を優先した目的選択的レビュー。
数表の効果係数を合成モデルへ移植せず、研究ごとに観測単位と識別対象を残す。

## R01 — 政府調達と労働市場

Jean-Noël Barrot and Ramana Nanda (2020), “The Employment Effects of Faster Payment:
Evidence from the Federal Quickpay Reform.” *Journal of Finance* 75(6), 3139–3173.
DOI: [10.1111/jofi.12955](https://doi.org/10.1111/jofi.12955)。

- 確認：[発行学会の刊行版要旨](https://afajof.org/issue/volume-75-issue-6/)。
  HBS working paper 17-004の検索索引に序論の記述は得たが、直接PDF取得は403。
- 採用：対象企業の雇用効果と、地域の非対象企業への押し出しを区別する。
- 限界：今回は推定式・個票・頑健性検証を再現していない。刊行版の効果量を別分野に転用しない。
- [学会の再現資料案内](https://afajof.org/supplements/)は確認したが、再現パッケージの実行はしていない。

## R02 — 保険料の時点、選好、仲介者の履行

Lorenzo Casaburi and Jack Willis (2018), “Time versus State in Insurance:
Experimental Evidence from Contract Farming in Kenya.” *AER* 108(12), 3778–3813.
DOI: [10.1257/aer.20171526](https://www.aeaweb.org/articles?id=10.1257/aer.20171526)。

- 確認：出版社要旨と[ATAI公開の刊行PDF](https://www.atai-research.org/wp-content/uploads/2017/08/aer.20171526.pdf)。
  pp.3778–3781、設計§II、Fig.3・Table 2、§IVの現金供与・時間選好・履行リスクに関する箇所。
- 採用：本文で示した加入率、利息付きの設計、単純な現金不足だけでは足りない点、仲介企業の履行問題。
- 限界：無作為化された購入条件の研究であり、同額の防災給付時点の純効果でも、長期の被害軽減率でもない。
  企業の経営難を保険の因果効果としない。

## R03 — 災害専用支出の外にある保護

Tatyana Deryugina (2017), “The Fiscal Cost of Hurricanes: Disaster Aid versus Social Insurance.”
*AEJ: Economic Policy* 9(3), 168–198.
[10.1257/pol.20140296](https://www.aeaweb.org/articles?id=10.1257/pol.20140296)。

- 確認：出版社要旨。補遺の存在は確認したが、本文PDFの直接取得は403。
- 採用：被災郡で災害専用でない政府移転が増加するという論文の結果。
- 限界：今回のFEMA記録へ効果額を足していない。現在の米国や他国の全制度の有効性を保証しない。

## R04 — 回復の反例と観測単位

Tatyana Deryugina, Laura Kawano and Steven Levitt (2018), “The Economic Impact of Hurricane
Katrina on Its Victims: Evidence from Individual Tax Returns.” *AEJ: Applied Economics* 10(2), 202–233.
[10.1257/app.20160307](https://www.aeaweb.org/articles?id=10.1257/app.20160307)。

- 確認：出版社要旨。著者による[NBER解説](https://www.nber.org/reporter/2021number1/economic-lessons-natural-disasters)の
  人と場所を区別する箇所。本文PDFの直接取得は403。
- 採用：所得・雇用の比較的短期の変化と持続する居住地の変化を区別する。
- 限界：税務記録で追える集団・経済指標の研究。全被災者の総厚生、健康、被害の消滅ではない。

## R05 — 接続による分散と伝播

Daron Acemoglu, Asuman Ozdaglar and Alireza Tahbaz-Salehi (2015), “Systemic Risk and Stability
in Financial Networks.” *AER* 105(2), 564–608.
[10.1257/aer.20130456](https://www.aeaweb.org/articles?id=10.1257/aer.20130456)。

- 確認：出版社の刊行版要旨とMIT公開working paperの要旨。刊行版の全証明は未精査。
- 採用：結合の効果がショックの規模等に依存するという条件付きの理論的先例。
- 限界：銀行間債務モデル。防災組織の接続や本稿の整備費の作用と同一ではない。

## R06 — 資金で代替できない投入物

Jean-Noël Barrot and Julien Sauvagnat (2016), “Input Specificity and the Propagation of
Idiosyncratic Shocks in Production Networks.” *QJE* 131(3), 1543–1592.
[10.1093/qje/qjw018](https://doi.org/10.1093/qje/qjw018)。

- 確認：[MIT著者最終稿の登録情報と要旨](https://dspace.mit.edu/entities/publication/63f3398c-f351-4c90-9ad3-71bf214c9ab2)。
- 採用：自然災害に伴う供給者のショックが顧客・他の供給者へ伝わり、投入の特殊性が関わるという実証結果。
- 限界：全モデル・推定表を再検証していない。本稿では効果量を用いず、現物供給経路を別に記録する根拠とする。

## R07 — 「資金の時間」は先行研究の中心でもある

Francis Ghesquiere and Olivier Mahul (2010), “Financial Protection of the State against
Natural Disasters: A Primer.” World Bank Policy Research Working Paper 5429.
[公式PDF](https://documents1.worldbank.org/curated/en/227011468175734792/pdf/WPS5429.pdf)。

- 確認：要旨、本文pp.15–18（PDF pp.16–19）、資金不足とrisk layeringの節。
- 採用：即時の流動性と復興全体の資源を分け、手段の費用・利用可能時点を比較する先行整理。
- 限界：2010年の研究。記載された商品条件や費用表を2026年の現行条件とは呼ばず、係数も採用しない。
  working paperの著者見解と世銀の現行政策を区別する。

## R08 — 長い履歴と、特定できていない媒介経路

Rachel Young and Solomon Hsiang (2024), “Mortality caused by tropical cyclones in the United States.”
*Nature* 635, 121–128.
[10.1038/s41586-024-07945-5](https://www.nature.com/articles/s41586-024-07945-5)。

- 確認：公式の本文HTML、要旨、観測期間・州単位の設計、死亡の時間応答、Methodsに関する本文記述。
  補遺の全頑健性検証とコードの再実行はしていない。
- 採用：物理的な災害終了と長期の健康影響を切り離す必要。
- 限界：州別の長期推定は特定の家計の「支払遅延→死亡」の因果鎖を同定しない。
  今回の2000–2024年の宣言群とは対象・期間・粒度が違う。死亡係数は移植しない。

## R09 — 行政上の選定にも競合説明がある

Thomas A. Garrett and Russell S. Sobel (2003), “The Political Economy of FEMA Disaster Payments.”
*Economic Inquiry* 41(3), 496–509.
[10.1093/ei/cbg023](https://onlinelibrary.wiley.com/doi/abs/10.1093/ei/cbg023)。

- 確認：出版社の書誌と要旨。St. Louis Fed公開working paperの書誌は確認、直接PDFは502。
- 採用：宣言・配分に政治的な説明を検討した歴史的な先例。需要・能力だけの機構に限定しない。
- 限界：要旨が報告する政治要因の割合は採用しない。対象期間・推定仕様の再点検は未了。
  本稿データで現在の政治的偏りを測ったことにはならない。
  刊行年は巻号の2003年を用い、サイトの電子掲載日2007年と混同しない。

## R10 — 前稿から継承した気候上の出発点

UNEP (2026), *Limiting Overshoot: Navigating the Exceedance of 1.5°C and Pathways towards Return*.
[公式要旨](https://www.unep.org/en/publications/report/limiting-overshoot-navigating-exceedance-15degc-and-pathways-towards-return/executive-summary)。

- 今回再確認：要旨の項目1–5。原報告の既読範囲は[前稿資料台帳S14](../../proposals/2026-10-24-joint-executability/SOURCES.ja.md)に記録済み。
- 採用：長期平均の超過、現在の公約全面履行シナリオの予想ピーク、対策継続の必要。
- 限界：約1.8℃は普遍的な物理下限でも許容目標でもない。

## D01 — OpenFEMA

[データ紹介](https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2)、
[データAPI](https://www.fema.gov/api/open/v2/DisasterDeclarationsSummaries)、
[辞書API](https://www.fema.gov/api/open/v1/OpenFemaDataSetFields)。

- HTML紹介ページは403だったが、公式APIで定義・対象・本文を取得した。
- 公的な宣言・指定地域の記録。支払日、現場の保護開始、受益者全体の分母を持つデータではない。
- データ辞書はdeclarationDate、declarationRequestDate、incidentBeginDateを別項目として定義している。
- 原文の取得URL・時刻・ハッシュは[manifest](../../../artifacts/cross_domain_audit_v01/snapshot_20261025/manifest.json)。
- 必要な帰属表示は[入力契約](../../../experiments/cross_domain_audit_v01/CONTRACT.ja.md)に記載。

## D02 — World Bank WDI / International Debt Statistics

[総外債返済比率](https://data.worldbank.org/indicator/DT.TDS.DECT.EX.ZS)、
[公的・保証付き返済比率](https://data.worldbank.org/indicator/DT.TDS.DPPG.XP.ZS)。CC BY 4.0。

- APIの指標メタデータと国×年の実値を保存。取得された系列の`lastupdated`は2026-10-08。
- 分子は実際に支払われた元利払等、分母は輸出受取。政府税収でも、将来支払予定でもない。
- 対象、年、指標、比較窓、欠測処理は[入力契約](../../../experiments/cross_domain_audit_v01/CONTRACT.ja.md)。
- 年次比率は再集計できるが、日次の資金繰りや災害時の支払能力を同定できない。

## アクセスできなかった追加候補

世銀IEGの *Managing Disaster-Related Fiscal Risks in a Shock-Prone World* のOverview/Chapter 4は検索索引に
内容が出たが、直接取得が403で、今回の結論の根拠には採用していない。
前稿のWFP評価全文も今回再取得しておらず、既読の公表概要を定量的根拠へ格上げしていない。
