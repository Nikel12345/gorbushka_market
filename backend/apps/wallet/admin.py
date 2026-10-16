from django import forms
from django.contrib import admin

from apps.core.exceptions import BusinessError

from . import services
from .models import Bucket, Wallet, WalletOperation, WalletTransaction

BUCKETS = [bucket.value for bucket in Bucket]


class WalletTransactionInline(admin.TabularInline):
    """Журнал не редактируется: исправления — новой корректировкой (правкой балансов выше)."""

    model = WalletTransaction
    extra = 0
    fields = ("created_at", "kind", "bucket", "amount", "balance_after", "description", "operation")
    readonly_fields = fields
    can_delete = False
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request, obj=None):
        return False


class WalletAdminForm(forms.ModelForm):
    comment = forms.CharField(
        label="Комментарий к изменению",
        required=False,
        max_length=200,
        help_text="Попадёт в описание корректировки в журнале.",
    )

    class Meta:
        model = Wallet
        fields = ["user", *BUCKETS]


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """
    Балансы редактируются: изменение сохраняется операцией «Корректировка»
    с проводками на разницу (wallet.services.adjust_wallet), а не прямой записью в поля.
    """

    form = WalletAdminForm
    list_display = ("user", "available", "bonus", "frozen", "updated_at")
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [WalletTransactionInline]

    def get_readonly_fields(self, request, obj=None):
        # Владельца у существующего кошелька не меняем: его журнал принадлежит этому пользователю
        return [*self.readonly_fields, "user"] if obj else self.readonly_fields

    def save_model(self, request, obj, form, change):
        target = {bucket: form.cleaned_data[bucket] for bucket in BUCKETS}
        if change:
            current = Wallet.objects.get(pk=obj.pk)
            deltas = {bucket: target[bucket] - getattr(current, bucket) for bucket in BUCKETS}
        else:
            for bucket in BUCKETS:
                setattr(obj, bucket, 0)
            obj.save()
            deltas = target

        comment = form.cleaned_data.get("comment") or "без комментария"
        try:
            services.adjust_wallet(user=obj.user, deltas=deltas, description=f"Админка ({request.user}): {comment}")
        except BusinessError as error:
            # Форма уже проверила ограничения модели; сюда попадаем только при гонке с другой операцией
            self.message_user(request, f"Баланс не изменён: {error.message}", level="error")
        obj.refresh_from_db()


class OperationEntryInline(WalletTransactionInline):
    fields = ("wallet", "bucket", "amount", "balance_after")
    readonly_fields = fields


@admin.register(WalletOperation)
class WalletOperationAdmin(admin.ModelAdmin):
    """Операции — журнал: суммы не меняются (иначе разойдутся с балансами), описание можно поправить."""

    list_display = ("id", "kind", "description", "created_at")
    list_filter = ("kind",)
    search_fields = ("description",)
    readonly_fields = ("kind", "created_at")
    inlines = [OperationEntryInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
