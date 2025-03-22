from django.db import models


class StudentRecord(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.IntegerField()
    high_school_grad = models.IntegerField()
    first_term = models.IntegerField()  # First term of full-time college enrollment
    term = models.IntegerField()  # Current term
    course = models.ForeignKey('Course', on_delete=models.CASCADE)  # Course taken
    grade = models.CharField(max_length=2)  # Letter grade (e.g., 'A', 'B', 'C', etc.)
    credits = models.IntegerField()  # Credit hours
    course_attributes = models.CharField(max_length=255, blank=True, null=True)  # Any additional attributes
    institution = models.CharField(max_length=255)  # Where course was taken
    student_attributes = models.BigIntegerField(blank=True, null=True)  # Other flags
    counts_toward_major = models.BooleanField(default=False)  # for PTD calculations

    def __str__(self):
        return f"{self.student_id} - {self.course.course_id} ({self.grade})"


class MajorMapping(models.Model):
    major_code = models.CharField(max_length=20, primary_key=True)  # Unique code from the dataset from registrar
    major_name_web = models.CharField(max_length=255, unique=True)  # Web scraped major name
    # the course name as it appears in 'Major Codes.xlsx'
    major_name_registrar = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.major_code} - {self.major_name_registrar}"


class StudentMajor(models.Model):
    student = models.ForeignKey(StudentRecord, on_delete=models.CASCADE)  # Student association
    major = models.ForeignKey(MajorMapping, on_delete=models.CASCADE)  # Major mapping
    catalog_year = models.IntegerField()  # Year student follows for degree requirements

    class Meta:
        unique_together = ('student', 'major')  # Each student-major pair should be unique

    def __str__(self):
        return f"{self.student.student_id} - {self.major.major_name} ({self.catalog_year})"


class Course(models.Model):
    course_id = models.CharField(max_length=12, primary_key=True)  # SUBJECT-COURSE_NUMBER
    subject = models.CharField(max_length=8)
    course_number = models.CharField(max_length=8)
    credits = models.IntegerField()

    def __str__(self):
        return f"{self.course_id}: {self.course_name}"


class MajorCourse(models.Model):
    major = models.ForeignKey(MajorMapping, on_delete=models.CASCADE)  # The major
    course = models.ForeignKey(Course, on_delete=models.CASCADE)  # The course
    REQUIREMENT_TYPES = [
        ('Core', 'Core Requirement'),
        ('Elective', 'Elective'),
        ('Not Applicable', 'Not Applicable')
    ]
    requirement_type = models.CharField(max_length=20, choices=REQUIREMENT_TYPES)  # Classification

    class Meta:
        unique_together = ('major', 'course')  # Each major-course pair should be unique

    def __str__(self):
        return f"{self.major.major_name} - {self.course.course_name} ({self.requirement_type})"


class StudentAudit(models.Model):
    student = models.ForeignKey(StudentRecord, on_delete=models.CASCADE)  # Student association
    term = models.IntegerField()  # Semester of audit
    total_credits = models.IntegerField()  # Total attempted credits
    major_credits = models.IntegerField()  # Credits applicable to major
    ptc_major = models.DecimalField(max_digits=5, decimal_places=2)  # % toward degree
    eligible = models.BooleanField()  # Final eligibility status
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('student', 'term')  # Each student should only have one audit per term

    def __str__(self):
        status = "Eligible" if self.eligible else "Ineligible"
        return f"{self.student.student_id} - Term {self.term}: {status} ({self.ptc_major}%)"
