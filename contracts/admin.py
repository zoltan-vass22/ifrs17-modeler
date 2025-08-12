from django.contrib import admin
from .models import (
    Portfolio, Product, ContractGroup,
    PremiumPattern, AcquisitionCashflowPolicy,
)


@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "currency", "created_at", "updated_at")
    search_fields = ("code", "name")
    list_filter = ("currency",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "measurement_model", "created_at", "updated_at")
    search_fields = ("code", "name")
    list_filter = ("measurement_model",)


@admin.register(PremiumPattern)
class PremiumPatternAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "frequency", "is_level", "created_at", "updated_at")
    list_filter = ("frequency", "is_level")
    search_fields = ("code", "name")


@admin.register(AcquisitionCashflowPolicy)
class AcquisitionCashflowPolicyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "directly_attributable",
                    "amortize_by_coverage_units", "created_at", "updated_at")
    list_filter = ("directly_attributable", "amortize_by_coverage_units")
    search_fields = ("code", "name")


@admin.register(ContractGroup)
class ContractGroupAdmin(admin.ModelAdmin):
    list_display = (
        "code", "name", "portfolio", "product", "cohort_year",
        "coverage_term_years", "premium_term_years", "currency",
        "policy_count", "sum_assured", "written_premium",
        "created_at", "updated_at",
    )
    list_filter = ("portfolio", "product", "cohort_year", "currency")
    search_fields = ("code", "name")
    autocomplete_fields = ("portfolio", "product", "premium_pattern", "acq_policy")
