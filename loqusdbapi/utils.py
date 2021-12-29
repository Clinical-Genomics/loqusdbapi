import logging
from pathlib import Path
from typing import List, Union, Dict

from cyvcf2 import VCF

from loqusdb.constants import GENOTYPE_MAP
from loqusdb.models import Variant
from loqusdb.plugins.mongo.adapter import MongoAdapter
from loqusdb.utils.profiling import compare_profiles
from loqusdb.utils.delete import delete
from loqusdb.build_models.variant import get_variant_id, get_coords, check_par
from loqusdbapi.exceptions import VCFParserError, ProfileDuplicationError
from loqusdbapi.models import Case, Individual
from loqusdbapi.settings import settings

LOG = logging.getLogger("__name__")


def get_profiles(adapter: MongoAdapter, vcf_file: str) -> Dict[str, str]:
    """
    Reads VCF file containing one or more samples.
    Creates a dictionary where each sample ID from VCF file is a key.
    Retrieves coordinates for each variant from loqusdb.profile_variants
    Adds each variant of each sample as value of the dictionary.
    Returns a dictionary :
    {SAMPLE_ID : [var1, var2, ..., var50]}

    """

    vcf = VCF(vcf_file, threads=settings.cyvcf_threads)
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


def check_vcf_gq_field(
    vcf_path: Union[Path, str],
) -> None:
    vcf_file = VCF(vcf_path, threads=settings.cyvcf_threads)
    if not vcf_file.contains("GQ"):
        raise VCFParserError(f"GQ not found in {vcf_path}")


def get_vcf_variant_count(vcf_path: Union[Path, str]) -> int:
    vcf = VCF(vcf_path, threads=settings.cyvcf_threads)
    return sum(1 for _ in vcf)


def check_snv_variant_types(vcf_path: Union[Path, str]) -> None:
    snv_vcf = VCF(vcf_path, threads=settings.cyvcf_threads)
    for variant in snv_vcf:
        if variant.var_type not in ["sv", "cnv"]:
            continue
        raise VCFParserError(f"Variant types found in {vcf_path}: {variant.var_type}, allowed: snv")


def check_profile_duplicates(adapter: MongoAdapter, profiles: dict) -> None:
    """Compare profile variants from upload with all profiles of all cases in database.
    Raises error if profile matches any of the existing profiles"""
    for existing_case in adapter.cases():

        if existing_case.get("individuals") is None:
            continue

        for individual in existing_case["individuals"]:
            if not individual.get("profile"):
                continue

            for sample, profile in profiles.items():
                similarity = compare_profiles(profile, individual["profile"])
                if similarity >= settings.load_hard_threshold:
                    raise ProfileDuplicationError(
                        f"Profile of sample {sample} "
                        f"matches existing profile {individual.get('ind_id')}"
                    )


def build_case_object(
    adapter: MongoAdapter,
    case_id: str,
    profile_path: Union[Path, str],
    vcf_path: Union[Path, str],
    vcf_sv_path: Union[Path, str] = None,
) -> Case:
    """Build case document and insert into the database, return resulting document"""

    # Create case object prior to parsing VCF files
    case_object: Case = Case(
        case_id=case_id, profile_path=profile_path, vcf_path=vcf_path, vcf_sv_path=vcf_sv_path
    )
    # Parse MAF profiles from profile files and save in the case object
    profiles: dict = get_profiles(adapter=adapter, vcf_file=case_object.profile_path)
    # Check if profiles have any duplicates in the database
    check_profile_duplicates(adapter=adapter, profiles=profiles)
    # CHeck that SNV file has GQ field
    check_vcf_gq_field(vcf_path=case_object.vcf_path)
    # CHeck that SNV file doesnt have SV variants
    check_snv_variant_types(vcf_path=case_object.vcf_path)
    for sample_index, (sample, profile) in enumerate(profiles.items()):
        individual = Individual(
            ind_id=sample,
            case_id=case_id,
            ind_index=sample_index,
            profile=profile,
        )
        case_object.individuals.append(individual)
        case_object.inds[sample] = individual
        if not case_object.vcf_sv_path:
            continue
        case_object.sv_individuals.append(individual)
        case_object.sv_inds[sample] = individual

    case_object.nr_variants = get_vcf_variant_count(vcf_path=case_object.vcf_path)
    if case_object.vcf_sv_path:
        case_object.nr_sv_variants = get_vcf_variant_count(vcf_path=case_object.vcf_sv_path)

    adapter.add_case(case_object.dict(by_alias=True, exclude={"id"}))

    return Case(**adapter.case({"case_id": case_id}))


def insert_snv_variants(adapter: MongoAdapter, case_obj: Case) -> None:
    """Build variant documents and bulk insert them into database"""
    variants = []
    for variant in VCF(case_obj.vcf_path, threads=settings.cyvcf_threads):
        variant_id = get_variant_id(variant=variant)
        ref = variant.REF
        alt = variant.ALT[0]

        coordinates = get_coords(variant)
        chrom = coordinates["chrom"]
        pos = coordinates["pos"]
        found_homozygote = 0
        found_hemizygote = 0

        for ind_obj in case_obj.individuals:
            ind_pos = ind_obj["ind_index"]
            if int(variant.gt_quals[ind_pos]) < settings.load_gq_threshold:
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
                    case_id=case_obj.case_id,
                    homozygote=found_homozygote,
                    hemizygote=found_hemizygote,
                    is_sv=False,
                    id_column=variant.ID,
                )
                variants.append(variant_obj)
    adapter.add_variants(variants=variants)


def insert_sv_variants(adapter: MongoAdapter, case_obj: Case) -> None:
    """Build sv_variant documents and insert them into database on the fly, one at a time"""

    for variant in VCF(case_obj.vcf_sv_path, threads=settings.cyvcf_threads):
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
            case_id=case_obj.case_id,
            homozygote=0,
            hemizygote=0,
            is_sv=True,
            id_column=variant.ID,
        )
        adapter.add_structural_variant(variant=variant_obj, max_window=settings.load_sv_window)


def load_case_variants(
    adapter: MongoAdapter,
    case_obj: Case,
) -> None:
    """Load case variants into loqusdb"""

    try:
        insert_snv_variants(adapter=adapter, case_obj=case_obj)
        if not case_obj.vcf_sv_path:
            return
        insert_sv_variants(adapter=adapter, case_obj=case_obj)
    except Exception as e:
        LOG.error(f"{e}")
        delete(adapter=adapter, case_obj=case_obj.dict(), genome_build=settings.genome_build)
        raise
