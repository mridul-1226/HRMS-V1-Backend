from rest_framework import serializers
from apis.models import Company

class CompanyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = [
            'name', 'industry', 'size', 'address', 'countryCode',
            'phone', 'logo', 'tax_id', 'website'
        ]
        extra_kwargs = {field: {'required': False, 'allow_null': True} for field in fields}