"""
Курсы ЦБ РФ: https://www.cbr.ru/scripts/XML_daily.asp — бесплатно, без ключа и регистрации.
Ответ — XML в windows-1251:
<ValCurs Date="21.10.2026"><Valute><CharCode>USD</CharCode><Nominal>1</Nominal><Value>82,8879</Value>...
"""
import datetime
import urllib.request
import xml.etree.ElementTree as ET
from decimal import Decimal

DAILY_URL = "https://www.cbr.ru/scripts/XML_daily.asp"
TIMEOUT_SECONDS = 5


class CbrError(Exception):
    """ЦБ не ответил или ответил не тем."""


def fetch_rate(code: str, on_date: datetime.date) -> tuple[datetime.date, Decimal]:
    """
    Официальный курс валюты на дату: (дата курса, рублей за 1 единицу).
    На выходные и праздники ЦБ отдаёт курс последнего рабочего дня — с его датой.
    """
    request = urllib.request.Request(
        f"{DAILY_URL}?date_req={on_date:%d/%m/%Y}", headers={"User-Agent": "gorbushka-market"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
    except OSError as error:  # URLError, HTTPError и таймауты — наследники OSError
        raise CbrError(f"ЦБ недоступен: {error}") from error
    return parse_rate(body, code)


def parse_rate(body: bytes, code: str) -> tuple[datetime.date, Decimal]:
    try:
        root = ET.fromstring(body)
        rate_date = datetime.datetime.strptime(root.attrib["Date"], "%d.%m.%Y").date()
        for valute in root.iter("Valute"):
            if valute.findtext("CharCode") == code:
                nominal = Decimal(valute.findtext("Nominal"))
                value = Decimal(valute.findtext("Value").replace(",", "."))
                return rate_date, (value / nominal).quantize(Decimal("0.0001"))
    except (ET.ParseError, KeyError, ValueError, ArithmeticError, TypeError, AttributeError) as error:
        raise CbrError(f"Не разобрать ответ ЦБ: {error}") from error
    raise CbrError(f"В ответе ЦБ нет курса {code}.")
