from django.contrib import admin

from apps.reports.models import FinalReport


@admin.register(FinalReport)
class FinalReportAdmin(admin.ModelAdmin):
    list_display = ("user", "simulation", "readiness_percent", "created_at")
    list_filter = ("simulation__company",)
    search_fields = ("user__email", "company_alignment", "ai_generated_analysis")
