from django.db import models
from core.models import TimeStampedMixin, CodeNameMixin, Currency


class MeasurementModel(models.TextChoices):
    GMM = "GMM", "General Measurement Model"
    VFA = "VFA", "Variable Fee Approach"  # reserved for later phases


class PremiumFrequency(models.TextChoices):
    SINGLE = "SINGLE", "Single"
    ANNUAL = "ANNUAL", "Annual"
    SEMI_ANNUAL = "SEMI_ANNUAL", "Semi-Annual"
    QUARTERLY = "QUARTERLY", "Quarterly"
    MONTHLY = "MONTHLY", "Monthly"


class Portfolio(TimeStampedMixin, CodeNameMixin):
    """Logical container for products and groups (e.g., Life HU)."""
    currency = models.CharField(
        max_length=3,
        choices=Currency.choices,
        default=Currency.HUF,
    )


class Product(TimeStampedMixin, CodeNameMixin):
    """
    High-level product definition (e.g., 20Y Term Non-Par).
    Keep this lean; details go to assumptions/engine.
    """
    measurement_model = models.CharField(
        max_length=3, choices=MeasurementModel.choices, default=MeasurementModel.GMM
    )
    # Optionally tie a default premium pattern later


class PremiumPattern(TimeStampedMixin, CodeNameMixin):
    """
    Describes how premiums are paid, independent of the cohort (group).
    A product can reference one (FK from ContractGroup, so you can vary by group if needed).
    """
    frequency = models.CharField(
        max_length=12, choices=PremiumFrequency.choices, default=PremiumFrequency.ANNUAL
    )
    is_level = models.BooleanField(default=True)  # level vs stepwise


class AcquisitionCashflowPolicy(TimeStampedMixin, CodeNameMixin):
    """
    Policy describing direct attribution and amortization style for acquisition CF.
    The engine will use this as a hint (later phases).
    """
    directly_attributable = models.BooleanField(default=True)
    amortize_by_coverage_units = models.BooleanField(default=True)


class ContractGroup(TimeStampedMixin, CodeNameMixin):
    """
    IFRS 17 annual cohort (group). Minimum fields the engine will need for M0.
    """
    portfolio = models.ForeignKey(Portfolio, on_delete=models.PROTECT, related_name="groups")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="groups")
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.HUF)

    cohort_year = models.PositiveIntegerField()          # e.g., 2024
    coverage_term_years = models.PositiveIntegerField()  # service period length
    premium_term_years = models.PositiveIntegerField()   # <= coverage_term_years

    premium_pattern = models.ForeignKey(
        PremiumPattern, on_delete=models.PROTECT, related_name="groups"
    )
    acq_policy = models.ForeignKey(
        AcquisitionCashflowPolicy, on_delete=models.PROTECT, related_name="groups"
    )

    # Simple volumes at inception (toy)
    policy_count = models.PositiveIntegerField(default=0)
    sum_assured = models.DecimalField(max_digits=18, decimal_places=2, default=0)      # nominal
    written_premium = models.DecimalField(max_digits=18, decimal_places=2, default=0)  # nominal

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["portfolio", "product", "cohort_year", "code"],
                name="uniq_group_per_portfolio_product_year_code",
            ),
        ]
