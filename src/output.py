from src.models import Student, StudentRecord, StudentAudit, AuditFlag, MajorMapping
from src.eligibility import get_semester_number
import pandas as pd 


def change_bool_to_checkmark(b: bool):
    if b:
        return chr(ord('✔'))
    else:
        return 'X'
    
def eligible_column_output(b: bool):
    if b:
        return "X"
    else:
        return ""

def create_dataframe(term):
    student_ids = (
        StudentRecord.objects
        .filter(term=term)
        .values_list('student_id', flat=True)
        .distinct()
    )

    data_to_output = []

    for sid in student_ids:
        student = Student.objects.filter(student_id = sid).first()
        sa = StudentAudit.objects.filter(student = sid).values().first()
        major = student.major
        sd = []
        sd.append(eligible_column_output(sa.get('eligible'))) #Valid 0
        sd.append(sid) # T# 1
        sd.append("") # Name 2
        sd.append("") # Sport 3
        sd.append(StudentRecord.objects.filter(student_id = sid).values('first_term').first()['first_term']) #First Full Time Term 4
        sd.append("BS") # Degree 5
        sd.append(major.major_code) # Program 6
        sd.append(sa.get('da_credits')) # Degree Applicable Credits 7
        sd.append(major.total_credits_required) # Total Needed Credits 8
        sd.append(sa.get('ptc_major')) # Percent towards completion 9
        sd.append(change_bool_to_checkmark(sa.get('total_term_credits') >= 6)) # 6 credits taken 10
        sd.append(change_bool_to_checkmark(sa.get('total_term_credits') >= 9)) # 9 credits taken 11
        sd.append(change_bool_to_checkmark(sa.get('total_term_credits') >= 6)) # 18 credits taken full year 12
        sd.append(change_bool_to_checkmark(sa.get('total_term_credits') >= 9)) # 24 credits taken full year 13
        sd.append(sa.get('gpa')) # GPA 14
        sd.append(change_bool_to_checkmark(sa.get('satisfactory_gpa'))) # Eligible? GPA 15
        sd.append(change_bool_to_checkmark(sa.get('satisfactory_ptc_major'))) # Eligible? PTC 16
        sd.append(sa.get('total_term_credits')) #6 DA 17
        sd.append(sa.get('total_academic_year_credits')) #18 Taken 18
        data_to_output.append(sd)
    
    df = pd.DataFrame(data_to_output)
    df.columns = ["Valid", "T#", "Name", "Sport", "First FT Term" , "Degree", "Program", "DA Credits", "Total", "PTC","6", "9", "18", "24" , "GPA", "GPA check", "PTC check","6_DA", "18_Taken"]
    df.set_index("T#",inplace=True)

    return df   

def output_to_csv(term):
    df = create_dataframe(term)
    df.to_csv(str(term) + ".csv")

def output_to_xlsx(term):
    df = create_dataframe(term)
    filepath = str(term) + ".xlsx"
    df.to_excel(filepath)