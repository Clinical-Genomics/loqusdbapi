"""

Small loqusdb api

"""
import logging
from pathlib import Path
from typing import List, Optional

from bson import json_util
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from mongo_adapter import get_client
from mongo_adapter.exceptions import Error as DB_Error
from pydantic import BaseModel, BaseSettings
from starlette.responses import JSONResponse
from starlette.background import BackgroundTasks

from loqusdb.plugins.mongo.adapter import MongoAdapter
from loqusdb.utils.delete import delete as delete_command
from loqusdbapi.exceptions import LoqusdbAPIError
from loqusdbapi.models import Case, Variant, StructuralVariant, Cases
from loqusdbapi.settings import settings
from loqusdbapi.utils import build_case_object, load_case_variants

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
    }


@app.get("/variants/{variant_id}", response_model=Variant)
def read_variant(variant_id: str, db: MongoAdapter = Depends(database)):
    variant = db.get_variant({"_id": variant_id})
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
            "chrom": chrom,
            "end_chrom": end_chrom or chrom,
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
    nr_cases_snvs = db.nr_cases(snv_cases=True, sv_cases=False)
    nr_cases_svs = db.nr_cases(snv_cases=False, sv_cases=True)

    return dict(
        nr_cases_snvs=nr_cases_snvs,
        nr_cases_svs=nr_cases_svs,
    )


@app.get("/cases/{case_id}", response_model=Case)
def read_case(case_id: str, db: MongoAdapter = Depends(database)):
    case = db.case({"case_id": case_id})
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} not found"
        )
    return JSONResponse(jsonable_encoder(Case(**case)), status_code=status.HTTP_200_OK)


@app.delete("/cases/{case_id}")
async def delete_case(
    background_tasks: BackgroundTasks, case_id: str, db: MongoAdapter = Depends(database)
):
    existing_case = db.case({"case_id": case_id})
    if not existing_case:
        return JSONResponse(f"Case {case_id} does not exist", status_code=status.HTTP_404_NOT_FOUND)
    background_tasks.add_task(
        delete_command, adapter=db, case_obj=existing_case, genome_build=settings.genome_build
    )
    return JSONResponse(f"Case {case_id} will be deleted", status_code=status.HTTP_202_ACCEPTED)


@app.post("/cases/{case_id}")
def load_case(
    background_tasks: BackgroundTasks,
    case_id: str,
    snv_file: str,
    profile_file: str,
    sv_file: Optional[str] = None,
    db: MongoAdapter = Depends(database),
):
    if db.case({"case_id": case_id}):
        return JSONResponse(f"Case {case_id} already exists", status_code=status.HTTP_409_CONFLICT)

    if (
        (sv_file and not Path(sv_file).exists())
        or not Path(snv_file).exists()
        or not Path(profile_file).exists()
    ):
        return JSONResponse(
            "Input file path does not exist",
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
        )

    try:
        case_result: dict = build_case_object(
            case_id=case_id,
            vcf_path=snv_file,
            vcf_sv_path=sv_file,
            profile_path=profile_file,
            adapter=db,
        )
    except LoqusdbAPIError as e:
        return JSONResponse(
            f"LoqusdbAPIError: {e.message}",
            status_code=status.HTTP_406_NOT_ACCEPTABLE,
        )

    print(f"Created {case_result}")
    load_case_variants(adapter=db, case_obj=case_result)
    return JSONResponse(jsonable_encoder(Case(**case_result)), status_code=status.HTTP_202_ACCEPTED)
