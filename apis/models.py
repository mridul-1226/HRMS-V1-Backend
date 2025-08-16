from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin', 'Company Admin'),
        ('employee', 'Employee'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='employee')
    company = models.ForeignKey('Company', on_delete=models.CASCADE, null=True, blank=True)
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
    

class Employee(models.Model):
    EMPLOYEE_TYPE_CHOICES = (
        ('sales', 'Sales-Onfield'),
        ('office', 'In-Office'),
    )
    employee_id = models.CharField(max_length=50, unique=True)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='employee_profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='employees')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    employee_type = models.CharField(max_length=10, choices=EMPLOYEE_TYPE_CHOICES)
    department = models.CharField(max_length=100, blank=True)
    joining_date = models.DateField()
    phone = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    bank_account = models.CharField(max_length=100, blank=True)
    emergency_contact = models.JSONField(default=dict, blank=True)
    dob = models.DateField(null=True)
    documents = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.employee_id})"