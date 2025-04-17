import pandas as pd
from django.core.exceptions import ValidationError
from django.db import transaction

from src.models import Student, StudentRecord, MajorMapping, Course, NodeCourse
from src.utils import load_major_code_lookup


# Data Import Functions
def is_duplicate_record(student_id, term, course_id):
    return StudentRecord.objects.filter(
        student__student_id=student_id,
        term=term,
        course__course_id=course_id
    ).exists()


def import_student_data_from_csv(file_path):
    try:
        df = pd.read_csv(file_path)

        col_map = {
            "ID": "student_id",
            "HS_GRAD": "high_school_grad",
            "FT_SEM": "first_term",
            "MAJOR": "major_code",
            "CONC": "concentration_code",
            "CATALOG": "catalog_year",
            "TERM": "term",
            "SUBJ": "subject",
            "CRSE": "course_number",
            "GRADE": "grade",
            "CREDITS": "credits",
            "CRSE_ATTR": "course_attributes",
            "INSTITUTION": "institution"
        }

        required_cols = set(col_map.keys()) - {"CONC", "CRSE_ATTR"}
        missing = required_cols - set(df.columns)
        if missing:
            return {"success": False, "message": f"Missing required columns: {', '.join(missing)}"}

        # Load major mappings from the database
        major_map = {(m.major_code, m.catalog_year): m for m in MajorMapping.objects.all()}
        course_map = {c.course_id: c for c in Course.objects.all()}

        # Load official web names to code mapping from CSV
        major_lookup_df = load_major_code_lookup("major_codes.csv")
        name_to_code = dict(zip(major_lookup_df["Major Name Web"], major_lookup_df["Major Code"]))

        students_created = 0
        records_created = 0
        # Track unmatched majors with associated student_ids
        unmatched_majors: dict[str, list[str]] = {}

        with transaction.atomic():
            for _, row in df.iterrows():
                student_id = str(row["ID"])
                major_code = str(row["MAJOR"]).strip()
                conc_code = str(row["CONC"]).strip() if "CONC" in row and pd.notna(row["CONC"]) else None
                catalog_year = int(row["CATALOG"])
                term = int(row["TERM"])
                course_id = f"{row['SUBJ']}-{row['CRSE']}"

                effective_code = conc_code or major_code
                matched_web_names = major_lookup_df.loc[
                    major_lookup_df["Major Code"] == effective_code, "Major Name Web"]

                if matched_web_names.empty:
                    unmatched_majors.setdefault(effective_code, []).append(student_id)
                    continue

                major_name_web = matched_web_names.iloc[0]
                major_obj = MajorMapping.objects.filter(major_code=effective_code, catalog_year=catalog_year).first()
                if not major_obj:
                    unmatched_majors.setdefault(major_name_web, []).append(student_id)
                    continue

                # ... (rest of logic remains unchanged)

        if unmatched_majors:
            print("\n⚠️ Unmatched majors found in CSV (no corresponding scraped catalog):")
            for major, students in unmatched_majors.items():
                print(f" - {major}: {', '.join(students)}")

        return {
            "success": True,
            "message": f"Imported {records_created} student records across {students_created} students."
        }

    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {e}"}

def populate_catalog_from_payload(payload):
    from src.models import MajorMapping, Course, RequirementNode, NodeCourse
    from django.db import transaction

    with transaction.atomic():
        major_data = payload["major"]
        major, _ = MajorMapping.objects.update_or_create(
            major_code=major_data["major_code"],
            catalog_year=major_data["catalog_year"],
            defaults={
                "major_name_web": major_data["major_name_web"],
                "major_name_registrar": major_data["major_name_registrar"],
                "total_credits_required": major_data["total_credits_required"]
            }
        )

        # Create courses
        course_objs = []
        existing_ids = set(Course.objects.filter(
            course_id__in=[c["course_id"] for c in payload["courses"]]
        ).values_list("course_id", flat=True))

        for c in payload["courses"]:
            if c["course_id"] not in existing_ids:
                course_objs.append(Course(**c))
        Course.objects.bulk_create(course_objs)

        # Insert RequirementNodes in correct order
        id_to_node_obj = {}
        for i, node_data in enumerate(payload["requirement_nodes"]):
            parent_obj = id_to_node_obj.get(node_data["parent_id"])
            db_node = RequirementNode.objects.create(
                major=major,
                parent=parent_obj,
                name=node_data["name"],
                type=node_data["type"],
                required_credits=node_data["required_credits"]
            )
            id_to_node_obj[i] = db_node

        # Map Course objects
        course_map = {c.course_id: c for c in Course.objects.filter(
            course_id__in=[c["course_id"] for c in payload["courses"]]
        )}

        # Add NodeCourse mappings
        node_course_objs = []
        for nc in payload["node_courses"]:
            node_obj = id_to_node_obj[nc["node_id"]]
            course_obj = course_map[nc["course_id"]]
            node_course_objs.append(NodeCourse(node=node_obj, course=course_obj))

        NodeCourse.objects.bulk_create(node_course_objs)

        return {
            "major": major,
            "nodes_created": len(id_to_node_obj),
            "courses_created": len(course_objs),
            "node_courses_created": len(node_course_objs)
        }
