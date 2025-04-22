import pandas as pd
from django.db import transaction

from src.models import Student, StudentRecord, MajorMapping, Course, NodeCourse, RequirementNode
from src.utils import load_major_code_lookup, normalize_catalog_term


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
            "FT_TERM": "first_term",
            "MAJOR": "major_code",
            "CONC": "concentration_code",
            "CATALOG": "catalog_year",
            "TERM": "term",
            "SUBJ": "subject",
            "CRSE": "course_number",
            "GRADE": "grade",
            "CREDITS": "credits",
            "CRSE_ATTR": "course_attributes",
            "INSTITUTION": "institution",
            "FT_TERM_CNT": "ft_term_cnt"
        }

        required_cols = set(col_map.keys()) - {"CONC", "CRSE_ATTR"}
        missing = required_cols - set(df.columns)
        if missing:
            return {"success": False, "message": f"Missing required columns: {', '.join(missing)}"}

        # Load major and course mappings from DB
        major_map = {(m.major_code, m.catalog_year): m for m in MajorMapping.objects.all()}
        course_map = {c.course_id: c for c in Course.objects.all()}

        # Load web name → major code mapping
        major_lookup_df = load_major_code_lookup("major_codes.csv")
        name_to_code = dict(zip(major_lookup_df["Major Name Web"], major_lookup_df["Major Code"]))

        students_created = 0
        records_created = 0
        unmatched_majors: dict[str, list[str]] = {}

        with transaction.atomic():
            for _, row in df.iterrows():
                student_id = str(row["ID"])
                major_code = str(row["MAJOR"]).strip()
                conc_code = str(row["CONC"]).strip() if "CONC" in row and pd.notna(row["CONC"]) else None
                effective_code = conc_code or major_code
                catalog_year = normalize_catalog_term(int(row["CATALOG"]))
                term = int(row["TERM"])
                course_id = f"{row['SUBJ']}-{row['CRSE']}"

                # Verify that the major exists in scraped data
                matched_web_names = major_lookup_df.loc[
                    major_lookup_df["Major Code"] == effective_code, "Major Name Web"
                ]
                if matched_web_names.empty:
                    unmatched_majors.setdefault(effective_code, []).append(student_id)
                    continue

                major_obj = major_map.get((effective_code, catalog_year))
                if not major_obj:
                    unmatched_majors.setdefault(effective_code, []).append(student_id)
                    continue

                # Create or update Student
                student, _ = Student.objects.get_or_create(student_id=student_id)
                updated = False
                if student.major != major_obj:
                    student.major = major_obj
                    updated = True
                if student.declared_major_code != major_code:
                    student.declared_major_code = major_code
                    updated = True
                if updated:
                    student.save(update_fields=["major", "declared_major_code"])

                # Create or find Course
                if course_id not in course_map:
                    course = Course.objects.create(
                        course_id=course_id,
                        subject=row["SUBJ"],
                        course_number=row["CRSE"],
                        course_name="",  # Optional field
                        credits=row["CREDITS"]
                    )
                    course_map[course_id] = course
                else:
                    course = course_map[course_id]

                if StudentRecord.objects.filter(student=student, term=term, course=course).exists():
                    continue  # skip duplicate records

                if not pd.notna(row.get("CREDITS")):
                    continue  # skip any rows without CREDITS since those are likely incomplete.

                record = StudentRecord(
                    student=student,
                    high_school_grad=row.get("HS_GRAD", row.get("FT_TERM")),
                    first_term=row["FT_TERM"],
                    term=term,
                    course=course,
                    grade=row["GRADE"],
                    credits=int(row["CREDITS"]),
                    course_attributes=row.get("CRSE_ATTR", "") if pd.notna(row.get("CRSE_ATTR", "")) else "",
                    institution=row["INSTITUTION"],
                    counts_toward_major=False,
                    ft_term_cnt=int(row.get("FT_TERM_CNT", 0))
                )

                # Determine degree applicability
                if course.nodecourse_set.filter(node__major=major_obj).exists():
                    record.counts_toward_major = True

                record.save()
                records_created += 1

            students_created = Student.objects.count()

        if unmatched_majors:
            print("\n⚠️ Unmatched majors found in CSV (no corresponding scraped catalog):")
            for major, students in unmatched_majors.items():
                print(f" - {major}: {', '.join(list(set(students)))}")

        return {
            "success": True,
            "message": f"Imported {records_created} student records across {students_created} students."
        }

    except Exception as e:
        return {"success": False, "message": f"Unexpected error: {e}"}


def populate_catalog_from_payload(payload):
    with transaction.atomic():
        major_data = payload["major"]

        # Create or update MajorMapping
        major, _ = MajorMapping.objects.update_or_create(
            major_code=major_data["major_code"],
            catalog_year=major_data["catalog_year"],
            defaults={
                "base_major_code": major_data.get("base_major_code"),
                "major_name_web": major_data["major_name_web"],
                "major_name_registrar": major_data["major_name_registrar"],
                "total_credits_required": major_data["total_credits_required"]
            }
        )

        # Create missing courses
        course_ids = [c["course_id"] for c in payload["courses"]]
        existing_ids = set(
            Course.objects.filter(course_id__in=course_ids).values_list("course_id", flat=True)
        )
        new_courses = [Course(**c) for c in payload["courses"] if c["course_id"] not in existing_ids]
        if new_courses:
            Course.objects.bulk_create(new_courses)

        # Refresh the course map to include new inserts
        course_map = {
            c.course_id: c for c in Course.objects.filter(course_id__in=course_ids)
        }

        # Insert RequirementNodes and preserve parent structure
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

        # Create NodeCourse mappings
        node_course_objs = []
        for nc in payload["node_courses"]:
            node_obj = id_to_node_obj[nc["node_id"]]
            course_obj = course_map[nc["course_id"]]
            node_course_objs.append(NodeCourse(node=node_obj, course=course_obj))

        NodeCourse.objects.bulk_create(node_course_objs)

        return {
            "major": major,
            "nodes_created": len(id_to_node_obj),
            "courses_created": len(new_courses),
            "node_courses_created": len(node_course_objs)
        }
