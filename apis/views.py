from rest_framework.response import Response
from rest_framework import status

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