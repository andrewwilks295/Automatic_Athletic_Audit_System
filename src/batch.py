import requests

from src.course_parser import parse_course_structure_as_tree
from src.data import populate_catalog_from_payload
from src.log_utils import CatalogBatchLogger
from src.models import MajorMapping
from src.suu_scraper import pull_catalog_year, find_all_programs_link, find_degree, fetch_total_credits, \
    get_catalog_years
from src.utils import match_major_name_web_to_registrar, prepare_django_inserts, load_major_code_lookup


def scrape_catalog_year(year, majors, major_code_df, threshold=85, dry_run=False):

    results = []

    catalog_url = pull_catalog_year(year)
    all_programs_link = find_all_programs_link(catalog_url)
    catalog_year = int(year[:4] + "30")  # Convert to term format

    for major_name_web in majors:
        try:
            major_code, _, _ = match_major_name_web_to_registrar(major_name_web, major_code_df)

            if MajorMapping.objects.filter(major_code=major_code, catalog_year=catalog_year).exists():
                results.append({
                    "status": "skipped",
                    "major_name_web": major_name_web,
                    "reason": "Already imported"
                })
                continue

            program_url = find_degree(all_programs_link, major_name_web)
            if not program_url:
                results.append({
                    "status": "failed",
                    "major_name_web": major_name_web,
                    "reason": "Could not find program URL"
                })
                continue

            print_url = program_url + "&print"
            html = requests.get(print_url).text
            total_credits = fetch_total_credits(html)
            structure = parse_course_structure_as_tree(html)

            major_code, major_name_registrar, score = match_major_name_web_to_registrar(major_name_web, major_code_df)

            if score < threshold:
                results.append({
                    "status": "skipped",
                    "major_name_web": major_name_web,
                    "reason": f"Low match confidence ({score}%)"
                })
                continue

            payload = prepare_django_inserts(
                parsed_tree=structure,
                major_code=major_code,
                major_name_web=major_name_web,
                major_name_registrar=major_name_registrar,
                total_credits_required=total_credits,
                catalog_year=catalog_year
            )

            if not dry_run:
                populate_catalog_from_payload(payload)

            results.append({
                "status": "parsed" if dry_run else "imported",
                "major_name_web": major_name_web
            })

        except Exception as e:
            results.append({
                "status": "failed",
                "major_name_web": major_name_web,
                "reason": str(e)
            })

    return results


def batch_scrape_all_catalogs(
    base_url="https://www.suu.edu/academics/catalog/",
    majors_file="majors.txt",
    threshold=85,
    dry_run=False,
    selected_years=None  # optional list of years to include
):
    logger = CatalogBatchLogger()
    # Get catalog years and their catoid mappings
    catalog_year_map = get_catalog_years(base_url)

    # Filter years if specified
    if selected_years:
        catalog_year_map = {k: v for k, v in catalog_year_map.items() if k in selected_years}

    # Load list of majors
    with open(majors_file) as f:
        majors = [line.strip() for line in f if line.strip()]

    # Load major codes
    major_code_df = load_major_code_lookup("major_codes.csv")

    for year_str in sorted(catalog_year_map.keys(), reverse=True):
        print(f"\n📅 Catalog Year: {year_str}")
        try:
            results = scrape_catalog_year(
                year=year_str,
                majors=majors,
                major_code_df=major_code_df,
                threshold=threshold,
                dry_run=dry_run
            )
            for r in results:
                match r["status"]:
                    case "parsed":
                        logger.parsed(r["major_name_web"])
                    case "imported":
                        logger.imported(r["major_name_web"])
                    case "skipped":
                        logger.skipped(r["major_name_web"], r.get("reason"))
                    case "failed":
                        logger.failed(r["major_name_web"], r.get("reason"))
        except Exception as e:
            print(f"❌ ERROR in catalog year {year_str}: {e}")

    logger.close()