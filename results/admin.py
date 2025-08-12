from django.contrib import admin
from .models import ResultSet, RollforwardLine


class RollforwardLineInline(admin.TabularInline):
    model = RollforwardLine
    extra = 0
    fields = ("period_index", "component", "amount")
    ordering = ("period_index", "component")


@admin.register(ResultSet)
class ResultSetAdmin(admin.ModelAdmin):
    list_display = ("code", "group", "scenario_name", "measurement_date", "currency", "created_at")
    list_filter = ("scenario_name", "currency", "measurement_date")
    search_fields = ("code", "group__code", "group__name")
    inlines = [RollforwardLineInline]
