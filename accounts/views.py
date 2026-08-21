from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .permissions import IsOwner
from .serializers import (
    ChangePasswordSerializer,
    LogoutSerializer,
    OwnerSerializer,
    OwnerTokenObtainPairSerializer,
)


class OwnerLoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = OwnerTokenObtainPairSerializer


class OwnerTokenRefreshView(TokenRefreshView):
    permission_classes = [AllowAny]


class LogoutView(generics.GenericAPIView):
    permission_classes = [IsOwner]
    serializer_class = LogoutSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Successfully logged out."},
            status=status.HTTP_200_OK,
        )


class CurrentOwnerView(generics.RetrieveAPIView):
    permission_classes = [IsOwner]
    serializer_class = OwnerSerializer

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    permission_classes = [IsOwner]
    serializer_class = ChangePasswordSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": (
                    "Password changed successfully. "
                    "Use the new password for future logins."
                )
            },
            status=status.HTTP_200_OK,
        )