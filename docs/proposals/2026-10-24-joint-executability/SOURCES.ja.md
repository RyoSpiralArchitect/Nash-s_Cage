# 資料台帳：保護の同時実行可能性仮説

初回確認日：2026-10-24 JST。S06の比較対象・識別範囲を2026-10-25 JSTに追加照合。
[理論草案](PROPOSAL.ja.md)の根拠・対立する説明・未確認点を分けた選択的な文献調査。
系統的レビュー、網羅性保証、独創性の確定、現行法の網羅的確認ではない。
本文を読めた範囲と、発行元の要旨だけを確認した資料を区別する。
ウェブ原本の新しい固定アーカイブは作成しておらず、以下はURLと閲読範囲の記録である。
過去の保存資料やハッシュを、今回の取得物だと主張しない。

## A. 理論・方法と対立する説明

### S01 — 多中心的制度：Ostrom, 2010

Elinor Ostrom. “Beyond Markets and States: Polycentric Governance of Complex Economic Systems.”
American Economic Review 100(3), 641–672. DOI: `10.1257/aer.100.3.641`。

- [出版社・書誌](https://www.aeaweb.org/articles?id=10.1257/aer.100.3.641)
- [大学公開の論文複製](https://web.augsburg.edu/sabo/BeyondMarketsandStatesPolycentricGovernanceofComplexEconomicSystems.pdf)
- 閲読範囲：出版社書誌、公開論文の冒頭。後続ページの取得は不安定で、全編精読を主張しない。
- 採用：市場／国家の二分法では捉えにくい、多層の制度配置を扱う先行研究。
- 制限：全体を一つの司令塔として設計する発想への歯止め。特定の接続方式が常に優越するという根拠にはしない。

### S02 — 行政負担：Moynihan, Herd and Harvey, 2015

Donald Moynihan, Pamela Herd, Hope Harvey.
“Administrative Burden: Learning, Psychological, and Compliance Costs in Citizen-State Interactions.”
Journal of Public Administration Research and Theory 25(1), 43–69.
DOI: `10.1093/jopart/muu009`。

- [出版社](https://doi.org/10.1093/jopart/muu009)
- 閲読範囲：出版社の検索取得で要旨・書誌を確認。本文はアクセスエラーとなり未精読。
- 採用：市民側の学習・心理・遵守の負担、および負担配分が政治的選択になりうるという問題設定。
- 制限：心理的負担を金銭に単純換算しない。暑熱現場の遅延や賃金への係数は得られない。

### S03 — 継続可能な制御：Mayne et al., 2000

D. Q. Mayne, J. B. Rawlings, C. V. Rao, P. O. M. Scokaert.
“Constrained model predictive control: Stability and optimality.”
Automatica 36(6), 789–814. DOI: `10.1016/S0005-1098(99)00214-9`。

- [出版社](https://www.sciencedirect.com/science/article/pii/S0005109899002149)
- [著者所属大学の論文情報](https://experts.illinois.edu/en/publications/constrained-model-predictive-control-stability-and-optimality/)
- 閲読範囲：大学掲載の要旨、出版社検索取得の導入・定式化部分。全ての証明は未確認。
- 採用：有限期間で計画し最初の操作を適用する方法、状態・操作・終端条件と安定性の区別。
- 制限：工学的制御の保証が、入力未同定の社会制度や当リポジトリのv0.4に成立するとは言わない。

### S04 — 適応経路：Haasnoot et al., 2013

Marjolijn Haasnoot, Jan H. Kwakkel, Warren E. Walker, Judith ter Maat.
“Dynamic adaptive policy pathways: A method for crafting robust decisions for a deeply uncertain world.”
Global Environmental Change 23(2), 485–498. DOI: `10.1016/j.gloenvcha.2012.12.006`。

- [大学公開原論文](https://ris.utwente.nl/ws/files/247793059/Haasnoot2013dynamic.pdf)
- [開発機関の手法解説](https://publicwiki.deltares.nl/pages/viewpage.action?navigatingVersions=true&pageId=119053112)
- 閲読範囲：原論文の要旨、2節の経路・切替・監視、4節の実装準備に関する部分。
- 採用：条件が変わると従来行動が目的を満たさなくなること、切替と将来の選択肢を準備すること。
- 制限：「経路」「見直し」「選択肢を残す」は既存の考え。本提案だけの新規概念とはしない。

### S05 — 情報が作用する別機構：Morris and Shin, 2002

Stephen Morris, Hyun Song Shin. “Social Value of Public Information.”
American Economic Review 92(5), 1521–1534. DOI: `10.1257/000282802762024610`。

- [出版社・要旨](https://www.aeaweb.org/articles?id=10.1257/000282802762024610)
- [著者所属大学の原論文](https://economics.mit.edu/sites/default/files/publications/morris-socialvalueofpublicinformation.pdf)
- 閲読範囲：原論文p.1521以降の導入と要旨。
- 採用：他者への同調・戦略的補完性と私的情報を含む特定モデルでは、公共情報の厚生効果が一意に正とは限らない。
- 対立する説明：制度接続の結果が資金・時間だけでなく、信念や協調の仕組みを通じて変わる可能性。
- 制限：同論文にも情報が有益となる条件がある。暑熱合成の整備費による悪化を、この機構の再現とは呼ばない。

## B. 支払の時点に関する実証研究

### S06 — 洪水前の現金給付：Pople et al., 2026

Ashley Pople, Ruth Hill, Stefan Dercon, Ben Brunckhorst.
“The Importance of Being Early? Anticipatory Cash Transfers for Flood-Affected Households.”
The World Bank Economic Review, lhag016. 2026-05-11公刊。
DOI: `10.1093/wber/lhag016`。

- [出版社・本文](https://academic.oup.com/wber/advance-article/doi/10.1093/wber/lhag016/8675570)
- 閲読範囲：要旨、導入、受給群の定義と識別上の制約を説明する部分。10月25日に3.1節・8節を追加照合。
- 対象：2020年のバングラデシュ洪水。2026年の新しい災害の観測ではない。
- 比較対象：主要比較は早期給付群と未受給群。同額の早期・事後給付の直接比較はできないと8節に明記される。
- 採用：早い給付と、選べる対応・資産保全・厚生の関係を問う実証的な先行研究。
- 重要な制限：利用するデジタル口座等が受給を分ける非無作為比較。観測できる属性には限りがあり、著者も所得・資産等の未観測差を点検できない制約を記す。
- 不採用：日本の暑熱への効果量移植、主要比較によって同額支払の「時点だけ」の効果を識別したとの主張。

### S07 — 同額の事前・事後給付：WFP, 2026

World Food Programme. “Bangladesh, Anticipatory Action: Impact evaluation.”
発行元ページ公表日：2026-09-11。

- [発行元の評価概要](https://www.wfp.org/publications/bangladesh-anticipatory-action-impact-evaluation)
- [評価報告書へのリンク](https://docs.wfp.org/api/documents/WFP-0000175893/download/)
- 確認範囲：WFPの紹介ページのみ。PDFリンクは閲読可能な本文を返さず、方法・数表・実施年の詳細は未確認。
- 発行元の説明：洪水ピーク前と約1か月後・2か月後の給付を比べる無作為化評価で、同額の事前給付の利点を報告。
- 位置づけ：支払時点を区別する研究として重要な追加閲読候補。S06と同じ研究とみなさない。
- 不採用：標本数、効果量、流動性が媒介した割合、本仮説がこの報告で証明されたとの主張。

## C. 既存制度と更新を尊重するための公的資料

### S08 — 厚生労働省、2026-03-18

「職場における熱中症防止対策に係る検討会」報告書等と、
「職場における熱中症防止のためのガイドライン」。

- [公表ページ](https://www.mhlw.go.jp/stf/newpage_71721.html)
- [ガイドライン本文](https://www.mhlw.go.jp/content/11201250/001676048.pdf)
- 閲読範囲：公表ページの要点、本文第1・第2・第3冒頭。臨床手順全体のレビューではない。
- 採用：既存制度自身が、リスク評価、作業環境・作業管理等を一体として扱い、業種・業態に応じた選択を促している。
- 区別：ガイドラインの望ましい措置と、安衛則上の義務を同じ強さの規範として扱わない。
- 不採用：制度の存在からの現場実行率、保護率、死亡減少の独立した因果推定。
  公表ページにある施策寄与の評価は、当方が因果効果を同定したことを意味しない。

### S09 — 国土交通省、2026-02-27通知／2026-04-01適用

「土木請負工事における現場環境改善費の積算要領」。

- [猛暑対策の公式入口](https://www.mlit.go.jp/about/nettyuu.html)
- [通知・積算要領](https://www.mlit.go.jp/tec/content/001984908.pdf)
- 閲読範囲：通知、要領第3～第6。本文の費用経路・対象・適用日を確認。
- 採用：施設・設備等の費用を積算する既存経路。第4の100%は所定の現場環境改善費を基礎とする上限。
- 不採用：実費や休業賃金の100%補償、末端への入金済み額、全自治体・民間工事への一律適用。

### S10 — 新潟県農地部、2026-10-20更新

「工事における現場環境改善費の積算要領の一部改定について（令和8年10月）」。

- [発行部署の改定案内](https://www.pref.niigata.lg.jp/sec/nochikanri/1347224530209.html)
- 閲読範囲：改定内容と適用時期のウェブ本文。別添要領全条項は未レビュー。
- 採用：当該部署の案内には、熱中症・防寒の施設設備の積上げ上限（従前の率計上額50%）撤廃、協議・変更等の整理が記され、2026-10-20以降の入札公告・通知の工事からの適用が示される。
- 含意：制度を静的な全国共通値へ潰さず、発注主体・文書版・公告日をキーにする必要がある。
- 不採用：「国の100%上限が全国で撤廃された」という読み替え、当該対象工事の実際の支払完了。
  9月9日の監査記録を遡って書き換える根拠にも用いない。

### S11 — IPCC AR6 WGII, 2022

Climate Change 2022: Impacts, Adaptation and Vulnerability,
Summary for Policymakers, C.3–C.5。

- [公式SPM](https://www.ipcc.ch/report/ar6/wg2/chapter/summary-for-policymakers/)
- [公式第16章](https://www.ipcc.ch/report/ar6/wg2/chapter/chapter-16/)
- 閲読範囲：公式サイトから検索取得された適応限界・不適応・実施条件の該当部分。
  直接openは403となった。新しい全編レビューや最新報告書の網羅確認ではない。
- 採用：資金・制度等の制約、硬い適応限界、適応しても残る損失、負担が偏る危険の区別。
- 制限：公的な統合評価であり、当仮説を直接検証した単一の実験ではない。
  「資金と制度をつなげば必ず回復する」という過大な提唱を制限する資料。

## D. 発電レーンの出典を再確認した範囲

### S12 — FY2024総合エネルギー統計・2026 NID

- [経産省・FY2024確報の公表（2026-04-14）](https://www.meti.go.jp/press/2026/04/20260414001/20260414001.html)
- [資源エネルギー庁・統計入口](https://www.enecho.meti.go.jp/statistics/total_energy/results.html)
- [国立環境研究所・2026 NID時系列データ（2026-05-29）](https://www.nies.go.jp/gio/archive/nirdata/2026.html)
- 確認範囲：METI/資源エネルギー庁は公式ページの検索取得、NIESは公式ページの直接閲読。
  元Excelを再ダウンロード・再抽出・再計算していない。
- 採用：既存会計入力の出典・年次・公表日の再確認。保存済み21区分の17/1/3は、当リポジトリの固定結果から引用する。
- 不採用：今回の閲読時点での生データとのバイト一致、現在の油種別在庫、特定機の限界排出効果、部門別炭素予算。

## E. Ryōの追加提示：1.5℃超過と、残された経路

### S13 — Health Policy Watch, 2026-09-02

Stefan Anderson. “World Has No Realistic Path to Meet 1.5ºC Warming Target, UN Declares.”

- [提示された記事](https://healthpolicy-watch.news/world-has-missed-1-5c-warming-target-un-declares/)
- 閲読範囲：記事本文。記事から一次報告・公式要旨・発表資料へ遡った。
- 位置づけ：今回の問いを更新した報道資料。理論・科学上の根拠はS14へ直接接続する。

### S14 — UNEP, 2026-09-02公表

United Nations Environment Programme. Limiting Overshoot: Navigating exceedance of 1.5°C and pathways towards return.
Nairobi. DOI: 10.59117/20.500.11822/49857.

- [公式書誌・公開入口](https://wedocs.unep.org/handle/20.500.11822/49857)
- [公式要旨](https://www.unep.org/en/publications/report/limiting-overshoot-navigating-exceedance-15degc-and-pathways-towards-return/executive-summary)
- [原報告](https://wedocs.unep.org/bitstreams/fedb12d1-54de-4ab7-bed9-6e8d9522f8b4/download)
- [公式発表](https://www.unep.org/en/news-and-stories/press-release/unep-world-set-cross-15degc-global-warming-can-still-limit-adapt-and)
- 閲読範囲：公式要旨・発表、原報告の本文p.17（1.2と注4–6）、p.44 Box 2、pp.86–87、結論冒頭p.89。全編精読ではない。
- 採用：草案6.1の三点、および危機中の資金・制度能力の圧迫。長期平均の超過見通しを、単年の記録だけの話へ縮小しない。
- 数値の扱い：約1.8℃は特定の公約実行シナリオの中心推計。安全基準でも全経路に共通の物理的下限でもない。
- 記事中の「あと3年」等は本提案の入力係数に採用していない。個別の国・燃料・設備に世界の炭素予算を割り当てたとも主張しない。
- 理論への作用：「通常運用へ移行」を被害前への復元と同一視しない。同報告が先行している機構を、本稿の新発見と主張しない。
- 公的評価の重要な更新として採用する。これによって当リポジトリの合成結果が実証へ昇格するわけではない。

## F. 調べたが主要根拠に昇格しなかったもの

- Blackwell (1951), “Comparison of Experiments”：
  [Berkeleyの原論文書誌](https://digicoll.lib.berkeley.edu/record/112749)を確認したがPDF本文は403。
  Blackwell (1953), DOI `10.1214/aoms/1177729032` も原文を取得できなかった。
  原定理を今回精読したとは扱わない。草案の命題Aは、限定した集合包含から独立に示す。
- Nobel PrizeのOstrom講演ページ・PDFは取得に失敗し、S01では出版社と論文複製を利用した。
- 発行元以外の紹介記事は探索の手がかりにとどめ、効果量の根拠には使わなかった。

## G. 既存結果の参照点と初稿時の照合（2026-10-24）

対象checkout：`RyoSpiralArchitect/Nash-s_Cage`。
基準commit：[803200abc3bd1759550bddc323ee15e6bfc363a2](https://github.com/RyoSpiralArchitect/Nash-s_Cage/commit/803200abc3bd1759550bddc323ee15e6bfc363a2)。
開始時にローカルmainの同SHAと未変更状態を確認した。最新リモートを取得したとの主張はしない。

| 入力 | 今回行った読み取り・算術照合 | 行っていないこと |
|---|---|---|
| `artifacts/feasibility_v03/episodes.csv` | evaluation 5,184行をscenario/controllerで再集計し、失敗数・緊急時間・残予算を既存集計と照合 | モデル実行、全トレース監査、係数変更 |
| `artifacts/sustained_v04/episodes.csv` | evaluationかつprimaryの960行を同様に集計。48ケースずつの基準17対7と緊急時間66.958333を確認 | 事後選択の回帰ロットを独立評価に合算すること |
| `artifacts/heat_institution_v01/evaluation/episodes.csv` | 10,240行を読み、factorialの2,304対応世界をscenario/seedで突合。各世界4arm、各条件32seed。72条件の情報＋接続−通常の平均曝露差の符号が26/22/24と確認 | 新しい乱数生成、追加シーズン、仮説検定 |
| `artifacts/power_jp_fy2024/summary.json` | 21行、RECONCILED 17、REJECT 1、UNKNOWN 3を既存文書と照合 | 原Excelの再照合、実測在庫の推定 |
| `artifacts/heat_public_audit_v01/analysis-r02/audit.json` | 公開死亡要約の時計対0/19と、三つの較正ゲートが未解消であることを確認 | 0/19を応答なし・保護なしと解釈すること |

暑熱の照合では、保存CSVの小数丸めを考慮し、条件平均差の絶対値1e-9未満をゼロとして数えた。
これは数値照合の許容幅であり、統計的な同等性判定ではない。
最初の補助集計コマンドは構文エラーで停止したため採用せず、標準CSV読み取りによる集計で照合した。
既存の実験runner、テストスイート、replayは一度も起動していない。
この実行範囲の記述は10月24日の初稿作成時を指す。翌日の読み合わせ・merge用の既存CIは
[レビュー記録](REVIEW.ja.md)とPR上の検証記録で区別し、新しい仮説の実証には数えない。

分析検証では、既存結果、実装に置いた仮定、外部資料、今回の推論を分けた。
とくに「到達量≠健康保護」「公開制度≠現場への到達」「総予算≠主体別の途中残高」を区別した。
評価は、理論草案として **Share with caveats**。仮説の実証、効果の因果同定、現場の実行権限は未取得。
この台帳自体は、原資料の真正性を暗号学的に認証するreceiptではない。
