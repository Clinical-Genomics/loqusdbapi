from pathlib import Path
from typing import Optional, List

from pydantic import BaseModel, validator, ValidationError


class Case(BaseModel):
    case_id: str
    profile_path: Path
    vcf_path: Optional[Path]
    vcf_sv_path: Optional[Path]
    nr_variants: Optional[int] = 0
    nr_sv_variants: Optional[int] = 0
    individuals: Optional[list] = []
    sv_individuals: Optional[list] = []
    _inds: Optional[dict] = {}
    _sv_inds: Optional[dict] = {}

    @validator("vcf_path", "profile_path", "vcf_sv_path")
    def validate_path_exists(cls, value):
        if not value:
            return
        if Path(value).exists():
            return Path(value).absolute()
        raise ValidationError

    @property
    def sv_inds(self):
        return self._sv_inds


class Individual(BaseModel):
    ind_id: str
    case_id: str
    mother: Optional[str]
    father: Optional[str]
    sex: Optional[str]
    phenotype: Optional[str]
    ind_index: Optional[int]
    profile: Optional[dict] = {}
    similar_samples: Optional[list] = []


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