import os
from datetime import datetime

import django

# initialize django (sqlite ORM only)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from src.batch import batch_scrape_all_catalogs
from src.utils import print_requirement_tree
from src.models import MajorMapping, StudentAudit
from src.data import import_student_data_from_csv
from src.eligibility import run_audit
from src.output import output_to_csv


def main():
    batch_scrape_all_catalogs(
        base_url="https://www.suu.edu/academics/catalog/",
        majors_file="majors.txt",
        threshold=85,
        dry_run=True,  # Set to True for testing without DB writes
        selected_years=["2024-2025"],  # Or set to None to select all.
        max_threads=8
    )
    filepath = "cleaned_bogus_data.csv"
    print(import_student_data_from_csv(filepath))
    StudentAudit.objects.all().delete()
    run_audit(202430)
    output_to_csv(202430)

if __name__ == "__main__":
    start = datetime.now()
    start_ct = MajorMapping.objects.all().count()
    main()
    elapsed = datetime.now() - start
    diff_ct = MajorMapping.objects.all().count() - start_ct
    print(f"created: {diff_ct} in {elapsed.total_seconds()} seconds")
