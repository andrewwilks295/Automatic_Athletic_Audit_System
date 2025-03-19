import django
import os

# initialize django (sqlite ORM only)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
django.setup()

from src.data import import_student_data_from_csv
from src.models import MajorMapping


def run():
    # filepath = "Automatic Athletic Audit System/cleaned_bogus_data.csv"
    # print(import_student_data_from_csv(filepath))
    majors = MajorMapping.objects.all()
    with open('majors.txt', 'w') as mtxt:
        for major in majors:
            mtxt.write(major.major_name_web + "\n")


if __name__ == '__main__':
    run()
    print("Goodbye.")
