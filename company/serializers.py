from rest_framework import serializers
from apis.models import Company
from .models import Policy

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