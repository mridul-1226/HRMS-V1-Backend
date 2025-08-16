from rest_framework import status
from rest_framework.views import APIView
from apis.views import BaseResponseMixin, JWTAuth
from rest_framework_simplejwt.authentication import JWTAuthentication
from apis.models import Company
from serializers import CompanyUpdateSerializer, CompanyDetailSerializer
from apis.views import JWTAuth


class CompanyView(APIView, BaseResponseMixin, JWTAuth):

    def post(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error

            data = request.data

            name = data.get('comapnyName')
            email = data.get('email')
            industry = data.get('industry')
            size = data.get('size')
            address = data.get('address')
            countryCode = data.get('countryCode')
            phone = data.get('phone')

            if not name or not email or not industry or not size or not address or not countryCode or not phone:
                return self.error_response(error_message="Enter all required Fields.", status=status.HTTP_400_BAD_REQUEST)

            if not hasattr(user, 'company') or user.company is None:
                return self.error_response(error_message="No company found for user.", status=status.HTTP_404_NOT_FOUND)

            company = user.company

            serializer = CompanyDetailSerializer(company, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
            else:
                return self.error_response(error_message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            return self.success_response({
                "id": str(company.id),
                "name": company.name,
                "email": company.email,
                'message': "Company details added successfully."
            }, status=status.HTTP_200_OK)
        
        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")


    def patch(self, request):
        try:
            user, error = self.check_jwt_token(request)
            if user is None:
                return error
            
            if not hasattr(user, 'company') or user.company is None:
                return self.error_response(error_message="No company found for user.", status=status.HTTP_404_NOT_FOUND)

            company = user.company

            serializer = CompanyUpdateSerializer(company, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return self.success_response({
                    "id": str(company.id),
                    "name": company.name,
                    "email": company.email,
                    'message': "Company updated successfully."
                }, status=status.HTTP_200_OK)
            return self.error_response(error_message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return self.error_response(error_message=f"Something went wrong: {e}")