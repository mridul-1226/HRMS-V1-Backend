from rest_framework import status
from rest_framework.views import APIView
from apis.views import BaseResponseMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from apis.models import Company
from serializers import CompanyUpdateSerializer


class CompanyView(APIView, BaseResponseMixin):

    def post(self, request):
        userJson = JWTAuthentication().authenticate(request)
        if not userJson:
            return self.error_response(error_message="Authentication failed", status=status.HTTP_401_UNAUTHORIZED)
        user = userJson[0]

        data = request.data

        name = data.get('comapnyName')
        email = data.get('email')
        industry = data.get('industry')
        size = data.get('size')
        address = data.get('address')
        countryCode = data.get('countryCode')
        phone = data.get('phone')
        logo = data.get('logo', None)
        tax_id = data.get('tax_id', '')
        website = data.get('website', '')

        if not name or not email or not industry or not size or not address or not countryCode or not phone:
            return self.error_response(error_message="Enter all required Fields.", status=status.HTTP_400_BAD_REQUEST)

        if hasattr(user, 'company') and user.company is not None:
            return self.success_response(data= {'message':"Company details already filled."}, status=status.HTTP_400_BAD_REQUEST)

        company = Company.objects.create(
            name=name,
            email=email,
            industry=industry,
            size=size,
            address=address,
            countryCode=countryCode,
            phone=phone,
            logo=logo,
            tax_id=tax_id,
            website=website
        )

        user.company = company
        user.save()

        return self.success_response({
            "id": str(company.id),
            "name": company.name,
            "email": company.email,
            'message':"Company created successfully."
        }, status=status.HTTP_201_CREATED)


    def patch(self, request):
        userJson = JWTAuthentication().authenticate(request)
        if not userJson:
            return self.error_response(error_message="Authentication failed!", status=status.HTTP_401_UNAUTHORIZED)
        user = userJson[0]

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
        else:
            return self.error_response(error_message=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
