from django.db import models


class Student(models.Model):
    student_id = models.IntegerField(primary_key=True)  # aligns with "ID" field from CSV
    major = models.ForeignKey("MajorMapping", null=True, blank=True, on_delete=models.SET_NULL)
    declared_major_code = models.CharField(max_length=20, blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.student_id)


class MajorMapping(models.Model):
    major_code = models.CharField(max_length=20)
    catalog_year = models.IntegerField()
    major_name_web = models.CharField(max_length=255)
    major_name_registrar = models.CharField(max_length=255)
    total_credits_required = models.IntegerField()

    class Meta:
        unique_together = ("major_code", "catalog_year")

    def __str__(self):
        return f"{self.major_code} ({self.catalog_year})"


class Course(models.Model):
    course_id = models.CharField(max_length=12, primary_key=True)
    subject = models.CharField(max_length=8)
    course_number = models.CharField(max_length=8)
    course_name = models.CharField(max_length=255)
    credits = models.IntegerField()

    def __str__(self):
        return f"{self.course_id}: {self.course_name}"


class RequirementNode(models.Model):
    major = models.ForeignKey(MajorMapping, on_delete=models.CASCADE)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=[
        ("credits", "Credit Requirement"),
        ("choose", "Choose One Subgroup"),
        ("header", "Informational Header"),
        ("group", "General Group"),
    ])
    required_credits = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name} ({self.type})"


class NodeCourse(models.Model):
    node = models.ForeignKey(RequirementNode, on_delete=models.CASCADE, related_name="courses")
    course = models.ForeignKey(Course, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.course} in {self.node}"


class StudentRecord(models.Model):
    id = models.AutoField(primary_key=True)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    high_school_grad = models.IntegerField()
    first_term = models.IntegerField()
    term = models.IntegerField()
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    grade = models.CharField(max_length=2)
    credits = models.IntegerField()
    course_attributes = models.CharField(max_length=255, blank=True, null=True)
    institution = models.CharField(max_length=255)
    student_attributes = models.BigIntegerField(blank=True, null=True)
    counts_toward_major = models.BooleanField(default=False, null=True)

    def __str__(self):
        return f"{self.student.student_id} - {self.course.course_id} ({self.grade})"

    class Meta:
        indexes = [
            models.Index(fields=['student']),
            models.Index(fields=['term']),
        ]


class StudentAudit(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    term = models.IntegerField()
    total_term_credits = models.IntegerField()
    da_credits = models.IntegerField()
    total_academic_year_credits = models.IntegerField()
    ptc_major = models.DecimalField(max_digits=5, decimal_places=2)
    satisfactory_ptc_major = models.BooleanField()
    eligible = models.BooleanField()
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    satisfactory_gpa = models.BooleanField()

    class Meta:
        unique_together = ('student', 'term')

    def __str__(self):
        status = "Eligible" if self.eligible else "Ineligible"
        return f"{self.student.student_id} - Term {self.term}: {status} ({self.ptc_major}%)"
