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
from src.batch import batch_scrape_all_catalogs


def main():
    batch_scrape_all_catalogs(
        base_url="https://www.suu.edu/academics/catalog/",
        majors_file="majors.txt",
        threshold=85,
        dry_run=False,  # Set to True for testing without DB writes
        selected_years=["2021-2022",
                        "2022-2023",
                        "2023-2024",
                        "2024-2025",
                        "2025-2026", ]  # Or set to None to select all.
    )


if __name__ == "__main__":
    main()
