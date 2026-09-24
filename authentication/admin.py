from django.contrib import admin
from .models import StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'status', 'course', 'created_at')
    list_filter = ('status', 'course')
    search_fields = ('user__username', 'user__email')