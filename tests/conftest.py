from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from loqusdbapi.main import app, database

### Fixtures used in test_main ###


@pytest.fixture
def mock_db(case_payload):
    """Return a fake database adapter with default behavior."""

    db = Mock()

    db.cases.return_value = []
    db.case.return_value = case_payload
    db.add_case.return_value = None
    db.profile_variants.return_value = [
        {
            "_id": "7_124491972_C_A",
            "chrom": "7",
            "pos": 124491972,
            "ref": "C",
            "alt": "A",
        }
    ]

    return db


@pytest.fixture
def client(mock_db):
    """Return a FastAPI test client."""

    def get_db():
        return mock_db

    app.dependency_overrides[database] = get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def nr_cases_value() -> int:
    return 42


@pytest.fixture
def variant_payload() -> dict[str, Any]:
    """Return a minimal valid Variant payload for API tests."""
    return {
        "_id": "1_100_A_C",
        "chrom": "1",
        "observations": 1,
        "start": 100,
        "end": 200,
        "ref": "A",
        "alt": "C",
        "homozygote": 0,
        "hemizygote": 0,
    }


@pytest.fixture
def sv_payload() -> dict[str, Any]:
    """Minimal valid StructuralVariant payload."""
    return {
        "_id": "sv1",
        "chrom": "1",
        "end_chrom": "1",
        "sv_type": "DEL",
        "pos": 100,
        "end": 200,
        "observations": 1,
        "end_left": 100,
        "end_right": 200,
        "end_sum": 300,
        "length": 100,
        "pos_left": 100,
        "pos_right": 200,
        "pos_sum": 300,
    }


@pytest.fixture
def case_payload() -> dict[str, Any]:
    """Minimal valid Case payload matching the Pydantic model."""

    return {
        "_id": "mongo_id_123",
        "case_id": "case123",
        "profile_path": None,
        "vcf_path": None,
        "vcf_sv_path": None,
        "nr_variants": 0,
        "nr_sv_variants": 0,
        "individuals": [],
        "sv_individuals": [],
        "_inds": {},
        "_sv_inds": {},
    }


@pytest.fixture
def case_object() -> dict:
    return {
        "case_id": "case123",
        "nr_variants": 10,
        "nr_sv_variants": 2,
    }


### Fixtures used in test_utils ###


@pytest.fixture
def vcf_path() -> str:
    """Path to test VCF fixture used for VCF extraction in tests."""
    return "tests/fixtures/test.vcf.gz"


@pytest.fixture
def sv_vcf_path() -> str:
    """Path to test VCF fixture used for VCF extraction in tests."""
    return "tests/fixtures/test.SV.vcf.gz"


@pytest.fixture
def profiles_vcf_path() -> str:
    """Path to test VCF fixture used for profile extraction tests."""
    return "tests/fixtures/profile_snv.vcf.gz"


@pytest.fixture
def fake_compare_profiles():
    """Return a function that simulates a low similarity profile comparison."""

    def compare(profile1, profile2):
        return 0.2

    return compare
