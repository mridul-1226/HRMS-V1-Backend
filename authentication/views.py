from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from google.oauth2 import id_token
from google.auth.transport import requests
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
import random
import string
from django.conf import settings
from apis.views import BaseResponseMixin

User = get_user_model()


class GoogleOAuthView(APIView, BaseResponseMixin):
    
    def post(self, request):
        token = request.data.get('id_token')
        try:
            igd = settings.GID
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), settings.GID)

            google_id = idinfo['sub']
            email = idinfo['email']
            name = idinfo.get('name', '')
            profile_picture = idinfo.get('picture', '')

            username = self.generate_unique_username(name)

            user, created = User.objects.get_or_create(
                email=email, 
                defaults= {
                    'username': username,
                    'google_id': google_id,
                    'first_name': name,
                    'profile_picture': profile_picture
                })
            
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
                    'name': name,
                    'profile_picture': profile_picture,
                    'username': username
                },
            })
        
        except ValueError:
            return self.error_response(error_message='Invalid Google token', status_code=status.HTTP_400_BAD_REQUEST,)
            

    def generate_unique_username(self, name):
        base_username = name.lower().replace(' ', '_') or 'user'
        username = base_username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1
        return username