#!/usr/bin/env python3
"""Public-evidence audit; no empirical model calibration or live intervention."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import math
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE_DIR = ROOT / "artifacts/heat_public_audit_v01/sources"
ARCHIVED_INPUTS = ("run.py", "test_run.py", "evidence.json", "CONTRACT.ja.md")
INPUTS = ARCHIVED_INPUTS + ("test_publication.py",)
R02_INPUT_DIR = ROOT / "artifacts/heat_public_audit_v01/history/r02_inputs"
R02_RECEIPT_SHA256 = "02b36e001d732c48984a3e672b0bc8d7e4709a79f33e9a2ccfec6069a8d497b2"
LOADED_SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
OUTPUTS = ("audit.json", "artifact.json", "audit.ipynb", "receipt.json")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value, label):
    require(type(value) is int and value >= 0, f"{label}: nonnegative integer required")
    return value


def number(value, label):
    require(type(value) in (int, float) and math.isfinite(value), f"{label}: finite number required")
    return value


def reject_constant(value):
    raise ValueError(f"nonfinite JSON constant: {value}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"),
                       parse_constant=reject_constant, object_pairs_hook=unique_object)
    def finite(item):
        if isinstance(item, float):
            require(math.isfinite(item), "nonfinite JSON number")
        elif isinstance(item, list):
            for child in item:
                finite(child)
        elif isinstance(item, dict):
            for child in item.values():
                finite(child)
    finite(value)
    return value


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def no_links(path):
    """Check the supplied path before resolving away any symlink components."""
    path = Path(path).absolute()
    require(".." not in path.parts, "parent traversal is not an artifact path")
    for component in (path, *path.parents):
        require(not component.is_symlink(), f"symlink path rejected: {component}")
    return path


def input_snapshot(directory=HERE, names=INPUTS):
    directory = no_links(directory)
    result = {}
    for name in names:
        path = no_links(directory / name)
        require(path.is_file(), f"missing input: {name}")
        result[name] = digest(path)
    if directory == HERE:
        require(result["run.py"] == LOADED_SOURCE_SHA256, "loaded source changed")
    return result


def coverage_bounds(total, delivered, not_delivered, unknown):
    """Bounds on documented action receipt, never physical safety or a CI."""
    if total is None:
        return {"status": "UNKNOWN", "reason": "denominator missing"}
    for label, value in (("total", total), ("delivered", delivered), ("not_delivered", not_delivered), ("unknown", unknown)):
        integer(value, label)
    require(total > 0, "zero denominator")
    require(delivered + not_delivered + unknown == total, "partition does not close")
    return {"status": "BOUNDED" if unknown else "OBSERVED",
            "lower": delivered / total, "upper": (delivered + unknown) / total,
            "unknown_fraction": unknown / total, "denominator": total}


def timestamp(value):
    require(isinstance(value, str), "timestamp must be text")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None and parsed.utcoffset() is not None, "timezone required")
    return parsed.astimezone(timezone.utc)


def time_bounds(record):
    require(isinstance(record, dict), "time record must be an object")
    state = record.get("status")
    if state == "EXACT":
        require(set(record) == {"status", "at", "evidence"} and record["evidence"], "exact time evidence required")
        point = timestamp(record["at"])
        return point, point
    if state == "INTERVAL":
        require(set(record) == {"status", "earliest", "latest", "evidence"} and record["evidence"], "interval evidence required")
        lo, hi = timestamp(record["earliest"]), timestamp(record["latest"])
        require(lo <= hi, "inverted time interval")
        return lo, hi
    if state == "APPROXIMATE":
        require(set(record) == {"status", "text", "evidence"} and record["text"] and record["evidence"], "approximate text/evidence required")
        return None
    if state == "UNKNOWN":
        require(set(record) == {"status", "reason"} and record["reason"], "unknown reason required")
        return None
    if state == "NOT_DONE_BY_CUTOFF":
        require(set(record) == {"status", "cutoff", "evidence"} and record["evidence"], "censor evidence required")
        timestamp(record["cutoff"])
        return None
    raise ValueError(f"unsupported time status: {state}")


def elapsed_seconds(start, end):
    """Same episode/clock definition must be established by the input contract."""
    first, last = time_bounds(start), time_bounds(end)
    require(start["status"] != "NOT_DONE_BY_CUTOFF", "unobserved start cannot anchor a latency")
    if first is None:
        return {"status": "UNKNOWN", "reason": "start lacks quantified bounds"}
    if end["status"] == "NOT_DONE_BY_CUTOFF":
        cutoff = timestamp(end["cutoff"])
        require(cutoff >= first[1], "cutoff precedes latest start")
        return {"status": "RIGHT_CENSORED", "lower_seconds": (cutoff - first[1]).total_seconds(),
                "upper_seconds": None}
    if last is None:
        return {"status": "UNKNOWN", "reason": "end lacks quantified bounds"}
    upper = (last[1] - first[0]).total_seconds()
    require(upper >= 0, "end precedes start; check episode or preventive action")
    lower = max(0.0, (last[0] - first[1]).total_seconds())
    return {"status": "EXACT" if lower == upper else "INTERVAL",
            "lower_seconds": lower, "upper_seconds": upper}


def net_paid_cash(transactions):
    """Only realized net cash flows. Not resource cost or economic incidence."""
    if not transactions:
        return {"status": "UNKNOWN_EMPTY_LEDGER", "net_received_jpy": None,
                "non_paid_rows": 0, "economic_incidence": "UNKNOWN", "resource_cost": "UNKNOWN"}
    seen, balances, unpaid = set(), {}, 0
    for row in transactions:
        require(set(row) == {"id", "item", "payer", "payee", "amount_jpy", "stage", "paid_at", "evidence"}, "cash schema mismatch")
        for key in ("id", "item", "payer", "payee", "evidence"):
            require(isinstance(row[key], str) and row[key].strip(), f"cash {key} missing")
        require(row["id"] not in seen, "duplicate transaction")
        seen.add(row["id"])
        require(row["payer"] != row["payee"], "self transfer")
        amount = integer(row["amount_jpy"], "amount_jpy")
        require(row["stage"] in {"ESTIMATED", "APPROVED", "PAID"}, "unknown payment stage")
        if row["stage"] != "PAID":
            require(row["paid_at"] is None, "unpaid row has paid date")
            unpaid += 1
            continue
        timestamp(row["paid_at"])
        balances[row["payer"]] = balances.get(row["payer"], 0) - amount
        balances[row["payee"]] = balances.get(row["payee"], 0) + amount
    require(sum(balances.values()) == 0, "cash ledger does not balance")
    return {"status": "SUPPLIED_ROWS_ONLY", "net_received_jpy": balances, "non_paid_rows": unpaid,
            "economic_incidence": "UNKNOWN", "resource_cost": "UNKNOWN"}


def validate_evidence(evidence):
    require(evidence["format"] == "heat-public-evidence/v1", "wrong evidence format")
    require(evidence["status"] == "PUBLIC_DESCRIPTIVE_ONLY", "claim boundary changed")
    source_ids = [s["id"] for s in evidence["sources"]]
    require(len(source_ids) == len(set(source_ids)), "duplicate source")
    all_rows = evidence["measurements"] + evidence["rest_frequency"]
    for row in all_rows:
        require(row["source"] in source_ids and row["cohort"], "unresolved provenance/cohort")
        require(integer(row["denominator"], "denominator") > 0, "zero survey denominator")
        percentage = number(row["reported_percent"], "reported_percent")
        require(0 <= percentage <= 100, "percentage out of range")
        require(row["precision"] == "rounded_percent" and row["numerator"] is None,
                "rounded publication must not fabricate exact counts")
    frequency = evidence["rest_frequency"]
    require(len(frequency) == 4 and len({r["label"] for r in frequency}) == 4, "frequency categories incomplete")
    require({r["denominator"] for r in frequency} == {1093}, "frequency denominators differ")
    require(sum(r["reported_percent"] for r in frequency) == 100, "published categories do not close")
    cases = evidence["timing_case_audit"]["cases"]
    require(sorted(r["case_id"] for r in cases) == list(range(1, 20)), "fatal case audit must cover all 19 once")
    for row in cases:
        require(type(row["exact_recognition_and_initial_cooling_clock_pair"]) is bool, "case flag must be boolean")
        require(row["source"] == "final" and 11 <= row["page"] <= 16, "case provenance mismatch")
        interval = row["reported_interval"]
        if interval is not None:
            require(number(interval["nominal_minutes"], "minutes") >= 0, "negative interval")
            require(interval["precision"] == "approximate_unquantified_error", "false precision")
            require(interval["is_initial_response_latency"] is False, "incompatible event anchors")
    for row in evidence["national_final"]:
        integer(row["casualties"], "casualties")
        require(integer(row["deaths"], "deaths") <= row["casualties"], "deaths not a subset")
    require([r["year"] for r in evidence["national_final"]] == [2024, 2025], "national vintage mismatch")
    gate = evidence["calibration_gate"]
    require(gate["status"] == "BLOCKED", "descriptive sources cannot admit calibration")
    require(all(gate[k].startswith("UNKNOWN:") for k in ("floor", "response_time", "cost_incidence")), "missing empirical gate")


def verify_sources(evidence, directory=SOURCE_DIR):
    directory = no_links(directory)
    files = [s["file"] for s in evidence["sources"]]
    require(len(set(files)) == len(files), "source file collision")
    for name in files:
        require(Path(name).name == name and name not in {".", ".."}, "source path traversal")
    actual = {p.name for p in directory.iterdir()}
    require(actual == set(files), "source directory closure mismatch")
    for source in evidence["sources"]:
        path = no_links(directory / source["file"])
        require(path.is_file() and not path.is_symlink(), "source must be a regular local snapshot")
        require(digest(path) == source["sha256"], f"source hash mismatch: {source['id']}")


def analyze(evidence):
    validate_evidence(evidence)
    rows = evidence["national_final"]
    cases = evidence["timing_case_audit"]["cases"]
    complete = sum(r["exact_recognition_and_initial_cooling_clock_pair"] for r in cases)
    return {"status": "DESCRIPTIVE_AUDIT_COMPLETE_CALIBRATION_BLOCKED",
            "exact_clock_pair_completeness": {"numerator": complete, "denominator": len(cases), "unit": "public fatal-case summaries", "rate": complete / len(cases)},
            "national_change": {"casualties": rows[1]["casualties"] - rows[0]["casualties"],
                                "deaths": rows[1]["deaths"] - rows[0]["deaths"],
                                "casualties_ratio_change": rows[1]["casualties"] / rows[0]["casualties"] - 1,
                                "deaths_ratio_change": rows[1]["deaths"] / rows[0]["deaths"] - 1},
            "source_count": len(evidence["sources"]),
            "unidentified": evidence["calibration_gate"],
            "causal_effect": "NOT_IDENTIFIED", "intervention_authority": "NONE"}


def report_artifact(evidence, result, generated_at):
    sources = [{"id": s["id"], "label": s["title"], "href": s["url"],
                "query": {"description": "公開原資料の手動転記。PDFのページと分母を確認。証拠台帳のSHA-256でローカル原資料と照合。", "url": s["url"],
                          "executed_at": generated_at, "filters": {"audit_as_of": evidence["checked_on"]}}} for s in evidence["sources"]]
    source_by_id = {s["id"]: s for s in evidence["sources"]}
    def link(key, label):
        return f"[{label}]({source_by_id[key]['url']})"
    title = "Heat Protection: Evidence and Gaps"
    blocks = []
    def md(key, body, source=None):
        block = {"id": key, "type": "markdown", "body": body}
        if source:
            block["sourceId"] = source
        blocks.append(block)
    md("title", f"# {title}")
    md("summary", "## Executive Summary\n\n既存制度を空白にせず、日本の暑熱労働対策を『対象・実行・費用負担』に分けて監査した。2026年9月9日確認。\n\n- 制度と資金経路は存在する。実際に届く範囲とは区別する。\n- 実施状況の調査はあるが、労働者の保護到達率や応答時間の代表値へは変換できない。\n- 次の実装は、名簿・イベント・支払の接続。合成実験への実測値投入はまだ止める。")
    md("scope", "## 対象範囲は、保護とお金で同じではない\n\n暑熱対策の施行通知は、同じ場所で当該作業をする非労働者も作業者に含め、混在現場では元方事業者と関係請負人双方の措置義務を説明している（p3–4）。賃金・保険の対象は別に照合する。温度・時間条件は規定の対象範囲であり、安全な境界や一律停止命令ではない。研究上の承認記録を理由に避難や救急対応を待たせない。", "notice")
    md("survey_context", "## 実施状況は観測できるが、全国の保護率にはならない\n\n監督署調査は2025年6–9月に指導した4業種の事業場。建設アンケートは、建設労務安全研究会会員の発災事業場（多くは総合工事業）の任意回答で、延べ1,100事業場。無作為標本ではなく、非発災現場の分母もない。最終報告書p4–5の対象説明を採用した。", "report")
    blocks.append({"id": "survey_table", "type": "table", "tableId": "scope_table"})
    md("frequency_context", "## 設備の存在と、使えた記録を分ける\n\n冷却休憩の頻度は、不明が46%。これは回答群内の記録状態であって、未実施46%という意味ではない。原資料の丸めた百分率を保持し、人数への逆算はしない。設問の頻度区分を分単位の応答時間として扱わない。", "survey")
    blocks.append({"id": "frequency_chart", "type": "chart", "chartId": "rest_frequency"})
    md("timing", "## 時間の断片はあるが、同じ時計ではない\n\n2025年死亡事例の公開要約19件を全件確認した。初回の異常認知と初回冷却の正確な時計時刻の対を抽出できたのは0/19件。これは公開要約の項目充足率であり、未対応率ではない。\n\n事例6には休憩を促してから再訪まで約10分、事例7には飲水・休憩から再訪・冷房車内への移動まで約15分、事例11には冷却等の措置後に再び倒れるまで約1時間という記載がある。始点・終点も目的も異なるため平均しない。死亡例だけの選択標本から通常現場の遅延や救命閾値も求めない。", "final")
    md("cost", "## 積算への計上と、労働者への入金を分ける\n\n2026年4月適用の要領では、現場の施設・設備向け暑熱・防寒対策は、妥当性と個人向け費用との重複を確認した上で積上げ計上する。上限は所定の算出式による現場環境改善費の100%。対策実費や休業賃金の100%補償ではない。地方・民間の契約への適用も個別に確認が要る。", "cost")
    md("income", "## 所得の維持も、すでに制度側の課題になっている\n\n国交省のサポートパッケージは、費用・工期の支援に加え、日給制等の年収確保と、賃金・労働時間の実態調査を扱っている。したがって『国が何も考慮していない』という前提は置けない。ただし、この資料は現場別の実支払台帳ではない。", "support")
    md("pay_rules", "## 予防的な休止と、発症後の休業は別の経路\n\n使用者の責に帰すべき事由による休業には平均賃金60%以上の休業手当という規定があるが、個々の暑熱休止への適用や契約上の上積みは別途確認する。" + link("wage", "厚労省Q&A") + "\n\n傷病による就労不能等の要件を満たす場合の休業（補償）等給付を、発症前の休止の補償率として使わない。就業形態・加入・認定・実入金は別の項目にする。" + link("compensation", "厚労省の給付案内"))
    md("national", "## 改善を示す証拠も残す\n\n2026年5月公表の確定値資料では、2025年は死傷者1,803人（死亡・休業4日以上）、うち死亡19人。資料内の2024年は1,257人、死亡31人で、死傷者は546人増、死亡は12人減。過去の速報値と混ぜない。厚労省は重篤化防止対策の寄与を認めているが、この前後比較を本研究の因果推定とはしない。曝露、天候、就業者構成、報告・把握の変化が残る。", "final")
    md("next", "## 次の実装は、三つの記録を同じ対象に結ぶ\n\n1. 同じ現場・期間の全作業者と、必要な保護機会の分母を確定する。\n2. 認知・離脱・冷却・再評価の時刻を、欠測・概数・打切り込みで照合する。\n3. 同じ契約系列の費目、実支払、賃金、後日振替労働を結ぶ。\n\nまずは許可された過去記録の再生。規定の対象、実行の到達、所得保護の対象を別々に集計する。地域・現場・提供者の選定と個票の利用許可は未了。現実データを未取得のままFurnaceで較正実験を増やさない。")
    md("questions", "## 何を確かめれば、次へ進めるか\n\n- 既存の記録を持つ現場で、名簿・暑熱イベント・支払の三者を匿名化して照合できるか。\n- 保護が間に合わないのは、認知・離脱・冷却設備への到達のどこか。\n- 費用は既に支払われているが配分が違うのか、承認後の入金が遅いのか、制度の対象外なのか。\n\nいずれも、現在の公開資料だけで原因を確定していない。")
    md("limits", "## 主張の上限\n\n公開資料の転記・分母・版・ハッシュは検査できた。保護到達率、代表的応答時間、主体別の最終負担額はUNKNOWN。法的・医学的判断、全国効果推定、デジタルツイン完成の証拠ではない。スナップショットであり、以後の改定や資料の網羅性を保証しない。元の合成実験と結果は変更していない。")
    # Materialize from the manually transcribed source JSON using the same
    # self-contained SQL exposed in the report. SQL does not prove transcription.
    def query_rows(raw, selection, order):
        literal = json.dumps(raw, ensure_ascii=False).replace("'", "''")
        sql = f"WITH transcribed AS (SELECT key, value FROM json_each('{literal}'))\nSELECT {selection}\nFROM transcribed ORDER BY {order}"
        with contextlib.closing(sqlite3.connect(":memory:")) as db:
            db.row_factory = sqlite3.Row
            rows = [dict(r) for r in db.execute(sql)]
        return rows, sql
    table_rows, table_sql = query_rows(evidence["measurements"],
        "key + 1 AS ordinal, json_extract(value, '$.label') AS metric, "
        "json_extract(value, '$.reported_percent') || '%' AS published, "
        "json_extract(value, '$.denominator') AS n, json_extract(value, '$.meaning') AS boundary, "
        "json_extract(value, '$.cohort') AS cohort, json_extract(value, '$.page') AS page", "ordinal")
    chart_rows, chart_sql = query_rows(evidence["rest_frequency"],
        "json_extract(value, '$.order') AS ordinal, json_extract(value, '$.label') AS label, "
        "json_extract(value, '$.reported_percent') AS reported_percent, "
        "json_extract(value, '$.reported_percent') / 100.0 AS share, "
        "json_extract(value, '$.denominator') AS denominator, "
        "json_extract(value, '$.cohort') AS cohort, json_extract(value, '$.page') AS page, "
        "json_extract(value, '$.precision') AS precision", "ordinal")
    for key, sql, pages in (("survey_extract", table_sql, "3,9,16"), ("frequency_extract", chart_sql, "16")):
        sources.append({"id": key, "label": "資料4・手動転記の再計算 p" + pages, "href": source_by_id["survey"]["url"],
                        "query": {"engine": "sqlite", "language": "sql", "sql": sql, "executed_at": generated_at,
                                  "description": "PDF原表を転記したJSONから表示値を算出。原資料の抽出APIではない。",
                                  "tables_used": ["json_each"], "filters": {"period": "2025-06-01/2025-09-30", "sampling": "原資料に含まれる選択された設問回答のみ"},
                                  "metric_definitions": {"share": "原表の丸め済み百分率 / 100。正確な分子人数は不明。"}}})
    chart = {"id": "rest_frequency", "title": "建設業・発災事例の冷却休憩頻度", "subtitle": "2025年6–9月の任意回答、設問n=1,093。原図の丸め値・不明を含む。",
             "type": "bar", "dataset": "frequency", "sourceId": "frequency_extract", "valueFormat": "percent",
             "encodings": {"x": {"field": "label", "type": "nominal", "label": "回答区分"}, "y": {"field": "share", "type": "quantitative", "label": "回答割合"}},
             "options": {"orientation": "horizontal"}}
    table = {"id": "scope_table", "title": "調査値と分母", "subtitle": "各行は異なる設問・部分集団。数字同士を保護率として比較しない。", "dataset": "survey", "sourceId": "survey_extract", "defaultSort": {"field": "ordinal", "direction": "asc"},
             "columns": [{"field": "ordinal", "label": "順"}, {"field": "metric", "label": "記録された項目"}, {"field": "published", "label": "公表割合"}, {"field": "n", "label": "設問分母"}, {"field": "boundary", "label": "読み取れる範囲"}]}
    return {"surface": "report", "manifest": {"version": 1, "surface": "report", "title": title, "generatedAt": generated_at, "blocks": blocks, "sources": sources, "tables": [table], "charts": [chart]},
            "snapshot": {"version": 1, "generatedAt": generated_at, "status": "partial", "datasets": {"survey": table_rows, "frequency": chart_rows},
                         "accessIssues": [{"id": "empirical_records_missing", "message": "現場の分母・応答イベント・支払台帳は未取得。実測較正はBLOCKED。"}]}, "sources": sources}


def write_json(path, value):
    # Exclusive creation and byte writes preserve evidence and LF on Windows.
    path = no_links(path)
    data = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with path.open("xb") as handle:
        handle.write(data)


def notebook(evidence, result):
    """Standard nbformat JSON; execute simple Python cells without installing Jupyter."""
    cells, namespace, count = [], {}, 0
    def md(text):
        cells.append({"cell_type": "markdown", "metadata": {}, "source": text.splitlines(True)})
    def code(text):
        nonlocal count
        count += 1
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            exec(compile(text, f"heat-audit-cell-{count}", "exec"), namespace)
        cells.append({"cell_type": "code", "metadata": {}, "execution_count": count,
                      "source": text.splitlines(True), "outputs": [{"output_type": "stream", "name": "stdout", "text": stream.getvalue().splitlines(True)}]})
    md("# Heat protection audit\n\n## tl;dr\n公開記述の監査は完了。現場の保護率・応答時間・費用帰着は未同定。")
    md("## Context & Methods\n\n### Key Assumptions\n公的資料の手動転記。選択標本、丸め、時点更新、労働者と事業場の違いを保持。\nセルは標準Pythonの共有名前空間で上から実行。Jupyter/nbclientカーネル実行は未検証。")
    md("## Data\n\n原資料のURL・SHA-256は同梱データ内。最初の4行は異なる設問分母の検査用表示であり比較集団ではない。")
    code("import json\ndata = json.loads(" + repr(json.dumps(evidence, ensure_ascii=False)) + ")\nfor row in data['measurements'][:10]:\n    print(row['id'], row['denominator'], row['reported_percent'], row['precision'])")
    md("## Results\n\n率から人数を逆算せず、死亡を死傷者の外数として加算しない。")
    code("assert all(r['numerator'] is None for r in data['measurements'] + data['rest_frequency'])\nassert sum(r['reported_percent'] for r in data['rest_frequency']) == 100\na, b = data['national_final']\nassert (b['casualties'] - a['casualties'], b['deaths'] - a['deaths']) == (546, -12)\nprint('casualties change:', b['casualties'] / a['casualties'] - 1)\nprint('deaths change:', b['deaths'] / a['deaths'] - 1)")
    code("cases = data['timing_case_audit']['cases']\nassert sorted(c['case_id'] for c in cases) == list(range(1, 20))\ncomplete = sum(c['exact_recognition_and_initial_cooling_clock_pair'] for c in cases)\nprint('Exact clock pairs in public fatal-case summaries:', complete, '/', len(cases))\nassert complete == 0\nassert data['calibration_gate']['status'] == 'BLOCKED'\nprint('Calibration BLOCKED; no empirical parameters emitted.')")
    md("## Takeaways\n\n必要なのは同じ現場・期間の名簿、イベント、支払の接続。公開集計を合成モデルの係数へ直接入れない。原資料の現在のハッシュ照合・契約関数の試験はrun.py/test_run.pyが担う。")
    return {"nbformat": 4, "nbformat_minor": 4, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3"}, "execution_engine": "stdlib exec, sequential shared namespace; not Jupyter kernel"}, "cells": cells}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--verify", action="store_true", help="verify hashes, closure and deterministic reconstruction without writing")
    parser.add_argument("--input-revision", choices=("current", "r02"), default="current",
                        help="r02 is read-only replay of the pinned 2026-09-09 checkpoint")
    args = parser.parse_args()
    active_inputs = input_snapshot()
    require(args.verify or args.input_revision == "current", "archived inputs are verification-only")
    input_dir = R02_INPUT_DIR if args.input_revision == "r02" else HERE
    input_names = ARCHIVED_INPUTS if args.input_revision == "r02" else INPUTS
    input_hashes = input_snapshot(input_dir, input_names)
    evidence = read_json(input_dir / "evidence.json")
    out = no_links(args.out)
    require(out != SOURCE_DIR and SOURCE_DIR not in out.parents and out != HERE and HERE not in out.parents, "output overlaps inputs")
    if args.verify:
        if args.input_revision == "r02":
            require({p.name for p in input_dir.iterdir()} == set(ARCHIVED_INPUTS), "archived input closure mismatch")
            require(digest(no_links(out / "receipt.json")) == R02_RECEIPT_SHA256, "not the pinned r02 receipt")
        verify_output(out, evidence, input_hashes, input_dir, input_names, active_inputs)
        print("VERIFIED: source/output closure, hashes, reconstruction; calibration remains BLOCKED")
        return
    require(not out.exists(), "output exists; use a new output directory")
    verify_sources(evidence)
    result = analyze(evidence)
    generated_at = datetime.now(timezone.utc).isoformat()
    artifact = report_artifact(evidence, result, generated_at)
    nb = notebook(evidence, result)
    verify_sources(evidence)
    require(input_hashes == input_snapshot(), "inputs changed during analysis")
    no_links(out.parent).mkdir(parents=True, exist_ok=True)
    no_links(out.parent)
    with tempfile.TemporaryDirectory(prefix=".heat-audit-", dir=out.parent) as temporary:
        stage = Path(temporary)
        for name, value in (("audit.json", result), ("artifact.json", artifact), ("audit.ipynb", nb)):
            write_json(stage / name, value)
        receipt = {"format": "heat-public-audit-receipt/v1", "generated_at": generated_at,
                   "input_sha256": input_hashes, "source_sha256": {s["file"]: s["sha256"] for s in evidence["sources"]},
                   "output_sha256": {name: digest(stage / name) for name in OUTPUTS[:-1]},
                   "source_closure": "VERIFIED_BEFORE_AND_AFTER", "notebook_cells_executed": sum(c["cell_type"] == "code" for c in nb["cells"]),
                   "notebook_engine": "stdlib exec, not Jupyter kernel", "calibration": "BLOCKED"}
        write_json(stage / "receipt.json", receipt)
        verify_output(stage, evidence, input_hashes, active_inputs=active_inputs)
        # Reserve a new destination. Never replace an existing bundle, even if
        # its input hashes match. A failed publish remains an invalid partial
        # bundle for inspection; no user-owned destination is cleaned up.
        no_links(out).mkdir(exist_ok=False)
        for name in OUTPUTS:
            with no_links(out / name).open("xb") as handle:
                handle.write((stage / name).read_bytes())
        verify_output(out, evidence, input_hashes, active_inputs=active_inputs)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def verify_output(out, evidence, input_hashes, input_dir=HERE, input_names=INPUTS, active_inputs=None):
    out = no_links(out)
    active_inputs = input_snapshot() if active_inputs is None else active_inputs
    require(input_snapshot() == active_inputs, "active verifier inputs changed")
    require(input_snapshot(input_dir, input_names) == input_hashes, "input identity mismatch")
    require(read_json(input_dir / "evidence.json") == evidence, "evidence identity mismatch")
    names = set(OUTPUTS)
    require({p.name for p in out.iterdir()} == names, "analysis output closure mismatch")
    require(all((out / n).is_file() and not (out / n).is_symlink() for n in names), "invalid output file")
    before = {n: digest(out / n) for n in names}
    receipt = read_json(out / "receipt.json")
    require(isinstance(receipt, dict) and set(receipt) == {
        "format", "generated_at", "input_sha256", "source_sha256", "output_sha256",
        "source_closure", "notebook_cells_executed", "notebook_engine", "calibration"}, "receipt schema mismatch")
    require(receipt["format"] == "heat-public-audit-receipt/v1", "wrong receipt format")
    timestamp(receipt["generated_at"])
    require(receipt["calibration"] == "BLOCKED", "receipt cannot admit calibration")
    require(receipt["source_closure"] == "VERIFIED_BEFORE_AND_AFTER", "source verification claim mismatch")
    require(type(receipt["notebook_cells_executed"]) is int and receipt["notebook_cells_executed"] == 3, "notebook execution count mismatch")
    require(receipt["notebook_engine"] == "stdlib exec, not Jupyter kernel", "notebook engine claim mismatch")
    require(receipt["input_sha256"] == input_hashes, "input identity mismatch")
    require(set(receipt["output_sha256"]) == names - {"receipt.json"}, "receipt output set mismatch")
    require(all(before[n] == sha for n, sha in receipt["output_sha256"].items()), "output hash mismatch")
    require(receipt["source_sha256"] == {s["file"]: s["sha256"] for s in evidence["sources"]}, "source identity mismatch")
    verify_sources(evidence)
    result = analyze(evidence)
    require(read_json(out / "audit.json") == result, "audit reconstruction mismatch")
    require(read_json(out / "artifact.json") == report_artifact(evidence, result, receipt["generated_at"]), "report reconstruction mismatch")
    require(read_json(out / "audit.ipynb") == notebook(evidence, result), "notebook reconstruction mismatch")
    verify_sources(evidence)
    require(before == {n: digest(out / n) for n in names}, "outputs changed during verification")
    require({p.name for p in out.iterdir()} == names, "output closure changed during verification")
    no_links(out)
    require(all(not (out / n).is_symlink() for n in names), "output link changed during verification")
    require(input_hashes == input_snapshot(input_dir, input_names), "inputs changed during verification")
    require(active_inputs == input_snapshot(), "active verifier inputs changed")


if __name__ == "__main__":
    main()
