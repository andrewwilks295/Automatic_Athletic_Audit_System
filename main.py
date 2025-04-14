import os
from datetime import datetime

import django

# initialize django (sqlite ORM only)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from src.batch import batch_scrape_all_catalogs
from src.utils import print_requirement_tree


def main():
    batch_scrape_all_catalogs(
        base_url="https://www.suu.edu/academics/catalog/",
        majors_file="majors.txt",
        threshold=85,
        dry_run=False,  # Set to True for testing without DB writes
        selected_years=["2024-2025",]  # Or set to None to select all.
    )


if __name__ == "__main__":
    start = datetime.now()
    main()
    elapsed = datetime.now() - start
    print(elapsed)
    print_requirement_tree(30)
