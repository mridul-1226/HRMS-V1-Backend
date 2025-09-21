from rest_framework import status
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
import random
import string
from apis.models import Employee, Company
from firebase_admin import auth
from apis.views import BaseResponseMixin, JWTAuth
from django.core.mail import send_mail
from django.conf import settings
from company.models import Policy
from django.core.cache import cache
import authentication.firebase_init
from apis.serializers import MyTokenObtainPairSerializer
from company.serializers import CompanyInfoSerializer
from django.db import transaction


User = get_user_model()

# Login & user delete by admin API
class AuthView(APIView, BaseResponseMixin):

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        try:
            if email:
                user = User.objects.select_related('company').get(email=email)
            else:
                return self.error_response(error_message='Email is required!')
            if user.check_password(password):
                serializer = MyTokenObtainPairSerializer(data={'email': email, 'password': password, 'username': user.username})
                serializer.is_valid(raise_exception=True)
                tokens = serializer.validated_data
                company = user.company
                company_data = CompanyInfoSerializer(company).data if company else None
                if user.user_type == 'admin':
                    required_types = [choice[0] for choice in Policy.POLICY_TYPE_CHOICES if choice[0] != 'others']
                    existing_types = Policy.objects.filter(
                        company=company,
                        employee__isnull=True,
                        department__isnull=True,
                        type__in=required_types
                    ).values_list('type', flat=True).distinct()
                    has_company_policy = all(t in existing_types for t in required_types) if company else False
                    from company.models import Department
                    departments = Department.objects.filter(company=company)
                
                departments_csv = ','.join([f"{dept.name}:{dept.id}" for dept in departments]) if user.user_type == 'admin' else None
                return self.success_response(data={
                    'message': 'Login successful!',
                    'access_token': tokens['access'],
                    'refresh_token': tokens['refresh'],
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'name': user.first_name,
                        'profile_picture': user.profile_picture,
                        'username': user.username,
                    },
                    'company': company_data,
                    'role': user.user_type,
                    'has_company_policy': has_company_policy if user.user_type == 'admin' else None,
                    'departments': departments_csv,
                })
            
            return self.error_response(error_message='Username or Password is incorrect!')
        
        except User.DoesNotExist:
            return self.error_response(error_message='Username doesn\'t exists!')
        
        except Exception as e:
            return self.error_response(error_message=f'Some error occurred: {e}')
        

    def delete(self, request):
        try:
            emp_id = request.data.get('emp_id')

            admin, error = JWTAuth().check_jwt_token(request)
            if admin is None:
                return error

            if admin.user_type != 'admin':
                return self.error_response(error_message='Only company admins can delete users.', status_code=status.HTTP_403_FORBIDDEN)

            employee = Employee.objects.select_related('company', 'user').get(employee_id=emp_id)
            if employee.company != admin.company:
                return self.error_response(error_message='You can only delete users from your own company.', status_code=status.HTTP_403_FORBIDDEN)
            
            with transaction.atomic():
                user = employee.user
                user.delete()
            return self.success_response(data={'message': 'User deleted successfully!'})
        except Exception as e:
            return self.error_response(error_message=f'Some error occurred: {e}', status_code=status.HTTP_400_BAD_REQUEST)
        

# Google oAuth API
class GoogleOAuthView(APIView, BaseResponseMixin):
    
    def post(self, request):
        token = request.data.get('id_token').strip()

        try:
            decoded_token = auth.verify_id_token(token)
            uid = decoded_token.get("user_id") or decoded_token.get("uid")
            email = decoded_token.get("email")
            name = decoded_token.get("name")
            profile_picture = decoded_token.get("picture")

            username = self.generate_unique_username(name)

            with transaction.atomic():
                user, created = User.objects.select_related('company').get_or_create(
                    email=email, 
                    defaults={
                        'username': username,
                        'first_name': name,
                        'google_id': uid,
                        'profile_picture': profile_picture,
                        'user_type': 'admin',
                    }
                )
                
                if created:
                    company = Company.objects.create(
                        name=name + "'s Company",
                        ownerName=name,
                        email=email,
                    )
                    user.company = company
                    user.set_password(username)
                    user.save()
                else:
                    if not user.company:
                        company = Company.objects.create(
                            name=name + "'s Company",
                            ownerName=name,
                            email=email,
                        )
                        user.company = company
                        user.save()
                    
                    required_types = [choice[0] for choice in Policy.POLICY_TYPE_CHOICES if choice[0] != 'others']
                    existing_types = Policy.objects.filter(
                        company=company,
                        employee__isnull=True,
                        department__isnull=True,
                        type__in=required_types
                    ).values_list('type', flat=True).distinct()
                    has_company_policy = all(t in existing_types for t in required_types) if company else False

            company = user.company
            company_data = CompanyInfoSerializer(company).data if company else None
            from company.models import Department
            departments = Department.objects.filter(company=company)
            departments_csv = ','.join([f"{dept.name}:{dept.id}" for dept in departments]) if user.user_type == 'admin' else None

            serializer = MyTokenObtainPairSerializer(data={'email': email, 'password': username if created else None, 'username': username if created else None})
            if created:
                serializer.is_valid(raise_exception=True)
                tokens = serializer.validated_data
            else:
                refresh = MyTokenObtainPairSerializer.get_token(user)
                tokens = {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token)
                }

            return self.success_response(data={
                'message': 'Token verified successfully!',
                'access_token': tokens['access'],
                'refresh_token': tokens['refresh'],
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.first_name,
                    'profile_picture': user.profile_picture,
                    'username': user.username,
                },
                'company': company_data,
                'role': 'admin',
                'has_company_policy': has_company_policy if not created else False,
                'departments': departments_csv,
            })
        
        except ValueError as e:
            return self.error_response(error_message=f'Invalid Google token {e}', status_code=status.HTTP_400_BAD_REQUEST,)
        
        except Exception as e:
            return self.error_response(error_message=f'{e}', status_code=status.HTTP_400_BAD_REQUEST,)
            
    def generate_unique_username(self, name):
        base_username = name.lower().replace(' ', '_') or 'user'
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        return username
    


# Update password API
class UpdatePasswordView(APIView, BaseResponseMixin):

    def post(self, request):
        email = request.data.get('email')
        oldPassword = request.data.get('oldPassword')
        newPassword = request.data.get('newPassword')

        try:
            user = User.objects.get(email=email)
            if user.check_password(oldPassword):
                user.set_password(newPassword)
                user.save()
                return self.success_response(data={
                    'message': 'Password updated successfully!',
                })
            return self.error_response(error_message='Incorrect password!')
        except User.DoesNotExist:
            return self.error_response(error_message='Username doesn\'t exists!')
        except Exception as e:
            return self.error_response(error_message=f'Some error occurred: {e}')
        

# Send reset password mail
class ResetPasswordView(APIView, BaseResponseMixin):
    def post(self, request):
        email = request.data.get('email')

        try:
            user = User.objects.select_related('company').get(email=email)
            otp = ''.join(random.choices(string.digits, k=6))
            cache.set(f'otp_{user.id}', otp, timeout=600)

            print(otp)

            self.send_email_to_user(
                subject='HRMS Password Reset OTP',
                message=f'Your OTP for password reset is: {otp}\nThis OTP will expire in 10 minutes.',
                recipient_email=user.email
            )

            return self.success_response(data={
                'message': 'OTP sent to your email',
                'user_id': user.id,
            })
        except User.DoesNotExist:
            return self.error_response(error_message='Username doesn\'t exists!')
        except Exception as e:
            return self.error_response(error_message=f'Some error occurred: {e}')
        
    def send_email_to_user(self, subject, message, recipient_email):
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
        

# Verify reset password using OTP
class ResetPasswordConfirmView(APIView, BaseResponseMixin):
    def post(self, request):
        email=request.data.get('email')
        otp=request.data.get('otp')
        new_password=request.data.get('new_password')

        try:
            user=User.objects.get(email=email)
            
            cached_otp=cache.get(f'otp_{user.id}')
            if not cached_otp or cached_otp != otp:
                return self.error_response(error_message='Invalid OTP!')
            
            user.set_password(new_password)
            user.save()
            cache.delete(f'otp_{user.id}')
            return self.success_response(data={'message': 'Password reset successfully'})
        except User.DoesNotExist:
            return self.error_response(error_message='Invalid user', status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return self.error_response(error_message=f'Some error occurred: {e}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)