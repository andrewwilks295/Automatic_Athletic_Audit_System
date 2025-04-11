from django.db import transaction

from src.models import StudentRecord, StudentAudit


"""
TODO: Eligibility
We need the following data for output:
- total DA credits
- cumulative GPA
- percent towards completion (completed / total for degree) - still need total degree credits
"""

# Define the grade points mapping
# This mapping is based on the provided grading system.
GRADE_POINTS = {
    'A': 4.0,   'A-': 3.7,
    'B+': 3.3,  'B': 3.0,  'B-': 2.7,
    'C+': 2.3,  'C': 2.0,  'C-': 1.7,
    'D+': 1.3,  'D': 1.0,  'D-': 0.7,
    'F': 0.0,
    'TA': 4.0,   'TA-': 3.7,
    'TB+': 3.3,  'TB': 3.0,  'TB-': 2.7,
    'TC+': 2.3,  'TC': 2.0,  'TC-': 1.7,
    'TD+': 1.3,  'TD': 1.0,  'TD-': 0.7,
    'TF': 0.0,
    'A*': None,   'A-*': None,
    'B+*': None,  'B*': None,  'B-*': None,
    'C+*': None,  'C*': None,  'C-*': None,
    'D+*': None,  'D*': None,  'D-*': None,
    'F*': 0.0,
    'P': None,   # Pass (no GPA impact)
    'NP': 0.0,   # Not Pass
    'W': None,   # Withdrawn
    'I': None,   # Incomplete
    'AU': None   # Audit
}


def get_grade_points(grade: str) -> float | None:
    return GRADE_POINTS.get(grade.strip().upper())


def passed(grade: str) -> bool:
    points = get_grade_points(grade)
    return points is not None and points >= 2.0


# Define rules for particular semesters in a function decorated with @rule.

ELIGIBILITY_RULES = []

def rule(semesters):
    def decorator(func):
        ELIGIBILITY_RULES.append((semesters, func))
        return func

    return decorator


@rule(range(1, 5))  # Semesters 1–4
def freshman_rule(student, records):
    return sum(r.credits for r in records if passed(r.grade)) >= 6


@rule(range(5, 11))  # Semesters 5–10
def upperclass_rule(student, records):
    return sum(r.credits for r in records if passed(r.grade) and r.counts_toward_major) >= 6


def calculate_gpa(sid):
    total_points = 0.0
    total_credits = 0
    records = StudentRecord.objects.filter(student_id=sid)

    for record in records:
        points = get_grade_points(record.grade)
        if points is not None:
            total_points += points * record.credits
            total_credits += record.credits

    return round(total_points / total_credits, 2) if total_credits else 0.0


def get_semester_number(student_id: int, current_term: int, first_term: int) -> int:
    # Get all unique terms the student has taken courses in (after first full-time term)
    terms = (
        StudentRecord.objects
        .filter(student_id=student_id, term__gte=first_term)
        .values_list('term', flat=True)
        .distinct()
    )
    sorted_terms = sorted(terms)

    if current_term not in sorted_terms:
        raise ValueError(f"Current term {current_term} not found for student {student_id}")

    # 1-based semester index
    return sorted_terms.index(current_term) + 1


def run_eligibility_audit(term):
    print(f"\nStarting eligibility audit for term {term}...\n")

    student_ids = (
        StudentRecord.objects
        .filter(term=term)
        .values_list('student_id', flat=True)
        .distinct()
    )

    for sid in student_ids:
        print(f"\nAuditing student ID: {sid}")

        all_terms = (
            StudentRecord.objects
            .filter(student_id=sid)
            .values_list('term', flat=True)
            .distinct()
        )
        sorted_terms = sorted(t for t in all_terms if t >= StudentRecord.objects.filter(student_id=sid).first().first_term)

        if term not in sorted_terms:
            print(f"Term {term} not found in student's active terms. Skipping.")
            continue

        semester_number = sorted_terms.index(term) + 1
        print(f"Full-time semester number: {semester_number}")

        records = StudentRecord.objects.filter(student_id=sid, term=term)
        student = records.first()
        gpa = calculate_gpa(sid)
        print(f"Calculated GPA: {gpa:.2f}")

        eligible = False
        for semesters, rule_fn in ELIGIBILITY_RULES:
            if semester_number in semesters:
                eligible = rule_fn(student, records)
                print(f"Applied rule for semesters {list(semesters)} → Eligible: {eligible}")
                break

        total_credits = sum(r.credits for r in records if passed(r.grade))
        major_credits = sum(r.credits for r in records if passed(r.grade) and r.counts_toward_major)
        ptc_major = round((major_credits / 120) * 100, 2)

        with transaction.atomic():
            audit, created = StudentAudit.objects.update_or_create(
                student=student,
                term=term,
                defaults={
                    'total_credits': total_credits,
                    'major_credits': major_credits,
                    'ptc_major': ptc_major,
                    'gpa': gpa,
                    'eligible': eligible
                }
            )
            status = "created" if created else "updated"
            print(f"StudentAudit {status}: {audit}")
