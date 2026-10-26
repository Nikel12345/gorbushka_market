from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from . import services


@receiver(user_logged_in, dispatch_uid="cart_merge_guest_cart")
def merge_guest_cart(sender, request, user, **kwargs):
    """Любой вход (страница входа, регистрация, оформление заказа гостем) забирает корзину гостя из сессии."""
    session = getattr(request, "session", None)
    cart_id = session.pop(services.GUEST_CART_SESSION_KEY, None) if session is not None else None
    if cart_id:
        services.merge_guest_cart(cart_id, user)
