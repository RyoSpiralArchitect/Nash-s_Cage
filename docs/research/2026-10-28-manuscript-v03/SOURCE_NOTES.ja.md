# 論文v0.3のための追加出典確認

確認日：2026-10-28 JST。文献・公表資料の確認記録であり、新しい実験・因果推定ではない。
既存台帳の閲読日・閲読範囲は書き換えず、今回増えた確認と原稿への作用をここに記録する。
目的選択的な再確認であって、系統的レビューや独創性の確定ではない。RVCIMはF0のまま。

## 1. Ghesquiere & Mahul：法的・行政的実行経路も既に先行している

Francis Ghesquiere and Olivier Mahul (2010), *Financial Protection of the State against Natural
Disasters: A Primer*. World Bank Policy Research Working Paper 5429, September 2010。
[発行元書誌](https://documents.worldbank.org/en/publication/documents-reports/documentdetail/227011468175734792)、
[公式原文](https://documents1.worldbank.org/curated/en/227011468175734792/pdf/WPS5429.pdf)。

- 既存の記録：[異分野資料台帳R07](../2026-10-25-cross-domain-executability/SOURCES.ja.md)は要旨と本文pp.15–18を確認していた。
- 今回追加：本文p.12（PDFの14枚目）の *The Administrative and Legal Dimension* とBox 3の全文を、
  公開PDFの抽出テキストで確認。書誌・要旨も再確認した。全編の精読、実例の追試、現行制度の調査ではない。
- 先行する貢献：資金を早く調達しても、その配分・執行手続が未整備なら対応につながらないと論じ、
  緊急時の権限、予算配分と移転、実施調整、調達、資金追跡・監査、事前契約や物資予約を一緒に扱う。
  緊急性を理由に統制を外すことによる漏出にも注意を向けている。
- 原稿への作用：「時間と資金を結ぶ」「権限・支払・実施を一つの経路で見る」こと自体を、
  Nash's Cageが初めて発見したとは書かない。先行する実務設計を継ぐことを明示する。
- 限界：2010年の著者による研究枠組みであり、世界銀行の現行方針や2026年の金融条件ではない。
  本文の数値・商品条件・制度実例を現行入力へ移植していない。

本研究内の追加点の候補は、これらの要素を、受け手と非受益者、主体別・時点別の資金余裕、
共有の現物資源、実際の履行と継続、異議・訂正・解除まで追える入力契約と事前の検証条件に落とすことにある。
その組合せの学術的新規性も未確定である。「先行文献にはない」とは結論しない。

## 2. 実証研究：使う結果と、持ち込まない因果説明

以下は発行元の書誌・要旨または大学の著者最終稿登録情報を2026-10-28に再確認した。
推定表・補遺・再現コードの再実行は行っていない。既存台帳で本文を読めた範囲は、その記録を維持する。

| 書誌と一次出典 | 原稿に採用できる貢献 | 越えない境界 |
|---|---|---|
| Jean-Noël Barrot and Ramana Nanda (2020), “The Employment Effects of Faster Payment: Evidence from the Federal Quickpay Reform.” *Journal of Finance* 75(6), 3139–3173. DOI `10.1111/jofi.12955`。[学会の刊行版要旨](https://afajof.org/issue/volume-75-issue-6/) | 受取企業の雇用改善と、同じ労働市場の非対象企業への押し出しを併せて評価。逼迫市場で純効果が小さいという結果 | 支払前倒しを一般に否定しない。日本の保護施策への係数移植や、今回のデータによる再現ではない |
| Lorenzo Casaburi and Jack Willis (2018), “Time versus State in Insurance: Experimental Evidence from Contract Farming in Kenya.” *AER* 108(12), 3778–3813. DOI `10.1257/aer.20171526`。[出版社](https://www.aeaweb.org/articles?id=10.1257/aer.20171526) | 支払時点を変えた保険の無作為化試験。流動性だけでなく現在バイアス・取引相手の履行リスクも関わる | 保険加入は最終的な保護の履行ではない。同額の防災給付時点だけを変えた実験でもない |
| Tatyana Deryugina (2017), “The Fiscal Cost of Hurricanes: Disaster Aid versus Social Insurance.” *AEJ: Economic Policy* 9(3), 168–198. DOI `10.1257/pol.20140296`。[出版社](https://www.aeaweb.org/articles?id=10.1257/pol.20140296) | 災害専用制度以外の社会保障移転も、被災後の保護と公的費用の一部 | 災害予算だけを制度全体とみなさない。FEMAの宣言から支払や保護完了を推定する根拠にはならない |
| Tatyana Deryugina, Laura Kawano and Steven Levitt (2018), “The Economic Impact of Hurricane Katrina on Its Victims: Evidence from Individual Tax Returns.” *AEJ: Applied Economics* 10(2), 202–233. DOI `10.1257/app.20160307`。[出版社](https://www.aeaweb.org/articles?id=10.1257/app.20160307) | 所得・雇用の回復と、持続する居住地の変化を区別できる | 所得回復を全被災者の健康・厚生・地域の全面的回復と同一視しない |
| Jean-Noël Barrot and Julien Sauvagnat (2016), “Input Specificity and the Propagation of Idiosyncratic Shocks in Production Networks.” *QJE* 131(3), 1543–1592. DOI `10.1093/qje/qjw018`。[MIT登録情報・要旨](https://dspace.mit.edu/entities/publication/63f3398c-f351-4c90-9ad3-71bf214c9ab2) | 自然災害に伴う供給者のショックの伝播と、投入の特殊性を扱う | 資金移転だけで代替不能な投入物が生まれると置かない。モデルの崩壊閾値や効果量は採用しない |
| Rachel Young and Solomon Hsiang (2024), “Mortality caused by tropical cyclones in the United States.” *Nature* 635, 121–128. DOI `10.1038/s41586-024-07945-5`。[出版社本文](https://www.nature.com/articles/s41586-024-07945-5) | 災害後の影響を物理的事象の終了で打ち切らない根拠。今回は書誌、要旨、州単位の設計を説明する本文を再確認 | 長期死亡の推定は特定家計の「支払遅延→死亡」を識別しない。Katrinaの所得研究とは観測単位・期間が異なるため相殺しない |

Pople et al. (2026)の書誌は[Oxford大学の刊行版登録](https://ora.ox.ac.uk/objects/uuid%3Aca0b464e-9c4d-4aab-9553-1124b4f79747)でも確認した。
著者はAshley Pople, Ruth Hill, Stefan Dercon, Ben Brunckhorst、題名は
“The Importance of Being Early? Anticipatory Cash Transfers for Flood-Affected Households”、
*The World Bank Economic Review*, article `lhag016`, DOI `10.1093/wber/lhag016`、公刊日2026-05-11。
今回は本文の比較設計を再精読したとは扱わず、[既存S06の識別範囲](../../proposals/2026-10-24-joint-executability/SOURCES.ja.md)を維持する。
2020年介入の早期給付群と未受給群の主比較を、同額の早期・事後給付の無作為比較と書き換えない。

[WFPの2026-09-11公表ページ](https://www.wfp.org/publications/bangladesh-anticipatory-action-impact-evaluation)は、
同額の洪水前給付と約1・2か月後給付を比較する別の無作為化評価を紹介している。
今回は紹介ページだけを再確認し、全文・数表の閲読や媒介機構の同定に格上げしていない。
Pople et al.の研究と同一の研究として数えない。

## 3. 理論：候補となる機構と、既存命題の表現を整える

- Stephen Morris and Hyun Song Shin (2002), “Social Value of Public Information.” *AER* 92(5),
  1521–1534, DOI `10.1257/000282802762024610`。
  [出版社要旨](https://www.aeaweb.org/articles?id=10.1257/000282802762024610)を再確認。
  公共情報の効果は、戦略的補完性と私的情報を含むモデルで条件に依存する。
  「制度による罰則が変わらなければ情報は無効」と一般化しない。
  本稿の整備費による悪化を同論文の機構の再現とも呼ばない。
- Daron Acemoglu, Asuman Ozdaglar and Alireza Tahbaz-Salehi (2015), “Systemic Risk and Stability
  in Financial Networks.” *AER* 105(2), 564–608, DOI `10.1257/aer.20130456`。
  [出版社要旨](https://www.aeaweb.org/articles?id=10.1257/aer.20130456)を再確認。
  接続が安定化にも伝播にもなる条件付き金融モデル。社会制度の接続数から効果を判定する根拠にはしない。
- [PW-001–006](../prior-work/2026-10-28-coordination-capability-power.ja.md)の書誌・閲読範囲は別記録のまま保つ。
  Cooper & Johnの協調失敗、Holmström & Tiroleの流動性供給、Senの能力、Bachrach & Baratzの議題設定、
  Debnamの方法上の批判を、それぞれ理論・規範・概念批判として位置づける。
  今回の再確認ではHolmström & TiroleのNBERページは403となり、新しい本文確認は得ていない。

原稿への論理上の注意は、先行文献の実証結果とは別である。
他者の方策を固定し、協力・非協力の比較集合が非空で最大値が得られる条件の下では、
利得差が正なら協力は厳密に好まれ、ゼロなら同点になりうる。
厳密な正値を協力一般の必要条件とせず、各主体の好みから共同実行可能性・均衡・物理的保護を自動的に導かない。

## 4. UNEPの超過温暖化報告

United Nations Environment Programme (2026), *Limiting Overshoot: Navigating exceedance of
1.5°C and pathways towards return*. DOI `10.59117/20.500.11822/49857`。
[公式要旨](https://www.unep.org/en/publications/report/limiting-overshoot-navigating-exceedance-15degc-and-pathways-towards-return/executive-summary)
の項目1–6を再確認した。

長期平均の1.5℃超過という出発点、現在の公約を全面履行する楽観的シナリオでも予想ピークが1.8℃であること、
超過を安全・許容可能とはみなさないこと、排出削減と適応をともに進める必要を原稿へ反映する。
1.8℃をあらゆる経路の物理的下限とは呼ばない。救援費が将来の対策を圧迫するフィードバックの議論も先行しており、
本研究の新発見としない。温度指標が下がることから不可逆な損失の解消や支援終了を導かない。

## 5. この確認で行っていないこと

論文の全証明・補遺の精査、原データの再推定、制度の現行条件の網羅確認、実験の実行はしていない。
書誌の再確認は論文全体の妥当性の認証ではなく、外部の証拠は本研究のF0モデルを較正したことにもならない。
原論文全文・外部コード・ページ画像をRepoへ複製していない。

[研究ノート入口](../README.ja.md) / [先行研究目録](../prior-work/README.ja.md)
