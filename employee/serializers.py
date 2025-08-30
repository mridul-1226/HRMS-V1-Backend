from rest_framework import serializers
from apis.models import Employee

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = '__all__'
        read_only_fields = ['employee_id', 'created_at', 'updated_at']

    def create(self, validated_data):
        required_fields = [
            'user', 'company', 'department', 'first_name', 'employee_type', 'joining_date'
        ]
        missing_fields = [field for field in required_fields if field not in validated_data or validated_data[field] in [None, '']]
        if missing_fields:
            raise serializers.ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        return super().create(validated_data)