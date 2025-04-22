from django.db import transaction
from typing import List
from src.models import *

GRADE_POINTS = {
    'A': 4.0, 'A-': 3.7, 'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7, 'D+': 1.3, 'D': 1.0, 'D-': 0.7,
    'F': 0.0, 'TA': 4.0, 'TA-': 3.7, 'TB+': 3.3, 'TB': 3.0, 'TB-': 2.7,
    'TC+': 2.3, 'TC': 2.0, 'TC-': 1.7, 'TD+': 1.3, 'TD': 1.0, 'TD-': 0.7,
    'TF': 0.0, 'F*': 0.0, 'NP': 0.0,
    'A*': None, 'A-*': None, 'B+*': None, 'B*': None, 'B-*': None,
    'C+*': None, 'C*': None, 'C-*': None, 'D+*': None, 'D*': None, 'D-*': None,
    'P': None, 'W': None, 'I': None, 'AU': None
}

def get_grade_points(grade: str) -> float | None:
    return GRADE_POINTS.get(grade.strip().upper())

def passed(grade: str) -> bool:
    points = get_grade_points(grade)
    return points is not None and points >= 2.0

class Requirement:
    def __init__(self, req: RequirementNode):
        self.__complete = False
        self.__courses = NodeCourse.objects.filter(node=req)
        self.__required_credits = req.required_credits
        self.credits = 0

    def is_complete(self) -> bool:
        return self.__complete

    def completed(self):
        self.__complete = True

    def is_required_course(self, stu_rec_course: Course) -> bool:
        for c in self.__courses:
            if c.course.course_id == stu_rec_course.course_id:
                self.credits += stu_rec_course.credits
                if self.__required_credits <= self.credits:
                    self.completed()
                return True
        return False

def create_req_list(major_id):
    requirements = RequirementNode.objects.filter(major=major_id)
    return [Requirement(r) for r in requirements if r.required_credits is not None]

def check_if_required(req_list: List[Requirement], course_id) -> bool:
    return any(not r.is_complete() and r.is_required_course(course_id) for r in req_list)

def calculate_gpa(sid):
    total_points = 0.0
    total_credits = 0
    for record in StudentRecord.objects.filter(student_id=sid):
        points = get_grade_points(record.grade)
        if points is not None:
            total_points += points * record.credits
            total_credits += record.credits
    return round(total_points / total_credits, 2) if total_credits else 0.0

def run_audit(current_term: int):
    print(f"\nStarting eligibility audit for term {current_term}...\n")

    student_ids = (
        StudentRecord.objects
        .filter(term=current_term)
        .values_list('student_id', flat=True)
        .distinct()
    )

    if not student_ids:
        print("No Students found.")

    for sid in student_ids:
        print(f"\nAuditing student ID: {sid}")
        student = Student.objects.filter(student_id=sid).first()
        if not student:
            continue

        major = student.major
        if not major:
            gpa = calculate_gpa(sid)
            audit = StudentAudit.objects.create(
                student=student,
                term=current_term,
                total_term_credits=0,
                da_credits=0,
                total_academic_year_credits=0,
                ptc_major=0,
                satisfactory_ptc_major=False,
                eligible=False,
                gpa=gpa,
                satisfactory_gpa=gpa >= 2.0
            )
            audit.add_flag(
                code="missing_major",
                level=AuditFlag.ERROR,
                message="Student has no associated major in the database. Manual review required."
            )
            print(f"❌ Missing major for student {sid}. Audit flagged.")
            continue

        first_record = StudentRecord.objects.filter(student=sid).first()
        if not first_record:
            continue

        num_terms = student.ft_term_cnt
        print(f"Full-time semester number: {num_terms}")

        records = StudentRecord.objects.filter(student=sid)
        major_requirements = create_req_list(major)

        credits_c_term = 0
        total_credits_academic_year = 0
        da_credits_c_term = 0
        total_da_credits = 0

        if num_terms <= 2:
            terms = records.values_list("term", flat=True).distinct()
            latest_full_academic_year = sorted(list(terms))
        elif current_term % 100 == 30:
            latest_full_academic_year = [current_term - 100, current_term - 20]
        elif current_term % 100 == 10:
            latest_full_academic_year = [current_term - 80, current_term]
        else:
            latest_full_academic_year = [current_term - 90, current_term - 10]

        for record in records:
            if passed(record.grade):
                if record.term == current_term:
                    credits_c_term += record.credits
                if record.term in latest_full_academic_year:
                    total_credits_academic_year += record.credits
                if check_if_required(major_requirements, record.course):
                    if record.term == current_term:
                        da_credits_c_term += record.credits
                    total_da_credits += record.credits

        gpa = calculate_gpa(sid)
        ptc = (total_da_credits / major.total_credits_required) * 100 if major.total_credits_required else 0

        current_term_credits = credits_c_term if num_terms < 5 else da_credits_c_term

        satisfactory_gpa = (
            gpa >= 1.8 if num_terms < 3 else
            gpa >= 1.9 if num_terms < 5 else
            gpa >= 2.0
        )
        satisfactory_ptc = (
            ptc > 40.0 if num_terms == 4 else
            ptc > 60.0 if num_terms == 6 else
            ptc > 80.0 if num_terms == 8 else
            True
        )
        satisfactory_term_credits = current_term_credits >= 6
        satisfactory_year_credits = (
            True if num_terms == 1 else
            total_credits_academic_year >= 24 if num_terms == 2 else
            total_credits_academic_year >= 18
        )

        eligible = all([
            satisfactory_gpa,
            satisfactory_ptc,
            satisfactory_term_credits,
            satisfactory_year_credits
        ])

        with transaction.atomic():
            audit, created = StudentAudit.objects.update_or_create(
                student=student,
                term=current_term,
                defaults={
                    'total_term_credits': current_term_credits,
                    'da_credits': total_da_credits,
                    'total_academic_year_credits': total_credits_academic_year,
                    'ptc_major': ptc,
                    'satisfactory_ptc_major': satisfactory_ptc,
                    'eligible': eligible,
                    'gpa': gpa,
                    'satisfactory_gpa': satisfactory_gpa
                }
            )
            print(f"StudentAudit {'created' if created else 'updated'}: {audit}")
