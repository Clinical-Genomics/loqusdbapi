"""

Small loqusdb api

"""

from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, status
from mongo_adapter import get_client
from mongo_adapter.exceptions import Error as DB_Error
from pydantic import BaseModel, BaseSettings
from starlette.responses import JSONResponse

import loqusdb
from loqusdb.plugins.mongo.adapter import MongoAdapter
from loqusdb.utils.delete import delete as delete_command


class Settings(BaseSettings):
    uri: Optional[str] = "mongodb://localhost:27017/loqusdb"
    db_name: Optional[str] = "loqusdb"
    genome_build: Optional[str] = "GRCh37"


settings = Settings()
app = FastAPI()


class BaseVariant(BaseModel):
    chrom: str
    observations: int
    families: List[str] = []
    total: int


class Variant(BaseVariant):
    _id: str
    start: int
    end: int
    ref: str
    alt: str
    homozygote: int
    hemizygote: int


class StructuralVariant(BaseVariant):
    end_chrom: str
    end_left: int
    end_right: int
    sv_type: str
    length: int
    pos_left: int
    pos_right: int


class Cases(BaseModel):
    nr_cases_snvs: Optional[int]
    nr_cases_svs: Optional[int]


class Case(BaseModel):
    case_id: str
    nr_variants: Optional[int]
    nr_sv_variants: Optional[int]


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
    return case


@app.delete("/cases/{case_id}")
def delete_case(case_id: str, db: MongoAdapter = Depends(database)):
    existing_case = db.case({"case_id": case_id})
    if not existing_case:
        return JSONResponse(f"Case {case_id} does not exist", status_code=404)
    delete_command(adapter=db, case_obj=existing_case, genome_build=settings.genome_build)
    return JSONResponse(f"Case {case_id} deleted", status_code=200)


@app.post("/cases/{case_id}")
async def load_case(
    case_id: str,
    snv_file: str,
    sv_file: Optional[str] = None,
    profile_file: Optional[str] = None,
    db: MongoAdapter = Depends(database),
):
    if db.case({"case_id": case_id}):
        return JSONResponse(f"Case {case_id} already exists", status_code=409)

    pass
