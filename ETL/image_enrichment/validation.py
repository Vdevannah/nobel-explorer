from __future__ import annotations

import html
import re
from datetime import date
from typing import Any


HUMAN_QID = "Q5"

SUPPORTED_IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
}

_RESTRICTIVE_LICENSE_MARKERS = (
    "noncommercial",
    "non commercial",
    "no derivative",
    "noderivative",
    "all rights reserved",
    "rights reserved",
    "fair use",
    "not for reuse",
    "not-for-reuse",
)
_RESTRICTIVE_CC_VARIANT_PATTERN = re.compile(
    r"\bby[\s-]?nc\b|\bby[\s-]?nd\b|\bnc[\s-]?sa\b|\bnc[\s-]?nd\b",
    re.IGNORECASE,
)
_CC0_MARKERS = ("cc0", "public domain dedication")
_PUBLIC_DOMAIN_MARKERS = ("public domain", "pd old", "pd-old", "pd us", "pd-us")

# Phase 7.5I-A: exactly the five reusable-but-previously-unrecognized
# license families identified by the Phase 7.5I Commons policy audit
# (artifacts/commons_license_policy_audit.json) as "potential
# normalization-only" cases -- each verified against its own
# authoritative LicenseUrl (gnu.org, Flickr Commons, etalab.gouv.fr,
# kogl.or.kr) before being added here. Deliberately five explicit,
# named markers, not a generic "anything unrecognized is fine" catch-all.
_GFDL_MARKER = "gfdl"
_COPYRIGHTED_FREE_USE_MARKER = "copyrighted free use"
_NO_RESTRICTIONS_MARKER = "no restrictions"
_LICENCE_OUVERTE_MARKER = "licence ouverte"
_KOGL_MARKER = "kogl"

# Phase 7.5M-A: the UK Open Government Licence version 3.0 only, verified
# directly against its authoritative text (nationalarchives.gov.uk) and
# against Commons' own licensing policy (Commons:UK_Open_Government_Licence),
# which documents OGL as an accepted Commons-free license and is backed by
# extensive existing Commons precedent (e.g. official UK PM/Cabinet
# portraits licensed OGL 3.0). Matches only version 3 (as "OGL 3",
# "OGL v3", "OGL 3.0", etc.) -- OGL versions 1 and 2 were never verified
# and are deliberately NOT matched here.
_OGL_V3_PATTERN = re.compile(r"\bogl[\s-]?v?3(?:\.0)?\b", re.IGNORECASE)

# Phase 7.5N: Commons' formally-templated "Attribution only license"
# (Template:Attribution, Wikidata Q98923445) -- verified directly against
# the template's own displayed terms: "The copyright holder of this file
# allows anyone to use it for any purpose, provided that the copyright
# holder is properly attributed," permitting redistribution, derivative
# works, and commercial use. A distinct, standalone Commons license, not
# a CC BY variant, and never rewritten as one. Matched only on an EXACT,
# whole-string match of the combined license text -- "Attribution" alone,
# nothing else -- so a genuine "Creative Commons Attribution 4.0" string
# (already caught by the CC BY pattern above) can never reach this branch.
_ATTRIBUTION_ONLY_EXACT = "attribution"
_CC_BY_SA_PATTERN = re.compile(
    r"cc[\s-]?by[\s-]?sa[\s-]?(\d+(?:\.\d+)?)?", re.IGNORECASE
)
_CC_BY_PATTERN = re.compile(
    r"cc[\s-]?by[\s-]?(\d+(?:\.\d+)?)?(?![\s-]?sa)", re.IGNORECASE
)
_TAG_PATTERN = re.compile(r"<[^>]+>")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def _clean_license_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[_/]+", " ", value).strip().lower()


def parse_restrictions(raw: str | None) -> list[str]:
    """Split Commons' 'Restrictions' extmetadata field into normalized,
    lowercase tokens (e.g. "personality", "trademark|insignia" ->
    ["trademark", "insignia"]). Never touches the copyright-license
    fields -- this is purely the non-copyright restrictions list.
    """
    if not raw:
        return []
    parts = re.split(r"[|,;]", raw)
    return [part.strip().lower() for part in parts if part.strip()]


def normalize_license(extmetadata: dict[str, Any]) -> dict[str, Any]:
    """Normalize Commons extmetadata license fields into a conservative,
    explainable reusability determination.

    Never infers "safe to use" from the file merely being hosted on
    Commons; only from explicit license/usage-terms/copyright metadata.
    status is one of: "reusable", "restrictive", "unclear", "missing".
    """
    license_short_name = extmetadata.get("LicenseShortName")
    license_full = extmetadata.get("License")
    usage_terms = extmetadata.get("UsageTerms")
    license_url = extmetadata.get("LicenseUrl")
    copyrighted = extmetadata.get("Copyrighted")

    result: dict[str, Any] = {
        "raw_license_short_name": license_short_name,
        "raw_license": license_full,
        "raw_usage_terms": usage_terms,
        "license_url": license_url,
        "normalized": None,
        "status": "missing",
        "reusable": False,
    }

    combined = " ".join(
        _clean_license_text(value)
        for value in (license_short_name, license_full, usage_terms)
        if value
    )
    is_public_domain_copyright = (
        copyrighted is not None
        and _clean_license_text(copyrighted) == "false"
    )

    if not combined:
        if is_public_domain_copyright:
            result.update(
                normalized="Public Domain", status="reusable", reusable=True
            )
        return result

    if (
        any(marker in combined for marker in _RESTRICTIVE_LICENSE_MARKERS)
        or _RESTRICTIVE_CC_VARIANT_PATTERN.search(combined)
    ):
        result.update(status="restrictive", normalized=license_short_name or license_full)
        return result

    if any(marker in combined for marker in _CC0_MARKERS):
        result.update(normalized="CC0", status="reusable", reusable=True)
        return result

    sa_match = _CC_BY_SA_PATTERN.search(combined)
    if sa_match:
        version = sa_match.group(1)
        result.update(
            normalized=f"CC BY-SA {version}" if version else "CC BY-SA",
            status="reusable",
            reusable=True,
        )
        return result

    by_match = _CC_BY_PATTERN.search(combined)
    if by_match:
        version = by_match.group(1)
        result.update(
            normalized=f"CC BY {version}" if version else "CC BY",
            status="reusable",
            reusable=True,
        )
        return result

    if any(marker in combined for marker in _PUBLIC_DOMAIN_MARKERS) or is_public_domain_copyright:
        result.update(normalized="Public Domain", status="reusable", reusable=True)
        return result

    # Phase 7.5I-A: preserve Commons' own license label verbatim in
    # `normalized` for these five -- never rewritten or generalized -- so
    # image_license always reflects exactly what Commons recorded.
    if _GFDL_MARKER in combined:
        result.update(normalized=license_short_name or license_full, status="reusable", reusable=True)
        return result

    if _COPYRIGHTED_FREE_USE_MARKER in combined:
        result.update(normalized=license_short_name or license_full, status="reusable", reusable=True)
        return result

    if _NO_RESTRICTIONS_MARKER in combined:
        result.update(normalized=license_short_name or license_full, status="reusable", reusable=True)
        return result

    if _LICENCE_OUVERTE_MARKER in combined:
        result.update(normalized=license_short_name or license_full, status="reusable", reusable=True)
        return result

    if _KOGL_MARKER in combined:
        result.update(normalized=license_short_name or license_full, status="reusable", reusable=True)
        return result

    if _OGL_V3_PATTERN.search(combined):
        result.update(normalized=license_short_name or license_full, status="reusable", reusable=True)
        return result

    if combined == _ATTRIBUTION_ONLY_EXACT:
        result.update(normalized=license_short_name or license_full, status="reusable", reusable=True)
        return result

    result.update(status="unclear", normalized=license_short_name or license_full)
    return result


def _plain_text(value: str | None) -> str | None:
    if not value:
        return None
    text = _TAG_PATTERN.sub(" ", value)
    text = html.unescape(text)
    text = _WHITESPACE_PATTERN.sub(" ", text).strip()
    return text or None


def normalize_attribution(extmetadata: dict[str, Any]) -> dict[str, Any]:
    """Extract a safe, human-readable attribution string from Commons
    extmetadata.

    Commons Artist/Credit/Attribution fields may contain HTML; this strips
    markup rather than rendering or executing it, and never fabricates
    attribution that Commons does not provide.
    """
    artist_raw = extmetadata.get("Artist")
    credit_raw = extmetadata.get("Credit")
    attribution_raw = extmetadata.get("Attribution")

    artist = _plain_text(artist_raw)
    credit = _plain_text(credit_raw)
    explicit_attribution = _plain_text(attribution_raw)

    if explicit_attribution:
        normalized = explicit_attribution
    elif artist and credit and artist != credit:
        normalized = f"{artist} ({credit})"
    elif artist:
        normalized = artist
    elif credit:
        normalized = credit
    else:
        normalized = None

    had_html = bool(
        (artist_raw and artist_raw != artist)
        or (credit_raw and credit_raw != credit)
        or (attribution_raw and attribution_raw != explicit_attribution)
    )

    return {
        "normalized": normalized,
        "artist": artist,
        "credit": credit,
        "had_html": had_html,
    }


def validate_media_type(
    mime: str | None,
    has_browser_thumbnail: bool = False,
) -> dict[str, Any]:
    """Classify Commons-reported MIME type for browser-display suitability.

    status is one of: "supported", "unsupported_image", "non_image",
    "unknown". A file whose original media type is uncommon for direct
    browser display (e.g. TIFF) is still treated as "supported" when
    Commons has already rendered a browser-safe thumbnail derivative
    (iiurlwidth) — the thumbnail is what actually gets served/persisted,
    not the raw original, so the original format alone is not a reason
    to withhold an otherwise-valid image.
    """
    if not mime:
        return {"is_image": False, "status": "unknown", "mime": mime}
    if mime in SUPPORTED_IMAGE_MIME_TYPES:
        return {"is_image": True, "status": "supported", "mime": mime}
    if mime.startswith("image/"):
        if has_browser_thumbnail:
            return {
                "is_image": True,
                "status": "supported",
                "mime": mime,
                "via_thumbnail": True,
            }
        return {"is_image": True, "status": "unsupported_image", "mime": mime}
    return {"is_image": False, "status": "non_image", "mime": mime}


def decide_commons_validation(
    *,
    identity_action: str | None,
    p18_filename: str | None,
    commons_lookup_status: str,
    file_info: dict[str, Any] | None,
    license_info: dict[str, Any] | None,
    attribution_info: dict[str, Any] | None,
    media_info: dict[str, Any] | None,
) -> dict[str, Any]:
    """Produce an explainable ACCEPT / REVIEW / SKIP decision for a
    Commons-hosted candidate image.

    Conservative by design: ACCEPT requires an already-accepted identity
    match, a resolvable Commons file, a usable image URL, a known
    canonical source, a clearly reusable license, and (when required)
    extractable attribution.
    """
    reasons: list[str] = []
    warnings: list[str] = []
    skip_reasons: list[str] = []
    review_reasons: list[str] = []

    if identity_action != "ACCEPT":
        skip_reasons.append(
            f"Wikidata identity decision was {identity_action!r}, not ACCEPT"
        )
    if not p18_filename:
        skip_reasons.append("no P18 (image) filename on the Wikidata entity")
    if commons_lookup_status == "error":
        skip_reasons.append("Commons lookup failed (network/transport error)")
    elif commons_lookup_status == "missing":
        skip_reasons.append("P18 filename does not resolve on Commons")

    if skip_reasons:
        return {
            "decision": "SKIP",
            "copyright_decision": "SKIP",
            "non_copyright_restrictions": [],
            "reasons": reasons,
            "warnings": warnings,
            "skip_reasons": skip_reasons,
            "review_reasons": review_reasons,
        }

    assert file_info is not None
    assert license_info is not None
    assert attribution_info is not None
    assert media_info is not None

    if media_info["status"] == "non_image":
        skip_reasons.append(f"media type is not an image ({media_info['mime']})")
    elif media_info["status"] == "unknown":
        review_reasons.append("media/MIME type could not be determined")
    elif media_info["status"] == "unsupported_image":
        review_reasons.append(
            f"image format is uncommon for browser display ({media_info['mime']})"
        )
    else:
        reasons.append(f"media type is a supported image ({media_info['mime']})")

    if not file_info.get("canonical_source_url"):
        skip_reasons.append("no canonical Commons source page available")
    else:
        reasons.append("canonical Commons source page resolved")

    image_url = file_info.get("thumbnail_url") or file_info.get("image_url")
    if not image_url:
        review_reasons.append("no browser-displayable image URL available")
    else:
        reasons.append("browser-displayable image URL resolved")

    if license_info["status"] == "reusable":
        reasons.append(f"license is clearly reusable ({license_info['normalized']})")
    elif license_info["status"] == "restrictive":
        skip_reasons.append(
            "license is clearly restrictive "
            f"({license_info.get('normalized') or license_info.get('raw_license_short_name')})"
        )
    elif license_info["status"] == "missing":
        review_reasons.append("no license metadata found on Commons file")
    else:
        review_reasons.append(
            "license metadata is unclear "
            f"({license_info.get('raw_license_short_name') or license_info.get('raw_license')})"
        )

    attribution_required = (file_info.get("extmetadata") or {}).get(
        "AttributionRequired"
    )
    requires_attribution = (
        license_info["status"] == "reusable"
        and license_info["normalized"] not in ("CC0", "Public Domain")
    ) or (
        bool(attribution_required)
        and _clean_license_text(attribution_required) == "true"
    )

    if requires_attribution and not attribution_info.get("normalized"):
        review_reasons.append(
            "license appears to require attribution, but none could be extracted"
        )
    elif attribution_info.get("normalized"):
        reasons.append("attribution/credit information available")
    else:
        warnings.append("no attribution/credit information available on Commons")

    # Snapshot the decision on copyright/reuse grounds alone -- media
    # format, source page, license, and attribution -- before the
    # non-copyright Commons "Restrictions" field is considered at all.
    if skip_reasons:
        copyright_decision = "SKIP"
    elif review_reasons:
        copyright_decision = "REVIEW"
    else:
        copyright_decision = "ACCEPT"

    # Phase 7.5I-C / 7.5N: Commons' "Restrictions" field is a non-copyright
    # notice (personality/trademark/etc.), structurally distinct from the
    # License/UsageTerms fields already evaluated above. A restriction
    # list that is *exactly* one of these single, named values -- and
    # only when the copyright side has independently reached ACCEPT --
    # is recorded and reported but does not by itself force REVIEW.
    # Anything else (insignia, an unrecognized restriction, either of
    # these combined with any other restriction -- e.g. the Red Cross/
    # IFRC "ihl|trademarked|insignia" case) continues through the prior,
    # more conservative behavior unchanged and still forces REVIEW.
    _EXEMPT_SOLO_RESTRICTIONS = ("personality", "trademarked")
    restrictions_raw = (file_info.get("extmetadata") or {}).get("Restrictions")
    parsed_restrictions = parse_restrictions(restrictions_raw)
    non_copyright_restrictions: list[str] = []

    if parsed_restrictions:
        if (
            len(parsed_restrictions) == 1
            and parsed_restrictions[0] in _EXEMPT_SOLO_RESTRICTIONS
            and copyright_decision == "ACCEPT"
        ):
            non_copyright_restrictions = parsed_restrictions
            warnings.append(
                f"Commons reports additional restrictions: {restrictions_raw} "
                f"({parsed_restrictions[0]}-only, copyright license independently "
                "reusable -- not treated as a copyright/reuse blocker)"
            )
        else:
            warnings.append(f"Commons reports additional restrictions: {restrictions_raw}")
            review_reasons.append("Commons file has additional recorded restrictions")

    if skip_reasons:
        decision = "SKIP"
    elif review_reasons:
        decision = "REVIEW"
    else:
        decision = "ACCEPT"

    return {
        "decision": decision,
        "copyright_decision": copyright_decision,
        "non_copyright_restrictions": non_copyright_restrictions,
        "reasons": reasons,
        "warnings": warnings,
        "skip_reasons": skip_reasons,
        "review_reasons": review_reasons,
    }


def _year(value: str | date | None) -> int | None:
    if isinstance(value, date):
        return value.year
    if isinstance(value, str) and len(value) >= 4:
        try:
            return int(value[:4])
        except ValueError:
            return None
    return None


def validate_person_candidate(
    laureate: dict[str, Any],
    candidate: dict[str, Any]
) -> list[str]:
    conflicts = []
    if HUMAN_QID not in candidate.get("instance_of_ids", []):
        conflicts.append("candidate is not identified as a human")

    source_birth_date = laureate.get("birth_date")
    candidate_birth_date = candidate.get("birth_date")
    if source_birth_date and candidate_birth_date:
        source_year = _year(source_birth_date)
        candidate_year = _year(candidate_birth_date)
        if source_year and candidate_year and source_year != candidate_year:
            conflicts.append(
                "birth year conflicts "
                f"({source_year} != {candidate_year})"
            )
    return conflicts


def validate_organization_candidate(
    laureate: dict[str, Any],
    candidate: dict[str, Any]
) -> list[str]:
    if HUMAN_QID in candidate.get("instance_of_ids", []):
        return ["organization candidate is identified as a human"]
    return []
