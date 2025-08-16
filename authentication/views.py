from rest_framework import status
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import random
import string
from apis.models import Employee, Company
from firebase_admin import auth
from apis.views import BaseResponseMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
import authentication.firebase_init


User = get_user_model()

class AuthView(APIView, BaseResponseMixin):

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        try:
            user = User.objects.get(username=username)
            if user.check_password(password):
                refresh = RefreshToken.for_user(user)
                user_type = user.user_type
                return self.success_response(data={
                    'message': 'Login successful!',
                    'access_token': str(refresh.access_token),
                    'refresh_token': str(refresh),
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'name': user.first_name,
                        'profile_picture': user.profile_picture,
                        'type': user_type
                    },
                })
            
            return self.error_response(error_message='Username or Password is incorrect!')
        
        except User.DoesNotExist:
            return self.error_response(error_message='Username doesn\'t exists!')
        
        except Exception as e:
            return self.error_response(error_message=f'Some error occurred: {e}')
        

    def delete(self, request):
        try:
            emp_id = request.data.get('emp_id')
            user_auth = JWTAuthentication()

            try:
                auth_result = user_auth.authenticate(request)
            except (InvalidToken, AuthenticationFailed):
                return self.error_response(error_message='Authentication credentials were not provided or invalid.', status_code=status.HTTP_401_UNAUTHORIZED)
            if not auth_result:
                return self.error_response(error_message='Authentication credentials were not provided or invalid.', status_code=status.HTTP_401_UNAUTHORIZED)
            admin = auth_result[0]

            if admin.user_type != 'admin':
                return self.error_response(error_message='Only company admins can delete users.', status_code=status.HTTP_403_FORBIDDEN)

            employee = Employee.objects.get(employee_id=emp_id)
            if employee.company != admin.company:
                return self.error_response(error_message='You can only delete users from your own company.', status_code=status.HTTP_403_FORBIDDEN)
            
            employee.delete()
            return self.success_response(data={'message': 'User deleted successfully!'})
        except Exception as e:
            return self.error_response(error_message=f'Some error occurred: {e}', status_code=status.HTTP_400_BAD_REQUEST)
        


class GoogleOAuthView(APIView, BaseResponseMixin):
    
    def post(self, request):
        token = request.data.get('id_token').strip()

        try:
            decoded_token = auth.verify_id_token(token)
            uid = decoded_token["uid"]
            email = decoded_token.get("email")
            name = decoded_token.get("name")
            profile_picture = decoded_token.get("picture")

            username = self.generate_unique_username(name)

            user, created = User.objects.get_or_create(
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
                    email=email,
                )
                user.company = company
                user.set_password(username)
                user.save()
            else:
                if not user.company:
                    company = Company.objects.create(
                        name=name + "'s Company",
                        email=email,
                    )
                    user.company = company
                    user.save()

            refresh = RefreshToken.for_user(user)
            return self.success_response(data={
                'message': 'Token verified successfully!',
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'name': user.first_name,
                    'profile_picture': user.profile_picture,
                    'company_id': user.company.company_id if user.company else None,
                    'company_name': user.company.name if user.company else None,
                    'username': user.username,
                },
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
    

class UpdatePasswordView(APIView, BaseResponseMixin):

    def post(self, request):
        username = request.data.get('username')
        oldPassword = request.data.get('oldPassword')
        newPassword = request.data.get('newPassword')

        try:
            user = User.objects.get(username=username)
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
        


class ResetPasswordView(APIView, BaseResponseMixin):
    def post(self, request):
        email = request.data.get('email')
        company_id = request.data.get('company_id')

        try:
            user = User.objects.get(email=email, company__company_id=company_id)
            otp = ''.join(random.choices(string.digits, k=6))
            cache.set(f'otp_{user.id}', otp, timeout=600)

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
        

class ResetPasswordConfirmView(APIView, BaseResponseMixin):
    def post(self, request):
        id=request.get('user_id')
        email=request.get('email')
        otp=request.get('otp')
        new_password=request.get('new_password')

        try:
            user=User.objects.get(id=id)
            if(user.email != email):
                return self.error_response(error_message='Invalid user id!')
            
            cached_otp=cache.get(f'otp_{id}')
            if not cached_otp or cached_otp != otp:
                return self.error_response(error_message='Invalid OTP!')
            
            user.set_password(new_password)
            user.save()
            cache.delete(f'otp_{id}')
            return self.success_response(data={'message': 'Password reset successfully'})
        
        except User.DoesNotExist:
            return self.error_response(error_message='Invalid user', status_code=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return self.error_response(error_message=f'Some error occurred: {e}', status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)