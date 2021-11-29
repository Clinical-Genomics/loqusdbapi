from pathlib import Path
from typing import List, Union

from cyvcf2 import VCF

from loqusdb.plugins.mongo.adapter import MongoAdapter
from loqusdb.utils.profiling import get_profiles, compare_profiles
from loqusdbapi.exceptions import VCFParserError, ProfileDuplicationError
from loqusdbapi.models import Case, Individual
from loqusdbapi.settings import settings


def parse_snv_vcf(vcf_path: Union[Path, str], case_object: Case) -> Case:
    snv_vcf = VCF(vcf_path, threads=settings.cyvcf_threads)
    if not snv_vcf.contains("GQ"):
        raise VCFParserError(f"GQ not found in {vcf_path}")
    snv_vcf_variant_count = 0
    snv_vcf_individuals = snv_vcf.samples
    snv_vcf_var_types = set()

    for variant in snv_vcf:
        snv_vcf_variant_count += 1
        snv_vcf_var_types.add(variant.var_type)

    if len(snv_vcf_var_types) != 1:
        raise VCFParserError(f"Variant types in {vcf_path}: {len(snv_vcf_var_types)}, required: 1")
    if "snv" not in snv_vcf_var_types:
        raise VCFParserError(f"Variant types in {vcf_path}: {snv_vcf_var_types}, required: snv")

    case_object.nr_variants = snv_vcf_variant_count
    case_object.individuals = snv_vcf_individuals
    case_object.vcf_path = vcf_path

    return case_object


def parse_sv_vcf(vcf_path: Union[Path, str], case_object: Case) -> Case:
    sv_vcf = VCF(vcf_path, threads=settings.cyvcf_threads)
    if not sv_vcf.contains("GQ"):
        raise VCFParserError(f"GQ not found in {vcf_path}")
    sv_vcf_variant_count = 0
    sv_vcf_individuals = sv_vcf.samples
    sv_vcf_var_types = set()

    for variant in sv_vcf:
        sv_vcf_variant_count += 1
        sv_vcf_var_types.add(variant.var_type)
    if len(sv_vcf_var_types) != 1:
        raise VCFParserError(f"Variant types in {vcf_path}: {len(sv_vcf_var_types)}, required: 1")

    if "sv" not in sv_vcf_var_types:
        raise VCFParserError(f"Variant types in {vcf_path}: {sv_vcf_var_types}, required: sv")
    case_object.nr_sv_variants = sv_vcf_variant_count
    case_object.sv_individuals = sv_vcf_individuals
    case_object.vcf_sv_path = vcf_path
    return case_object


def parse_profiles(adapter: MongoAdapter, case_object: Case) -> Case:

    profiles = get_profiles(adapter=adapter, vcf_file=case_object.profile_path)
    profile_vcf = VCF(case_object.profile_path, threads=settings.cyvcf_threads)
    samples: List[str] = profile_vcf.samples
    for sample_index, sample in enumerate(samples):
        individual = Individual(
            ind_id=sample,
            case_id=case_object.case_id,
            ind_index=sample_index,
            profile=profiles[sample],
        )
        if case_object.vcf_path:
            case_object.individuals.append(individual.dict())
            case_object.inds[sample] = individual.dict()
        if case_object.vcf_sv_path:
            case_object.sv_individuals.append(individual.dict())
            case_object.sv_inds[sample] = individual.dict()

    return case_object


def check_profile_duplicates(adapter: MongoAdapter, case_object: Case) -> Case:
    for case in adapter.cases():

        if case.get("individuals") is None:
            continue

        for individual in case["individuals"]:
            if not individual.get("profile"):
                continue

            for sample in case_object.individuals:
                similarity = compare_profiles(sample.profile, individual["profile"])
                if similarity >= settings.load_hard_threshold:
                    raise ProfileDuplicationError(
                        f"Profile of sample {sample.ind_id} "
                        f"matches existing profile {individual.get('ind_id')}"
                    )

                elif similarity >= settings.load_soft_threshold:
                    match = f"{case['case_id']}.{individual['ind_id']}"
                    sample.similar_samples.append(match)

    return case_object


def build_case_object(
    adapter: MongoAdapter,
    case_id: str,
    profile_path: Union[Path, str],
    vcf_path: Union[Path, str] = None,
    vcf_sv_path: Union[Path, str] = None,
) -> Case:

    case_object: Case = Case(
        case_id=case_id, profile_path=profile_path, vcf_path=vcf_path, vcf_sv_path=vcf_sv_path
    )
    case_object: Case = parse_profiles(adapter=adapter, case_object=case_object)
    case_object: Case = check_profile_duplicates(adapter=adapter, case_object=case_object)

    if vcf_path:
        case_object: Case = parse_snv_vcf(vcf_path=vcf_path, case_object=case_object)

    if vcf_sv_path:
        case_object: Case = parse_sv_vcf(vcf_path=vcf_sv_path, case_object=case_object)

    adapter.add_case(case_object.dict(by_alias=True))

    return adapter.case({"case_id": case_id})
