import pandas as pd
import os
from django.db import transaction
from django.core.exceptions import ValidationError
from src.models import StudentRecord, StudentMajor, Course, MajorMapping, MajorCourse
from pathlib import Path
from src.utils import (
    extract_credits_from_name,
    parse_course_csv,
    populate_catalog_from_payload,
    split_courses_by_credit_blocks,
    match_major_name_web_to_registrar,
    normalize_major_name_web
)

#  Helper Functions
def is_duplicate_record(student_id, term, course_id, institution=None):
    query = StudentRecord.objects.filter(
        student_id=student_id,
        term=term,
        course__course_id=course_id,
    )

    if institution:
        query = query.filter(institution=institution)

    return query.exists()


### Data Import Functions ###

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
                term = row[readable_to_col["term"]]

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

                # Check if student record was previously uploaded
                if is_duplicate_record(student_id, term, course_id):
                    continue

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

            # Bulk insert
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


def prepare_django_inserts(parsed_structure, major_code, major_name_web, major_name_registrar):
    """
    Converts the parsed import structure into Django model-ready dicts.
    Returns a dict with keys: major, courses, groups, subgroups, major_courses.
    """
    from collections import defaultdict

    # MajorMapping object
    major_record = {
        "major_code": major_code,
        "major_name_web": major_name_web,
        "major_name_registrar": major_name_registrar
    }

    # Prepare unique courses
    courses = {}
    groups = []
    subgroups = []
    major_courses = []

    for group in parsed_structure:
        group_name = group["group_name"]

        if group["type"] == "credits":
            # RequirementGroup (credits)
            group_obj = {
                "name": group_name,
                "group_type": "credits",
                "required_credits": group["credits"]
            }
            groups.append(group_obj)

            for course in group["courses"]:
                course_id = f"{course.subject}-{course.number}"
                courses[course_id] = {
                    "course_id": course_id,
                    "subject": course.subject,
                    "course_number": course.number,
                    "course_name": course.name,
                    "credits": course.credits
                }
                major_courses.append({
                    "course_id": course_id,
                    "group_name": group_name,
                    "subgroup_name": None
                })

        elif group["type"] in ["choose_dir", "choose_csv"]:
            # RequirementGroup (choose)
            group_obj = {
                "name": group_name,
                "group_type": "choose",
                "required_credits": None
            }
            groups.append(group_obj)

            for sg in group["subgroups"]:
                # Subgroup record
                sg_obj = {
                    "group_name": group_name,
                    "name": sg["name"],
                    "required_credits": sg["credits"]
                }
                subgroups.append(sg_obj)

                for course in sg["courses"]:
                    course_id = f"{course.subject}-{course.number}"
                    courses[course_id] = {
                        "course_id": course_id,
                        "subject": course.subject,
                        "course_number": course.number,
                        "course_name": course.name,
                        "credits": course.credits
                    }
                    major_courses.append({
                        "course_id": course_id,
                        "group_name": group_name,
                        "subgroup_name": sg["name"]
                    })

    return {
        "major": major_record,
        "courses": list(courses.values()),
        "groups": groups,
        "subgroups": subgroups,
        "major_courses": major_courses
    }



def import_major_from_folder_fixed(base_path, major_name_web, catalog_year, major_code_df):
    """
    Parses a major folder's structure to identify and classify its requirement groups.

    Automatically resolves major_code and major_name_registrar using fuzzy match.

    Returns:
        parsed_structure (list),
        major_info: dict with {major_code, major_name_web, major_name_registrar}
    """
    base_path = Path(base_path)
    parsed_structure = []

    # Step 1: Match major_name_web to registrar data
    major_code, major_name_registrar, score = match_major_name_web_to_registrar(major_name_web, major_code_df)
    major_info = {
        "major_code": major_code,
        "major_name_web": major_name_web,
        "major_name_registrar": major_name_registrar,
        "match_score": score
    }

    # Step 2: Walk directory structure and parse requirement groups
    for entry in base_path.iterdir():
        if entry.is_file() and entry.suffix.lower() == ".csv":
            group_name = entry.stem
            credit_info = extract_credits_from_name(group_name)

            if isinstance(credit_info, list):  # choose group in flat csv
                courses = parse_course_csv(entry)
                course_blocks = split_courses_by_credit_blocks(courses, credit_info)
                parsed_structure.append({
                    "type": "choose_csv",
                    "group_name": group_name,
                    "subgroups": [
                        {"name": f"Group {chr(65+i)}", "credits": credit_info[i], "courses": block}
                        for i, block in enumerate(course_blocks)
                    ]
                })
            else:
                courses = parse_course_csv(entry)
                parsed_structure.append({
                    "type": "credits",
                    "group_name": group_name,
                    "credits": credit_info,
                    "courses": courses
                })

        elif entry.is_dir():
            group_name = entry.name
            subgroup_entries = list(entry.glob("*/*.csv"))

            if subgroup_entries:
                subgroups = []
                for csv_path in subgroup_entries:
                    subgroup_name = csv_path.parent.name
                    subgroup_credits = extract_credits_from_name(subgroup_name)
                    courses = parse_course_csv(csv_path)
                    subgroups.append({
                        "name": subgroup_name,
                        "credits": subgroup_credits,
                        "courses": courses
                    })
                parsed_structure.append({
                    "type": "choose_dir",
                    "group_name": group_name,
                    "subgroups": subgroups
                })
            else:
                for subgroup_file in entry.glob("*.csv"):
                    subgroup_name = subgroup_file.stem
                    subgroup_credit = extract_credits_from_name(subgroup_name)
                    courses = parse_course_csv(subgroup_file)
                    parsed_structure.append({
                        "type": "credits",
                        "group_name": subgroup_name,
                        "credits": subgroup_credit,
                        "courses": courses
                    })

    return parsed_structure, major_info


def batch_import_catalog_year(catalog_folder, major_code_df, threshold=85, dry_run=False):
    """
    Imports all majors from a given catalog folder (e.g., '2024-2025').

    Args:
        catalog_folder (str or Path): Path to the catalog year folder containing major subfolders.
        major_code_df (pd.DataFrame): The dataframe from parsed major_codes.csv.
        threshold (int): Minimum acceptable match confidence (0–100) for fuzzy matching.
        dry_run (bool): If True, data is parsed but not committed to the database.

    Returns:
        List of import result dicts with keys:
            - major_name_web
            - major_code
            - major_name_registrar
            - match_score
            - status ('imported', 'skipped', 'failed')
            - reason (optional)
    """
    results = []
    catalog_path = Path(catalog_folder)

    for major_dir in catalog_path.iterdir():
        if not major_dir.is_dir():
            continue

        major_name_web = major_dir.name
        print(f"\n📁 Processing: {major_name_web}")

        try:
            parsed_structure, major_info = import_major_from_folder_fixed(
                base_path=major_dir,
                major_name_web=major_name_web,
                catalog_year=catalog_path.name,
                major_code_df=major_code_df
            )

            if major_info["match_score"] < threshold:
                results.append({
                    "major_name_web": major_info["major_name_web"],
                    "major_code": major_info["major_code"],
                    "major_name_registrar": major_info["major_name_registrar"],
                    "match_score": major_info["match_score"],
                    "status": "skipped",
                    "reason": f"Low confidence match ({major_info['match_score']}%)"
                })
                print(f"⚠️  Skipped: Low confidence match ({major_info['match_score']}%)")
                continue

            payload = prepare_django_inserts(
                parsed_structure,
                major_info["major_code"],
                major_info["major_name_web"],
                major_info["major_name_registrar"]
            )

            if not dry_run:
                populate_catalog_from_payload(payload)

            results.append({
                "major_name_web": major_info["major_name_web"],
                "major_code": major_info["major_code"],
                "major_name_registrar": major_info["major_name_registrar"],
                "match_score": major_info["match_score"],
                "status": "imported" if not dry_run else "parsed"
            })

            print(f"✅ {'Parsed' if dry_run else 'Imported'}: {major_info['major_code']} ({major_info['match_score']}%)")

        except Exception as e:
            results.append({
                "major_name_web": major_name_web,
                "status": "failed",
                "reason": str(e)
            })
            print(f"❌ Failed to import {major_name_web}: {e}")

    return results
