from django.contrib import admin
from .models import DiscountCurve, RiskAdjustmentParams

@admin.register(DiscountCurve)
class DiscountCurveAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "curve_type", "compounding", "periods", "created_at", "updated_at")
    list_filter = ("curve_type", "compounding")
    search_fields = ("code", "name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("curve_type", "code")
    list_per_page = 50

@admin.register(RiskAdjustmentParams)
class RiskAdjustmentParamsAdmin(admin.ModelAdmin):
    list_display = ("code", "method", "factor", "created_at", "updated_at")
    list_filter = ("method",)
    search_fields = ("code",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("code",)
    list_per_page = 50
