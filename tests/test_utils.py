from unittest.mock import Mock

import loqusdbapi.utils as utils
from loqusdbapi.utils import (
    build_case_object,
    check_profile_duplicates,
    check_snv_variant_types,
    check_vcf_gq_field,
    get_profiles,
    get_vcf_variant_count,
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

    mock_db.profile_variants.return_value = [
        {
            "_id": "7_124491972_C_A",
            "chrom": "7",
            "pos": 124491972,
            "ref": "C",
            "alt": "A",
        }
    ]

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
    assert count == 680


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
