from ETL.image_enrichment.license_policy_audit import (
    classify_image_suitability,
    classify_license_family,
    extract_additional_restrictions,
    is_normalization_candidate,
)


def extmetadata(**overrides):
    base = {
        "License": None,
        "LicenseShortName": None,
        "LicenseUrl": None,
        "UsageTerms": None,
        "AttributionRequired": None,
        "Attribution": None,
        "Artist": None,
        "Credit": None,
        "Copyrighted": None,
        "Restrictions": None,
        "ImageDescription": None,
    }
    base.update(overrides)
    return base


# 1. Recognized families classify correctly.
def test_cc0_family():
    assert classify_license_family(extmetadata(LicenseShortName="CC0 1.0"))["family"] == "CC0"


def test_cc_by_sa_family():
    result = classify_license_family(extmetadata(LicenseShortName="CC BY-SA 3.0"))
    assert result["family"] == "CC BY-SA"


def test_cc_by_family_not_confused_with_by_sa():
    result = classify_license_family(extmetadata(LicenseShortName="CC BY 4.0"))
    assert result["family"] == "CC BY"


def test_public_domain_from_copyrighted_false():
    result = classify_license_family(extmetadata(Copyrighted="False"))
    assert result["family"] == "Public Domain"


def test_missing_license_family():
    assert classify_license_family(extmetadata())["family"] == "Missing"


def test_restrictive_family():
    result = classify_license_family(extmetadata(LicenseShortName="CC BY-NC 2.0"))
    assert result["family"] == "Restrictive (non-free)"


# 2. Gaps in the *current* validator that this audit is meant to surface.
def test_gfdl_is_its_own_family_not_unclear():
    result = classify_license_family(extmetadata(LicenseShortName="GFDL 1.2"))
    assert result["family"] == "GFDL"


def test_gfdl_and_cc_by_sa_is_dual_license_family():
    result = classify_license_family(
        extmetadata(LicenseShortName="GFDL 1.2, CC BY-SA 3.0")
    )
    assert result["family"] == "CC + GFDL dual-license"


def test_copyrighted_free_use_is_its_own_family():
    result = classify_license_family(extmetadata(LicenseShortName="Copyrighted free use"))
    assert result["family"] == "Copyrighted free use"


def test_no_restrictions_is_its_own_family():
    result = classify_license_family(extmetadata(LicenseShortName="No restrictions"))
    assert result["family"] == "No restrictions"


def test_licence_ouverte_is_its_own_family():
    result = classify_license_family(extmetadata(LicenseShortName="Licence Ouverte"))
    assert result["family"] == "Licence Ouverte (French Open License)"


def test_bare_attribution_is_flagged_ambiguous_not_guessed():
    result = classify_license_family(extmetadata(LicenseShortName="Attribution"))
    assert result["family"] == "Attribution-only"


def test_license_url_recovers_by_sa_version_when_short_name_is_generic():
    result = classify_license_family(
        extmetadata(
            LicenseShortName="Attribution-Share Alike",
            LicenseUrl="https://creativecommons.org/licenses/by-sa/2.5/deed.en",
        )
    )
    assert result["family"] == "CC BY-SA"
    assert "2.5" in result["basis"]


# 3. Additional restrictions are captured separately from license family
# -- never merged into the copyright decision (section 4).
def test_restrictions_are_extracted_independently_of_license():
    meta = extmetadata(LicenseShortName="CC BY-SA 4.0", Restrictions="personality")
    family = classify_license_family(meta)
    restrictions = extract_additional_restrictions(meta)

    assert family["family"] == "CC BY-SA"
    assert restrictions == ["personality"]


def test_multiple_restrictions_are_split():
    restrictions = extract_additional_restrictions(extmetadata(Restrictions="trademark|insignia"))
    assert restrictions == ["trademark", "insignia"]


def test_no_restrictions_field_is_empty_list():
    assert extract_additional_restrictions(extmetadata()) == []


# 4. Normalization-candidate flagging never implies acceptance.
def test_gfdl_unclear_in_current_validator_is_flagged_as_normalization_candidate():
    assert is_normalization_candidate("GFDL", "unclear") is True


def test_restrictive_family_is_never_a_normalization_candidate():
    assert is_normalization_candidate("Restrictive (non-free)", "unclear") is False


def test_already_recognized_family_is_not_flagged_again():
    # CC BY-SA is already recognized by the current validator (status
    # would be "reusable", not "unclear"/"missing"), so it shouldn't be
    # double-counted as a normalization gap.
    assert is_normalization_candidate("CC BY-SA", "reusable") is False


# 5. Image suitability classification (section 6).
def test_chemical_diagram_is_not_a_portrait():
    result = classify_image_suitability("Person", "18-crown-6-potassium.png", "Crown ether coordinating a potassium ion")
    assert result["suitability"] == "NON_PORTRAIT"


def test_signature_file_is_not_a_portrait():
    result = classify_image_suitability("Person", "Autograph of Rayleigh.png", None)
    assert result["suitability"] == "NON_PORTRAIT"


def test_named_portrait_photo_is_portrait():
    result = classify_image_suitability("Person", "John_Gurdon_Cambridge_2012.JPG", "Portrait photograph")
    assert result["suitability"] == "PORTRAIT"


def test_organization_logo_is_organization_visual():
    result = classify_image_suitability("Organization", "Artboard_3_copy_2@3x-8_(1).png", "American Friends Service Committee logo")
    assert result["suitability"] == "ORGANIZATION_VISUAL"


def test_ambiguous_case_is_uncertain_not_guessed():
    result = classify_image_suitability("Person", "IMG_0001.jpg", None)
    assert result["suitability"] == "UNCERTAIN"


# 6. Regression: a real portrait's caption naming the subject's
# university affiliation must not be misread as "this image is a
# building." Institution-name words are only meaningful in the filename
# itself, never in free-text description/caption content.
def test_university_affiliation_in_caption_does_not_reject_a_portrait():
    result = classify_image_suitability(
        "Person",
        "Akira Yoshino 20170920 (cropped 2).jpg",
        "Akira Yoshino, Professor of the Graduate School of Science and "
        "Technology, Meijo University, received the Order of Culture.",
    )
    assert result["suitability"] != "NON_PORTRAIT"


def test_building_word_in_filename_itself_is_still_flagged():
    result = classify_image_suitability("Person", "Harvard_University_campus.jpg", None)
    assert result["suitability"] == "NON_PORTRAIT"
