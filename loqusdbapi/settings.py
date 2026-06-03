from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    uri: Optional[str] = "mongodb://localhost:27017/loqusdb"
    db_name: Optional[str] = "loqusdb"
    genome_build: Optional[str] = "GRCh37"
    chr_prefix: Optional[str] = ""
    load_gq_threshold: Optional[int] = 20
    load_hard_threshold: Optional[float] = 0.95
    load_soft_threshold: Optional[float] = 0.95
    load_sv_window: Optional[int] = 2000
    cyvcf_threads: Optional[int] = 4


settings = Settings()
