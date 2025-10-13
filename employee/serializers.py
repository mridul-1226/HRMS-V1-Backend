from rest_framework import serializers
from apis.models import Employee

class EmployeeSerializer(serializers.ModelSerializer):
    joining_date = serializers.DateField(input_formats=['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d'])
    dob = serializers.DateField(input_formats=['%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d'], required=False)

    class Meta:
        model = Employee
        fields = '__all__'
        read_only_fields = ['employee_id', 'created_at', 'updated_at']

    def create(self, validated_data):
        print("EmployeeSerializer create called with validated_data:", validated_data)
        required_fields = [
            'user', 'company', 'department', 'first_name', 'last_name', 'salary', 'phone', 'joining_date', 'employee_type'
        ]
        missing_fields = [field for field in required_fields if field not in validated_data or validated_data[field] in [None, '']]
        if missing_fields:
            raise serializers.ValidationError(f"Missing required fields: {', '.join(missing_fields)}")
        return super().create(validated_data)