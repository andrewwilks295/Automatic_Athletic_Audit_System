import pandas as pd
from django.db import transaction
from myapp.models import Course, MajorMapping, MajorCourse

def update_major_course_associations(file_path):
    """
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
                
if __name__ == "__main__":
    # Path to the Exercise Science CSV file
    file_path = "Exercise Science (B.S.).csv"
    update_major_course_associations(file_path)
