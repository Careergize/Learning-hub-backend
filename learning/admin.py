from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import (
    Certificate,
    Enrollment,
    LessonProgress,
    ScheduleSession,
    Attendance,
    ChecklistItem,
    Achievement,
)


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
@admin.register(ScheduleSession)
class ScheduleSessionAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "topic",
        "date",
        "start_time",
        "end_time",
        "instructor",
        "platform",
    )
    list_filter = ("course", "instructor", "date")
    search_fields = ("topic", "course__title", "instructor__name")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "session", "status", "check_in_time")
    list_filter = ("status",)
    search_fields = ("student__username", "session__topic")


@admin.register(ChecklistItem)
class ChecklistItemAdmin(admin.ModelAdmin):
    list_display = ("student", "session", "text", "done")
    list_filter = ("done",)
    search_fields = ("student__username", "text", "session__topic")

@admin.register(Achievement)
class AchievementAdmin(admin.ModelAdmin):
    list_display = ("student", "title", "earned_at")
    search_fields = ("student__username", "title")