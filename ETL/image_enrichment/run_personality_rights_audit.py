import json
import time
from collections import Counter
from pathlib import Path

from backend.database.connection import SessionLocal
from backend.repositories import laureate_repository
from ETL.image_enrichment.commons import CommonsClient, CommonsError
from ETL.image_enrichment.license_policy_audit import (
    classify_image_suitability,
    classify_license_family,
)
from ETL.image_enrichment.validation import normalize_license

UNRESOLVED_AUDIT_PATH = Path("artifacts/image_enrichment_unresolved_audit.json")
LICENSE_AUDIT_PATH = Path("artifacts/commons_license_policy_audit.json")
OUTPUT_PATH = Path("artifacts/personality_rights_image_audit.json")


def main() -> None:
    license_audit = json.loads(LICENSE_AUDIT_PATH.read_text(encoding="utf-8"))
    target_ids = [
        r["nobel_laureate_id"] for r in license_audit["records"]
        if "personality" in r.get("additional_restrictions", [])
    ]
    unresolved = json.loads(UNRESOLVED_AUDIT_PATH.read_text(encoding="utf-8"))
    filenames = {r["nobel_laureate_id"]: r["p18_filename"] for r in unresolved["records"]}

    print(f"auditing {len(target_ids)} personality-rights records (fresh live Commons re-read)", flush=True)

    db = SessionLocal()
    commons_client = CommonsClient()
    audited = []
    start_time = time.monotonic()
    try:
        for index, nobel_id in enumerate(target_ids):
            step_start = time.monotonic()
            laureate = laureate_repository.get_by_nobel_id(db, nobel_id)
            filename = filenames[nobel_id]

            entry = {
                "laureate_id": laureate.laureate_id if laureate else None,
                "nobel_laureate_id": nobel_id,
                "full_name": laureate.full_name if laureate else None,
                "laureate_type": laureate.laureate_type if laureate else None,
                "commons_filename": filename,
            }

            info = None
            try:
                info = commons_client.get_file_info(filename)
            except CommonsError as error:
                entry["fetch_status"] = "network_error"
                entry["fetch_error"] = str(error)
                audited.append(entry)
                print(f"  [{time.monotonic()-start_time:6.1f}s] ({index+1}/{len(target_ids)}) {entry['full_name']!r} -> NETWORK ERROR", flush=True)
                continue

            if info is None:
                entry["fetch_status"] = "not_found_on_commons"
                audited.append(entry)
                print(f"  [{time.monotonic()-start_time:6.1f}s] ({index+1}/{len(target_ids)}) {entry['full_name']!r} -> NOT FOUND", flush=True)
                continue

            extmetadata = info.get("extmetadata", {}) or {}
            license_family = classify_license_family(extmetadata)
            current = normalize_license(extmetadata)
            suitability = classify_image_suitability(
                entry["laureate_type"] or "Person", filename, extmetadata.get("ImageDescription")
            )
            raw_restrictions = extmetadata.get("Restrictions")

            entry.update({
                "fetch_status": "ok",
                "commons_source_page": info.get("canonical_source_url"),
                "image_url": info.get("thumbnail_url") or info.get("image_url"),
                "mime": info.get("mime"),
                "metadata": {
                    "LicenseShortName": extmetadata.get("LicenseShortName"),
                    "License": extmetadata.get("License"),
                    "LicenseUrl": extmetadata.get("LicenseUrl"),
                    "UsageTerms": extmetadata.get("UsageTerms"),
                    "Copyrighted": extmetadata.get("Copyrighted"),
                    "Restrictions_raw": raw_restrictions,
                    "Attribution": extmetadata.get("Attribution"),
                    "Artist": extmetadata.get("Artist"),
                    "Credit": extmetadata.get("Credit"),
                },
                "copyright_license_family": license_family["family"],
                "copyright_license_basis": license_family["basis"],
                "current_validator_license_status": current["status"],
                "current_validator_license_normalized": current["normalized"],
                "personality_rights_warning_raw": raw_restrictions,
                "image_suitability": suitability["suitability"],
                "image_suitability_basis": suitability["basis"],
            })
            audited.append(entry)

            elapsed = time.monotonic() - step_start
            print(
                f"  [{time.monotonic()-start_time:6.1f}s, {elapsed:4.1f}s] ({index+1}/{len(target_ids)}) "
                f"{entry['full_name']!r} | license={license_family['family']!r} "
                f"validator_status={current['status']!r} restrictions={raw_restrictions!r} "
                f"suitability={suitability['suitability']!r}",
                flush=True,
            )
    finally:
        db.close()

    ok = [r for r in audited if r.get("fetch_status") == "ok"]
    license_family_counts = Counter(r["copyright_license_family"] for r in ok)
    restriction_pattern_counts = Counter(r["personality_rights_warning_raw"] for r in ok)
    suitability_counts = Counter(r["image_suitability"] for r in ok)
    reusable_now = [r for r in ok if r["current_validator_license_status"] == "reusable"]
    unclear_independent = [r for r in ok if r["current_validator_license_status"] in ("unclear", "missing")]
    restrictive_independent = [r for r in ok if r["current_validator_license_status"] == "restrictive"]
    personality_only_blocker = [r for r in ok if r["current_validator_license_status"] == "reusable"]

    summary = {
        "total": len(audited),
        "fetched_ok": len(ok),
        "fetch_failures": len(audited) - len(ok),
        "underlying_license_family_counts": dict(license_family_counts),
        "personality_rights_warning_pattern_counts": {
            (k if k is not None else "(none)"): v for k, v in restriction_pattern_counts.items()
        },
        "image_suitability_counts": dict(suitability_counts),
        "otherwise_reusable_license_count": len(reusable_now),
        "independently_unclear_license_count": len(unclear_independent),
        "independently_restrictive_license_count": len(restrictive_independent),
        "personality_warning_is_only_blocker_count": len(personality_only_blocker),
    }

    output = {"summary": summary, "records": audited}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== SUMMARY ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
