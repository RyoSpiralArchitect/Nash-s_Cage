"""Project checked public results into bounded native-chart/source payloads."""
import argparse
import csv
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--analysis", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    with (args.analysis / "world_bank_series.csv").open() as f:
        cells = list(csv.DictReader(f))
    summary = json.loads((args.analysis / "summary.json").read_text())
    labels = {"DT.TDS.DECT.EX.ZS": "総外債", "DT.TDS.DPPG.XP.ZS": "公的・保証付き長期外債"}
    rows = [{"year": r["year"], "scope": labels[r["indicator"]],
             "ratio_pct": None if r["value_pct"] == "" else float(r["value_pct"])}
            for r in cells if r["country"] == "BGD"]
    rows.sort(key=lambda r: (r["year"], r["scope"]))
    source = {
        "label": "World Bank WDI / International Debt Statistics",
        "links": [
            {"label": "総外債返済比率", "url": "https://data.worldbank.org/indicator/DT.TDS.DECT.EX.ZS"},
            {"label": "公的・保証付き返済比率", "url": "https://data.worldbank.org/indicator/DT.TDS.DPPG.XP.ZS"}],
        "metricDefinitions": [
            {"id": "total-debt", "name": "総外債", "definition": "総外債返済比率は実際の外債返済・利払等を財・サービス・第一次所得の輸出受取で割った百分率。"},
            {"id": "public-debt", "name": "公的・保証付き", "definition": "公的・保証付き長期外債返済比率は当該の元利払を同じ輸出受取で割った百分率。"}],
        "filters": ["国: Bangladesh", "指標: DT.TDS.DECT.EX.ZS と DT.TDS.DPPG.XP.ZS"],
        "caveats": ["分母は政府税収ではない。国の年次比率から政府・現場の時点別資金繰りは同定できない。",
                    "両指標は対象が重なっており、合計しない。国内債務・未払予定額は表さない。",
                    "原APIの最終更新日は2026-10-08。取得日とは別。CC BY 4.0。"],
        "evidenceFlow": [{"kind": "validation", "title": "確認した結果", "detail": "2か国×25年×2指標の100セルに欠測・重複はなく、比較窓8件の平均と分母を元APIから別言語で再計算し一致した。図はそのうちBangladeshの50セル。"}]
    }
    chart = {"schemaVersion": 1, "id": "bangladesh-debt-scope", "queryId": "wb-bangladesh-history",
             "title": "バングラデシュの外債返済比率",
             "description": "2000–2024年。分母は輸出受取で、政府税収ではない。",
             "chart": {"type": "line", "x": "year", "y": "ratio_pct", "series": "scope",
                       "xLabel": "年", "yLabel": "輸出受取に対する比率（%）", "startAtZero": True,
                       "showXAxisLabel": False, "showLegend": True},
             "rows": rows, "columns": ["year", "scope", "ratio_pct"], "source": source,
             "theme": "codex-classic", "height": 330}
    receipt = {"schemaVersion": 1, "items": [{"id": "bangladesh-debt-scope", "title": "年次外債返済比率の対象別比較",
                "queries": [{"id": "wb-bangladesh-history", "source": source, "rows": rows,
                             "columns": [{"field": "year", "label": "年"}, {"field": "scope", "label": "対象"},
                                         {"field": "ratio_pct", "label": "輸出受取比（%）"}],
                             "reportingPeriod": "2000–2024年", "preview": {"kind": "partial", "note": "取得した100セルのうちBangladeshの50セル。", "totalRows": 100}}]}]}
    fema_all = summary["fema"]["summaries"][0]
    other = {"schemaVersion": 1, "items": [
        {"id": "fema-administrative-clocks", "title": "行政の日付と実際の保護は別の観測",
         "queries": [{"id": "fema-dates", "source": {
             "label": "OpenFEMA DisasterDeclarationsSummaries v2",
             "links": [{"label": "公式データ説明", "url": "https://www.fema.gov/openfema-data-page/disaster-declarations-summaries-v2"}],
             "metricDefinitions": [{"id": "lag", "name": "開始から宣言", "definition": "開始から宣言の日数は、公式incidentBeginDateとdeclarationDateをUTC暦日に直して引いた値。宣言IDを一回ずつ数える。"}],
             "filters": ["宣言種別: DR", "宣言日: 2000-01-01以上2025-01-01未満（UTC）"],
             "caveats": ["1,542宣言は独立した災害1,542件ではない。宣言されなかった被害は分母にいない。",
                         "この日差は無保護期間・入金待ち・現場の応答時間ではない。",
                         "申請日には欠測1件と未解決の負の日差があり、原記録を推測修正していない。"],
             "evidenceFlow": [{"kind": "validation", "title": "集計単位の確認", "detail": "元データ29,471地域行を1,542宣言へ縮約。ID重複と対象フィールドの宣言内不一致は0。"}]},
             "rows": [{"declarations": summary["fema"]["declarations"], "median_days": fema_all["begin_to_declaration_days"]["median"],
                       "q25_days": fema_all["begin_to_declaration_days"]["q25"], "q75_days": fema_all["begin_to_declaration_days"]["q75"]}],
             "columns": ["declarations", "median_days", "q25_days", "q75_days"],
             "reportingPeriod": "宣言年2000–2024", "preview": {"kind": "aggregate", "note": "宣言単位の集計。四分位点は観測分布であり信頼区間ではない。"}}]},
        {"id": "local-benefit-system-effect", "title": "受取側の改善と、周辺・仲介者の制約を分ける",
         "queries": [
             {"id": "quickpay", "source": {"label": "Barrot & Nanda (2020)",
                 "links": [{"label": "Journal of Finance 刊行版要旨", "url": "https://afajof.org/issue/volume-75-issue-6/"}],
                 "caveats": ["刊行版要旨を確認。個票と推定式の再現はしていない。"]},
                 "summary": "支払前倒しの対象企業の雇用増と、地域の非対象企業への押し出しを併せて報告。"},
             {"id": "insurance-timing", "source": {"label": "Casaburi & Willis (2018)",
                 "links": [{"label": "刊行論文", "url": "https://www.atai-research.org/wp-content/uploads/2017/08/aer.20171526.pdf"}],
                 "caveats": ["加入率は保護の最終履行率ではない。企業の経営難を保険設計の因果効果としない。"]},
                 "summary": "保険料の後払いで加入が増える一方、仲介企業の経営難による契約履行問題も記録された。"}]}]}
    for name, value in (("chart.json", chart), ("chart-sources.json", receipt), ("other-sources.json", other)):
        (args.out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"chart_rows": len(rows), "out": str(args.out)}))


if __name__ == "__main__":
    main()
