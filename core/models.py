from django.db import models



class TimeStampedMixin(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class CodeNameMixin(models.Model):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"


class Currency(models.TextChoices):
    HUF = "HUF", "Hungarian Forint"
    EUR = "EUR", "Euro"
    USD = "USD", "US Dollar"
    GBP = "GBP", "British Pound"
