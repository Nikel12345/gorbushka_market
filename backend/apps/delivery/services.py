"""
Доступное время доставки. Используется списком слотов в API и (следующим шагом)
оформлением заказа для проверки выбранного времени.
"""
import datetime
from dataclasses import dataclass

from django.utils import timezone

from apps.core.exceptions import BusinessError

from .models import DeliveryMethod, DeliveryTimeWindow


@dataclass(frozen=True)
class DeliverySlot:
    date: datetime.date
    window: DeliveryTimeWindow

    @property
    def window_id(self) -> int:
        return self.window.id

    @property
    def start(self) -> datetime.time:
        return self.window.start_time

    @property
    def end(self) -> datetime.time:
        return self.window.end_time


def get_slots(method: DeliveryMethod, now: datetime.datetime | None = None) -> list[DeliverySlot]:
    """
    Слоты на slot_days_ahead дней, начиная с сегодня + eta_min_days
    (время — по TIME_ZONE проекта). Сегодняшние интервалы, которые уже начались,
    не предлагаются.
    """
    if not method.has_slots:
        return []

    now = timezone.localtime(now)
    windows = [window for window in method.time_windows.all() if window.is_active]
    first_day = now.date() + datetime.timedelta(days=method.eta_min_days or 0)

    slots = []
    for offset in range(method.slot_days_ahead):
        day = first_day + datetime.timedelta(days=offset)
        for window in windows:
            if day == now.date() and window.start_time <= now.time():
                continue
            slots.append(DeliverySlot(date=day, window=window))
    return slots


def validate_slot(
    method: DeliveryMethod,
    *,
    date: datetime.date | None,
    window_id: int | None,
    now: datetime.datetime | None = None,
) -> DeliverySlot | None:
    """Проверяет выбранное покупателем время. Для способов без выбора времени — None."""
    if not method.has_slots:
        if date or window_id:
            raise BusinessError(f"Для способа «{method.name}» время не выбирается.", code="slot_not_supported")
        return None

    if not date or not window_id:
        raise BusinessError(f"Выберите время доставки для способа «{method.name}».", code="slot_required")

    for slot in get_slots(method, now=now):
        if slot.date == date and slot.window_id == window_id:
            return slot
    raise BusinessError("Выбранное время доставки недоступно.", code="slot_unavailable")
