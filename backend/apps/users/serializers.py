import re

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from . import services
from .models import User

PHONE_CHARS = re.compile(r"^\+?[\d\s()-]+$")


class PhoneField(serializers.CharField):
    """
    Телефон в любой привычной записи: «+7 999 123-45-67», «8 (999) 123-45-67», «9991234567».
    Хранится цифрами с «+»: +79991234567. Российский номер можно без кода страны. Пусто — можно.
    """

    default_error_messages = {"invalid_phone": "Введите номер телефона, например +7 999 123-45-67."}

    def __init__(self, **kwargs):
        kwargs.setdefault("max_length", 30)
        kwargs.setdefault("allow_blank", True)
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        if not value:
            return ""
        if not PHONE_CHARS.match(value):
            self.fail("invalid_phone")
        digits = re.sub(r"\D", "", value)
        if len(digits) == 10:
            digits = "7" + digits
        elif len(digits) == 11 and digits.startswith("8") and not value.startswith("+"):
            digits = "7" + digits[1:]
        if not 11 <= len(digits) <= 15:
            self.fail("invalid_phone")
        return "+" + digits


def validate_new_password(password: str, user: User) -> None:
    """Валидаторы паролей (длина, похожесть на email и т.д.) из AUTH_PASSWORD_VALIDATORS."""
    try:
        password_validation.validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": list(exc.messages)}) from exc


class UserSerializer(serializers.ModelSerializer):
    """is_staff — сотрудник магазина: ему доступна админка (/admin/...)."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "phone", "is_staff", "date_joined"]
        read_only_fields = fields


class ProfileUpdateSerializer(serializers.ModelSerializer):
    """Что пользователь может менять сам. Email — только через отдельный сценарий с подтверждением."""

    phone = PhoneField(required=False)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone"]

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
        candidate = User(
            email=attrs["email"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        validate_new_password(attrs["password"], candidate)
        return attrs

    def create(self, validated_data):
        return services.register_user(**validated_data)


class CheckoutAccountSerializer(serializers.Serializer):
    """
    Гость на оформлении заказа указывает почту и пароль. Есть аккаунт с этой почтой — это вход:
    пароль должен подойти. Нет — регистрация: пароль проверяется как при регистрации, а сам аккаунт
    создаёт оформление (в одной транзакции с заказом). validated_data["user"] — найденный аккаунт или None.
    """

    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        email = User.objects.normalize_email(attrs["email"])
        user = None
        if User.objects.filter(email__iexact=email).exists():
            user = services.authenticate_user(self.context.get("request"), email=email, password=attrs["password"])
            if user is None:
                raise serializers.ValidationError({"password": ["Неверный пароль от аккаунта с этой почтой."]})
        else:
            validate_new_password(attrs["password"], User(email=email))
        return {**attrs, "email": email, "user": user}


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
