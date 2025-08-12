from django.db import models
from django.core.exceptions import ValidationError
from core.models import TimeStampedMixin, CodeNameMixin


class CurveType(models.TextChoices):
    LOCKED_IN = "LOCKED_IN", "Locked-in (at initial recognition)"
    CURRENT = "CURRENT", "Current (measurement-date)"


class Compounding(models.TextChoices):
    ANNUAL = "ANNUAL", "Annual"
    # You can add SEMI_ANNUAL, MONTHLY later if needed.


class DiscountCurve(TimeStampedMixin, CodeNameMixin):
    """
    Minimal discount curve for Phase 1/2.
    Store a simple term-structure as a list of per-period spot rates (decimals).
    Example: [0.03, 0.03, 0.03] for 3 annual periods @ 3%.
    """
    curve_type = models.CharField(max_length=10, choices=CurveType.choices, default=CurveType.CURRENT)
    compounding = models.CharField(max_length=10, choices=Compounding.choices, default=Compounding.ANNUAL)

    # Store term structure as JSON list of numbers (floats/decimals).
    rates = models.JSONField(help_text="List of per-period spot rates as decimals, e.g. [0.03, 0.031, 0.032].")

    def clean(self):
        if not isinstance(self.rates, list) or len(self.rates) == 0:
            raise ValidationError("rates must be a non-empty list")
        for r in self.rates:
            try:
                float(r)
            except Exception as _:
                raise ValidationError("rates must be numeric values")

    @property
    def periods(self) -> int:
        return len(self.rates)


class RAMethod(models.TextChoices):
    TOY_FACTOR = "TOY_FACTOR", "Toy factor × expected claims"   # Phase 1
    # Future:
    CONFIDENCE_LEVEL = "CONFIDENCE_LEVEL", "Confidence level method"
    COST_OF_CAPITAL = "COST_OF_CAPITAL", "Cost of capital method"


class RiskAdjustmentParams(TimeStampedMixin, CodeNameMixin):
    method = models.CharField(max_length=20, choices=RAMethod.choices, default=RAMethod.TOY_FACTOR)
    factor = models.DecimalField(
        max_digits=6, decimal_places=4, default=0.1000,
        help_text="For TOY_FACTOR, RA per period = factor × expected claims."
    )
    notes = models.TextField(blank=True, default="")
