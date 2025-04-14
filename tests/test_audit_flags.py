from django.test import TestCase
from src.models import Student, Course, MajorMapping, StudentRecord, StudentAudit, AuditFlag

class AuditFlagTests(TestCase):
    def setUp(self):
        self.major = MajorMapping.objects.create(
            major_code="EXSC",
            catalog_year=202430,
            major_name_web="Exercise Science (B.S.)",
            major_name_registrar="Exercise Science",
            total_credits_required=120
        )

        self.course = Course.objects.create(
            course_id="KIN-3050",
            subject="KIN",
            course_number="3050",
            course_name="Motor Learning",
            credits=3
        )

        self.student = Student.objects.create(
            student_id=1001,
            major=self.major
        )

        self.record = StudentRecord.objects.create(
            student=self.student,
            high_school_grad=2022,
            first_term=202310,
            term=202430,
            course=self.course,
            grade="A",
            credits=3,
            institution="SUU"
        )

        self.audit = StudentAudit.objects.create(
            student=self.student,
            term=202430,
            total_term_credits=3,
            da_credits=3,
            total_academic_year_credits=3,
            ptc_major=5.0,
            satisfactory_ptc_major=False,
            gpa=4.0,
            satisfactory_gpa=True,
            eligible=False
        )

    def test_create_flag(self):
        self.audit.add_flag(
            code="partial_history",
            level=AuditFlag.WARNING,
            message="Only 1 term found."
        )
        self.assertEqual(AuditFlag.objects.count(), 1)
        flag = AuditFlag.objects.first()
        self.assertEqual(flag.level, AuditFlag.WARNING)
        self.assertEqual(flag.student_audit, self.audit)

    def test_cascade_delete(self):
        self.audit.add_flag(
            code="unsupported_major",
            level=AuditFlag.ERROR,
            message="Missing catalog data"
        )
        self.assertEqual(AuditFlag.objects.count(), 1)

        # Delete the audit → should also delete the flag
        self.audit.delete()
        self.assertEqual(AuditFlag.objects.count(), 0)
