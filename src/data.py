import csv
from django.core.exceptions import ValidationError
from src.models import StudentRecord

def import_student_records(csv_filepath):
    with open(csv_filepath, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        student_records = []
        for row in reader:
            try:
                record = StudentRecord(
                    student_id=int(row["student_id"]),
                    high_school_grad=int(row["high_school_grad"]),
                    first_term=int(row["first_term"]),
                    major=row.get("major", None),
                    concentration=row.get("concentration", None),
                    minors=row.get("minors", None),
                    catalog_year=int(row["catalog_year"]),
                    term=int(row["term"]),
                    subject=row["subject"],
                    course_number=row["course_number"],
                    grade=row.get("grade", None),
                    credits=int(row["credits"]),
                    course_attribute=row.get("course_attribute", None),
                    institution=row["institution"],
                    student_attribute=row.get("student_attribute", None),
                )
                record.full_clean()  # Validate the model before saving
                student_records.append(record)
            except (ValueError, ValidationError) as e:
                print(f"Error processing row {row}: {e}")

        # Bulk insert for better performance
        StudentRecord.objects.bulk_create(student_records)
        print(f"Successfully imported {len(student_records)} records.")
