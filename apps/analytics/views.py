from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.analytics.models import ReadinessAnalytics


@login_required
def analytics_home(request):
    analytics = ReadinessAnalytics.objects.filter(user=request.user).select_related("company")
    return render(request, "analytics/home.html", {"analytics": analytics})
