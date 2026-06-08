from typing import Any

from fastapi.testclient import TestClient

import loqusdbapi.main as main


def test_read_root(client: TestClient) -> None:
    """Test root endpoint."""

    response = client.get("/")

    assert response.status_code == 200

    body = response.json()

    assert body["message"] == "Welcome to the loqusdbapi"
    assert "loqusdb_version" in body


def test_read_variant_found(
    client: TestClient,
    mock_db: Any,
    variant_payload: dict,
    nr_cases_value: int,
) -> None:
    """Test successful retrieval of a variant."""

    mock_db.get_variant.return_value = variant_payload
    mock_db.nr_cases.return_value = nr_cases_value

    response = client.get("/variants/1_100_A_C")

    assert response.status_code == 200
    body = response.json()

    assert body["total"] == nr_cases_value
    assert body["chrom"] == "1"


def test_read_variant_not_found(client: TestClient, mock_db: Any) -> None:
    """Test 404 response when variant does not exist."""

    # DB returns nothing → triggers 404
    mock_db.get_variant.return_value = None

    response = client.get("/variants/1_100_A_C")

    assert response.status_code == 404

    body = response.json()
    assert body["detail"] == "Variant 1_100_A_C not found"


def test_read_sv_found(client: TestClient, mock_db: Any, sv_payload: dict) -> None:
    """Test successful retrieval of structural variant."""

    mock_db.get_structural_variant.return_value = sv_payload
    mock_db.nr_cases.return_value = 7

    response = client.get(
        "/svs/",
        params={
            "chrom": "1",
            "pos": 100,
            "end": 200,
            "sv_type": "DEL",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["chrom"] == "1"
    assert body["sv_type"] == "DEL"
    assert body["total"] == 7


def test_read_sv_not_found(client: TestClient, mock_db: Any) -> None:
    """Test 404 response when structural variant is not found."""

    mock_db.get_structural_variant.return_value = None

    response = client.get(
        "/svs/",
        params={
            "chrom": "1",
            "pos": 100,
            "end": 200,
            "sv_type": "DEL",
        },
    )

    assert response.status_code == 404

    body = response.json()
    assert body["detail"] == "Variant not found"


def test_read_cases(client: TestClient, mock_db: Any) -> None:
    """Test SNV and SV case counts are returned correctly."""

    mock_db.nr_cases.side_effect = [10, 5]

    response = client.get("/cases")

    assert response.status_code == 200

    body = response.json()

    assert body == {
        "nr_cases_snvs": 10,
        "nr_cases_svs": 5,
    }


def test_read_case_found(client: TestClient, mock_db: Any, case_payload: dict) -> None:
    """Test successful retrieval of a case."""

    mock_db.case.return_value = case_payload

    response = client.get("/cases/case123")

    assert response.status_code == 200

    body = response.json()

    assert body["case_id"] == "case123"


def test_read_case_not_found(client: TestClient, mock_db: Any) -> None:
    """Test 404 when case does not exist."""

    mock_db.case.return_value = None

    response = client.get("/cases/case123")

    assert response.status_code == 404
    assert response.json()["detail"] == "Case case123 not found"


def test_delete_case_not_found(client: TestClient, mock_db: Any) -> None:
    """Test deleting a case that does not exist returns 404."""

    mock_db.case.return_value = None

    response = client.delete("/cases/case123")

    assert response.status_code == 404
    assert response.json() == "Case case123 does not exist"


def test_delete_case_success(client, mock_db, monkeypatch):
    """Test successful deletion of a case."""

    mock_db.case.return_value = {"case_id": "case123"}

    def fake_delete(**kwargs):
        """Fake delete function."""
        return None

    monkeypatch.setattr(
        "loqusdbapi.main.delete",
        fake_delete,
    )

    response = client.delete("/cases/case123")

    assert response.status_code == 200
    assert response.json() == "Case case123 had been deleted"


def test_load_case_success(
    client: TestClient,
    mock_db: Any,
    monkeypatch,
    case_object: dict,
) -> None:
    """Test successful case load.
    Mocks file existence checks, case object construction, and variant insertion
    to isolate the endpoint from filesystem and database side effects.
    Verifies that a valid request returns the expected case data.
    """

    mock_db.case.return_value = None

    def fake_exists(self: object) -> bool:
        return True

    monkeypatch.setattr(main.Path, "exists", fake_exists)

    def fake_build_case_object(**kwargs: Any) -> dict:
        return case_object

    monkeypatch.setattr(main, "build_case_object", fake_build_case_object)

    def fake_insert_case_variants(**kwargs: Any) -> None:
        return None

    monkeypatch.setattr(main, "insert_case_variants", fake_insert_case_variants)

    response = client.post(
        "/cases/case123",
        params={
            "snv_file": "snvs.vcf",
            "profile_file": "profile.txt",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["case_id"] == "case123"
    assert body["nr_variants"] == 10
    assert body["nr_sv_variants"] == 2
