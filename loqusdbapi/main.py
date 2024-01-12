"""

Small loqusdb api

"""
import logging
import loqusdb
from pathlib import Path
from typing import Optional, List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from mongo_adapter import get_client
from mongo_adapter.exceptions import Error as DB_Error
from starlette.responses import JSONResponse

from loqusdb.plugins.mongo.adapter import MongoAdapter
from loqusdb.utils.delete import delete
from loqusdbapi.exceptions import LoqusdbAPIError
from loqusdbapi.models import Case, Variant, StructuralVariant, Cases
from loqusdbapi.settings import settings
from loqusdbapi.utils import build_case_object, insert_case_variants

LOG = logging.getLogger("__name__")

app = FastAPI()


def database(uri: str = None, db_name: str = None) -> MongoAdapter:
    uri = uri or settings.uri
    db_name = db_name or settings.db_name
    try:
        client = get_client(
            uri=uri,
        )
    except DB_Error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not connect to database"
        )

    return MongoAdapter(client, db_name=db_name)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to the loqusdbapi",
        "loqusdb_version": loqusdb.__version__,
    }

def set_chromosome(chrom: Optional[str]) -> Optional[str]:
    """Getting right MT chromosome, according to the query and the genome build used in the app."""
    if settings.genome_build == "GRCh38" and chrom == "MT":
        return "M"
    return chrom

@app.get("/variants/{variant_id}", response_model=Variant)
def read_variant(variant_id: str, db: MongoAdapter = Depends(database)):
    variant_coordinates : List[str] = variant_id.split("_")
    variant_coordinates[0] : str = set_chromosome(variant_coordinates[0])
    variant = db.get_variant({"_id": "_".join(variant_coordinates)})
    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Variant {variant_id} not found"
        )
    variant["total"] = db.nr_cases(snv_cases=True, sv_cases=False)
    return variant


@app.get("/svs/", response_model=StructuralVariant)
def read_sv(
    chrom: str,
    pos: int,
    end: int,
    sv_type: str,
    db: MongoAdapter = Depends(database),
    end_chrom: str = None,
):
    structural_variant = db.get_structural_variant(
        {
            "chrom": set_chromosome(chrom),
            "end_chrom": set_chromosome(end_chrom) or set_chromosome(chrom),
            "sv_type": sv_type,
            "pos": pos,
            "end": end,
        }
    )
    if not structural_variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    structural_variant["total"] = db.nr_cases(snv_cases=False, sv_cases=True)

    return structural_variant


@app.get("/cases", response_model=Cases)
def read_cases(db: MongoAdapter = Depends(database)):
    """Return counts of SNV and SV variants in database"""
    nr_cases_snvs = db.nr_cases(snv_cases=True, sv_cases=False)
    nr_cases_svs = db.nr_cases(snv_cases=False, sv_cases=True)

    return dict(
        nr_cases_snvs=nr_cases_snvs,
        nr_cases_svs=nr_cases_svs,
    )


@app.get("/cases/{case_id}", response_model=Case)
def read_case(case_id: str, db: MongoAdapter = Depends(database)):
    """Return a specific case given petname ID"""
    case = db.case({"case_id": case_id})
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} not found"
        )
    return JSONResponse(jsonable_encoder(Case(**case)), status_code=status.HTTP_200_OK)


@app.delete("/cases/{case_id}")
def delete_case(case_id: str, db: MongoAdapter = Depends(database)):
    """Delete a specific case given petname ID"""
    existing_case = db.case({"case_id": case_id})
    if not existing_case:
        return JSONResponse(f"Case {case_id} does not exist", status_code=status.HTTP_404_NOT_FOUND)
    try:
        delete(adapter=db, case_obj=existing_case, genome_build=settings.genome_build)
        return JSONResponse(f"Case {case_id} had been deleted", status_code=status.HTTP_200_OK)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error {e.__class__.__name__}: {e}; Case may be partially deleted",
        )


@app.post("/cases/{case_id}", response_model=Case)
def load_case(
    case_id: str,
    snv_file: str,
    profile_file: str,
    sv_file: Optional[str] = None,
    db: MongoAdapter = Depends(database),
):
    """Upload a case to loqusdb"""
    if db.case({"case_id": case_id}):
        return JSONResponse(f"Case {case_id} already exists", status_code=status.HTTP_409_CONFLICT)

    if (
        (sv_file and not Path(sv_file).exists())
        or not Path(snv_file).exists()
        or not Path(profile_file).exists()
    ):
        raise HTTPException(
            detail="Input file path does not exist",
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
        )

    try:
        case_object: Case = build_case_object(
            case_id=case_id,
            vcf_path=snv_file,
            vcf_sv_path=sv_file,
            profile_path=profile_file,
            adapter=db,
        )
        insert_case_variants(adapter=db, case_obj=case_object)
        return JSONResponse(jsonable_encoder(case_object), status_code=status.HTTP_200_OK)
    except LoqusdbAPIError as e:
        LOG.error(e)
        raise HTTPException(
            detail=f"Exception {e.__class__.__name__}: {e.message}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        LOG.error(e)
        raise HTTPException(
            detail=f"Exception {e.__class__.__name__} {e}",
            status_code=status.HTTP_400_BAD_REQUEST,
        )
