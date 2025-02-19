from django.test import TestCase
from src.models import StudentRecord

from src.data import import_student_records

#  test cases for data modules


class StudentRecordTest(TestCase):

    def setUp(self):
        # create test data here
        return super().setUp()
    
    def test_import_student_records_from_csv(self):
        # test import_student_records function here
        ...

