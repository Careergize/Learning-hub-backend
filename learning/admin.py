from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Certificate, Enrollment, LessonProgress


class LessonProgressInline(admin.TabularInline):
    model = LessonProgress
    extra = 0


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "status", "progress_percent", "last_accessed")
    list_filter = ("status", "course__category")
    search_fields = ("student__username", "course__title")
    inlines = [LessonProgressInline]


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ("certificate_id", "enrollment", "issued_date", "share_count")
    search_fields = ("certificate_id", "enrollment__student__username")
