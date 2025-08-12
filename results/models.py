from django.db import models
from django.utils import timezone
from decimal import Decimal
from core.models import TimeStampedMixin, CodeNameMixin, Currency
from contracts.models import ContractGroup


class Component(models.TextChoices):
    # Keep this minimal for Phase 1; expand in Phase 3 (movement categories)
    INIT_PV_IN = "INIT_PV_IN", "Initial PV of inflows"
    INIT_PV_OUT = "INIT_PV_OUT", "Initial PV of outflows"
    INIT_RA = "INIT_RA", "Initial Risk Adjustment (PV)"
    INIT_FCF = "INIT_FCF", "Initial Fulfilment Cash Flows"
    INIT_CSM = "INIT_CSM", "Initial CSM"
    INIT_LOSS_COMP = "INIT_LOSS_COMP", "Initial Loss Component"

    CSM_OPEN = "CSM_OPEN", "Opening CSM"
    CSM_INT = "CSM_INT", "CSM interest (locked-in)"
    CSM_REL = "CSM_REL", "CSM release (coverage units)"
    CSM_CLOSE = "CSM_CLOSE", "Closing CSM"

    RA_OPEN = "RA_OPEN", "Opening RA"
    RA_REL = "RA_REL", "RA release"
    RA_CLOSE = "RA_CLOSE", "Closing RA"

    BEL_OPEN = "BEL_OPEN", "Opening BEL (excl. CSM)"
    BEL_CLOSE = "BEL_CLOSE", "Closing BEL (excl. CSM)"

    REV_SERVICE = "REV_SERVICE", "Insurance revenue (service)"
    EXP_SERVICE = "EXP_SERVICE", "Insurance service expenses"
    SRV_RESULT = "SRV_RESULT", "Insurance service result"

    FIN_RESULT = "FIN_RESULT", "Insurance finance income/expense"


class ResultSet(TimeStampedMixin, CodeNameMixin):
    """
    A single calculation run for one ContractGroup under one scenario.
    """
    group = models.ForeignKey(ContractGroup, on_delete=models.CASCADE, related_name="result_sets")
    currency = models.CharField(max_length=3, choices=Currency.choices)
    scenario_name = models.CharField(max_length=100, default="BASE")
    measurement_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["group", "scenario_name", "measurement_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} — {self.group.code} — {self.scenario_name} @ {self.measurement_date}"


class RollforwardLine(models.Model):
    """
    One numeric output line for a period (t = 0 for initial recognition).
    Keep amounts as Decimal for accounting.
    """
    result = models.ForeignKey(ResultSet, on_delete=models.CASCADE, related_name="lines")
    period_index = models.PositiveIntegerField(help_text="0 = initial recognition; 1..N = subsequent periods")
    component = models.CharField(max_length=32, choices=Component.choices)
    amount = models.DecimalField(max_digits=24, decimal_places=6, default=Decimal("0.0"))

    class Meta:
        indexes = [
            models.Index(fields=["result", "period_index", "component"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["result", "period_index", "component"],
                name="uniq_result_period_component",
            )
        ]

    def __str__(self) -> str:
        return f"{self.result.code} t={self.period_index} {self.component}: {self.amount}"
