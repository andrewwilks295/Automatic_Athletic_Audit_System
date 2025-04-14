import pandas as pd
from django.core.exceptions import ValidationError
from django.db import transaction

from src.models import Student, StudentRecord, MajorMapping, Course, NodeCourse


# Data Import Functions
def is_duplicate_record(student_id, term, course_id):
    return StudentRecord.objects.filter(
        student__student_id=student_id,
        term=term,
        course__course_id=course_id
    ).exists()


def import_student_data_from_csv(file_path):
    """
    Reads a CSV file and imports student data into the database.
    Returns a result dict with success status and message.
    """
    try:
        df = pd.read_csv(file_path)

        # Mapping from raw CSV column names to our model fields
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

        # Check required columns
        required_cols = {"ID", "HS_GRAD", "FT_SEM", "MAJOR", "CATALOG", "TERM", "SUBJ", "CRSE", "GRADE", "CREDITS", "INSTITUTION"}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            return {"success": False, "message": f"Missing required columns: {', '.join(missing_cols)}"}

        # Load majors and courses into memory for lookup
        major_map = {(m.major_code, m.catalog_year): m for m in MajorMapping.objects.all()}
        course_map = {c.course_id: c for c in Course.objects.all()}

        students_created = 0
        records_created = 0

        with transaction.atomic():
            for _, row in df.iterrows():
                student_id = int(row["ID"])
                major_code = str(row["MAJOR"]).strip()
                conc_code = str(row["CONC"]).strip() if "CONC" in row and pd.notna(row["CONC"]) else None
                effective_major = conc_code or major_code
                catalog_year = int(row["CATALOG"])
                term = int(row["TERM"])
                course_id = f"{row['SUBJ']}-{row['CRSE']}"

                # Try to find matching major
                major = major_map.get((effective_major, catalog_year))
                if not major:
                    continue  # skip this row if no major match

                # Create or update Student entry
                student, _ = Student.objects.get_or_create(student_id=student_id)

                updated = False
                if student.major != major:
                    student.major = major
                    updated = True
                if student.declared_major_code != major_code:
                    student.declared_major_code = major_code
                    updated = True
                if updated:
                    student.save(update_fields=["major", "declared_major_code"])

                # Create course if missing
                if course_id not in course_map:
                    course = Course.objects.create(
                        course_id=course_id,
                        subject=row["SUBJ"],
                        course_number=row["CRSE"],
                        course_name="",  # Optional, since it's missing in input
                        credits=row["CREDITS"]
                    )
                    course_map[course_id] = course
                else:
                    course = course_map[course_id]

                # Skip if this record already exists
                if StudentRecord.objects.filter(student=student, term=term, course=course).exists():
                    continue

                # Create StudentRecord
                record = StudentRecord(
                    student=student,
                    high_school_grad=row["HS_GRAD"],
                    first_term=row["FT_SEM"],
                    term=term,
                    course=course,
                    grade=row["GRADE"],
                    credits=row["CREDITS"],
                    course_attributes=row.get("CRSE_ATTR", "") if pd.notna(row.get("CRSE_ATTR", "")) else "",
                    institution=row["INSTITUTION"],
                    counts_toward_major=False
                )

                # Check for requirement match
                if course.nodecourse_set.filter(node__major=major).exists():
                    record.counts_toward_major = True

                record.save()
                records_created += 1

            students_created = Student.objects.count()

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
