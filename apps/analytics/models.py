from django.conf import settings
from django.db import models


class ReadinessAnalytics(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="readiness_analytics")
    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="readiness_analytics")
    total_simulations = models.PositiveIntegerField(default=0)
    average_readiness = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    strongest_area = models.CharField(max_length=160, blank=True)
    weakest_area = models.CharField(max_length=160, blank=True)
    last_report = models.ForeignKey("reports.FinalReport", on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "company")
        verbose_name_plural = "Readiness analytics"
        indexes = [
            models.Index(fields=["user", "company"]),
            models.Index(fields=["average_readiness"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.company.name}: {self.average_readiness}%"
