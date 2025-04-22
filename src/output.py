from src.models import Student, StudentRecord, StudentAudit, AuditFlag, MajorMapping
import pandas as pd


def change_bool_to_checkmark(b: bool):
    return '✔' if b else 'X'


def eligible_column_output(b: bool):
    return "X" if b else ""


def create_dataframe(term):
    student_ids = (
        StudentRecord.objects
        .filter(term=term)
        .values_list('student_id', flat=True)
        .distinct()
    )

    data_to_output = []

    for sid in student_ids:
        student = Student.objects.filter(student_id=sid).first()
        sa = StudentAudit.objects.filter(student=sid).first()
        major = student.major if student else None

        first_term = (
            StudentRecord.objects
            .filter(student_id=sid)
            .values_list('first_term', flat=True)
            .first()
        )

        ft_term_cnt = (
            StudentRecord.objects
            .filter(student_id=sid)
            .values_list('student_attributes', flat=True)
            .first()
        )

        flags = AuditFlag.objects.filter(student_audit=sa)
        flag_messages = "; ".join(
            f"[{f.level.upper()}] {f.code}: {f.message or ''}" for f in flags
        )

        sd = [
            eligible_column_output(sa.eligible),                          # [0] Valid
            sid,                                                          # [1] T#
            "",                                                           # [2] Name
            "",                                                           # [3] Sport
            first_term or "",                                             # [4] First FT Term
            "BS",                                                         # [5] Degree
            major.major_code if major else "",                           # [6] Program
            sa.da_credits,                                                # [7] DA Credits
            major.total_credits_required if major else "",               # [8] Total
            sa.ptc_major,                                                 # [9] PTC
            change_bool_to_checkmark(sa.total_term_credits >= 6),        # [10] 6
            change_bool_to_checkmark(sa.total_term_credits >= 9),        # [11] 9
            change_bool_to_checkmark(sa.total_academic_year_credits >= 18),  # [12] 18
            change_bool_to_checkmark(sa.total_academic_year_credits >= 24),  # [13] 24
            sa.gpa,                                                       # [14] GPA
            change_bool_to_checkmark(sa.satisfactory_gpa),               # [15] GPA check
            change_bool_to_checkmark(sa.satisfactory_ptc_major),         # [16] PTC check
            sa.total_term_credits,                                        # [17] 6_DA
            sa.total_academic_year_credits,                               # [18] 18_Taken
            ft_term_cnt or "",                                            # [19] FT_TERM_CNT
            flag_messages                                                 # [20] Notes
        ]

        data_to_output.append(sd)

    df = pd.DataFrame(data_to_output)
    df.columns = [
        "Valid", "T#", "Name", "Sport", "First FT Term", "Degree", "Program",
        "DA Credits", "Total", "PTC", "6", "9", "18", "24", "GPA", "GPA check",
        "PTC check", "6_DA", "18_Taken", "FT_TERM_CNT", "Notes"
    ]
    df.set_index("T#", inplace=True)
    return df


def output_to_csv(term):
    df = create_dataframe(term)
    df.to_csv(str(term) + ".csv")


def output_to_xlsx(term):
    df = create_dataframe(term)
    filepath = str(term) + ".xlsx"
    df.to_excel(filepath)
