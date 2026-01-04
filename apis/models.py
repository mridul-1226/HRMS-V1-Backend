from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from django.forms import ValidationError

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin', 'Company Admin'),
        ('employee', 'Employee'),
    )
    user_type = models.CharField(max_length=30, choices=USER_TYPE_CHOICES, default='employee')
    company = models.ForeignKey('Company', on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    email = models.EmailField(unique=True)
    profile_picture = models.URLField(max_length=200, blank=True, null=True)
    google_id = models.CharField(max_length=255, blank=True, null=True)
    isInitialPassword = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.username} ({self.user_type})"
    

class Company(models.Model):
    company_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    ownerName = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    industry = models.CharField(max_length=100, null=True)
    size = models.CharField(max_length=20, null=True)
    address = models.TextField(null=True)
    countryCode = models.CharField(max_length=4, default='+91', null=True)
    phone = models.CharField(max_length=15, null=True)
    logo = models.ImageField(upload_to='company_logos/', null=True, blank=True)
    tax_id = models.CharField(max_length=50, blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

class Department(models.Model):
    company = models.ForeignKey('Company', on_delete=models.CASCADE)
    name = models.CharField(max_length=60)
    description = models.TextField(blank=True)
    head = models.ForeignKey('Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='headed_departments')
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
        ('others', 'Others'),
    )

    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='policies', db_index=True)
    department = models.ForeignKey('Department', on_delete=models.CASCADE, null=True, blank=True, related_name='policies', db_index=True)
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, null=True, blank=True, related_name='policies', db_index=True)
    type = models.CharField(max_length=50, choices=POLICY_TYPE_CHOICES, db_index=True)
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
            models.Index(fields=['company', 'department', 'type']),
            models.Index(fields=['company', 'type']),
        ]


class Employee(models.Model):
    EMPLOYEE_TYPE_CHOICES = (
        ('sales', 'Sales-Onfield'),
        ('office', 'In-Office'),
    )
    employee_id = models.CharField(max_length=150, unique=True)
    user = models.OneToOneField('CustomUser', on_delete=models.CASCADE, related_name='employee_profile')
    company = models.ForeignKey('Company', on_delete=models.CASCADE, related_name='employees', db_index=True)
    department = models.ForeignKey('Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='employees')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    salary = models.CharField(max_length=10, blank=True)
    employee_type = models.CharField(max_length=30, choices=EMPLOYEE_TYPE_CHOICES)
    joining_date = models.DateField()
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    bank_account = models.CharField(max_length=100, blank=True)
    emergency_contact = models.JSONField(default=dict, blank=True)
    dob = models.DateField(null=True)
    documents = models.JSONField(default=dict, blank=True, null=True)
    working_hours = models.JSONField(default=dict)
    overtime_eligible = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id})"
    
    class Meta:
        indexes = [
            models.Index(fields=['company', 'department', 'employee_type']),
            models.Index(fields=['company', 'employee_type']),
            models.Index(fields=['company', 'department']),
        ]
    

class Attendance(models.Model):
    employee = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name='attendances', db_index=True)
    date = models.DateField(db_index=True)
    check_in = models.DateTimeField(null=True, blank=True)
    check_out = models.DateTimeField(null=True, blank=True)
    check_in_location = models.JSONField(null=True, blank=True)
    check_out_location = models.JSONField(null=True, blank=True)
    total_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    overtime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    undertime_hours = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    status = models.CharField(max_length=50, choices=(
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('leave', 'Leave'),
        ('holiday', 'Holiday'),
    ), default='present', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Attendance of {self.employee} on {self.date}"
    
    class Meta:
        unique_together = ['employee', 'date']
        