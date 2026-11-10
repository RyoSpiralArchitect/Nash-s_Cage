"""Independent recount of retained outputs; not an independent simulator."""
import gzip
import json
from pathlib import Path
import sys


def audit(out):
    out=Path(out)
    plan=json.loads((out/"plan.json").read_text())
    summary=json.loads((out/"summary.json").read_text())
    with gzip.open(out/"worlds.jsonl.gz","rt",encoding="utf-8") as f:
        rows=[json.loads(line) for line in f]
    assert len(rows)==summary["world_count"]
    assert len({r["world_id"] for r in rows})==len(rows)
    metrics=list(summary["totals"]["effective"])
    totals={c:{k:{s:0 for s in ("positive","negative","zero","undefined")} for k in metrics}
            for c in ("effective","nominal")}
    groups={v["name"]:{} for v in plan["views"]}
    partitions={"gain_other_retained_continued_no_extra_debt":0,
                "gain_other_lost_only":0,"gain_continuation_or_debt_only":0,"gain_both":0}
    by_id={r["world_id"]:r for r in rows}
    for r in rows:
        w=r["world"]; arms=r["arms"]
        assert arms["B"]==arms["N"]
        for arm, result in arms.items():
            payer,recipient,spent=w["payer_cash"],w["recipient_cash"],0
            used={t:0 for t in range(7)}
            times=[e["t"] for e in result["events"]]
            assert times==sorted(times)
            for e in result["events"]:
                if "amount" in e:
                    if e["actor"]=="payer":payer-=e["amount"]
                    else:recipient-=e["amount"]
                    spent+=e["amount"]
                if e["kind"] in ("other_service","target_service","review"):used[e["t"]]+=1
                if e["kind"]=="state":
                    assert (payer,recipient,spent)==(e["payer"],e["recipient"],e["spent"])
                    assert min(payer,recipient)>=0 and payer+recipient+spent==w["payer_cash"]+w["recipient_cash"]
                    assert used[e["t"]]==e["capacity_used"]<=w["capacity"] and e["protected_floor"]==1
            deliveries=[e for e in result["events"] if e["kind"]=="delivery"]
            assert len(deliveries)<=1
            m=result["metrics"]; t=deliveries[0]["t"] if deliveries else None
            assert m["target_time"]==t
            assert m["target_on_time"]==int(t is not None and t <= (5 if w["schedule"]=="patient" else 3))
            assert m["other_completed"]==int(any(e["kind"]=="other_service" for e in result["events"]))
            assert m["total_cost"]==spent==m["payer_cost"]+m["recipient_cost"]
            paid=sum(e["amount"] for e in result["events"] if e["kind"]=="maintenance")
            assert m["unpaid"]==(w["maintenance"]-paid if deliveries else 0)
            assert m["continued"]==int(bool(deliveries) and m["unpaid"]==0)
            if result["route"]=="alternative":assert w["alternative"]=="safe" and t<=w["expiry"]
        for c,(a,b) in {"effective":("E","N"),"nominal":("N","B")}.items():
            for k in metrics:
                x,y=arms[a]["metrics"][k],arms[b]["metrics"][k]
                d=None if x is None or y is None else x-y
                assert d==r["contrasts"][c][k]
                totals[c][k]["undefined" if d is None else "positive" if d>0 else "negative" if d<0 else "zero"]+=1
        d=r["contrasts"]["effective"]
        if d["target_on_time"]>0:
            lost=d["other_completed"]<0
            follow=not arms["E"]["metrics"]["continued"] or d["unpaid"]>0
            key=("gain_both" if lost and follow else "gain_other_lost_only" if lost else
                 "gain_continuation_or_debt_only" if follow else "gain_other_retained_continued_no_extra_debt")
            partitions[key]+=1
        for v in plan["views"]:
            key=tuple(w[k] for k in v["fields"])
            groups[v["name"]].setdefault(key,[]).append(r)
    assert totals==summary["totals"]
    expected={}
    for v in plan["views"]:
        for c in totals:
            stats={"view":v["name"],"contrast":c,"world_denominator":len(rows),
                   "class_denominator":len(groups[v["name"]]),"mixed_classes":dict.fromkeys(metrics,0),
                   "worlds_in_mixed_classes":dict.fromkeys(metrics,0)}
            for key, members in groups[v["name"]].items():
                bounds={}
                for k in metrics:
                    vals=[r["contrasts"][c][k] for r in members]; defined=[x for x in vals if x is not None]
                    limits={"min":min(defined) if defined else None,"max":max(defined) if defined else None,
                            "undefined":len(vals)-len(defined)}
                    bounds[k]=limits
                    if len(set(vals))>1:
                        stats["mixed_classes"][k]+=1;stats["worlds_in_mixed_classes"][k]+=len(vals)
                expected[(v["name"],c,key)]={"bounds":bounds,"worlds":len(members)}
            assert stats in summary["reports"]
    count=0
    view_fields={v["name"]:v["fields"] for v in plan["views"]}
    with gzip.open(out/"classes.jsonl.gz","rt",encoding="utf-8") as f:
        for line in f:
            r=json.loads(line);key=(r["view"],r["contrast"],tuple(r["observed"][k] for k in view_fields[r["view"]]))
            wanted=expected.pop(key)
            assert r["bounds"]==wanted["bounds"] and r["worlds"]==wanted["worlds"]
            count+=1
    assert not expected
    witnesses=json.loads((out/"witnesses.json").read_text())
    for x in witnesses:
        pair=[by_id[i] for i in x["world_ids"]]
        assert all({k:r["world"][k] for k in view_fields[x["view"]]}==x["observed"] for r in pair)
        assert [r["contrasts"][x["contrast"]][x["metric"]] for r in pair]==x["values"]
        assert x["values"][0]!=x["values"][1]
    return {"status":"RECOUNT_MATCH","worlds":len(rows),"arm_worlds":len(rows)*3,
            "class_contrast_rows":count,"witness_pairs":len(witnesses),"totals":totals,
            "target_gain_partition":partitions,
            "scope":"Retained-event accounting and recount; not independent simulation or real effects."}


if __name__=="__main__":
    print(json.dumps(audit(sys.argv[1]),ensure_ascii=False,indent=2,sort_keys=True))
