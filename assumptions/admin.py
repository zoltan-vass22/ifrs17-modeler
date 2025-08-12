from django.contrib import admin
from .models import DiscountCurve, RiskAdjustmentParams


@admin.register(DiscountCurve)
class DiscountCurveAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "curve_type", "compounding", "periods", "created_at", "updated_at")
    list_filter = ("curve_type", "compounding")
    search_fields = ("code", "name")


@admin.register(RiskAdjustmentParams)
class RiskAdjustmentParamsAdmin(admin.ModelAdmin):
    list_display = ("code", "method", "factor", "created_at", "updated_at")
    list_filter = ("method",)
    search_fields = ("code",)
