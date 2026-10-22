from django.db import models


class ExchangeRate(models.Model):
    """
    Курс ЦБ на дату — история и запас на случай, если ЦБ недоступен.
    Пишет currency.services при каждом получении курса; поправленный вручную курс
    перезапишется следующим ответом ЦБ за ту же дату.
    """

    currency = models.CharField("валюта", max_length=3, default="USD")
    date = models.DateField("дата курса")
    rate = models.DecimalField("рублей за 1 единицу", max_digits=12, decimal_places=4)
    updated_at = models.DateTimeField("получен", auto_now=True)

    class Meta:
        verbose_name = "курс валюты"
        verbose_name_plural = "курсы валют"
        ordering = ["-date", "currency"]
        constraints = [
            models.UniqueConstraint(fields=["currency", "date"], name="currency_rate_unique_date"),
            models.CheckConstraint(condition=models.Q(rate__gt=0), name="currency_rate_positive"),
        ]

    def __str__(self):
        return f"{self.currency} {self.rate} на {self.date:%d.%m.%Y}"
