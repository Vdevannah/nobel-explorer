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
    extract_additional_restrictions,
    is_normalization_candidate,
)
from ETL.image_enrichment.validation import normalize_license

AUDIT_INPUT_PATH = Path("artifacts/image_enrichment_unresolved_audit.json")
OUTPUT_PATH = Path("artifacts/commons_license_policy_audit.json")


def main() -> None:
    audit = json.loads(AUDIT_INPUT_PATH.read_text(encoding="utf-8"))
    records = [r for r in audit["records"] if r["category"] == "COMMONS_LICENSE"]
    print(f"auditing {len(records)} COMMONS_LICENSE records (read-only, live Commons re-read)", flush=True)

    db = SessionLocal()
    commons_client = CommonsClient()

    audited = []
    start_time = time.monotonic()
    try:
        for index, record in enumerate(records):
            step_start = time.monotonic()
            laureate = laureate_repository.get_by_nobel_id(db, record["nobel_laureate_id"])
            filename = record["p18_filename"]

            entry = {
                "laureate_id": record["laureate_id"],
                "nobel_laureate_id": record["nobel_laureate_id"],
                "full_name": record["full_name"],
                "laureate_type": laureate.laureate_type if laureate else None,
                "commons_filename": filename,
            }

            info = None
            network_error = None
            try:
                info = commons_client.get_file_info(filename)
            except CommonsError as error:
                # get_file_info raises CommonsError only for network/
                # transport failures, never for a genuinely missing file
                # -- never conflate the two in this audit's output.
                network_error = str(error)

            if network_error is not None:
                entry["fetch_status"] = "network_error"
                entry["fetch_error"] = network_error
                audited.append(entry)
                elapsed = time.monotonic() - step_start
                print(f"  [{time.monotonic()-start_time:6.1f}s, {elapsed:5.1f}s] ({index+1}/{len(records)}) {record['full_name']!r} -> NETWORK ERROR: {network_error}", flush=True)
                continue

            if info is None:
                entry["fetch_status"] = "not_found_on_commons"
                audited.append(entry)
                elapsed = time.monotonic() - step_start
                print(f"  [{time.monotonic()-start_time:6.1f}s, {elapsed:5.1f}s] ({index+1}/{len(records)}) {record['full_name']!r} -> genuinely not found on Commons", flush=True)
                continue

            extmetadata = info.get("extmetadata", {}) or {}
            license_family = classify_license_family(extmetadata)
            additional_restrictions = extract_additional_restrictions(extmetadata)
            current = normalize_license(extmetadata)
            normalization_candidate = is_normalization_candidate(license_family["family"], current["status"])
            suitability = classify_image_suitability(
                entry["laureate_type"] or "Person",
                filename,
                extmetadata.get("ImageDescription"),
            )

            entry.update({
                "fetch_status": "ok",
                "commons_file_page_url": info.get("canonical_source_url"),
                "image_url": info.get("thumbnail_url") or info.get("image_url"),
                "mime": info.get("mime"),
                "width": info.get("width"),
                "height": info.get("height"),
                "metadata": {
                    "LicenseShortName": extmetadata.get("LicenseShortName"),
                    "License": extmetadata.get("License"),
                    "UsageTerms": extmetadata.get("UsageTerms"),
                    "LicenseUrl": extmetadata.get("LicenseUrl"),
                    "Attribution": extmetadata.get("Attribution"),
                    "Artist": extmetadata.get("Artist"),
                    "Credit": extmetadata.get("Credit"),
                    "Copyrighted": extmetadata.get("Copyrighted"),
                    "Restrictions": extmetadata.get("Restrictions"),
                    "ImageDescription": extmetadata.get("ImageDescription"),
                },
                "license_family": license_family["family"],
                "license_family_basis": license_family["basis"],
                "additional_restrictions": additional_restrictions,
                "current_validator_status": current["status"],
                "current_validator_normalized": current["normalized"],
                "normalization_candidate": normalization_candidate,
                "image_suitability": suitability["suitability"],
                "image_suitability_basis": suitability["basis"],
            })
            audited.append(entry)

            elapsed = time.monotonic() - step_start
            print(
                f"  [{time.monotonic()-start_time:6.1f}s, {elapsed:5.1f}s] ({index+1}/{len(records)}) "
                f"{record['full_name']!r} | family={license_family['family']!r} "
                f"restrictions={additional_restrictions} validator={current['status']!r} "
                f"norm_candidate={normalization_candidate} suitability={suitability['suitability']!r}",
                flush=True,
            )
    finally:
        db.close()

    family_counts = Counter(r.get("license_family", "FETCH_FAILED") for r in audited)
    restriction_counts = Counter(
        restriction for r in audited for restriction in r.get("additional_restrictions", [])
    )
    suitability_counts = Counter(r.get("image_suitability", "FETCH_FAILED") for r in audited)

    def bucket(r: dict) -> str:
        if r.get("fetch_status") == "network_error":
            return "fetch_failed_transient"
        if r.get("fetch_status") == "not_found_on_commons":
            return "unsuitable_or_unclear"
        if r.get("fetch_status") != "ok":
            return "unsuitable_or_unclear"
        family = r.get("license_family")
        has_restrictions = bool(r.get("additional_restrictions"))
        status = r.get("current_validator_status")

        if family == "Restrictive (non-free)":
            return "unsuitable_or_unclear"
        if r.get("image_suitability") == "NON_PORTRAIT":
            return "unsuitable_or_unclear"

        # A license the current validator already treats as reusable, but
        # that is still held to REVIEW purely by an independent
        # (non-copyright) restriction warning -- e.g. a clean CC BY 4.0
        # file flagged only for "personality". Normalizing the license
        # would change nothing here; only a restriction *policy* decision
        # would. Never counted as a normalization win.
        if status == "reusable" and has_restrictions:
            return "policy_decision"

        if status == "reusable" and not has_restrictions:
            # Already reusable under existing policy with no other
            # blocker -- would not actually be in the COMMONS_LICENSE
            # bucket under current logic, but reported for completeness.
            return "reusable_no_blocker"

        if r.get("normalization_candidate") and not has_restrictions:
            return "normalization_only"
        if r.get("normalization_candidate") and has_restrictions:
            # Fixing the license alone would not be enough; still needs a
            # restriction-policy call too.
            return "policy_decision"

        return "policy_decision"

    for r in audited:
        r["policy_bucket"] = bucket(r)

    buckets = Counter(bucket(r) for r in audited)
    normalization_only = [r for r in audited if bucket(r) == "normalization_only"]
    policy_decision_needed = [r for r in audited if bucket(r) == "policy_decision"]
    unsuitable_or_unclear = [r for r in audited if bucket(r) == "unsuitable_or_unclear"]
    reusable_no_blocker = [r for r in audited if bucket(r) == "reusable_no_blocker"]

    summary = {
        "total": len(audited),
        "license_families": dict(family_counts),
        "additional_restrictions": dict(restriction_counts),
        "image_suitability": dict(suitability_counts),
        "potential_normalization_only_count": len(normalization_only),
        "clearly_reusable_under_current_policy_count": len(reusable_no_blocker),
        "requires_policy_decision_count": len(policy_decision_needed),
        "clearly_unsuitable_or_unclear_count": len(unsuitable_or_unclear),
        "bucket_breakdown": dict(buckets),
    }

    output = {"summary": summary, "records": audited}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    print("=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    print(f"Written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
