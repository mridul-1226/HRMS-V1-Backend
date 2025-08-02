from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = [
        ('employee', 'Employee'),
        ('hr', 'HR'),
        ('manager', 'Manager'),
        ('field_employee', 'Field Employee'),
    ]

    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='employee')
    email = models.EmailField(unique=True)
    profile_picture = models.URLField(max_length=200, blank=True, null=True)
    google_id = models.CharField(max_length=255, blank=True, null=True)
    def clean(self):
        super().clean()
        valid_choices = [choice if isinstance(choice, str) else choice[0] for choice in self.USER_TYPE_CHOICES]
        if self.user_type not in valid_choices:
            raise ValidationError({'user_type': f"Invalid user_type: {self.user_type}. Must be one of {valid_choices}."})

    def __str__(self):
        return self.username