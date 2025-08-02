from django.urls import path
from authentication.views import GoogleOAuthView

urlpatterns = [
    path('auth/google/', GoogleOAuthView.as_view(), name='google_oauth')
]
