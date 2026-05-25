from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from .serializers import CompanyInfoSerializer, PolicySerializer, DepartmentSerializer, EmployeeSerializer, AttendanceSerializer
from django.db import transaction
from .models import Policy, Department, Employee, Attendance
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from geopy.geocoders import Nominatim
from geopy.distance import geodesic


def get_place_from_location(lat, lon):
    try:
        geolocator = Nominatim(user_agent="hrms_app")
        location = geolocator.reverse((lat, lon), exactly_one=True)
        print(location)
        return location.address if location else "Unknown Location"
    except:
        return "Unknown Location"
    

class BaseResponseMixin:
    def success_response(self, data, status=status.HTTP_200_OK):
        print(data)
        return Response({
            "status": status,
            "success": True,
            "data": data
        }, status=status)

    def error_response(self, error_message, status=status.HTTP_400_BAD_REQUEST):
        print(error_message)
        return Response({
            "status": status,
            "success": False,
            "error": error_message
        }, status=status)
    
class JWTAuth(BaseResponseMixin):
    def check_jwt_token(self, request):
        user_auth_tuple = JWTAuthentication().authenticate(request)
        if not user_auth_tuple:
            return None, self.error_response(
                error_message="Authentication failed",
                status=status.HTTP_401_UNAUTHORIZED
            )
        user, auth = user_auth_tuple
        return user, auth


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

            if scope and scopeId:
                if scope == 'company':
                    if str(company.id) != str(scopeId):
                        return self.error_response(error_message="Unauthorized access to company.", status=status.HTTP_403_FORBIDDEN)
                    policies = Policy.objects.filter(company=company, department__isnull=True, employee__isnull=True)
                elif scope == 'department':
                    try:
                        department = Department.objects.get(id=scopeId, company=company)
                        print(f"Department found: {department.name}")
                    except Department.DoesNotExist:
                        return self.error_response(error_message="Department not found.", status=status.HTTP_404_NOT_FOUND)
                    policies = Policy.objects.filter(company=company, department=department, employee__isnull=True)
                    if not policies.exists():
                        policies = Policy.objects.filter(company=company, department__isnull=True, employee__isnull=True)
                elif scope == 'employee':
                    try:
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

    def get(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error

            company = getattr(user, 'company', None)
            if not company:
                return self.error_response(error_message="No company found for user.", status=status.HTTP_404_NOT_FOUND)

            departments = Department.objects.filter(company=company)
            serializer = DepartmentSerializer(departments, many=True)
            return self.success_response({
                "departments": serializer.data,
                "message": "Departments fetched successfully."
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")

    def patch(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error

            if getattr(user, 'user_type', None) != 'admin':
                return self.error_response(error_message="Only admin can update departments.", status=status.HTTP_403_FORBIDDEN)

            company = getattr(user, 'company', None)
            if not company:
                return self.error_response(error_message="No company found for user.", status=status.HTTP_404_NOT_FOUND)

            department_id = request.data.get('id')
            if not department_id:
                return self.error_response(error_message="Department ID is required.", status=status.HTTP_400_BAD_REQUEST)

            try:
                department = Department.objects.get(id=department_id, company=company)
            except Department.DoesNotExist:
                return self.error_response(error_message="Department not found in your company.", status=status.HTTP_404_NOT_FOUND)

            serializer = DepartmentSerializer(department, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return self.success_response({
                    "department": serializer.data,
                    "message": "Department updated successfully."
                }, status=status.HTTP_200_OK)
            else:
                return self.error_response(error_message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")


class AttendanceView(JWTAuth, APIView):
    def post(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error

            if user.user_type != 'employee':
                return self.error_response(error_message="Only employees can check in/out.", status=status.HTTP_403_FORBIDDEN)

            employee = getattr(user, 'employee_profile', None)
            if not employee:
                return self.error_response(error_message="Employee profile not found.", status=status.HTTP_404_NOT_FOUND)

            data = request.data
            latitude = data.get('latitude')
            longitude = data.get('longitude')

            if latitude is None or longitude is None:
                return self.error_response(error_message="Location is required.", status=status.HTTP_400_BAD_REQUEST)

            today = timezone.now().date()
            current_location = {'lat': latitude, 'lon': longitude, 'place': get_place_from_location(latitude, longitude)}

            # Get today's attendance record
            attendance = Attendance.objects.filter(employee=employee, date=today).first()

            if attendance is None:
                # Check-in: Create new attendance record
                serializer = AttendanceSerializer(data={
                    'employee': employee.id,
                    'date': today,
                    'check_in': timezone.now(),
                    'check_in_location': current_location,
                    'status': 'present'
                })
                if serializer.is_valid():
                    attendance = serializer.save()
                    message = "Checked in successfully."
                else:
                    return self.error_response(error_message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            elif attendance.check_out is None:
                # Check-out: Update existing record
                # Validate distance from check-in location
                if attendance.check_in_location:
                    check_in_lat = attendance.check_in_location.get('lat')
                    check_in_lon = attendance.check_in_location.get('lon')
                    if check_in_lat is not None and check_in_lon is not None:
                        distance = geodesic((check_in_lat, check_in_lon), (latitude, longitude)).meters
                        if distance > 100:
                            return self.error_response(error_message="Check-out location must be within 100 meters of check-in location.", status=status.HTTP_400_BAD_REQUEST)

                # Update with check-out data
                serializer = AttendanceSerializer(attendance, data={
                    'check_out': timezone.now(),
                    'check_out_location': current_location
                }, partial=True)
                if serializer.is_valid():
                    attendance = serializer.save()
                    message = "Checked out successfully."
                else:
                    return self.error_response(error_message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            else:
                # Already checked out
                return self.error_response(error_message="Already checked out for today.", status=status.HTTP_400_BAD_REQUEST)

            serializer = AttendanceSerializer(attendance)
            return self.success_response({
                "attendance": serializer.data,
                "message": message
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")

    def get(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error

            employee = getattr(user, 'employee_profile', None)
            if not employee:
                return self.error_response(error_message="Employee profile not found.", status=status.HTTP_404_NOT_FOUND)

            today = timezone.now().date()
            attendance = Attendance.objects.filter(employee=employee, date=today).first()

            if attendance:
                serializer = AttendanceSerializer(attendance)
                return self.success_response({
                    "attendance": serializer.data,
                    "message": "Today's attendance fetched successfully."
                }, status=status.HTTP_200_OK)
            else:
                return self.success_response({
                    "attendance": None,
                    "message": "No attendance record for today."
                }, status=status.HTTP_200_OK)

        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")


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
            data['company'] = company.id

            # Validate department exists in the company
            department_name = data.get('department_name')
            department_id = data.get('department')
            department = None
            try:
                if department_name:
                    department = Department.objects.get(name=department_name, company=company)
                elif department_id:
                    department = Department.objects.get(id=department_id, company=company)
            except Department.DoesNotExist:
                return self.error_response(error_message="Department not found in your company.", status=status.HTTP_404_NOT_FOUND)
            data['department'] = department.id if department else None

            # Create CustomUser first
            email = data.get('email')
            name = data.get('name')
            if not email or not name:
                return self.error_response(error_message="Email and name are required.", status=status.HTTP_400_BAD_REQUEST)

            if get_user_model().objects.filter(email=email).exists():
                return self.error_response(error_message="Email already exists.", status=status.HTTP_400_BAD_REQUEST)

            name = name.strip()
            name_parts = name.split() if name else []
            first_name = name_parts[0] if name_parts else ''
            last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

            if not data.get('first_name'):
                data['first_name'] = first_name
            if not data.get('last_name'):
                data['last_name'] = last_name

            serializer = None
            with transaction.atomic():
                username = self.generate_unique_username(name)
                user_data = {
                    'username': username,
                    'email': email,
                    'first_name': first_name[:150],
                    'last_name': last_name[:150],
                    'user_type': 'employee',
                    'company': company,
                    'isInitialPassword': True,
                }
                User = get_user_model()
                new_user = User.objects.create_user(**user_data)
                new_user.set_password(username)
                new_user.save()

                data['user'] = new_user.id
                serializer = EmployeeSerializer(data=data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

            greeting_name = first_name or name
            self.send_email(
                subject="Your Account Credentials",
                message=f"{greeting_name}, your account has been created. Your login email is {email} and password is {username}. Please change your password after logging in.",
                recipient_email=email
            )
            return self.success_response({
                "employee": serializer.data,
                "message": "Employee created successfully."
            }, status=status.HTTP_201_CREATED)
            
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

            employee_id = request.query_params.get('employee_id')

            if user.user_type == 'employee':
                # Employee can only view their own profile
                employee = getattr(user, 'employee_profile', None)
                if not employee:
                    return self.error_response(error_message="Employee profile not found.", status=status.HTTP_404_NOT_FOUND)
                serializer = EmployeeSerializer(employee)
                return self.success_response({
                    "employee": serializer.data,
                    "message": "Employee profile fetched successfully."
                }, status=status.HTTP_200_OK)
            else:
                # Admin can view specific employee or all employees
                if employee_id:
                    try:
                        employee = Employee.objects.select_related('user', 'department', 'company').get(
                            employee_id=employee_id, company=company
                        )
                        serializer = EmployeeSerializer(employee)
                        return self.success_response({
                            "employee": serializer.data,
                            "message": "Employee details fetched successfully."
                        }, status=status.HTTP_200_OK)
                    except Employee.DoesNotExist:
                        return self.error_response(error_message="Employee not found in your company.", status=status.HTTP_404_NOT_FOUND)
                else:
                    # Return paginated list of all employees in the company
                    employees = Employee.objects.select_related('user', 'department', 'company').filter(company=company)
                    paginator = PageNumberPagination()
                    paginator.page_size = 10  # Adjust as needed
                    result_page = paginator.paginate_queryset(employees, request)
                    serializer = EmployeeSerializer(result_page, many=True)
                    return paginator.get_paginated_response({
                        "employees": serializer.data,
                        "message": "Employees fetched successfully."
                    })

        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")
        

    def patch(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error

            company = getattr(user, 'company', None)
            if not company:
                return self.error_response(error_message="No company found for user.", status=status.HTTP_404_NOT_FOUND)

            employee_id = request.data.get('employee_id')

            if user.user_type == 'employee':
                employee = getattr(user, 'employee_profile', None)
                if not employee:
                    return self.error_response(error_message="Employee profile not found.", status=status.HTTP_404_NOT_FOUND)
            else:
                if not employee_id:
                    return self.error_response(error_message="Employee ID is required for admin updates.", status=status.HTTP_400_BAD_REQUEST)
                try:
                    employee = Employee.objects.get(employee_id=employee_id, company=company)
                except Employee.DoesNotExist:
                    return self.error_response(error_message="Employee not found in your company.", status=status.HTTP_404_NOT_FOUND)

            serializer = EmployeeSerializer(employee, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return self.success_response({
                    "employee": serializer.data,
                    "message": "Employee updated successfully."
                }, status=status.HTTP_200_OK)
            else:
                return self.error_response(error_message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")
        

    def generate_unique_username(self, name):
        base_username = name.lower().replace(' ', '_')[:140] or 'user'
        username = base_username
        counter = 1
        while get_user_model().objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        return username
    
    def send_email(self, subject, message, recipient_email):
        try:
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