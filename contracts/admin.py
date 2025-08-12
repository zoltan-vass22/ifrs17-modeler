from django.contrib import admin
from .models import (
    Portfolio, Product, ContractGroup,
    PremiumPattern, AcquisitionCashflowPolicy,
)

@admin.register(Portfolio)
class PortfolioAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "currency", "created_at", "updated_at")
    list_filter = ("currency",)
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("code",)
    list_per_page = 50

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "measurement_model", "created_at", "updated_at")
    list_filter = ("measurement_model",)
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("code",)
    list_per_page = 50

@admin.register(PremiumPattern)
class PremiumPatternAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "frequency", "is_level", "created_at", "updated_at")
    list_filter = ("frequency", "is_level")
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("code",)
    list_per_page = 50

@admin.register(AcquisitionCashflowPolicy)
class AcquisitionCashflowPolicyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "directly_attributable", "amortize_by_coverage_units", "created_at", "updated_at")
    list_filter = ("directly_attributable", "amortize_by_coverage_units")
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("code",)
    list_per_page = 50

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
    readonly_fields = ("created_at", "updated_at")
    ordering = ("portfolio__code", "product__code", "cohort_year", "code")
    list_per_page = 50
