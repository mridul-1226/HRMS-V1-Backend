from django.urls import path
from authentication.views import GoogleOAuthView, AuthView, UpdatePasswordView

urlpatterns = [
    path('auth/google/', GoogleOAuthView.as_view(), name='google_oauth'),
    path('auth/', AuthView.as_view(), name='auth'),
    path('auth/update-password/', UpdatePasswordView.as_view(), name='update-password')
]
