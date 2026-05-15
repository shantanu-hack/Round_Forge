from decimal import Decimal

from django.db.models import Avg, Count

from apps.analytics.models import ReadinessAnalytics
from apps.reports.models import FinalReport


def update_readiness_analytics(user, company):
    reports = FinalReport.objects.filter(user=user, simulation__company=company)
    aggregate = reports.aggregate(avg=Avg("readiness_percent"), total=Count("id"))
    last_report = reports.order_by("-created_at").first()

    strongest_area = ""
    weakest_area = ""
    if last_report:
        strongest_area = (last_report.strengths or [""])[0]
        weakest_area = (last_report.weaknesses or [""])[0]

    analytics, _ = ReadinessAnalytics.objects.update_or_create(
        user=user,
        company=company,
        defaults={
            "total_simulations": aggregate["total"] or 0,
            "average_readiness": aggregate["avg"] or Decimal("0"),
            "strongest_area": strongest_area[:160],
            "weakest_area": weakest_area[:160],
            "last_report": last_report,
        },
    )
    return analytics
