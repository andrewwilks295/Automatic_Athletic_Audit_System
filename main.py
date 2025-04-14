from pathlib import Path
import pandas as pd
import django
import os
import requests

# initialize django (sqlite ORM only)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from src.suu_scraper import (
    pull_catalog_year,
    find_all_programs_link,
    find_degree,
    fetch_total_credits,
)
from src.utils import load_major_code_lookup, match_major_name_web_to_registrar, prepare_django_inserts
from src.course_parser import parse_course_structure_as_tree
from src.data import populate_catalog_from_payload


def main():
    # ====== Configuration ======
    year = "2024-2025"
    major_name_web = "Exercise Science (B.S.)"  # ✅ Change this as needed
    threshold = 85
    dry_run = False

    # ====== Resolve major URL ======
    print(f"\n📦 Scraping: {major_name_web} ({year})")
    catalog_url = pull_catalog_year(year)
    all_programs_link = find_all_programs_link(catalog_url)
    program_url = find_degree(all_programs_link, major_name_web)

    if not program_url:
        print("❌ Could not locate program URL.")
        return

    # ====== Fetch clean HTML ======
    print_url = program_url + "&print"
    html = requests.get(print_url).text

    # ====== Parse structure and total credits ======
    parsed_tree = parse_course_structure_as_tree(html)
    print(parsed_tree)
    total_credits = fetch_total_credits(html)

    # ====== Match registrar info ======
    major_code_df = load_major_code_lookup("major_codes.csv")
    major_code, major_name_registrar, score = match_major_name_web_to_registrar(major_name_web, major_code_df)

    if score < threshold:
        print(f"⚠️ Match score too low ({score}%). Skipping.")
        return

    # ====== Prepare payload ======
    payload = prepare_django_inserts(
        parsed_tree,
        major_code,
        major_name_web,
        major_name_registrar,
        total_credits,
        catalog_year=202430
    )

    if dry_run:
        print("✅ Dry run complete. Parsed successfully.")
    else:
        result = populate_catalog_from_payload(payload)
        print(f"✅ Imported {result['nodes_created']} nodes, {result['courses_created']} courses.")


if __name__ == "__main__":
    main()
