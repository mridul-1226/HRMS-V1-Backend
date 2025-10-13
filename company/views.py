from rest_framework import status
from rest_framework.views import APIView
from apis.views import JWTAuth
from .serializers import CompanyInfoSerializer, PolicySerializer, DepartmentSerializer
from django.db import transaction
from .models import Policy
from apis.models import CustomUser, Employee
from django.contrib.auth import get_user_model



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
            
            if getattr(user, 'user_type', None) != 'admin':
                return self.error_response(error_message="Only admin can update policies.", status=status.HTTP_403_FORBIDDEN)

            data = request.data.get('policies')
            is_many = isinstance(data, list)

            company = getattr(user, 'company', None)
            if not company:
                return self.error_response(error_message="No company found for user.", status=status.HTTP_404_NOT_FOUND)
            from .models import Policy

            def policy_exists(policy_data):
                policy_type = policy_data.get('type')
                department = policy_data.get('department')
                employee = policy_data.get('employee')
                filters = {'company': company, 'type': policy_type}
                if employee:
                    filters['employee'] = employee
                elif department:
                    filters['department'] = department
                    filters['employee__isnull'] = True
                else:
                    filters['department__isnull'] = True
                    filters['employee__isnull'] = True
                return Policy.objects.filter(**filters).exists()

            if is_many:
                for policy_data in data:
                    if policy_exists(policy_data):
                        return self.error_response(
                            error_message=f"A policy of type '{policy_data.get('type')}' already exists. Please update it to make changes.",
                            status=status.HTTP_400_BAD_REQUEST
                        )
            else:
                if policy_exists(data):
                    return self.error_response(
                        error_message=f"A policy of type '{data.get('type')}' already exists. Please update it to make changes.",
                        status=status.HTTP_400_BAD_REQUEST
                    )

            serializer = PolicySerializer(data=data, many=is_many)
            if serializer.is_valid():
                serializer.save()
                return self.success_response({
                    "policy": serializer.data,
                    "message": "Policy(s) saved successfully."
                })
            else:
                return self.error_response(error_message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")
        
    
    def patch(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error

            if getattr(user, 'user_type', None) != 'admin':
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

            scope = request.query_params.get('scope')
            scopeId = request.query_params.get('scope_id')

            print(f"Scope: {scope}, Scope ID: {scopeId}")

            if scope and scopeId:
                if scope == 'company':
                    if str(company.id) != str(scopeId):
                        return self.error_response(error_message="Unauthorized access to company.", status=status.HTTP_403_FORBIDDEN)
                    policies = Policy.objects.filter(company=company, department__isnull=True, employee__isnull=True)
                elif scope == 'department':
                    try:
                        from .models import Department
                        department = Department.objects.get(id=scopeId, company=company)
                        print(f"Department found: {department.name}")
                    except Department.DoesNotExist:
                        return self.error_response(error_message="Department not found.", status=status.HTTP_404_NOT_FOUND)
                    policies = Policy.objects.filter(company=company, department=department, employee__isnull=True)
                    if not policies.exists():
                        policies = Policy.objects.filter(company=company, department__isnull=True, employee__isnull=True)
                elif scope == 'employee':
                    try:
                        from apis.models import Employee
                        employee = Employee.objects.get(id=scopeId, company=company)
                    except Employee.DoesNotExist:
                        return self.error_response(error_message="Employee not found.", status=status.HTTP_404_NOT_FOUND)
                    policies = Policy.objects.filter(company=company, employee=employee)
                else:
                    return self.error_response(error_message="Invalid scope.", status=status.HTTP_400_BAD_REQUEST)
                
                serializer = PolicySerializer(policies, many=True)
                return self.success_response({
                    "policies": serializer.data,
                    "message": "Policies fetched successfully."
                }, status=status.HTTP_200_OK)
            else:
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
        


class DepartmentView(JWTAuth, APIView):
    def post(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error

            if getattr(user, 'user_type', None) != 'admin':
                return self.error_response(error_message="Only admin can add departments.", status=status.HTTP_403_FORBIDDEN)

            company = getattr(user, 'company', None)
            if not company:
                return self.error_response(error_message="No company found for user.", status=status.HTTP_404_NOT_FOUND)

            data = request.data

            department = DepartmentSerializer(data=data)
            if department.is_valid():
                department.save(company=company)
                return self.success_response({
                    "department": department.data,
                    "message": "Department created successfully."
                }, status=status.HTTP_201_CREATED)
            
            return self.error_response(error_message=department.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")


        # TODO: Add PATCH and GET methods for DepartmentView if needed.
class EmployeeView(JWTAuth, APIView):
    def post(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                    return error

            if getattr(user, 'user_type', None) != 'admin':
                return self.error_response(error_message="Only admin can add employees.", status=status.HTTP_403_FORBIDDEN)
            
            company = getattr(user, 'company', None)
            if not company:
                return self.error_response(error_message="No company found for user.", status=status.HTTP_404_NOT_FOUND)

            data = request.data.copy()
            print("Request data:", data)
            print("Request data lengths:")
            for k, v in data.items():
                if isinstance(v, str):
                    print(f"{k}: len={len(v)}")
                elif isinstance(v, dict):
                    print(f"{k}: json len={len(str(v))}")
                else:
                    print(f"{k}: not str or dict")
            data['company'] = company.id

            # Validate department exists in the company
            department_name = data.get('department_name')
            department = None
            from .models import Department
            try:
                if department_name:
                    department = Department.objects.get(name=department_name, company=company)
            except Department.DoesNotExist:
                return self.error_response(error_message="Department not found in your company.", status=status.HTTP_404_NOT_FOUND)
            data['department'] = department.id if department else None

            # Create CustomUser first
            email = data.get('email')
            name = data.get('name')
            print("Name:", repr(name))
            print("Name len:", len(name))
            if not email or not name:
                return self.error_response(error_message="Email and name are required.", status=status.HTTP_400_BAD_REQUEST)

            if CustomUser.objects.filter(email=email).exists():
                return self.error_response(error_message="Email already exists.", status=status.HTTP_400_BAD_REQUEST)
            
            with transaction.atomic():
                username = self.generate_unique_username(name)
                print("Generated username:", repr(username))
                name_parts = name.split() if name else []
                first_name = name_parts[0] if name_parts else ''
                last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
                user_data = {
                    'username': username,
                    'email': email,
                    'first_name': first_name[:150],
                    'last_name': last_name[:150],
                    'user_type': 'employee',
                    'company': company,
                    'isInitialPassword': True,
                }
                print("First name value:", repr(user_data['first_name']))
                print("First name len:", len(user_data['first_name']))
                print("User data:", {k: repr(v) if isinstance(v, str) else v for k, v in user_data.items()})
                self.send_email(
                    subject="Your Account Credentials",
                    message=f"{name.split()[0]}, your account has been created. Your login email is {email} and password is {username}. Please change your password after logging in.",
                    recipient_email=email
                )
                User = get_user_model()
                new_user = User.objects.create_user(**user_data)
                print('dhweudhieddj')
                new_user.set_password(username)
                print("User created with id:", new_user.id, "username:", new_user.username)
                data['user'] = new_user.id

            from employee.serializers import EmployeeSerializer
            print("Data before serializer:", data)
            serializer = EmployeeSerializer(data=data)
            if serializer.is_valid():
                print("Serializer valid, validated_data:", serializer.validated_data)
                serializer.save()
                self.send_email(
                    subject="Your Account Credentials",
                    message=f"{name.split()[0]}, your account has been created. Your login email is {email} and password is {username}. Please change your password after logging in.",
                    recipient_email=email
                )
                return self.success_response({
                    "employee": serializer.data,
                    "message": "Employee created successfully."
                }, status=status.HTTP_201_CREATED)
            raise serializer.ValidationError(serializer.errors)
            
        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")
        

    def generate_unique_username(self, name):
        base_username = name.lower().replace(' ', '_')[:140] or 'user'
        username = base_username
        counter = 1
        while CustomUser.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        return username
    
    def send_email(self, subject, message, recipient_email):
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False