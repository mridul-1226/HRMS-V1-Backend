from rest_framework import status
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import random
import string
import firebase_admin
from firebase_admin import credentials, auth
from apis.views import BaseResponseMixin

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase-service-account.json")
    firebase_admin.initialize_app(cred)

User = get_user_model()


class GoogleOAuthView(APIView, BaseResponseMixin):
    
    def post(self, request):
        token = request.data.get('id_token').strip()

        print(f"Received token:{token}")
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
                    'profile_picture': profile_picture
                }
            )
            
            if created:
                random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                user.set_password(random_password)
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