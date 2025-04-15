from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from src.course_parser import parse_course_structure_as_tree
from src.data import populate_catalog_from_payload
from src.log_utils import CatalogBatchLogger
from src.models import MajorMapping
from src.suu_scraper import get_catalog_years
from src.suu_scraper import pull_catalog_year, find_all_programs_link, find_degree, fetch_total_credits
from src.utils import load_major_code_lookup
from src.utils import match_major_name_web_to_registrar, prepare_django_inserts


def scrape_catalog_year(year, majors, major_code_df, threshold=85, dry_run=False, max_threads=10):
    results = []

    catalog_url = pull_catalog_year(year)
    all_programs_link = find_all_programs_link(catalog_url)
    catalog_year = int(year[:4] + "30")

    scraped_payloads = []

    def scrape_major(major_name_web):
        try:
            match_result = match_major_name_web_to_registrar(major_name_web, major_code_df)
            score = match_result["score"]

            if score < threshold:
                return {
                    "status": "skipped",
                    "major_name_web": major_name_web,
                    "reason": f"Low match confidence ({score:.2f}%)"
                }

            if MajorMapping.objects.filter(
                major_code=match_result["major_code"], catalog_year=catalog_year
            ).exists():
                return {
                    "status": "skipped",
                    "major_name_web": major_name_web,
                    "reason": "Already imported"
                }

            program_url = find_degree(all_programs_link, major_name_web)
            if not program_url:
                return {
                    "status": "failed",
                    "major_name_web": major_name_web,
                    "reason": "Could not find program URL"
                }

            html = requests.get(program_url + "&print").text
            total_credits = fetch_total_credits(html)
            structure = parse_course_structure_as_tree(html)

            payload = prepare_django_inserts(
                parsed_tree=structure,
                match_result=match_result,
                major_name_web=major_name_web,
                total_credits_required=total_credits,
                catalog_year=catalog_year
            )

            return {
                "status": "scraped",
                "major_name_web": major_name_web,
                "payload": payload
            }

        except Exception as e:
            return {
                "status": "failed",
                "major_name_web": major_name_web,
                "reason": str(e)
            }

    # Parallel scraping
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        future_to_major = {executor.submit(scrape_major, m): m for m in majors}
        for future in as_completed(future_to_major):
            result = future.result()
            if result["status"] == "scraped":
                scraped_payloads.append(result)
            else:
                results.append(result)

    # Sequential DB insertions
    for scraped in scraped_payloads:
        try:
            if not dry_run:
                populate_catalog_from_payload(scraped["payload"])
            results.append({
                "status": "parsed" if dry_run else "imported",
                "major_name_web": scraped["major_name_web"]
            })
        except Exception as e:
            results.append({
                "status": "failed",
                "major_name_web": scraped["major_name_web"],
                "reason": str(e)
            })

    return results


def batch_scrape_all_catalogs(
    base_url="https://www.suu.edu/academics/catalog/",
    majors_file="majors.txt",
    threshold=85,
    dry_run=False,
    selected_years=None,  # optional list of years to include
    max_threads=4
):
    logger = CatalogBatchLogger()

    # Get catalog years and their catoid mappings
    catalog_year_map = get_catalog_years(base_url)

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
                dry_run=dry_run,
                max_threads=max_threads
            )
            for r in results:
                base_major_code = None
                major_code = None
                if "payload" in r:
                    major_code = r["payload"]["major"]["major_code"]
                    base_major_code = r["payload"]["major"].get("base_major_code")

                match r["status"]:
                    case "parsed":
                        logger.parsed(r["major_name_web"])
                    case "imported":
                        logger.imported(r["major_name_web"])
                    case "skipped":
                        logger.skipped(
                            r["major_name_web"],
                            reason=r.get("reason"),
                            extra=f"major_code={major_code}, base_major_code={base_major_code}"
                        )
                    case "failed":
                        logger.failed(
                            r["major_name_web"],
                            reason=r.get("reason"),
                            extra=f"major_code={major_code}, base_major_code={base_major_code}"
                        )
        except Exception as e:
            print(f"❌ ERROR in catalog year {year_str}: {e}")

    logger.close()