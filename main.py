
from pathlib import Path
import pandas as pd
import django
import os

# initialize django (sqlite ORM only)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from src.data import batch_import_catalog_year

def load_major_code_lookup(path: str) -> pd.DataFrame:
    """
    Load and clean the unified major_codes.csv for fuzzy matching.
    """
    df = pd.read_csv(path)
    df = df.rename(columns={
        "Major Code": "major_code",
        "Major Name Registrar": "major_name_registrar"
    })[["major_code", "major_name_registrar"]]
    return df.dropna(subset=["major_code", "major_name_registrar"])


def main():
    catalog_dir = Path("2024-2025")
    major_code_path = Path("major_codes.csv")

    if not catalog_dir.exists() or not major_code_path.exists():
        print("❌ Error: Required paths do not exist.")
        return

    # Load the major code lookup table
    major_code_df = load_major_code_lookup(major_code_path)

    # Run the dry-run batch import
    results = batch_import_catalog_year(
        catalog_folder=catalog_dir,
        major_code_df=major_code_df,
        threshold=85,
        dry_run=True
    )

    # Print summary
    print("\n📋 Dry Run Summary:")
    for result in results:
        status = result.get("status")
        name = result.get("major_name_web")
        code = result.get("major_code", "N/A")
        score = result.get("match_score", "N/A")
        print(f" - [{status.upper()}] {name} → {code} ({score}%)")


if __name__ == "__main__":
    main()
