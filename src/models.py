from django.db import models

class StudentRecord(models.Model):
    student_id = models.IntegerField()
    high_school_grad = models.IntegerField()
    first_term = models.IntegerField()
    major = models.CharField(max_length=100, null=True, blank=True)
    concentration = models.CharField(max_length=100, null=True, blank=True)
    minors = models.CharField(max_length=100, null=True, blank=True)
    catalog_year = models.IntegerField()
    term = models.IntegerField()
    subject = models.CharField(max_length=10)
    course_number = models.CharField(max_length=10)
    grade = models.CharField(max_length=5, null=True, blank=True)
    credits = models.IntegerField()
    course_attribute = models.CharField(max_length=10, null=True, blank=True)
    institution = models.CharField(max_length=50)
    student_attribute = models.CharField(max_length=50, null=True, blank=True)

    def __str__(self):
        return f"{self.student_id} - {self.subject} {self.course_number}"
