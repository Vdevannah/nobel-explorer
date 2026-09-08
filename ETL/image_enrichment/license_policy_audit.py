from __future__ import annotations

import re
from typing import Any

from ETL.image_enrichment.validation import parse_restrictions


# Section 3: explicit license-family taxonomy. Order matters -- most
# specific/unambiguous patterns are checked first. This module only
# classifies; it never decides ACCEPT/REVIEW/SKIP. It reads (never
# modifies) shared parsing from ETL.image_enrichment.validation so its
# view of the data can't drift from what the real validator sees.
_CC0_MARKERS = ("cc0", "public domain dedication")
_GFDL_MARKER = "gfdl"
_CC_BY_SA_PATTERN = re.compile(r"cc[\s-]?by[\s-]?sa[\s-]?(\d+(?:\.\d+)?)?", re.IGNORECASE)
_CC_BY_PATTERN = re.compile(r"cc[\s-]?by[\s-]?(\d+(?:\.\d+)?)?(?![\s-]?sa)", re.IGNORECASE)
_PUBLIC_DOMAIN_MARKERS = ("public domain", "pd-old", "pd old", "pd-us", "pd us")
_COPYRIGHTED_FREE_USE_MARKER = "copyrighted free use"
_NO_RESTRICTIONS_MARKER = "no restrictions"
_LICENCE_OUVERTE_MARKERS = ("licence ouverte", "open licence", "etalab")
_KOGL_MARKER = "kogl"
_FAL_MARKERS = ("fal", "free art license", "licence art libre")
_RESTRICTIVE_MARKERS = (
    "noncommercial", "non commercial", "no derivative", "noderivative",
    "all rights reserved", "rights reserved", "fair use",
    "not for reuse", "not-for-reuse",
)
_RESTRICTIVE_CC_VARIANT_PATTERN = re.compile(
    r"\bby[\s-]?nc\b|\bby[\s-]?nd\b|\bnc[\s-]?sa\b|\bnc[\s-]?nd\b", re.IGNORECASE
)

_LICENSE_URL_BY_SA_PATTERN = re.compile(
    r"creativecommons\.org/licenses/by-sa/([\d.]+)", re.IGNORECASE
)
_LICENSE_URL_BY_PATTERN = re.compile(
    r"creativecommons\.org/licenses/by/([\d.]+)", re.IGNORECASE
)

# Families that represent a real, named, generally-reusable Commons
# license/tag but that the *current* production regexes in validation.py
# do not recognize (verified by inspecting validation.normalize_license).
# Flagging one of these does not mean "accept" -- only "worth a human
# normalization decision," per section 5.
_NORMALIZATION_CANDIDATE_FAMILIES = {
    "GFDL",
    "CC + GFDL dual-license",
    "Copyrighted free use",
    "No restrictions",
    "Licence Ouverte (French Open License)",
    "KOGL (Korea Open Government License)",
    "FAL (Free Art License)",
}


def _clean(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"[_/]+", " ", value).strip().lower()


def classify_license_family(extmetadata: dict[str, Any]) -> dict[str, Any]:
    """Classify the copyright-license side of a Commons file's
    extmetadata into an explicit family, independent of any other
    (non-copyright) restriction warnings. Returns the family label plus
    the raw fields it was derived from, for transparency.
    """
    license_short_name = extmetadata.get("LicenseShortName")
    license_full = extmetadata.get("License")
    usage_terms = extmetadata.get("UsageTerms")
    license_url = extmetadata.get("LicenseUrl") or ""
    copyrighted = extmetadata.get("Copyrighted")

    combined = " ".join(
        _clean(value)
        for value in (license_short_name, license_full, usage_terms)
        if value
    )
    is_public_domain_copyright = (
        copyrighted is not None and _clean(copyrighted) == "false"
    )

    if not combined and not license_url:
        if is_public_domain_copyright:
            return {"family": "Public Domain", "basis": "Copyrighted=false, no license text"}
        return {"family": "Missing", "basis": "no license/usage-terms/short-name present"}

    has_gfdl = _GFDL_MARKER in combined
    has_by_sa = bool(_CC_BY_SA_PATTERN.search(combined)) or bool(_LICENSE_URL_BY_SA_PATTERN.search(license_url))

    if (
        any(marker in combined for marker in _RESTRICTIVE_MARKERS)
        or _RESTRICTIVE_CC_VARIANT_PATTERN.search(combined)
    ):
        return {"family": "Restrictive (non-free)", "basis": f"matched restrictive marker in {combined!r}"}

    if any(marker in combined for marker in _CC0_MARKERS):
        return {"family": "CC0", "basis": f"matched CC0 marker in {combined!r}"}

    if has_gfdl and has_by_sa:
        return {"family": "CC + GFDL dual-license", "basis": f"GFDL + CC BY-SA both present in {combined!r}"}

    if has_gfdl:
        return {"family": "GFDL", "basis": f"matched 'gfdl' in {combined!r}"}

    if has_by_sa:
        version_match = _CC_BY_SA_PATTERN.search(combined)
        url_match = _LICENSE_URL_BY_SA_PATTERN.search(license_url)
        version = (version_match.group(1) if version_match else None) or (url_match.group(1) if url_match else None)
        return {
            "family": "CC BY-SA",
            "basis": f"matched CC BY-SA pattern (version={version!r}) in {combined!r} or LicenseUrl",
        }

    by_match = _CC_BY_PATTERN.search(combined)
    url_by_match = _LICENSE_URL_BY_PATTERN.search(license_url)
    if by_match or url_by_match:
        version = (by_match.group(1) if by_match else None) or (url_by_match.group(1) if url_by_match else None)
        return {
            "family": "CC BY",
            "basis": f"matched CC BY pattern (version={version!r}) in {combined!r} or LicenseUrl",
        }

    if any(marker in combined for marker in _PUBLIC_DOMAIN_MARKERS) or is_public_domain_copyright:
        return {"family": "Public Domain", "basis": f"matched public-domain marker in {combined!r}"}

    if _COPYRIGHTED_FREE_USE_MARKER in combined:
        return {"family": "Copyrighted free use", "basis": f"matched {_COPYRIGHTED_FREE_USE_MARKER!r} in {combined!r}"}

    if _NO_RESTRICTIONS_MARKER in combined:
        return {"family": "No restrictions", "basis": f"matched {_NO_RESTRICTIONS_MARKER!r} in {combined!r}"}

    if any(marker in combined for marker in _LICENCE_OUVERTE_MARKERS):
        return {"family": "Licence Ouverte (French Open License)", "basis": f"matched marker in {combined!r}"}

    if _KOGL_MARKER in combined:
        return {"family": "KOGL (Korea Open Government License)", "basis": f"matched 'kogl' in {combined!r}"}

    if any(marker in combined for marker in _FAL_MARKERS):
        return {"family": "FAL (Free Art License)", "basis": f"matched marker in {combined!r}"}

    if combined.strip() == "attribution":
        return {"family": "Attribution-only", "basis": "UsageTerms/LicenseShortName is bare 'Attribution' with no version/URL"}

    if not combined and license_url:
        return {"family": "Unclear/Other", "basis": f"no license text, only LicenseUrl={license_url!r}"}

    return {"family": "Unclear/Other", "basis": f"no recognized pattern in {combined!r}"}


def extract_additional_restrictions(extmetadata: dict[str, Any]) -> list[str]:
    """Extract non-copyright restriction warnings (Commons 'Restrictions'
    field) as a distinct list, deliberately never merged into the
    copyright-license family above (section 4).

    Delegates to validation.parse_restrictions -- the canonical,
    production-used parser (Phase 7.5I-C) -- so the audit's view of a
    file's restrictions can never silently diverge from what the real
    validator actually parses.
    """
    return parse_restrictions(extmetadata.get("Restrictions"))


def is_normalization_candidate(family: str, current_validator_status: str) -> bool:
    """True when the license family is a real, named, generally-reusable
    Commons license/tag that the *current* production validator does not
    yet recognize as reusable. Classification only -- never an
    acceptance decision (section 5).
    """
    return (
        family in _NORMALIZATION_CANDIDATE_FAMILIES
        and current_validator_status in ("unclear", "missing")
    )


# Section 6: best-effort, filename/description heuristic image-suitability
# classification. Never a substitute for looking at the actual pixels;
# ambiguous cases are UNCERTAIN, not guessed.
#
# Two tiers, deliberately kept separate:
#   - "subject" markers describe what the image visually *shows* --
#     these are checked against BOTH filename and description, since a
#     caption saying "chemical structure of ..." or "signature of ..."
#     is a reliable signal regardless of where it appears.
#   - "institution-name" markers (university/institute/building/campus)
#     are NOT reliable in description text: a real portrait's Commons
#     caption routinely names the subject's university or workplace
#     affiliation ("Professor at Meijo University") without the *image*
#     being of a building at all. These are only checked against the
#     filename itself, where such a word is far more likely to describe
#     the depicted subject (e.g. "Harvard_University_campus.jpg").
_NON_PORTRAIT_SUBJECT_MARKERS = (
    "signature", "autograph", "medal", "coat of arms", "seal of",
    "flag of", "locator", "map of", "orthographic", "diagram",
    "structure", "molecule", "spectrogram", "chart", "graph of",
    "equation", "chemical", "crown ether", "apparatus", "monument",
    "statue", "stamp", "banknote", "certificate", "document scan",
    "grave", "plaque", "book cover", "title page",
)
_NON_PORTRAIT_FILENAME_ONLY_MARKERS = (
    "logo", "symbol", "icon", "building", "university", "institute",
    "campus",
)
_ORGANIZATION_VISUAL_MARKERS = (
    "logo", "emblem", "flag of", "headquarters", "building", "seal of",
)


def classify_image_suitability(
    laureate_type: str,
    filename: str,
    description: str | None,
) -> dict[str, Any]:
    filename_lower = filename.lower()
    haystack = f"{filename_lower} {(description or '').lower()}"

    def matches_non_portrait() -> str | None:
        for marker in _NON_PORTRAIT_SUBJECT_MARKERS:
            if marker in haystack:
                return marker
        for marker in _NON_PORTRAIT_FILENAME_ONLY_MARKERS:
            if marker in filename_lower:
                return marker
        return None

    if laureate_type == "Organization":
        if any(marker in haystack for marker in _ORGANIZATION_VISUAL_MARKERS):
            return {"suitability": "ORGANIZATION_VISUAL", "basis": "matched organization-visual marker"}
        non_portrait_marker = matches_non_portrait()
        if non_portrait_marker:
            return {"suitability": "NON_PORTRAIT", "basis": f"matched {non_portrait_marker!r} despite organization type"}
        return {"suitability": "UNCERTAIN", "basis": "no confident marker match; needs visual check"}

    # Person
    non_portrait_marker = matches_non_portrait()
    if non_portrait_marker:
        return {"suitability": "NON_PORTRAIT", "basis": f"matched non-portrait subject marker {non_portrait_marker!r}"}
    if "portrait" in haystack or "photograph" in haystack or "headshot" in haystack:
        return {"suitability": "PORTRAIT", "basis": "matched explicit portrait/photograph marker"}
    return {"suitability": "UNCERTAIN", "basis": "no confident marker match; needs visual check"}
