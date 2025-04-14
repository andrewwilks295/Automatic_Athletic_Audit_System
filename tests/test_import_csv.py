import io
import pandas as pd
from django.test import TestCase
from src.models import Student, Course, MajorMapping, StudentRecord, RequirementNode, NodeCourse
from src.data import import_student_data_from_csv  # or wherever the function lives


class CSVImportTests(TestCase):

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

        self.node = RequirementNode.objects.create(
            major=self.major,
            parent=None,
            name="Core",
            type="credits",
            required_credits=34
        )

        NodeCourse.objects.create(node=self.node, course=self.course)

        self.columns = [
            "ID", "HS_GRAD", "FT_SEM", "MAJOR", "CATALOG", "TERM", "SUBJ",
            "CRSE", "GRADE", "CREDITS", "CRSE_ATTR", "INSTITUTION"
        ]

        self.row = [
            1001, 2022, 202310, "EXSC", 202430, 202430, "KIN", "3050",
            "A", 3, "", "SUU"
        ]

    def test_basic_import_success(self):
        df = pd.DataFrame([self.row], columns=self.columns)
        path = self._save_temp_csv(df)

        result = import_student_data_from_csv(path)

        self.assertTrue(result["success"])
        self.assertEqual(Student.objects.count(), 1)
        self.assertEqual(StudentRecord.objects.count(), 1)

        student = Student.objects.first()
        self.assertEqual(student.major, self.major)

        record = StudentRecord.objects.first()
        self.assertTrue(record.counts_toward_major)

    def test_duplicate_entry_skipped(self):
        df = pd.DataFrame([self.row, self.row], columns=self.columns)
        path = self._save_temp_csv(df)

        result = import_student_data_from_csv(path)

        self.assertTrue(result["success"])
        self.assertEqual(StudentRecord.objects.count(), 1)  # duplicate ignored

    def test_major_change_is_updated(self):
        # First record with original major
        row1 = self.row.copy()
        df1 = pd.DataFrame([row1], columns=self.columns)
        path1 = self._save_temp_csv(df1)
        import_student_data_from_csv(path1)

        # Add another major to the system
        new_major = MajorMapping.objects.create(
            major_code="PSY",
            catalog_year=202430,
            major_name_web="Psychology (B.A., B.S.)",
            major_name_registrar="Psychology",
            total_credits_required=120
        )

        # Second record switches to new major
        row2 = row1.copy()
        row2[self.columns.index("MAJOR")] = "PSY"
        row2[self.columns.index("CRSE")] = "1111"  # different course
        row2[self.columns.index("SUBJ")] = "PSY"
        row2[self.columns.index("CREDITS")] = 3
        df2 = pd.DataFrame([row2], columns=self.columns)
        path2 = self._save_temp_csv(df2)
        import_student_data_from_csv(path2)

        student = Student.objects.get(student_id=1001)
        self.assertEqual(student.major.major_code, "PSY")
        self.assertEqual(StudentRecord.objects.count(), 2)

    def test_skips_invalid_major(self):
        bad_row = self.row.copy()
        bad_row[self.columns.index("MAJOR")] = "FAKE"

        df = pd.DataFrame([bad_row], columns=self.columns)
        path = self._save_temp_csv(df)

        result = import_student_data_from_csv(path)

        self.assertTrue(result["success"])
        self.assertEqual(StudentRecord.objects.count(), 0)

    def test_missing_course_is_created(self):
        # Remove course to force course creation
        self.course.delete()
        df = pd.DataFrame([self.row], columns=self.columns)
        path = self._save_temp_csv(df)

        result = import_student_data_from_csv(path)

        self.assertTrue(result["success"])
        self.assertEqual(Course.objects.filter(course_id="KIN-3050").count(), 1)

    def _save_temp_csv(self, df):
        """
        Save dataframe to temporary path and return its string path.
        Django test runner sets MEDIA_ROOT, so it's safe to write there.
        """
        import tempfile
        f = tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".csv")
        df.to_csv(f.name, index=False)
        return f.name
