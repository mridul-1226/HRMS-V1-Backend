from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication


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
                status_code=status.HTTP_401_UNAUTHORIZED
            )
        user, auth = user_auth_tuple
        return user, auth