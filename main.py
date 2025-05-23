import os
from datetime import datetime

import django

# initialize django (sqlite ORM only)
# THE FOLLOWING TWO LINES ARE REQUIRED FOR DJANGO ORM TO WORK AND MUST BE CALLED BEFORE ANY DJANGO IMPORTS.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()
# end of django initialization

from src.batch import batch_scrape_all_catalogs
from src.course_parser import print_requirement_tree
from src.models import MajorMapping, StudentAudit
from src.data import import_student_data_from_csv
from src.eligibility import run_audit
from src.output import output_to_csv, output_to_xlsx
from src.maintenance import delete_majors


def main():
    batch_scrape_all_catalogs(
        base_url="https://www.suu.edu/academics/catalog/",
        majors_file="majors.txt",
        dry_run=False,  # Set to True for testing without DB writes
        selected_years=[
            "2022-2024",
            "2023-2024",
            "2024-2025"
        ],
        max_threads=12
    )
    filepath = "Bogus_data_2.csv"
    print(import_student_data_from_csv(filepath))
    run_audit(202430)
    output_to_xlsx(202430)


if __name__ == "__main__":
    main()
