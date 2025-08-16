from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication


class BaseResponseMixin:
    def success_response(self, data, status_code=status.HTTP_200_OK):
        return Response({
            "status": status_code,
            "success": True,
            "data": data
        }, status=status_code)

    def error_response(self, error_message, status_code=status.HTTP_400_BAD_REQUEST):
        return Response({
            "status": status_code,
            "success": False,
            "error": error_message
        }, status=status_code)
    

class JWTAuth(BaseResponseMixin):
    def check_jwt_token(self, request):
        user_auth_tuple = JWTAuthentication().authenticate(request)
        if not user_auth_tuple:
            return None, self.error_response(
                error_message="Authentication failed",
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        user, auth = user_auth_tuple
        return user, auth