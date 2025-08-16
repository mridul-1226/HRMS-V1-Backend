from rest_framework import serializers
from apis.models import Company

class CompanyDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'name', 'ownerName', 'email', 'industry', 'size', 'address',
            'countryCode', 'phone', 'logo', 'tax_id', 'website'
        ]
        extra_kwargs = {
            'name': {'required': True},
            'ownerName': {'required': True},
            'email': {'required': True},
            'industry': {'required': True},
            'size': {'required': True},
            'address': {'required': True},
            'countryCode': {'required': True},
            'phone': {'required': True},
            'logo': {'required': False, 'allow_null': True, 'required': False},
            'tax_id': {'required': False, 'allow_null': True},
            'website': {'required': False, 'allow_null': True},
        }

class CompanyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'name', 'industry', 'size', 'address', 'countryCode',
            'phone', 'logo', 'tax_id', 'website'
        ]
        extra_kwargs = {field: {'required': False, 'allow_null': True} for field in fields}