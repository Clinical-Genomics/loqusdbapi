from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from loqusdbapi.main import app, database


@pytest.fixture
def mock_db():
    """Return a fake database adapter."""
    return Mock()


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
