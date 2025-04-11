from pathlib import Path
import pandas as pd
import django
import os

# initialize django (sqlite ORM only)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

# from src.data import batch_import_catalog_year
# from src.utils import load_major_code_lookup, load_total_credits_map
# def main():
#     catalog_dir = Path("2024-2025")
#     major_code_path = Path("major_codes.csv")

#     if not catalog_dir.exists() or not major_code_path.exists():
#         print("ERROR: Required paths do not exist.")
#         return

#     # Load the major code lookup table
#     major_code_df = load_major_code_lookup(major_code_path)
#     total_credits_map = load_total_credits_map(Path("2024-2025/total_credits.csv"))

#     # Run the dry-run batch import
#     results = batch_import_catalog_year(
#         catalog_folder=catalog_dir,
#         major_code_df=major_code_df,
#         total_credits_map=total_credits_map,
#         threshold=85,
#         dry_run=False
#     )

#     # Print summary
#     print("\nDry Run Summary:")
#     for result in results:
#         status = result.get("status")
#         name = result.get("major_name_web")
#         code = result.get("major_code", "N/A")
#         score = result.get("match_score", "N/A")
#         print(f" - [{status.upper()}] {name} → {code} ({score}% confidence)")


from src.suu_scraper import scrape_catalog_year
from src.utils import load_major_code_lookup


def main():
    year = "2024-2025"
    majors = ["Computer Science (B.S.)",
              "Exercise Science (B.S.)",
              "French (B.A.)",
              "Psychology (B.A., B.S.)", ]
    threshold = 85
    dry_run = True  # Set to True if you just want to test parsing

    # Load major code lookup from major_codes.csv
    major_code_df = load_major_code_lookup("major_codes.csv")

    scrape_catalog_year(
        year=year,
        majors=majors,
        major_code_df=major_code_df,
        threshold=threshold,
        dry_run=dry_run
    )


if __name__ == "__main__":
    main()
