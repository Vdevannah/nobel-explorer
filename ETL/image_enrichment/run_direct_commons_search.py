import json
import time
from pathlib import Path

from ETL.image_enrichment.commons import CommonsClient
from ETL.image_enrichment.direct_commons_search import (
    search_organization_candidates,
    search_person_candidates,
    validate_candidate,
)

INPUT_PATH = Path("artifacts/final_60_merged_context.json")
OUTPUT_PATH = Path("artifacts/direct_commons_search_results.json")


def main() -> None:
    records = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    print(f"running direct Commons search for {len(records)} records", flush=True)

    commons_client = CommonsClient()
    results = []
    start_time = time.monotonic()
    for index, record in enumerate(records):
        step_start = time.monotonic()
        is_org = record["laureate_type"] == "Organization"
        search_fn = search_organization_candidates if is_org else search_person_candidates
        candidates = search_fn(commons_client, record["full_name"])

        validated = []
        for candidate in candidates[:3]:  # cap per-person to limit API load; top plausible hits only
            outcome = validate_candidate(
                commons_client,
                record["laureate_id"],
                record["nobel_laureate_id"],
                record["full_name"],
                candidate,
            )
            validated.append({
                "filename": candidate,
                "commons_decision": outcome.get("commons_decision"),
                "image_url_candidate": outcome.get("image_url_candidate"),
                "canonical_source_url": outcome.get("canonical_source_url"),
                "license_normalized": outcome.get("license_normalized"),
                "attribution_normalized": outcome.get("attribution_normalized"),
                "reason": "; ".join(outcome.get("skip_reasons", []) + outcome.get("review_reasons", [])) or None,
            })

        results.append({
            "nobel_laureate_id": record["nobel_laureate_id"],
            "laureate_id": record["laureate_id"],
            "full_name": record["full_name"],
            "laureate_type": record["laureate_type"],
            "prior_category": record["prior_category"],
            "search_candidates_found": len(candidates),
            "validated_candidates": validated,
        })

        elapsed = time.monotonic() - step_start
        best = next((v for v in validated if v["commons_decision"] == "ACCEPT"), None)
        print(
            f"  [{time.monotonic()-start_time:6.1f}s, {elapsed:4.1f}s] ({index+1}/{len(records)}) "
            f"{record['full_name']!r} | candidates_found={len(candidates)} "
            f"best={'ACCEPT: ' + best['filename'] if best else 'none'}",
            flush=True,
        )

    OUTPUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    accepted = [r for r in results if any(v["commons_decision"] == "ACCEPT" for v in r["validated_candidates"])]
    print("=== SUMMARY ===")
    print(f"total: {len(results)}")
    print(f"with at least one Commons-ACCEPT candidate: {len(accepted)}")
    print(f"Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
