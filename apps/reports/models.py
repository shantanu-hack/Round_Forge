from django.conf import settings
from django.db import models


class FinalReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="final_reports")
    simulation = models.OneToOneField("interviews.SimulationSession", on_delete=models.CASCADE, related_name="final_report")
    readiness_percent = models.DecimalField(max_digits=5, decimal_places=2)
    round_analysis = models.JSONField(default=list)
    strengths = models.JSONField(default=list)
    weaknesses = models.JSONField(default=list)
    company_alignment = models.TextField()
    ai_generated_analysis = models.TextField()
    improvement_roadmap = models.JSONField(default=list)
    recommended_resources = models.JSONField(default=list)
    retry_recommendation = models.TextField()
    readiness_timeline = models.CharField(max_length=180)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["readiness_percent"]),
        ]

    def __str__(self):
        return f"{self.user} report - {self.readiness_percent}%"
