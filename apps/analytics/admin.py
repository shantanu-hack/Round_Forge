from django.contrib import admin

from apps.analytics.models import ReadinessAnalytics


@admin.register(ReadinessAnalytics)
class ReadinessAnalyticsAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "total_simulations", "average_readiness", "updated_at")
    list_filter = ("company",)
    search_fields = ("user__email",)
