from pathlib import Path
from typing import Optional, List, Union

from bson import ObjectId
from pydantic import BaseModel, validator, ValidationError, Field


class Individual(BaseModel):
    ind_id: str
    case_id: str
    mother: Optional[str]
    father: Optional[str]
    sex: Optional[str]
    phenotype: Optional[str]
    ind_index: Optional[int]
    profile: Optional[list] = []
    similar_samples: Optional[list] = []


class Case(BaseModel):
    id: Optional[Union[ObjectId, str]] = Field(alias="_id")
    case_id: str
    profile_path: Optional[Union[Path, str]]
    vcf_path: Optional[Union[Path, str]]
    vcf_sv_path: Optional[Union[Path, str]]
    nr_variants: Optional[int] = 0
    nr_sv_variants: Optional[int] = 0
    individuals: Optional[List[Individual]] = []
    sv_individuals: Optional[list] = []
    inds: Optional[dict] = Field(alias="_inds", default={})
    sv_inds: Optional[dict] = Field(alias="_sv_inds", default={})

    class Config:
        arbitrary_types_allowed = True

    @validator("vcf_path", "profile_path", "vcf_sv_path")
    def validate_path_exists(cls, value):
        if not value:
            return
        if Path(value).exists():
            return Path(value).absolute().as_posix()
        return value

    @validator("id")
    def id_to_str(cls, value):
        if value:
            return str(value)


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
