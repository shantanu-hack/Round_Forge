from django.contrib import admin

from apps.companies.models import Company, InterviewTrack


class InterviewTrackInline(admin.TabularInline):
    model = InterviewTrack
    extra = 0


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "pass_threshold", "is_active", "order")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [InterviewTrackInline]


@admin.register(InterviewTrack)
class InterviewTrackAdmin(admin.ModelAdmin):
    list_display = ("name", "company", "is_active")
    prepopulated_fields = {"slug": ("name",)}
    list_filter = ("company", "is_active")
