from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from . import services
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """is_staff — сотрудник магазина: ему доступна админка (/admin/...)."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "is_staff", "date_joined"]
        read_only_fields = fields


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Что пользователь может менять сам. Email — только через отдельный сценарий с подтверждением."""

    class Meta:
        model = User
        fields = ["first_name", "last_name"]

    def update(self, instance, validated_data):
        return services.update_profile(instance, **validated_data)

    def to_representation(self, instance):
        return UserSerializer(instance, context=self.context).data


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)

    def validate_email(self, value):
        email = User.objects.normalize_email(value)
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Пользователь с таким email уже зарегистрирован.")
        return email

    def validate(self, attrs):
        # Валидаторы паролей (длина, похожесть на email и т.д.) из AUTH_PASSWORD_VALIDATORS
        candidate = User(
            email=attrs["email"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            password_validation.validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": list(exc.messages)}) from exc
        return attrs

    def create(self, validated_data):
        return services.register_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    default_error_messages = {
        "invalid_credentials": "Неверный email или пароль.",
    }

    def validate(self, attrs):
        user = services.authenticate_user(
            self.context.get("request"),
            email=User.objects.normalize_email(attrs["email"]),
            password=attrs["password"],
        )
        # authenticate() возвращает None и для неактивных пользователей,
        # поэтому не раскрываем, существует ли аккаунт.
        if user is None:
            self.fail("invalid_credentials")
        attrs["user"] = user
        return attrs
