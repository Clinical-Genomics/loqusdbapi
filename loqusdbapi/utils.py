import logging
from pathlib import Path
from typing import List, Union

from cyvcf2 import VCF, Variant

from loqusdb.constants import GENOTYPE_MAP
from loqusdb.plugins.mongo.adapter import MongoAdapter
from loqusdb.utils.profiling import compare_profiles
from loqusdb.utils.delete import delete
from loqusdb.build_models.variant import get_variant_id, get_coords, check_par
from loqusdbapi.exceptions import VCFParserError, ProfileDuplicationError
from loqusdbapi.models import Case, Individual
from loqusdbapi.settings import settings

LOG = logging.getLogger("__name__")


def get_profiles(adapter: MongoAdapter, vcf_file: Path):

    vcf = VCF(vcf_file)
    individuals = vcf.samples
    profiles = {individual: [] for individual in individuals}

    for profile_variant in adapter.profile_variants():

        ref = profile_variant["ref"]
        alt = profile_variant["alt"]

        pos = profile_variant["pos"]
        end = pos + 1
        chrom = profile_variant["chrom"]

        region = f"{chrom}:{pos}-{end}"

        # Find variants in region

        found_variant = False
        for variant in vcf(region):

            variant_id = get_variant_id(variant)

            # If variant id i.e. chrom_pos_ref_alt matches
            if variant_id == profile_variant["_id"]:
                found_variant = True
                # find genotype for each individual in vcf
                for i, individual in enumerate(individuals):

                    genotype = GENOTYPE_MAP[variant.gt_types[i]]
                    if genotype == "hom_alt":
                        gt_str = f"{alt}{alt}"
                    elif genotype == "het":
                        gt_str = f"{ref}{alt}"
                    else:
                        gt_str = f"{ref}{ref}"

                    # Append genotype to profile string of individual
                    profiles[individual].append(gt_str)

                # Break loop if variant is found in region
                break

        # If no call was found for variant, give all samples a hom ref genotype
        if not found_variant:
            for individual in individuals:
                profiles[individual].append(f"{ref}{ref}")

    return profiles


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

    if "sv" in snv_vcf_var_types or "cnv" in snv_vcf_var_types:
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

    print(sv_vcf_var_types)

    case_object.nr_sv_variants = sv_vcf_variant_count
    case_object.sv_individuals = sv_vcf_individuals
    case_object.vcf_sv_path = vcf_path
    return case_object


def parse_profiles(adapter: MongoAdapter, case_object: Case) -> Case:

    profiles: dict = get_profiles(adapter=adapter, vcf_file=case_object.profile_path)
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
            case_object.individuals.append(individual)
            case_object.inds[sample] = individual
        if case_object.vcf_sv_path:
            case_object.sv_individuals.append(individual)
            case_object.sv_inds[sample] = individual

    return case_object


def check_profile_duplicates(adapter: MongoAdapter, case_object: Case) -> Case:
    for existing_case in adapter.cases():

        if existing_case.get("individuals") is None:
            continue

        for individual in existing_case["individuals"]:
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
                    match = f"{existing_case['case_id']}.{individual['ind_id']}"
                    sample.similar_samples.append(match)

    return case_object


def build_case_object(
    adapter: MongoAdapter,
    case_id: str,
    profile_path: Union[Path, str],
    vcf_path: Union[Path, str],
    vcf_sv_path: Union[Path, str] = None,
) -> dict:

    # Create case object prior to parsing VCF files
    case_object: Case = Case(
        case_id=case_id, profile_path=profile_path, vcf_path=vcf_path, vcf_sv_path=vcf_sv_path
    )
    # Parse MAF profiles from profile files and save in the case object
    case_object: Case = parse_profiles(adapter=adapter, case_object=case_object)

    # Check if profiles have any duplicates in the database
    case_object: Case = check_profile_duplicates(adapter=adapter, case_object=case_object)

    if vcf_path:
        case_object: Case = parse_snv_vcf(vcf_path=vcf_path, case_object=case_object)

    if vcf_sv_path:
        case_object: Case = parse_sv_vcf(vcf_path=vcf_sv_path, case_object=case_object)

    adapter.add_case(case_object.dict(by_alias=True, exclude_none=True))

    return adapter.case({"case_id": case_id})


def insert_snv_variants(adapter: MongoAdapter, vcf_file: Union[Path, str], case_obj: dict):

    variants = []
    for variant in VCF(vcf_file):
        variant_id = get_variant_id(variant=variant)
        ref = variant.REF
        alt = variant.ALT[0]

        coordinates = get_coords(variant)
        chrom = coordinates["chrom"]
        pos = coordinates["pos"]
        found_homozygote = 0
        found_hemizygote = 0

        for ind_obj in case_obj["individuals"]:
            ind_id = ind_obj["ind_id"]
            ind_pos = ind_obj["ind_index"]
            gq = int(variant.gt_quals[ind_pos])
            if gq < settings.gq_treshold:
                continue
            genotype = GENOTYPE_MAP[variant.gt_types[ind_pos]]

            if genotype in ["het", "hom_alt"]:

                if (
                    chrom in ["X", "Y"]
                    and ind_obj["sex"] == 1
                    and not check_par(chrom, pos, genome_build=settings.genome_build)
                ):
                    found_hemizygote = 1

                if genotype == "hom_alt":
                    found_homozygote = 1

                variant_obj = Variant(
                    variant_id=variant_id,
                    chrom=chrom,
                    pos=pos,
                    end=coordinates["end"],
                    ref=ref,
                    alt=alt,
                    end_chrom=coordinates["end_chrom"],
                    sv_type=coordinates["sv_type"],
                    sv_len=coordinates["sv_length"],
                    case_id=case_obj["case_id"],
                    homozygote=found_homozygote,
                    hemizygote=found_hemizygote,
                    is_sv=False,
                    id_column=variant.ID,
                )
                variants.append(variant_obj)
    adapter.add_variants(variants=variants)


def insert_sv_variants(adapter: MongoAdapter, vcf_file: Union[Path, str], case_obj: dict):

    for variant in VCF(vcf_file):
        variant_id = get_variant_id(variant=variant)
        ref = variant.REF
        alt = variant.ALT[0]
        coordinates = get_coords(variant)
        chrom = coordinates["chrom"]
        pos = coordinates["pos"]

        variant_obj = Variant(
            variant_id=variant_id,
            chrom=chrom,
            pos=pos,
            end=coordinates["end"],
            ref=ref,
            alt=alt,
            end_chrom=coordinates["end_chrom"],
            sv_type=coordinates["sv_type"],
            sv_len=coordinates["sv_length"],
            case_id=case_obj["case_id"],
            homozygote=0,
            hemizygote=0,
            is_sv=True,
            id_column=variant.ID,
        )
        adapter.add_structural_variant(variant=variant_obj, max_window=settings.load_sv_window)


def load_case_variants(
    adapter: MongoAdapter,
    case_obj: dict,
):
    try:
        vcf_path = case_obj.get("vcf_path")
        if vcf_path:
            insert_snv_variants(adapter=adapter, vcf_file=vcf_path, case_obj=case_obj)
        vcf_sv_path = case_obj.get("vcf_sv_path")
        if vcf_sv_path:
            insert_sv_variants(adapter=adapter, vcf_file=vcf_sv_path, case_obj=case_obj)
    except Exception as e:
        delete(adapter=adapter, case_obj=case_obj, genome_build=settings.genome_build)
