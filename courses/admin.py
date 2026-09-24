from django.contrib import admin

from .models import Category, Course, Instructor, Lesson, Skill


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    ordering = ["order"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "instructor", "level", "duration_weeks", "is_published")
    list_filter = ("category", "level", "is_published")
    search_fields = ("title", "instructor__name")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("skills",)
    inlines = [LessonInline]


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ("name", "role", "avatar_initials", "email")
    search_fields = ("name",)


admin.site.register(Category)
admin.site.register(Skill)
