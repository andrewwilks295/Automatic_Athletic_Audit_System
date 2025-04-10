from django.db import models


class StudentRecord(models.Model):
    id = models.AutoField(primary_key=True)
    student_id = models.IntegerField()
    high_school_grad = models.IntegerField()
    first_term = models.IntegerField()
    term = models.IntegerField()
    course = models.ForeignKey('Course', on_delete=models.CASCADE)
    grade = models.CharField(max_length=2)
    credits = models.IntegerField()
    course_attributes = models.CharField(max_length=255, blank=True, null=True)
    institution = models.CharField(max_length=255)
    student_attributes = models.BigIntegerField(blank=True, null=True)
    counts_toward_major = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.student_id} - {self.course.course_id} ({self.grade})"

    class Meta:
        indexes = [
            models.Index(fields=['student_id']),
            models.Index(fields=['term']),
        ]


class MajorMapping(models.Model):
    major_code = models.CharField(max_length=20, primary_key=True)
    major_name_web = models.CharField(max_length=255, unique=True)
    major_name_registrar = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return f"{self.major_code} - {self.major_name_registrar}"


class StudentMajor(models.Model):
    student = models.ForeignKey(StudentRecord, on_delete=models.CASCADE)
    major = models.ForeignKey(MajorMapping, on_delete=models.CASCADE)
    catalog_year = models.IntegerField()

    class Meta:
        unique_together = ('student', 'major')

    def __str__(self):
        return f"{self.student.student_id} - {self.major.major_name_registrar} ({self.catalog_year})"


class Course(models.Model):
    course_id = models.CharField(max_length=12, primary_key=True)
    subject = models.CharField(max_length=8)
    course_number = models.CharField(max_length=8)
    course_name = models.CharField(max_length=255)
    credits = models.IntegerField()

    def __str__(self):
        return f"{self.course_id}: {self.course_name}"


class RequirementGroup(models.Model):
    major = models.ForeignKey(MajorMapping, on_delete=models.CASCADE, related_name='requirement_groups')
    name = models.CharField(max_length=255)
    group_type = models.CharField(max_length=32, choices=[
        ('credits', 'Complete X Credits'),
        ('choose', 'Choose One Path'),
    ])
    required_credits = models.IntegerField(null=True, blank=True)  # Used only for 'credits' type

    def __str__(self):
        return f"{self.major.major_name_registrar} - {self.name} ({self.group_type})"


class RequirementSubgroup(models.Model):
    group = models.ForeignKey(RequirementGroup, on_delete=models.CASCADE, related_name='subgroups')
    name = models.CharField(max_length=255)
    required_credits = models.IntegerField()

    def __str__(self):
        return f"{self.group.name} → {self.name} ({self.required_credits} credits)"


class MajorCourse(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    group = models.ForeignKey(RequirementGroup, on_delete=models.CASCADE, null=True, blank=True)
    subgroup = models.ForeignKey(RequirementSubgroup, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ('course', 'group', 'subgroup')
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(group__isnull=False, subgroup__isnull=True) |
                    models.Q(group__isnull=True, subgroup__isnull=False)
                ),
                name='majorcourse_group_xor_subgroup'
            )
        ]

    def __str__(self):
        ref = self.subgroup.name if self.subgroup else self.group.name
        return f"{self.course.course_id} in {ref}"


class StudentAudit(models.Model):
    student = models.ForeignKey(StudentRecord, on_delete=models.CASCADE)
    term = models.IntegerField()
    total_credits = models.IntegerField()
    major_credits = models.IntegerField()
    ptc_major = models.DecimalField(max_digits=5, decimal_places=2)
    eligible = models.BooleanField()
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)

    class Meta:
        unique_together = ('student', 'term')

    def __str__(self):
        status = "Eligible" if self.eligible else "Ineligible"
        return f"{self.student.student_id} - Term {self.term}: {status} ({self.ptc_major}%)"


class StudentGroupResult(models.Model):
    audit = models.ForeignKey(StudentAudit, on_delete=models.CASCADE)
    group = models.ForeignKey(RequirementGroup, on_delete=models.CASCADE)
    satisfied = models.BooleanField()
    selected_subgroup = models.ForeignKey(RequirementSubgroup, null=True, blank=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.group.name} - {'✓' if self.satisfied else '✗'}"
