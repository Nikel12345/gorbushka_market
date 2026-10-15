from django.contrib import admin

from .models import Wallet, WalletTransaction


class WalletTransactionInline(admin.TabularInline):
    model = WalletTransaction
    extra = 0
    fields = ("created_at", "kind", "amount", "balance_after", "description")
    readonly_fields = fields
    can_delete = False
    ordering = ("-created_at", "-id")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    """Только просмотр: баланс меняется исключительно через wallet.services.change_balance."""

    list_display = ("user", "balance", "updated_at")
    search_fields = ("user__email",)
    readonly_fields = ("user", "balance", "created_at", "updated_at")
    inlines = [WalletTransactionInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
