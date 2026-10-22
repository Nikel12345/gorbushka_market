"""
Курс доллара и цены в рублях.

Цены товаров хранятся в долларах (Product.price_usd), а покупатель видит и платит рубли:
Product.price = price_usd × курс, округлённое до PRICE_RUB_STEP (по умолчанию до рубля).
В заказ попадает рублёвая цена на момент оформления — дальше курс на него не влияет.

Курс — официальный курс ЦБ на сегодня (cbr.py). Запрашивается при первом обращении и держится
в кеше до полуночи по Москве, так что у всех процессов он меняется одновременно; каждый полученный
курс сохраняется в ExchangeRate. ЦБ недоступен — берём последний сохранённый курс и спрашиваем
снова через RETRY_SECONDS. Курс в настройке USD_RUB_RATE отключает ЦБ.
"""
import datetime
import logging
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.core.exceptions import BusinessError

from . import cbr
from .models import ExchangeRate

logger = logging.getLogger(__name__)

USD = "USD"
CACHE_KEY = "currency:usd_rub"
RETRY_SECONDS = 5 * 60
KOPECK = Decimal("0.01")
HALF = Decimal("0.5")


class RateUnavailable(BusinessError):
    status_code = 503

    def __init__(self):
        super().__init__("Курс доллара сейчас недоступен, цены не посчитать. Попробуйте позже.", "rate_unavailable")


@dataclass(frozen=True)
class Rate:
    value: Decimal  # рублей за доллар
    date: datetime.date | None  # дата курса ЦБ; None — курс задан настройкой USD_RUB_RATE


def usd_rate() -> Rate:
    if settings.USD_RUB_RATE is not None:
        return Rate(settings.USD_RUB_RATE, None)
    rate = cache.get(CACHE_KEY)
    if rate is None:
        rate, timeout = _load_rate()
        cache.set(CACHE_KEY, rate, timeout)
    return rate


def _load_rate() -> tuple[Rate, int]:
    """Курс и сколько секунд его держать в кеше."""
    now = timezone.localtime()
    try:
        rate_date, value = cbr.fetch_rate(USD, now.date())
    except cbr.CbrError as error:
        saved = ExchangeRate.objects.filter(currency=USD).order_by("-date").first()
        if saved is None:
            logger.error("Нет курса доллара: %s", error)
            raise RateUnavailable() from error
        logger.warning("Курс ЦБ не получен (%s), берём сохранённый на %s", error, saved.date)
        return Rate(saved.rate, saved.date), RETRY_SECONDS

    ExchangeRate.objects.update_or_create(currency=USD, date=rate_date, defaults={"rate": value})
    midnight = datetime.datetime.combine(now.date() + datetime.timedelta(days=1), datetime.time(), now.tzinfo)
    return Rate(value, rate_date), max(int((midnight - now).total_seconds()), 1)


def usd_to_rub(amount: Decimal) -> Decimal:
    """Сумма в долларах → рубли по текущему курсу, с округлением цены до PRICE_RUB_STEP."""
    step = settings.PRICE_RUB_STEP
    steps = (amount * usd_rate().value / step).quantize(Decimal("1"), ROUND_HALF_UP)
    return (steps * step).quantize(KOPECK)


# Фильтр «цена от/до» покупатель задаёт в рублях, а в базе доллары. Границы считаются так,
# чтобы попали ровно товары, чья показанная (округлённая) цена в диапазоне.


def usd_from(rub: Decimal) -> Decimal:
    """Товары с price_usd >= этой суммы стоят в рублях не меньше rub."""
    step = settings.PRICE_RUB_STEP
    steps = (rub / step).to_integral_value(ROUND_CEILING)
    return (steps - HALF) * step / usd_rate().value


def usd_below(rub: Decimal) -> Decimal:
    """Товары с price_usd < этой суммы стоят в рублях не больше rub."""
    step = settings.PRICE_RUB_STEP
    steps = (rub / step).to_integral_value(ROUND_FLOOR)
    return (steps + HALF) * step / usd_rate().value
