"""

Small loqusdb api

"""

from typing import Optional, List

from fastapi import FastAPI, HTTPException, status, Depends
from pydantic import BaseModel, BaseSettings

from loqusdb.plugins.mongo import MongoAdapter
from mongo_adapter import get_client
from mongo_adapter.exceptions import Error as DB_Error


class Settings(BaseSettings):
    uri: str = "mongodb://localhost:27017/loqusdb"
    db_name: str = 'loqusdb'


settings = Settings()
app = FastAPI()


class BaseVariant(BaseModel):
    chrom: str
    observations: int
    families: List[str] = []
    nr_cases: int


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
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not connect to database")

    return MongoAdapter(client, db_name=db_name)


@app.get("/")
def read_root():
    return {"message": "Welcome to the loqusdbapi"}


@app.get("/variants/{variant_id}", response_model=Variant)
def read_variant(variant_id: str, db: MongoAdapter = Depends(database)):
    variant = db.get_variant({"_id": variant_id})
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Variant {variant_id} not found")
    variant["nr_cases"] = db.nr_cases(snv_cases=True, sv_cases=False)
    return variant


@app.get("/svs/", response_model=StructuralVariant)
def read_sv(chrom: str, pos: int, end: int, sv_type: str, db: MongoAdapter = Depends(database), end_chrom: str = None):
    structural_variant = db.get_structural_variant({
        'chrom': chrom,
        'end_chrom': end_chrom or chrom,
        'sv_type': sv_type,
        'pos': pos,
        'end': end
    })
    if not structural_variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found")
    structural_variant["nr_cases"] = db.nr_cases(snv_cases=False, sv_cases=True)

    return structural_variant


@app.get("/cases/{case_id}", response_model=Case)
def read_case(case_id: str, db: MongoAdapter = Depends(database)):
    case = db.case({"case_id": case_id})
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Case {case_id} not found")
    return case
