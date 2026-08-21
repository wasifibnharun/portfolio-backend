from django.contrib.auth import (
    authenticate,
    get_user_model,
    password_validation,
)
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
)
from rest_framework_simplejwt.tokens import RefreshToken, TokenError


User = get_user_model()


class OwnerSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "is_superuser",
        )
        read_only_fields = fields


class OwnerTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Authenticate only the superuser without revealing whether a
    submitted username exists.
    """

    invalid_credentials_message = "Invalid username or password."

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            username=attrs.get("username"),
            password=attrs.get("password"),
        )

        if (
            user is None
            or not user.is_active
            or not user.is_superuser
        ):
            raise AuthenticationFailed(
                self.invalid_credentials_message,
                code="invalid_credentials",
            )

        data = super().validate(attrs)

        data["user"] = OwnerSerializer(
            self.user,
            context=self.context,
        ).data

        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_refresh(self, value):
        try:
            token = RefreshToken(value)
        except TokenError as exc:
            raise serializers.ValidationError(
                "Invalid or expired refresh token."
            ) from exc

        request_user = self.context["request"].user
        token_user_id = token.payload.get("user_id")

        if str(token_user_id) != str(request_user.pk):
            raise serializers.ValidationError(
                "This refresh token does not belong to the current owner."
            )

        self.token = token
        return value

    def save(self, **kwargs):
        self.token.blacklist()


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )
    new_password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
    )

    def validate_old_password(self, value):
        user = self.context["request"].user

        if not user.check_password(value):
            raise serializers.ValidationError(
                "Old password is incorrect."
            )

        return value

    def validate_new_password(self, value):
        user = self.context["request"].user

        try:
            password_validation.validate_password(
                password=value,
                user=user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(list(exc.messages)) from exc

        return value

    def validate(self, attrs):
        if attrs["old_password"] == attrs["new_password"]:
            raise serializers.ValidationError(
                {
                    "new_password": (
                        "New password must be different "
                        "from the old password."
                    )
                }
            )

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])

        return user