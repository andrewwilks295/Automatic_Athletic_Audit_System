from src.models import StudentRecord, StudentAudit, StudentMajor
import pandas as pd 

def output_to_csv(term):

    student_ids = (
        StudentRecord.objects
        .filter(term=term)
        .values_list('student_id', flat=True)
        .distinct()
    )

    data_to_output = []

    for sid in student_ids:
        records = StudentRecord.objects.filter(student_id=sid, term=term)
        student = records.first()
        sa = StudentAudit.objects.filter(student = student).values().first()
        sd = []
        sd.append(sa.get('eligible')) #Valid 0
        sd.append("") #Empty space 1
        sd.append(sid) # T# 2
        sd.append("") # Name 3
        sd.append("") # Sport 4
        sd.append(StudentRecord.objects.filter(student_id = sid).values('first_term').first()['first_term']) #First Full Time Term 5
        sd.append("BS") # Degree 6
        sd.append(StudentMajor.objects.filter(student_id = sid).values('major_id').first()['major_id']) # Program 7
        sd.append(sa.get('major_credits')) # Degree Applicable Credits 8
        sd.append(120) # Total Needed Credits 9
        sd.append(sa.get('ptc_major')) # Percent towards completion 10
        sd.append(sa.get('gpa')) # GPA 11
        sd.append(sd[10] >= 2.0) # Eligible? GPA 12
        sd.append("") # Eligible? PTC 13
        data_to_output.append(sd)

    df = pd.DataFrame(data_to_output)
    df.columns = ["Valid","", "T#", "Name", "Sport", "First FT Term" , "Degree", "Program", "DA Credits", "Total", "PTC", "GPA", "GPA check", "PTC check"]
    df.set_index("T#",inplace=True)
    df.to_csv(str(term) + ".csv")