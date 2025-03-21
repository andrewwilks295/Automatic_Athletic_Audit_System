import pandas as pd
from django.db import transaction
from django.core.exceptions import ValidationError
from src.models import StudentRecord, StudentMajor, Course, MajorMapping, MajorCourse


def import_student_data_from_csv(file_path):
    """
    Reads a CSV file and imports student data into the database.

    :param file_path: Path to the uploaded CSV file
    :return: Dictionary with import summary
    """
    try:
        # Load CSV
        df = pd.read_csv(file_path)

        # import col name to readable name mapping
        col_to_readable = {
            "ID": "student_id",
            "HS_GRAD": "high_school_grad",
            "FT_SEM": "first_term",
            "MAJOR": "major",
            "CONC": "concentration",
            "MINORS": "minors",
            "CATALOG": "catalog_year",
            "TERM": "term",
            "SUBJ": "subject",
            "CRSE": "course_number",
            "GRADE": "grade",
            "CREDITS": "credits",
            "CRSE_ATTR": "course_attributes",
            "INSTITUTION": "institution"
        }

        readable_to_col = {i: j for j, i in col_to_readable.items()}

        # Validate required columns
        required_columns = {"student_id", "high_school_grad", "first_term", "major", "catalog_year",
                            "term", "subject", "course_number", "grade", "credits", "institution"}
        required_columns = set([readable_to_col[c] for c in required_columns])
        if not required_columns.issubset(df.columns):
            missing_columns = required_columns - set(df.columns)
            return {"success": False, "message": f"Missing required columns: {', '.join(missing_columns)}"}

        # Dictionaries to track existing records
        existing_majors = {m.major_code: m for m in MajorMapping.objects.all()}
        existing_courses = {c.course_id: c for c in Course.objects.all()}

        print(f"existing_majors: {len(existing_majors)}, existing_courses: {len(existing_courses)}")

        students_to_create = []
        courses_to_create = []
        student_majors_to_create = []
        student_records_to_create = []

        with transaction.atomic():  # Ensures all or nothing insertion
            for _, row in df.iterrows():
                student_id = row[readable_to_col["student_id"]]
                major_code = row[readable_to_col["major"]]
                catalog_year = row[readable_to_col["catalog_year"]]

                # Ensure major exists
                major_obj = existing_majors.get(major_code)
                if not major_obj:
                    continue  # Skip if the major is not found

                # Ensure course exists
                course_id = f"{row[readable_to_col['subject']]}{row[readable_to_col['course_number']]}"
                if existing_courses.get(course_id) is None:
                    course_obj = Course(
                        course_id=course_id,
                        subject=row[readable_to_col["subject"]],
                        course_number=row[readable_to_col["course_number"]],
                        credits=row[readable_to_col["credits"]]
                    )
                    courses_to_create.append(course_obj)
                    existing_courses[course_id] = course_obj  # Cache the new course

                # Create student record
                student_record = StudentRecord(
                    student_id=student_id,
                    high_school_grad=row[readable_to_col["high_school_grad"]],
                    first_term=row[readable_to_col["first_term"]],
                    term=row[readable_to_col["term"]],
                    course=existing_courses[course_id],
                    grade=row[readable_to_col["grade"]],
                    credits=row[readable_to_col["credits"]],
                    course_attributes=row.get(readable_to_col["course_attributes"]),
                    institution=row[readable_to_col["institution"]],
                    counts_toward_major=False  # Default to False, will update below
                )
                student_records_to_create.append(student_record)

                # Check if course counts toward major
                if MajorCourse.objects.filter(major=major_obj, course=existing_courses[course_id]).exists():
                    student_record.counts_toward_major = True

                # Ensure student-major association exists
                if not StudentMajor.objects.filter(student_id=student_id, major=major_obj).exists():
                    student_majors_to_create.append(
                        StudentMajor(student_id=student_id, major=major_obj, catalog_year=catalog_year))

            # Bulk insert to improve efficiency
            Course.objects.bulk_create(courses_to_create, ignore_conflicts=True)
            StudentMajor.objects.bulk_create(student_majors_to_create, ignore_conflicts=True)
            StudentRecord.objects.bulk_create(student_records_to_create, ignore_conflicts=True)

        return {"success": True, "message": "CSV import completed successfully!"}

    except ValidationError as e:
        return {"success": False, "message": f"Validation error: {e}"}
    except FileNotFoundError as e:
        return {"success": False, "message": f"File not found: {e}"}
    except Exception as e:
        print(type(e), e)
        return {"success": False, "message": f"Unexpected error: {e}"}


def update_major_course_associations(file_path):
    """
    TODO: Major code comes from MajorMapping object where the CSV filename matches MajorMapping.major_name_web, not CSV col
    Reads the Exercise Science CSV and for each row:
      - Constructs a course_id from subject and course_number.
      - If the course exists in the Course table and the major code exists in the MajorMapping table,
        creates an association in the MajorCourse table with a default requirement type of "Core".
    Assumes the CSV contains at least the following columns:
      - 'SUBJ': Subject code (e.g., "EXSC")
      - 'CRSE': Course number (e.g., "101")
      - 'MAJOR': Major code (e.g., "EXSCI")
    """
    # Load the CSV file into a DataFrame
    df = pd.read_csv(file_path)

    with transaction.atomic():
        for index, row in df.iterrows():
            subject = row["SUBJ"]
            course_number = row["CRSE"]
            major_code = row["MAJOR"]

            # Construct the course_id (smashed together subject and course_number)
            course_id = f"{subject}{course_number}"

            # Check if the course exists in the Course table.
            try:
                course_obj = Course.objects.get(course_id=course_id)
            except Course.DoesNotExist:
                print(f"Course {course_id} does not exist. Skipping row {index}.")
                continue

            # Check if the major exists in the MajorMapping table.
            try:
                major_obj = MajorMapping.objects.get(major_code=major_code)
            except MajorMapping.DoesNotExist:
                print(f"Major {major_code} not found. Skipping row {index}.")
                continue

            # If the association doesn't already exist, create it with default requirement type "Core"
            if not MajorCourse.objects.filter(major=major_obj, course=course_obj).exists():
                MajorCourse.objects.create(
                    major=major_obj,
                    course=course_obj,
                    requirement_type="Core"
                )
                print(f"Added association: Course '{course_id}', Major '{major_code}', Requirement Type 'Core'.")
            else:
                print(f"Association already exists for Course '{course_id}' and Major '{major_code}'.")
