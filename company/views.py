from rest_framework import status
from rest_framework.views import APIView
from apis.views import JWTAuth
from .serializers import CompanyInfoSerializer, PolicySerializer
from apis.views import JWTAuth
from django.db import transaction
from .models import Policy


class CompanyView(JWTAuth, APIView):
    def post(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error

            data = request.data

            name = data.get('ownerName')
            email = data.get('email')
            industry = data.get('industry')
            size = data.get('size')
            countryCode = data.get('countryCode')
            phone = data.get('phone')

            missing_fields = [field for field, value in {
                'name': name,
                'email': email,
                'industry': industry,
                'countryCode': countryCode,
                'size': size,
                'phone': phone,
            }.items() if not value]

            if missing_fields:
                return self.error_response(
                    error_message=f"Missing required fields: {', '.join(missing_fields)}",
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not hasattr(user, 'company') or user.company is None:
                return self.error_response(error_message="No company found for user.", status=status.HTTP_404_NOT_FOUND)

            company = user.company
            
            serializer = CompanyInfoSerializer(company, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
            else:
                return self.error_response(error_message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            company_data = CompanyInfoSerializer(company).data

            return self.success_response({
                "id": str(company.id),
                "company_detail": company_data,
                'message': "Company details added successfully."
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")

    def patch(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error
            
            if not hasattr(user, 'company') or user.company is None:
                return self.error_response(error_message="No company found for user.", status=status.HTTP_404_NOT_FOUND)

            company = user.company

            with transaction.atomic():
                serializer = CompanyInfoSerializer(company, data=request.data, partial=True)
                if serializer.is_valid():
                    serializer.save()
                    company_data = serializer.data
                    return self.success_response({
                        "id": str(company.id),
                        "name": company.name,
                        "email": company.email,
                        "company_detail": company_data,
                        'message': "Company updated successfully."
                    }, status=status.HTTP_200_OK)
                return self.error_response(error_message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")
        


class PolicyView(JWTAuth, APIView):
    def post(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error
            
            print(error)
            if not getattr(user, 'user_type', None) != 'admin':
                return self.error_response(error_message="Only admin can update policies.", status=status.HTTP_403_FORBIDDEN)

            serializer = PolicySerializer(data=request.data)
            if serializer.is_valid():
                serializer.save()
                return self.success_response({
                    "policy": serializer.data,
                    "message": "Policy saved successfully."
                }, status=status.HTTP_201_CREATED)
            else:
                return self.error_response(error_message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")
        
    
    def patch(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error

            if not getattr(user, 'user_type', None) != 'admin':
                return self.error_response(error_message="Only admin can update policies.", status=status.HTTP_403_FORBIDDEN)

            data = request.data
            policy_type = data.get('type')
            company = getattr(user, 'company', None)
            if not company:
                return self.error_response(error_message="No company found for user.", status=status.HTTP_404_NOT_FOUND)

            employee_id = data.get('employee_id')
            department_id = None
            employee = None
            if employee_id:
                try:
                    employee = company.employees.only('id', 'department_id').get(id=employee_id)
                except company.employees.model.DoesNotExist:
                    employee = None
                if not employee:
                    return self.error_response(error_message="Employee not found.", status=status.HTTP_404_NOT_FOUND)
                department_id = employee.department.id if employee.department else None
            else:
                department_id = data.get('department_id')

            policy = None
            try:
                if employee_id:
                    policy = Policy.objects.get(
                        company=company,
                        department_id=department_id,
                        employee_id=employee_id,
                        type=policy_type
                    )
                elif department_id:
                    policy = Policy.objects.get(
                        company=company,
                        department_id=department_id,
                        employee__isnull=True,
                        type=policy_type
                    )
                else:
                    policy = Policy.objects.get(
                        company=company,
                        department__isnull=True,
                        employee__isnull=True,
                        type=policy_type
                    )
            except Policy.DoesNotExist:
                return self.error_response(error_message="Policy not found.", status=status.HTTP_404_NOT_FOUND)

            serializer = PolicySerializer(policy, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return self.success_response({
                    "policy": serializer.data,
                    "message": "Policy updated successfully."
                }, status=status.HTTP_200_OK)
            else:
                return self.error_response(error_message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")
        
    def get(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error

            company = getattr(user, 'company', None)
            if not company:
                return self.error_response(error_message="No company found for user.", status=status.HTTP_404_NOT_FOUND)

            employee = getattr(user, 'employee', None)
            department = getattr(employee, 'department', None) if employee else None

            policy_types = dict(Policy.POLICY_TYPE_CHOICES).keys()
            policies_result = []

            for policy_type in policy_types:
                policy = None
                if employee:
                    policy = Policy.objects.filter(
                        company=company,
                        employee=employee,
                        type=policy_type
                    ).select_related('department', 'employee').first()
                if not policy and department:
                    policy = Policy.objects.filter(
                        company=company,
                        department=department,
                        employee__isnull=True,
                        type=policy_type
                    ).select_related('department').first()
                if not policy:
                    policy = Policy.objects.filter(
                        company=company,
                        department__isnull=True,
                        employee__isnull=True,
                        type=policy_type
                    ).first()
                if policy:
                    policies_result.append(policy)

            serializer = PolicySerializer(policies_result, many=True)
            return self.success_response({
                "policies": serializer.data,
                "message": "Policies fetched successfully."
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")