from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.authentication.models import User


@admin.register(User)
class RoundForgeUserAdmin(UserAdmin):
    list_display = ("email", "full_name", "target_role", "is_staff", "created_at")
    search_fields = ("email", "full_name", "username")
    ordering = ("-created_at",)
    fieldsets = UserAdmin.fieldsets + (("Round Forge", {"fields": ("full_name", "target_role")}),)
