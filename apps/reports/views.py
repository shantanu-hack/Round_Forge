from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.reports.models import FinalReport


@login_required
def report_list(request):
    reports = request.user.final_reports.select_related("simulation__company").order_by("-created_at")
    return render(request, "reports/list.html", {"reports": reports})


@login_required
def report_detail(request, report_id):
    report = get_object_or_404(
        FinalReport.objects.select_related("simulation__company", "simulation__track"),
        id=report_id,
        user=request.user,
    )
    return render(request, "reports/detail.html", {"report": report})
