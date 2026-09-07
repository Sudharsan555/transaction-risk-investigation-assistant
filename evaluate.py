#!/usr/bin/env python3
"""
CLI Evaluation Tool for NexusTiQ24 PS06 - Transaction Risk Investigation Assistant.

Designed specifically for hackathon evaluators, automated testbeds, and grading harnesses.
Allows evaluating any JSON test case via file argument, --input flag, or stdin pipe,
without requiring a running web server.

Usage:
    python evaluate.py <path_to_testcase.json>
    python evaluate.py --input <path_to_testcase.json>
    python evaluate.py --json <path_to_testcase.json>    # Output raw JSON only
    cat testcase.json | python evaluate.py              # Stdin pipe
"""

import sys
import json
import argparse
from pathlib import Path

# Force UTF-8 output on Windows consoles to prevent charmap UnicodeEncodeErrors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.models import CustomAnalysisRequest
from src.data_loader import DataLoader
from src.rule_engine import RiskRuleEngine
from src.llm_engine import LLMInvestigationEngine


def evaluate_single_payload(payload_dict: dict, data_loader: DataLoader, rule_engine: RiskRuleEngine, llm_engine: LLMInvestigationEngine) -> dict:
    request = CustomAnalysisRequest.model_validate(payload_dict)

    hist_txns = list(request.historical_transactions or [])
    obs_txns = list(request.observed_transactions or [])
    legacy_txns = list(request.transactions or [])

    # Auto-partition legacy or flat payloads to prevent baseline contamination
    if not hist_txns and not obs_txns and legacy_txns:
        if len(legacy_txns) >= 6:
            hist_txns = legacy_txns[:-1]
            obs_txns = [legacy_txns[-1]]
            eval_txns = obs_txns
        else:
            eval_txns = legacy_txns
    elif obs_txns:
        eval_txns = obs_txns
    elif legacy_txns:
        eval_txns = legacy_txns
    else:
        eval_txns = []

    cust_profile = request.customer_profile
    cust_id = request.customer_id or "CUSTOM-001"
    cust_name = request.customer_name or "Custom Sandbox Account"
    if cust_profile:
        cust_id = cust_profile.customer_id or cust_id
        cust_name = cust_profile.name or cust_name
    elif eval_txns and eval_txns[0].customer_id:
        cust_id = eval_txns[0].customer_id
    elif hist_txns and hist_txns[0].customer_id:
        cust_id = hist_txns[0].customer_id

    # Baseline derivation & contamination prevention
    if hist_txns:
        derived_profile = data_loader.derive_baseline(
            hist_txns,
            customer_id=cust_id,
            name=cust_name,
            exclude_transaction_ids=[t.transaction_id for t in eval_txns]
        )
        if cust_profile:
            derived_profile.account_type = cust_profile.account_type or derived_profile.account_type
            derived_profile.account_number = cust_profile.account_number or derived_profile.account_number
        cust_profile = derived_profile
        result = rule_engine.evaluate_customer(
            cust_id,
            transactions=eval_txns,
            profile=cust_profile,
            historical_transactions=hist_txns
        )
    else:
        if not eval_txns:
            empty_profile = cust_profile or data_loader.derive_baseline([], cust_id, cust_name)
            result = rule_engine.evaluate_customer(cust_id, transactions=[], profile=empty_profile)
        elif cust_profile is not None:
            result = rule_engine.evaluate_customer(cust_id, transactions=eval_txns, profile=cust_profile)
        else:
            derived_profile = data_loader.derive_baseline(eval_txns, cust_id, cust_name)
            result = rule_engine.evaluate_customer(cust_id, transactions=eval_txns, profile=derived_profile)

    report_md, model_name, fallback_used = llm_engine.generate_investigation_report(result)
    result.llm_report = report_md
    result.llm_model_used = model_name
    result.fallback_used = fallback_used

    return result.model_dump()


def run_evaluation(data: any, json_output_only: bool = False):
    data_loader = DataLoader()
    rule_engine = RiskRuleEngine(loader=data_loader)
    llm_engine = LLMInvestigationEngine()

    # Detect if multiple test cases in payload
    if isinstance(data, dict) and "test_cases" in data and isinstance(data["test_cases"], list):
        items = data["test_cases"]
    elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and ("historical_transactions" in data[0] or "observed_transactions" in data[0] or "customer_profile" in data[0]):
        items = data
    else:
        items = [data]

    results = []
    for idx, item in enumerate(items, 1):
        try:
            res_dict = evaluate_single_payload(item, data_loader, rule_engine, llm_engine)
            results.append(res_dict)
            if not json_output_only:
                print("=" * 72)
                print(f" NEXUSTIQ24 PS06 EVALUATION - CASE #{idx}")
                print("=" * 72)
                print(f"Customer ID    : {res_dict['customer_id']} ({res_dict['customer_name']})")
                print(f"Verdict        : {res_dict['verdict']}")
                print(f"Risk Score     : {res_dict['risk_score']}/100 (Urgency Index)")
                print(f"Evidence Status: {res_dict['evidence_status']}")
                print(f"Model Engine   : {res_dict['llm_model_used']} (Fallback: {res_dict['fallback_used']})")
                print(f"Findings Count : {len(res_dict['findings'])}")
                print("-" * 72)
                if res_dict['findings']:
                    print("TRIGGERED RISK FINDINGS:")
                    for f_idx, f in enumerate(res_dict['findings'], 1):
                        cited = ", ".join([f"[{cid}]" for cid in (f.get('cited_transaction_ids') or f.get('transaction_ids') or [])])
                        pts = f.get('points', 40 if f.get('severity') == 'HIGH' else 25)
                        print(f"  {f_idx}. [{f['severity']}] {f['rule_name']} (Points: {pts})")
                        print(f"     Cited Txns : {cited}")
                        print(f"     Observed   : {f['metric_observed']}")
                        print(f"     Baseline   : {f['baseline_reference']}")
                    print("-" * 72)
                print("INVESTIGATION REPORT:")
                print(res_dict['llm_report'])
                print("=" * 72)
                print()
        except Exception as e:
            print(f"❌ Error evaluating case #{idx}: {e}", file=sys.stderr)
            if json_output_only:
                results.append({"error": str(e)})

    if json_output_only:
        out = results if len(results) > 1 else (results[0] if results else {})
        print(json.dumps(out, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="CLI Evaluation Tool for NexusTiQ24 PS06 - Transaction Risk Investigation Assistant"
    )
    parser.add_argument("file", nargs="?", help="Path to JSON test case file.")
    parser.add_argument("--input", "-i", dest="input_file", help="Path to JSON test case file.")
    parser.add_argument("--json", action="store_true", help="Output raw JSON response only (ideal for automated grading scripts).")

    args = parser.parse_args()
    target_path = args.input_file or args.file

    raw_text = None
    if target_path:
        p = Path(target_path)
        if not p.exists():
            print(f"❌ Error: File not found: {target_path}", file=sys.stderr)
            sys.exit(1)
        raw_text = p.read_text(encoding="utf-8").strip()
    elif not sys.stdin.isatty():
        raw_text = sys.stdin.read().strip()
    else:
        parser.print_help()
        sys.exit(1)

    if not raw_text:
        print("❌ Error: Empty payload received.", file=sys.stderr)
        sys.exit(1)

    if "```json" in raw_text:
        raw_text = raw_text.split("```json")[1].split("```")[0].strip()
    elif "```" in raw_text:
        raw_text = raw_text.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON syntax: {e}", file=sys.stderr)
        sys.exit(1)

    run_evaluation(data, json_output_only=args.json)


if __name__ == "__main__":
    main()
