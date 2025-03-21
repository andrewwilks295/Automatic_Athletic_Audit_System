import django
import os

# initialize django (sqlite ORM only)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from src.data import import_student_data_from_csv, update_major_course_associations

import pandas as pd
from django.db import transaction
from src.models import Course, MajorMapping, MajorCourse


def run():
    # filepath = "Automatic Athletic Audit System/cleaned_bogus_data.csv"
    # print(import_student_data_from_csv(filepath))
    majors = MajorMapping.objects.all()
    with open('majors.txt', 'w') as mtxt:
        for major in majors:
            mtxt.write(major.major_name_web + "\n")


if __name__ == '__main__':
    ...
    # TODO: fix course association code to populate MajorCourse table. Run code below after.
    # file_path = "Automatic Athletic Audit System/WebScrapping Catalog Site/2024-2025/Exercise Science (B.S.).csv"
    # update_major_course_associations(file_path)
