#!/usr/bin/env python3
"""Recover only structured, public Core notices from a downloaded Actions log.

This is a secondary evidence source when a ZIP is unavailable. Missing notices
remain UNRUN; never infer native success from a build or an absent exception.
"""
import argparse
import base64
import hashlib
import json
import zlib
import copy
import shutil
from collections import Counter
from pathlib import Path
from run import REFERENCE, assert_native_bank_book, assert_native_fx, assert_native_fx_conversions, criteria_for, rows_for, verify_bundle, review_native_fixture
from evidence_index import FORMAT,EvidenceUnavailable,descriptor,load_index,load_phase,recover_files


def review_indexed(index,output,run_id,commit,fixtures,log,evidence_root=None):
    if evidence_root and Path(evidence_root).resolve()!=output.resolve():
        load_index(index,evidence_root)  # Check every source file before copying.
        entries={e['path']:e for p in index['phases'].values() for e in p['files']}
        entries[index['restore']['path']]=index['restore']
        for relative in entries:
            source=Path(evidence_root)/relative;target=output/relative;target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists():assert target.read_bytes()==source.read_bytes(),'Recovered/downloaded evidence differs'
            else:shutil.copyfile(source,target)
    payload,receipt=load_index(index,output)
    return review_payload(payload,receipt,index,output,run_id,commit,fixtures,log)

def review_payload(payload,receipt,index,output,run_id,commit,fixtures,log,full_repeat=True):
    proof=payload['primary']['build_evidence'];assert proof['lab_commit']==commit,'Indexed build proof belongs to another commit'
    bundle=verify_bundle(fixtures);results=copy.deepcopy(payload['primary']['coverage']);rows=results['groups']
    assert index['reference']==results['reference']==REFERENCE
    assert {r['case'] for r in rows}=={r['case'] for r in bundle['requirements']},'Frozen 34 groups required'
    from order_cases import GROUP_CHECKS,review_order_group
    from finance_cases import FINANCE_CHECKS,review_finance_group
    from api_cases import API_CHECKS,review_api_group
    from audit_cases import RUNTIME_CHECKS,review_runtime_group
    from recovery_cases import RECOVERY_CHECKS,review_recovery_group
    from run import review_native_fx
    for row in rows:
        evidence=payload['primary']['groups'][row['case']]
        for cases,review in [(GROUP_CHECKS,review_order_group),(FINANCE_CHECKS,review_finance_group),(API_CHECKS,review_api_group),(RUNTIME_CHECKS,review_runtime_group),(RECOVERY_CHECKS,review_recovery_group)]:
            if row['case'] in cases:review(row,evidence,fixtures)
        if row['case']=='FX01-03-MONEY01-03':review_native_fx(row,evidence,json.loads((fixtures/'fx.json').read_bytes()))
        if row['case']=='FIXTURE-HASH-NATIVE-EXPORT':review_native_fixture(row,evidence,fixtures)
        row['evidence']=next(e['path'] for e in index['phases']['primary']['files'] if e.get('role')=='group:'+row['case'])
    from repeat import assert_repeat_contents
    reviewed={'status':'UNRUN','complete':False,**receipt}
    if full_repeat:
        try:assert_repeat_contents(payload,fixtures);reviewed.update(status='PASS',complete=True)
        except Exception as error:reviewed.update(status='FAIL',error=type(error).__name__+': '+str(error))
    else:reviewed['reason']='Complete primary files reviewed; complete second-phase/restore evidence unavailable'
    results.update(source='Complete original indexed files recovered/downloaded and hash verified; native reviewers applied',
        run_id=run_id,lab_commit=commit,reference=REFERENCE,coverage_revision=2,
        log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),counts=dict(Counter(r['status'] for r in rows)),
        criteria=criteria_for(rows,proof,payload['primary']['benchmark'],index if full_repeat else None,fixtures,output),repeat_review=reviewed)
    (output/('isolated-repeat.json' if full_repeat else 'primary-phase-index.json')).write_text(json.dumps(index,indent=2)+'\n')
    (output/'coverage.json').write_text(json.dumps(results,indent=2)+'\n')
    return results


def extract(log, output, run_id, commit, fixtures, evidence_root=None):
    output.mkdir(parents=True, exist_ok=True)
    objects = []
    decoder = json.JSONDecoder()
    for line in log.read_text(errors="replace").splitlines():
        if "##[notice]" not in line:
            continue
        value = line.split("##[notice]", 1)[1].lstrip()
        if not value.startswith("{"):
            continue
        try:
            item, end = decoder.raw_decode(value)
        except json.JSONDecodeError:
            continue
        if value[end:].strip():
            continue  # Truncated or mixed output never establishes a result.
        objects.append(item)
    complete_fragments = {}
    latest_bundle = {}
    for item in objects:
        if item.get("complete_evidence_case") and item.get("reference") == REFERENCE:
            key=(item['complete_evidence_case'],item.get('content_sha256'),item.get('encoding','base64'))
            complete_fragments.setdefault(key,[]).append(item);latest_bundle[item['complete_evidence_case']]=key
    complete_groups = {}
    for case,key in latest_bundle.items():
        parts=complete_fragments[key]
        try:
            count = parts[0]["fragment_count"]
            assert count > 0 and len(parts) == count and {p["fragment_index"] for p in parts} == set(range(count))
            assert all(p["fragment_count"] == count and p["content_sha256"] == parts[0]["content_sha256"] for p in parts)
            raw = base64.b64decode("".join(p["base64_fragment"] for p in sorted(parts, key=lambda p: p["fragment_index"])), validate=True)
            if key[2]=='zlib+base64':raw=zlib.decompress(raw)
            else:assert key[2]=='base64','Unknown proof encoding'
            assert hashlib.sha256(raw).hexdigest() == parts[0]["content_sha256"]
            item = json.loads(raw)
            assert item["case"] == case and item["reference"] == REFERENCE
            complete_groups[case] = item
        except (AssertionError, KeyError, TypeError, ValueError,zlib.error):
            continue  # No inferred result from missing, duplicate or altered fragments.
    recover_files(objects,output,REFERENCE)
    index=complete_groups.get('ISOLATED-FRESH-REPLAY')
    if index and index.get('format')==FORMAT:
        try:return review_indexed(index,output,run_id,commit,fixtures,log,evidence_root)
        except EvidenceUnavailable:
            pass  # Preserve the index and available primary notices; repeat remains unverified.
        # A missing repeat fragment must not erase complete independent primary
        # probes. Each used primary file still needs its exact indexed hash.
        for entry in index['phases']['primary']['files']:
            role=entry.get('role','')
            if not (role.startswith('group:') or role=='benchmark'):continue
            try:
                actual=descriptor(output,output/entry['path'])
                assert (actual['bytes'],actual['sha256'])==(entry['bytes'],entry['sha256'])
                value=json.loads((output/entry['path']).read_bytes())
                complete_groups[value['case']]=value
            except (AssertionError,KeyError,ValueError,OSError):continue
    phase_index=complete_groups.get('EVIDENCE-PHASE-primary')
    if phase_index and phase_index.get('format')==FORMAT:
        try:
            primary,receipt=load_phase(phase_index,output,'primary')
            return review_payload({'primary':primary},receipt,phase_index,output,run_id,commit,fixtures,log,False)
        except EvidenceUnavailable:pass
    rows = rows_for(verify_bundle(fixtures))
    by_case = {r["case"]: r for r in rows}
    gates, exports, independent = {}, {}, {}
    product_steps, search_steps, search_queries, search_failures, book_steps, fx_steps, fx_failures = [], [], [], [], [], [], []
    proof = None
    fixture_sections = {}
    chunks = {}
    for item in objects:
        case = item.get("case")
        if case == "FIXTURE-HASH-NATIVE-EXPORT" and "section" in item and "records" in item:
            fixture_sections[item["section"]] = item["records"]
        if item.get("scope") == "native address fixture prerequisite, not a Core group":
            assert item.get("lab_commit") == commit and item.get("reference") == REFERENCE
            (output / "address-preflight.json").write_text(json.dumps(item, indent=2) + "\n")
        if item.get("metric_kind") == "runtime" and item.get("reference") == REFERENCE:
            (output / "runtime-metrics.json").write_text(json.dumps(item, indent=2) + "\n")
        if case in ("warranty", "disabled-price-retained") and "persisted" in item:
            product_steps.append(item)
        if case == "SEARCH01-04-NATIVE" and "step" in item:
            search_steps.append(item["step"])
        if case == "SEARCH01-04-NATIVE" and "inspection" in item:
            search_queries.append(item["inspection"])
        if case == "SEARCH01-04-NATIVE" and "failure" in item:
            search_failures.append(item["failure"])
        if case == "BANK-BOOK-FIXTURE" and "step" in item:
            book_steps.append(item["step"])
        if case == "FX01-03-MONEY01-03" and "step" in item:
            fx_steps.append(item["step"])
        if case == "FX01-03-MONEY01-03" and "payment_case" in item and "failure" in item:
            fx_failures.append(item)
        if "lab_commit" in item and "upstream_diff_exit_codes" in item and "suites" in item:
            assert item["lab_commit"] == commit, "Build proof belongs to another commit"
            proof = item
        if case in ("CO00", "TAX01-W") and "section" in item and "records" in item:
            if "record_index" in item:
                key = (case, item["section"])
                chunks.setdefault(key, []).append(item)
            else:
                exports.setdefault(case, {"case": case})[item["section"]] = item["records"]
        if case in ("CO00", "TAX01-W") and "sequences" in item:
            (output / f"{case}-committed-sequences.json").write_text(json.dumps(item, indent=2) + "\n")
        # The first runner fallback omitted top-level reference metadata. Its
        # complete preparation error still contains the verified native reference.
        # Recognize only that explicit legacy failure; never infer missing success.
        legacy_preparation_failure = (item.get("reference") is None and item.get("status") == "FAIL"
            and "Fixture preparation failed" in item.get("error", "")
            and ("'reference': '" + REFERENCE + "'") in item.get("error", ""))
        if case in ("CO00", "TAX01-W") and (item.get("reference") == REFERENCE or legacy_preparation_failure) and "status" in item:
            if legacy_preparation_failure:
                item["reference_evidence"] = "Exact pinned reference explicitly present in the complete native preparation error; legacy runner omitted top-level reference"
            gates[case] = item
            by_case[case + "-NATIVE"].update(status="UNRUN" if item["status"] == "PASS" else item["status"],
                observed_revision=1, complete=False, partial_gate_status=item["status"],
                reason=item.get("failed_stage", "Economic administrator gate; complete subcases pending"), evidence=f"{case}-gate.json")
        if case in ("PROD01-04", "SEARCH01-04-NATIVE", "BANK-BOOK-FIXTURE", "FX01-03-MONEY01-03", "FIXTURE-HASH-NATIVE-EXPORT") and "status" in item and item.get("reference") == REFERENCE:
            independent[case] = item
            by_case[case].update(status=item["status"], observed_revision=item["revision"], complete=item["complete"],
                reason=item.get("error", "Executed native independent case"), evidence=f"{case}.json")
    for (case, section), parts in chunks.items():
        count = parts[0]["record_count"]
        if (count > 0 and len(parts) == count and {p["record_index"] for p in parts} == set(range(count))
            and all(p["record_count"] == count and len(p["records"]) == 1 for p in parts)):
            exports.setdefault(case, {"case": case})[section] = [p["records"][0] for p in sorted(parts, key=lambda p: p["record_index"])]
    for case, item in gates.items():
        (output / f"{case}-gate.json").write_text(json.dumps(item, indent=2) + "\n")
    for case, item in exports.items():
        (output / f"{case}-native-export.json").write_text(json.dumps(item, indent=2) + "\n")
    for case, item in independent.items():
        if case == "FIXTURE-HASH-NATIVE-EXPORT":
            item["native_export"] = fixture_sections
            review_native_fixture(by_case[case], item, fixtures)
            if (item["status"], item["complete"]) != (by_case[case]["status"], by_case[case]["complete"]):
                item.update(reported_status=item["status"], reported_complete=item["complete"],
                    status=by_case[case]["status"], complete=by_case[case]["complete"], review_reason=by_case[case]["reason"])
            (output / f"{case}.json").write_text(json.dumps(item, indent=2) + "\n")
            continue
        item["steps"] = {"PROD01-04": product_steps, "SEARCH01-04-NATIVE": search_steps, "BANK-BOOK-FIXTURE": book_steps, "FX01-03-MONEY01-03": fx_steps}[case]
        if case == "SEARCH01-04-NATIVE":
            item["native_queries"] = search_queries
            item["subcase_failures"] = search_failures
        if case == "FX01-03-MONEY01-03":
            item["payment_failures"] = fx_failures
            configured = None
            try:
                conversions = [s["native_conversion"] for s in fx_steps if "native_conversion" in s]
                configured = next(s["persisted"] for s in fx_steps if s["case"] == "manager-authorized")
                assert_native_fx_conversions(conversions, json.loads((fixtures / "fx.json").read_bytes()), configured)
                item["partial_conversion_status"] = by_case[case]["partial_conversion_status"] = "PASS"
            except (AssertionError, KeyError, TypeError, StopIteration):
                pass  # Missing conversion evidence never establishes partial success.
        if item["status"] == "PASS":
            complete_notices = len(item["steps"]) == {"PROD01-04": 7, "SEARCH01-04-NATIVE": 11, "BANK-BOOK-FIXTURE": 5, "FX01-03-MONEY01-03": 9}[case]
            if not complete_notices:
                by_case[case].update(status="UNRUN", complete=False,
                    reason="PASS notice present but detailed persistence/query notices are incomplete; FX calculations alone cannot prove four committed native payments" if case == "FX01-03-MONEY01-03" else "PASS notice present but detailed persistence/query notices are incomplete; inspect full artifact")
            elif case == "BANK-BOOK-FIXTURE":
                receipts = [s["persisted"] for s in item["steps"] if s.get("case") == "native-advance-receipt"]
                try:
                    assert len(receipts) == 4
                    assert_native_bank_book({"company_id": receipts[0]["company_id"], "vouchers": receipts},
                        json.loads((fixtures / "bank-book.json").read_bytes()))
                    assert item["steps"][-1].get("case") == "fixture-replay" and item["steps"][-1].get("native_export_identical") is True
                except (AssertionError, KeyError, TypeError) as error:
                    by_case[case].update(status="FAIL", complete=False,
                        reason="Bank-book notice contradicts persisted native payment/journal detail: " + str(error))
            elif case == "FX01-03-MONEY01-03":
                try:
                    assert not fx_failures, "A failed native payment case cannot establish complete FX PASS"
                    payments = [s for s in fx_steps if s["case"] == "committed-payment-case"]
                    assert len(payments) == 3
                    persisted = dict(configured)
                    for field in ("invoices", "payments"):
                        persisted[field] = [record for s in payments for record in s["persisted"][field]]
                    assert all(s["persisted"].get("read_boundary") == "separate-http-after-payment-commit" for s in payments)
                    persisted["read_boundary"] = "separate-http-after-payment-commit"
                    persisted["company_id"] = payments[0]["persisted"]["company_id"]
                    persisted["company_code"] = payments[0]["persisted"]["company_code"]
                    assert_native_fx([s["result"] for s in payments], json.loads((fixtures / "fx.json").read_bytes()), persisted)
                    denials = [s for s in fx_steps if s["case"] in ("missing-rate", "operator-denied")]
                    assert len(denials) == 2 and [s["http_status"] for s in denials] == [422, 403]
                    assert all(s["native_effects_unchanged"] is True for s in denials)
                except (AssertionError, KeyError, TypeError, StopIteration) as error:
                    by_case[case].update(status="FAIL", complete=False,
                        reason="FX notice contradicts committed native payments, journal, settlement or rate/role details: " + str(error))
        if (item["status"], item["complete"]) != (by_case[case]["status"], by_case[case]["complete"]):
            item["reported_status"] = item["status"]
            item["reported_complete"] = item["complete"]
            item.update(status=by_case[case]["status"], complete=by_case[case]["complete"], review_reason=by_case[case]["reason"])
        (output / f"{case}.json").write_text(json.dumps(item, indent=2) + "\n")
    from order_cases import GROUP_CHECKS, review_order_group
    for case, item in complete_groups.items():
        if case not in GROUP_CHECKS:
            continue
        row = by_case[case]
        row.update(status=item["status"], observed_revision=item["revision"], complete=item["complete"],
                   evidence=case+".json", reason=item.get("error", "Complete executed native proof"))
        review_order_group(row, item, fixtures)
        if row["status"] != item["status"] or row["complete"] != item["complete"]:
            item.update(reported_status=item["status"], status=row["status"], complete=row["complete"], review_reason=row["reason"])
        (output / (case+".json")).write_text(json.dumps(item, indent=2)+"\n")
    if proof:
        (output / "build-evidence.json").write_text(json.dumps(proof, indent=2) + "\n")
    from finance_cases import FINANCE_CHECKS, review_finance_group
    for case,item in complete_groups.items():
        if case not in FINANCE_CHECKS:
            continue
        row=by_case[case]
        row.update(status=item['status'],observed_revision=item['revision'],complete=item['complete'],evidence=case+'.json',reason=item.get('error','Native finance execution'))
        review_finance_group(row,item,fixtures)
        if row['status']!=item['status'] or row['complete']!=item['complete']:
            item.update(reported_status=item['status'],status=row['status'],complete=row['complete'],review_reason=row['reason'])
        (output/(case+'.json')).write_text(json.dumps(item,indent=2)+'\n')
    from api_cases import API_CHECKS, review_api_group
    for case,item in complete_groups.items():
        if case not in API_CHECKS:continue
        row=by_case[case]
        row.update(status=item['status'],observed_revision=item['revision'],complete=item['complete'],evidence=case+'.json',reason=item.get('error','Native API execution'))
        review_api_group(row,item,fixtures)
        if row['status']!=item['status'] or row['complete']!=item['complete']:
            item.update(reported_status=item['status'],status=row['status'],complete=row['complete'],review_reason=row['reason'])
        (output/(case+'.json')).write_text(json.dumps(item,indent=2)+'\n')
    from audit_cases import RUNTIME_CHECKS, review_runtime_group
    from recovery_cases import RECOVERY_CHECKS, review_recovery_group
    for cases,review in [(RUNTIME_CHECKS,review_runtime_group),(RECOVERY_CHECKS,review_recovery_group)]:
        for case,item in complete_groups.items():
            if case not in cases:continue
            row=by_case[case];row.update(status=item['status'],observed_revision=item['revision'],complete=item['complete'],evidence=case+'.json',reason=item.get('error','Native runtime execution'))
            review(row,item,fixtures)
            if row['status']!=item['status'] or row['complete']!=item['complete']:
                item.update(reported_status=item['status'],status=row['status'],complete=row['complete'],review_reason=row['reason'])
            (output/(case+'.json')).write_text(json.dumps(item,indent=2)+'\n')
    benchmark=complete_groups.get("BENCHMARK-FIXED-PROFILE")
    repeat=complete_groups.get("ISOLATED-FRESH-REPLAY")
    for name,item in [("benchmark.json",benchmark),("isolated-repeat.json",repeat)]:
        if item:(output/name).write_text(json.dumps(item,indent=2)+"\n")
    results = {"source": "complete structured Actions log notices; ZIP availability tracked separately",
        "run_id": run_id, "lab_commit": commit, "reference": REFERENCE, "coverage_revision": 2,
        "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        "groups": rows, "counts": dict(Counter(r["status"] for r in rows)), "criteria": criteria_for(rows, proof,benchmark,repeat,fixtures,evidence_root),
        "patch_scenarios": {"status": "UNRUN", "count": 6},
        "limitations": "No missing notice is inferred. Economic gates retain incomplete role/state/atomicity coverage. Full metrics/recovery evidence require their actual result files."}
    (output / "coverage.json").write_text(json.dumps(results, indent=2) + "\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--fixtures", required=True, type=Path)
    parser.add_argument("--evidence-root", type=Path,
        help="Downloaded complete artifact root for indexed repeat verification; log index alone cannot prove PASS")
    args = parser.parse_args()
    result = extract(args.log, args.output, args.run_id, args.commit, args.fixtures,args.evidence_root)
    print(json.dumps({"groups": result["counts"], "criteria": dict(Counter(r["status"] for r in result["criteria"]))}))
