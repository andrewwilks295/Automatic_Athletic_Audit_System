from django.db import transaction
from typing import List
from src.models import *


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

# Create requirements class to simplify audit
class Requirement:
    def __init__(self, req: RequirementNode):
        self.__complete = False
        self.__courses = NodeCourse.objects.filter(node = req)
        self.__required_credits = req.required_credits
        self.credits = 0

    def __str__(self):
        return f"Complete: {self.__complete}, Required Credits: {self.__required_credits}, Current credits: {self.credits}, Courses: {self.__courses}"

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


#Creates list of all requirements for the major with the provided major id
def create_req_list(major_id):
    requirements = RequirementNode.objects.filter(major = major_id)
    return [Requirement(r) for r in requirements if r.required_credits is not None]


def check_if_required(req_list: List[Requirement], course_id) -> bool:
    for req in req_list:
        #print("check")
        if not req.is_complete() and req.is_required_course(course_id):
            return True
    return False


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
    sorted_terms = list(sorted(terms))

    #Remove non full time terms
    terms_to_remove = []
    records = StudentRecord.objects.filter(student_id=student_id)
    for term in sorted_terms:
        count = 0
        for record in records:
            if record.term == term:
                count += record.credits
        if count < 12:
            terms_to_remove.append(term)
    
    sorted_terms = [item for item in sorted_terms if item not in terms_to_remove]

    # 1-based semester index
    return len(sorted_terms)

def run_audit(current_term: int):
    print(f"\nStarting eligibility audit for term {current_term}...\n")
    #Get ids of all students
    student_ids = (
        StudentRecord.objects
        .filter(term=current_term)
        .values_list('student_id', flat=True)
        .distinct()
    )

    if student_ids.count() == 0:
        print("No Students found.")

    for sid in student_ids:
        print(f"\nAuditing student ID: {sid}")
        #Gather information needed for audit
        first_term = StudentRecord.objects.filter(student = sid).first().first_term
        num_terms = get_semester_number(sid, current_term, first_term)
        print(f"Full-time semester number: {num_terms}")
        credits_c_term = 0
        total_credits_academic_year = 0
        da_credits_c_term = 0
        total_da_credits = 0
        if num_terms <= 2:
            terms = (
                StudentRecord.objects
                .filter(student_id=sid)
                .values_list('term', flat=True)
                .distinct()
            )
            latest_full_academic_year = sorted(list(terms))
        elif current_term % 100 == 30:
            latest_full_academic_year = [current_term - 100, current_term-20]
        elif current_term % 100 == 10:
            latest_full_academic_year = [current_term - 80, current_term]
        else:
            latest_full_academic_year = [current_term - 90, current_term-10]
        records = StudentRecord.objects.filter(student_id=sid)
        major = Student.objects.filter(student_id = sid).first().major
        major_requirements = create_req_list(major)

        # Total up credits
        for record in records:
            if passed(record.grade):
                if record.term == current_term:
                    credits_c_term += record.credits
                if record.term in latest_full_academic_year:
                    total_credits_academic_year += record.credits
                if check_if_required(major_requirements,record.course):
                    if record.term == current_term:
                        da_credits_c_term += record.credits
                    total_da_credits += record.credits
        
        #Checking the Above is correct
        #print(credits_c_term)
        #print(total_credits_academic_year)
        #print(da_credits_c_term)
        #print(total_da_credits)
        
        
        #Calculate GPA and PTC
        gpa = calculate_gpa(sid)
        ptc = (total_da_credits/major.total_credits_required) * 100

        #Grab correct term numbers for semester number
        if num_terms in range(1,5):
            current_term_credits = credits_c_term
        else :
            current_term_credits = da_credits_c_term

        #Check GPA
        satisfactory_gpa = False
        if num_terms < 3:
            satisfactory_gpa = gpa >= 1.8
        elif num_terms < 5:
            satisfactory_gpa = gpa >= 1.9
        else:
            satisfactory_gpa = gpa >= 2.0

        #Check PTC
        satisfactory_ptc = False
        if num_terms == 4:
            satisfactory_ptc = ptc > 40.0
        elif num_terms == 6:
            satisfactory_ptc = ptc > 60.0
        elif num_terms == 8:
            satisfactory_ptc = ptc > 80.0
        else:
            satisfactory_ptc = True
        
        #Check Term Credits
        satisfactory_term_credits = current_term_credits >= 6

        #Check Academic Year Credits
        satisfactory_year_credits = False
        if num_terms == 1:
            satisfactory_year_credits = True
        elif num_terms ==2:
            satisfactory_year_credits = total_credits_academic_year >= 24
        else:
            satisfactory_year_credits = total_credits_academic_year >= 18

        #Checking the Above is correct
        #print(satisfactory_gpa)
        #print(satisfactory_ptc)
        #print(satisfactory_term_credits)
        #print(satisfactory_year_credits)

        #Check Elegiblity
        eligible = satisfactory_gpa and satisfactory_ptc and satisfactory_term_credits and satisfactory_year_credits

        #Pass info to db
        with transaction.atomic():
            audit, created = StudentAudit.objects.update_or_create(
                student = Student.objects.filter(student_id = sid).first,
                term = current_term,
                defaults={
                    'total_term_credits' : current_term_credits,
                    'da_credits' : total_da_credits,
                    'total_academic_year_credits' : total_credits_academic_year,
                    'ptc_major': ptc,
                    'satisfactory_ptc_major': satisfactory_ptc,
                    'eligible': eligible,
                    'gpa' : gpa,
                    'satisfactory_gpa' : satisfactory_gpa
                }
            )
            status = "created" if created else "updated"
            print(f"StudentAudit {status}: {audit}")