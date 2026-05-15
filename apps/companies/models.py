from django.db import models


class Company(models.Model):
    name = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    tagline = models.CharField(max_length=180)
    description = models.TextField()
    evaluation_style = models.TextField()
    benchmark_description = models.TextField()
    pass_threshold = models.PositiveSmallIntegerField(default=70)
    accent_color = models.CharField(max_length=24, default="#8fb8ff")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active", "order"]),
        ]

    def __str__(self):
        return self.name


class InterviewTrack(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="tracks")
    name = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("company", "slug")
        ordering = ["company__order", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.company.name} - {self.name}"
