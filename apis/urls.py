from django.urls import path
from authentication.views import GoogleOAuthView, AuthView, UpdatePasswordView, ResetPasswordView, ResetPasswordConfirmView
from .views import CompanyView, PolicyView, DepartmentView, EmployeeView, AttendanceView

urlpatterns = [
    path('auth/google/', GoogleOAuthView.as_view(), name='google_oauth'),
    path('auth/user/', AuthView.as_view(), name='auth'),
    path('auth/update-password/', UpdatePasswordView.as_view(), name='update-password'),
    path('auth/reset/password/', ResetPasswordView.as_view(), name='reset-password'),
    path('auth/reset/otp/', ResetPasswordConfirmView.as_view(), name='reset-otp'),
    
    path('company/details/', CompanyView.as_view(), name='company-details'),
    path('company/policy/', PolicyView.as_view(), name='company-policy'),
    path('department/', DepartmentView.as_view(), name='department'),
    path('employees/', EmployeeView.as_view(), name='employees'),
    path('attendance/', AttendanceView.as_view(), name='attendance'),
]