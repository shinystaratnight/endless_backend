from rest_framework_simplejwt.views import TokenObtainPairView

from r3sourcer.apps.login.api.serializers import JwtTokenObtainPairSerializer


class JwtTokenPairView(TokenObtainPairView):
    serializer_class = JwtTokenObtainPairSerializer
