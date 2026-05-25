from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.db import models

from .models import (Company, Policy, Department, Employee, Attendance)

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.user_type
        return token


class CompanyInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'ownerName', 'email', 'industry', 'size', 'address',
            'countryCode', 'phone', 'logo', 'tax_id', 'website'
        ]
        extra_kwargs = {
            'name': {'required': True},
            'email': {'required': True},
            'industry': {'required': True},
            'size': {'required': True},
            'address': {'required': False},
            'countryCode': {'required': False, 'allow_blank': True, 'default': '+91'},
            'phone': {'required': True},
            'logo': {'required': False, 'allow_null': True},
            'tax_id': {'required': False, 'allow_null': True},
            'website': {'required': False, 'allow_null': True},
        }


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = [
            'id', 'company', 'department', 'employee', 'type', 'title', 'details',
            'effective_date', 'created_at', 'updated_at'
        ]

    def validate(self, attrs):
        employee = attrs.get('employee')
        department = attrs.get('department')
        company = attrs.get('company')

        if employee:
            attrs['department'] = employee.department
            attrs['company'] = employee.company
        elif department:
            attrs['company'] = department.company

        if employee:
            if department and employee.department != department:
                raise serializers.ValidationError({'employee': 'Employee must belong to the specified department.'})
            if company and employee.company != company:
                raise serializers.ValidationError({'employee': 'Employee must belong to the specified company.'})
        elif department:
            if company and department.company != company:
                raise serializers.ValidationError({'department': 'Department must belong to the specified company.'})
        elif not company:
            raise serializers.ValidationError({'company': 'This field is required.'})

        return attrs
    

class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'company', 'name', 'leave_allotments', 'created_at', 'updated_at']
        extra_kwargs = {
            'company': {'required': True},
            'name': {'required': True},
            'leave_allotments': {'required': True},
        }

    def validate(self, attrs):
        company = attrs.get('company') or getattr(self.instance, 'company', None)
        name = attrs.get('name') or getattr(self.instance, 'name', None)

        if not company:
            raise serializers.ValidationError({'company': 'This field is required.'})
        if not name:
            raise serializers.ValidationError({'name': 'This field is required.'})

        instance_id = self.instance.pk if self.instance else None
        if Department.objects.filter(company=company, name=name).exclude(pk=instance_id).exists():
            raise serializers.ValidationError({'name': 'Department with this name already exists in the company.'})

        return attrs


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'user', 'company', 'department', 'first_name', 'last_name',
            'salary', 'employee_type', 'joining_date', 'phone', 'address', 'bank_account',
            'emergency_contact', 'dob', 'documents', 'working_hours', 'overtime_eligible',
            'created_at', 'updated_at'
        ]


    def validate(self, attrs):
        company = attrs.get('company') or getattr(self.instance, 'company', None)
        department = attrs.get('department') or getattr(self.instance, 'department', None)
        employee_type = attrs.get('employee_type') or getattr(self.instance, 'employee_type', None)

        if not company:
            raise serializers.ValidationError({'company': 'This field is required.'})
        if department and department.company != company:
            raise serializers.ValidationError({'department': 'Department must belong to the specified company.'})
        if not employee_type:
            raise serializers.ValidationError({'employee_type': 'This field is required.'})

        return attrs
    
class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = [
            'id', 'employee', 'date', 'check_in', 'check_out',
            'check_in_location', 'check_out_location',
            'total_hours', 'overtime_hours', 'undertime_hours', 'status', 'created_at', 'updated_at'
        ]

    def validate(self, attrs):
        employee = attrs.get('employee')
        check_in = attrs.get('check_in')
        check_out = attrs.get('check_out')

        # Employee is required only for creation, not for updates
        if not self.instance and not employee:
            raise serializers.ValidationError({'employee': 'This field is required.'})

        if check_out and not check_in and not (self.instance and self.instance.check_in):
            raise serializers.ValidationError({'check_out': 'Cannot check out without checking in first.'})

        if check_in and check_out:
            if check_out <= check_in:
                raise serializers.ValidationError({'check_out': 'Check out time must be after check in time.'})

        return attrs

    def create(self, validated_data):
        check_in = validated_data.get('check_in')
        check_out = validated_data.get('check_out')

        if check_out:
            raise serializers.ValidationError({'check_out': 'Check-out should be done via update (PATCH) on existing record.'})

        if check_in and not validated_data.get('date'):
            validated_data['date'] = check_in.date()


        return super().create(validated_data)

    def update(self, instance, validated_data):
        check_in = validated_data.get('check_in', instance.check_in)
        check_out = validated_data.get('check_out', instance.check_out)
        employee = validated_data.get('employee', instance.employee)

        if check_in and not validated_data.get('date', instance.date):
            validated_data['date'] = check_in.date()

        if check_out and not (check_in or instance.check_in):
            raise serializers.ValidationError({'check_out': 'Cannot check out without prior check-in.'})

        if check_in and check_out:
            total_hours = (check_out - check_in).total_seconds() / 3600
            validated_data['total_hours'] = round(total_hours, 2)

            standard_hours = self.get_standard_working_hours(employee)
            if total_hours > standard_hours:
                validated_data['overtime_hours'] = round(total_hours - standard_hours, 2)
                validated_data['undertime_hours'] = 0
            else:
                validated_data['undertime_hours'] = round(standard_hours - total_hours, 2)
                validated_data['overtime_hours'] = 0

        return super().update(instance, validated_data)

    def get_standard_working_hours(self, employee):
        policy = Policy.objects.filter(
            company=employee.company,
            type='working_hours'
        ).filter(
            models.Q(employee=employee) |
            models.Q(department=employee.department, employee__isnull=True) |
            models.Q(department__isnull=True, employee__isnull=True)
        ).order_by('-employee', '-department').first()

        if policy and 'standard_hours' in policy.details:
            return policy.details['standard_hours']
        return 8.0