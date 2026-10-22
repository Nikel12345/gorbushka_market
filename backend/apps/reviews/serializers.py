from rest_framework import serializers

from apps.catalog.models import Product

from . import services
from .models import EMPTY_TEXT_MESSAGE, TEXT_FIELDS, Review


class ReviewSerializer(serializers.ModelSerializer):
    """
    Отзыв — один для витрины и страницы покупателя; админка добавляет автора (ReviewAdminSerializer).
    Товар задаётся только при создании, автор — текущий пользователь.
    """

    product_id = serializers.PrimaryKeyRelatedField(source="product", queryset=Product.objects.on_sale())
    product_title = serializers.CharField(source="product.title", read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "product_id", "product_title", "author_name", "rating", *TEXT_FIELDS, "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_fields(self):
        fields = super().get_fields()
        if isinstance(self.instance, Review):
            fields["product_id"].read_only = True
        return fields

    def get_author_name(self, review) -> str:
        # Email на витрине не показываем
        return review.author.first_name.strip() or "Покупатель"

    def validate(self, attrs):
        if not any(attrs.get(field, getattr(self.instance, field, "")) for field in TEXT_FIELDS):
            raise serializers.ValidationError(EMPTY_TEXT_MESSAGE)
        return attrs

    def create(self, validated_data):
        # author приходит из view через serializer.save(author=...)
        return services.create_review(**validated_data)

    def update(self, instance, validated_data):
        return services.update_review(instance, **validated_data)


class ReviewAdminSerializer(ReviewSerializer):
    """Отзыв в админке магазина: плюс автор."""

    author_id = serializers.IntegerField(read_only=True)
    author_email = serializers.EmailField(source="author.email", read_only=True)

    class Meta(ReviewSerializer.Meta):
        fields = [*ReviewSerializer.Meta.fields, "author_id", "author_email"]
