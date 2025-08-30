from django.db import models
from django.core.exceptions import ValidationError

class Department(models.Model):
    company = models.ForeignKey('apis.Company', on_delete=models.CASCADE)
    name = models.CharField(max_length=60)
    description = models.TextField(blank=True)
    head = models.ForeignKey('apis.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_departments')
    leave_allotments = models.JSONField(default=dict, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company} - {self.name}"
    
    class Meta:
        unique_together = ['company', 'name']


class Policy(models.Model):
    POLICY_TYPE_CHOICES = (
        ('leave', 'Leave'),
        ('attendance', 'Attendance'),
        ('overtime', 'Overtime'),
        ('late', 'Late'),
        ('working_hours', 'Working Hours'),
    )

    company = models.ForeignKey('apis.Company', on_delete=models.CASCADE, related_name='policies')
    department = models.ForeignKey('Department', on_delete=models.CASCADE, null=True, blank=True, related_name='policies')
    employee = models.ForeignKey('apis.Employee', on_delete=models.CASCADE, null=True, blank=True, related_name='policies')
    type = models.CharField(max_length=50, choices=POLICY_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    details = models.JSONField(default=dict, blank=True)
    effective_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.employee and self.employee.company != self.company:
            raise ValidationError("Employee must belong to the same company.")
        if self.department and self.department.company != self.company:
            raise ValidationError("Department must belong to the same company.")
        if self.employee and self.department and self.employee.department != self.department:
            raise ValidationError("Employee must belong to the specified department.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.employee:
            return f"{self.title} ({self.type}) for {self.employee} of {self.department} of {self.company}"
        elif self.department:
            return f"{self.title} ({self.type}) for {self.department} of {self.company}"
        else:
            return f"{self.title} ({self.type}) for {self.company}"

    class Meta:
        unique_together = [
            ('company', 'type', 'employee', 'department'),
        ]
        indexes = [
            models.Index(fields=['company', 'department', 'employee', 'type']),
        ]