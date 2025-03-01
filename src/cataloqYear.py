import csv
from django.core.exceptions import ValidationError
from src.models import CatalogYear 

def import_catalog_year(csv_filepath):
    with open(csv_filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        for row in reader:
            try:
                catalog_year_record = CatalogYear(
                    catalog_year=int(row["catalog_year"]),
                    start_year=int(row["start_year"]),
                    end_year=int(row["end_year"]),
                    description=row.get("description", None),
                    term=int(row["term"]),
                    year=int(row["year"]),
                    
                )
                catalog_year_record.full_clean()  
                catalog_year_record.save()  
                print(f"Successfully inserted catalog year {row['catalog_year']}")
            except (ValueError, ValidationError) as e:
                print(f"Error processing row {row}: {e}")
