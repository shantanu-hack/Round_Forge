from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import render

from apps.analytics.models import ReadinessAnalytics
from apps.companies.models import Company
from apps.interviews.models import SimulationSession
from apps.reports.models import FinalReport


@login_required
def dashboard_home(request):
    companies = Company.objects.filter(is_active=True).prefetch_related("tracks")
    simulations = request.user.simulations.select_related("company", "current_round").order_by("-started_at")[:6]
    reports = request.user.final_reports.select_related("simulation__company").order_by("-created_at")[:4]
    analytics = ReadinessAnalytics.objects.filter(user=request.user).select_related("company")
    return render(
        request,
        "dashboard/home.html",
        {"companies": companies, "simulations": simulations, "reports": reports, "analytics": analytics},
    )


@staff_member_required
def admin_insights(request):
    stats = {
        "user_count": request.user.__class__.objects.count(),
        "report_count": FinalReport.objects.count(),
        "simulation_count": SimulationSession.objects.count(),
        "average_readiness": FinalReport.objects.aggregate(avg=Avg("readiness_percent"))["avg"] or 0,
    }
    recent_simulations = SimulationSession.objects.select_related("user", "company").order_by("-started_at")[:10]
    company_stats = (
        SimulationSession.objects.values("company__name")
        .annotate(total=Count("id"), avg=Avg("final_report__readiness_percent"))
        .order_by("company__name")
    )
    return render(
        request,
        "dashboard/admin_insights.html",
        {"stats": stats, "recent_simulations": recent_simulations, "company_stats": company_stats},
    )
