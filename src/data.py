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
    Automatically updates each student's declared major to reflect the latest entry.
    Skips duplicate course records per student+term+course_id.
    """
    try:
        df = pd.read_csv(file_path)

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

        readable_to_col = {v: k for k, v in col_to_readable.items()}

        required_columns = {
            "student_id", "high_school_grad", "first_term", "major", "catalog_year",
            "term", "subject", "course_number", "grade", "credits", "institution"
        }
        missing = [
            readable_to_col[c] for c in required_columns
            if readable_to_col.get(c) not in df.columns
        ]
        if missing:
            return {"success": False, "message": f"Missing required columns: {', '.join(missing)}"}

        existing_majors = {
            (m.major_code, m.catalog_year): m
            for m in MajorMapping.objects.all()
        }
        existing_courses = {
            c.course_id: c
            for c in Course.objects.all()
        }
        existing_students = {
            s.student_id: s
            for s in Student.objects.all()
        }

        new_students = []
        new_courses = []
        new_records = []

        # Used to prevent inserting duplicates from within the same CSV
        seen = set()

        with transaction.atomic():
            for _, row in df.iterrows():
                student_id = row[readable_to_col["student_id"]]
                major_code = row[readable_to_col["major"]]
                catalog_year = row[readable_to_col["catalog_year"]]
                term = row[readable_to_col["term"]]
                subject = row[readable_to_col["subject"]]
                number = row[readable_to_col["course_number"]]
                course_id = f"{subject}-{number}"

                # Ensure major exists
                major = existing_majors.get((major_code, catalog_year))
                if not major:
                    continue

                # Ensure course exists
                if course_id not in existing_courses:
                    course = Course(
                        course_id=course_id,
                        subject=subject,
                        course_number=number,
                        course_name="",
                        credits=row[readable_to_col["credits"]]
                    )
                    new_courses.append(course)
                    existing_courses[course_id] = course

                # Ensure student exists
                if student_id in existing_students:
                    student = existing_students[student_id]
                    if student.major != major:
                        student.major = major
                        student.save()
                else:
                    student = Student(student_id=student_id, major=major)
                    new_students.append(student)
                    existing_students[student_id] = student

                # Prevent duplicate inserts
                duplicate_key = (student_id, term, course_id)
                if duplicate_key in seen or StudentRecord.objects.filter(
                    student__student_id=student_id,
                    term=term,
                    course__course_id=course_id
                ).exists():
                    continue
                seen.add(duplicate_key)

                # Check if course counts toward this major
                counts_toward_major = NodeCourse.objects.filter(
                    course__course_id=course_id,
                    node__major=major
                ).exists()

                record = StudentRecord(
                    student=student,
                    high_school_grad=row[readable_to_col["high_school_grad"]],
                    first_term=row[readable_to_col["first_term"]],
                    term=term,
                    course=existing_courses[course_id],
                    grade=row[readable_to_col["grade"]],
                    credits=row[readable_to_col["credits"]],
                    course_attributes=row.get(readable_to_col.get("course_attributes")),
                    institution=row[readable_to_col["institution"]],
                    counts_toward_major=counts_toward_major
                )
                new_records.append(record)

            # Perform bulk inserts
            Course.objects.bulk_create(new_courses, ignore_conflicts=True)
            Student.objects.bulk_create(new_students, ignore_conflicts=True)
            StudentRecord.objects.bulk_create(new_records, ignore_conflicts=True)

        inserted = len(new_records)
        if inserted > 0:
            msg = f"Imported {inserted} student records."
        else:
            msg = "No new records inserted. All entries may have been duplicates or already uploaded."

        return {
            "success": True,
            "message": msg
        }

    except ValidationError as e:
        return {"success": False, "message": f"Validation error: {e}"}
    except FileNotFoundError as e:
        return {"success": False, "message": f"File not found: {e}"}
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
