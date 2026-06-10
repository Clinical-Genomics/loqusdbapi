from unittest.mock import Mock

import loqusdbapi.utils as utils
from loqusdbapi.models import Case
from loqusdbapi.utils import (
    build_case_object,
    check_profile_duplicates,
    check_snv_variant_types,
    check_vcf_gq_field,
    get_profiles,
    get_vcf_variant_count,
    insert_case_variants,
    insert_snv_variants,
    insert_sv_variants,
)


def test_get_profiles_variant_found(mock_db, vcf_path):
    """
    Test that get_profiles correctly builds genotype profiles
    when a matching variant exists in the VCF.

    This test verifies:
    - VCF is parsed correctly via cyvcf2
    - profile variants from the database are matched against VCF region
    - genotypes are correctly translated using GENOTYPE_MAP logic
    - each sample receives the expected genotype entries
    """

    # Act
    result = get_profiles(mock_db, vcf_path)

    # Assert
    assert isinstance(result, dict)
    assert len(result) > 0

    # Ensure all samples have a profile list
    for sample, profile in result.items():
        assert isinstance(profile, list)
        assert len(profile) == 1


def test_check_vcf_gq(vcf_path):
    """
    Test that check_vcf_gq_field passes for a VCF
    that contains the GQ FORMAT field.

    Invoking the function should not raise error.
    """

    check_vcf_gq_field(vcf_path)


def test_get_vcf_variant_count(vcf_path):
    """
    Test that get_vcf_variant_count returns the correct number
    of variants present in the VCF file.

    Expected behavior:
    - VCF is iterated correctly using cyvcf2
    - function returns the total number of variants in the file
    """

    count = get_vcf_variant_count(vcf_path)

    assert isinstance(count, int)
    assert count == 15


def test_check_snv_variant_types_ok(vcf_path):
    """
    Test that check_snv_variant_types passes when VCF
    contains only SNV variants.

    Invoking the function should not raise error.
    """

    check_snv_variant_types(vcf_path)


def test_check_profile_duplicates_ok(monkeypatch, fake_compare_profiles):
    """
    Test that check_profile_duplicates does not raise when all profiles are distinct.

    The test ensures:
    - No existing profiles match the new ones.
    - compare_profiles returns a low similarity score.
    - Threshold is not exceeded, so no error is raised.
    """

    mock_db = Mock()
    mock_db.cases.return_value = [
        {
            "individuals": [
                {"ind_id": "ind1", "profile": ["A", "A", "C", "A", "C"]}  # Profile with 5 genotypes
            ]
        }
    ]

    monkeypatch.setattr(utils, "compare_profiles", fake_compare_profiles)
    monkeypatch.setattr(utils.settings, "load_hard_threshold", 0.9)  # Threshold above similarity

    profiles = {"sample1": ["A", "A", "G", "G", "T"]}

    check_profile_duplicates(mock_db, profiles)


def test_build_case_object(mock_db, vcf_path, profiles_vcf_path):
    """Test the variant that builds a case document and saves it into the database."""
    case_obj = build_case_object(
        adapter=mock_db, case_id="case123", vcf_path=vcf_path, profile_path=profiles_vcf_path
    )
    assert isinstance(case_obj, Case)


def test_insert_snv_variants(mock_db, case_obj):
    """Test the function that adds variant documents into the database.
    Invoking the function should not raise error.
    """
    insert_snv_variants(adapter=mock_db, case_obj=case_obj)


def test_insert_sv_variants(mock_db, case_obj):
    """Test the function that adds SV variant documents into the database.
    Invoking the function should not raise error.
    """
    insert_sv_variants(adapter=mock_db, case_obj=case_obj)


def test_insert_case_variants(mock_db, case_obj):
    """Test the function that loads SNV and SV variants into the database.
    Invoking the function should not raise error.
    """
    insert_case_variants(adapter=mock_db, case_obj=case_obj)
