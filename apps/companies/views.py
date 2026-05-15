from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.companies.models import Company, InterviewTrack
from apps.interviews.services.progression import start_simulation


@login_required
def company_list(request):
    companies = Company.objects.filter(is_active=True).prefetch_related("tracks")
    return render(request, "companies/list.html", {"companies": companies})


@login_required
def company_detail(request, slug):
    company = get_object_or_404(Company.objects.prefetch_related("tracks__rounds"), slug=slug, is_active=True)
    recent = request.user.simulations.filter(company=company).select_related("current_round").order_by("-started_at")[:4]
    return render(request, "companies/detail.html", {"company": company, "recent": recent})


@login_required
@require_POST
def start_company_simulation(request, slug):
    company = get_object_or_404(Company, slug=slug, is_active=True)
    track = get_object_or_404(InterviewTrack, company=company, is_active=True)
    simulation = start_simulation(request.user, track)
    return redirect("interviews:simulation", simulation_id=simulation.id)
