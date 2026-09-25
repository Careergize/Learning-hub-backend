from django.contrib import admin

from .models import CourseNote, NoteBookmark, NoteCodeSnippet, NoteSection


class NoteSectionInline(admin.StackedInline):
    model = NoteSection
    extra = 0


class NoteCodeSnippetInline(admin.StackedInline):
    model = NoteCodeSnippet
    extra = 0


@admin.register(CourseNote)
class CourseNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "module_number", "note_type", "pages", "download_count")
    list_filter = ("note_type", "course")
    search_fields = ("title", "description", "course__title")
    inlines = [NoteSectionInline, NoteCodeSnippetInline]


@admin.register(NoteBookmark)
class NoteBookmarkAdmin(admin.ModelAdmin):
    list_display = ("student", "note", "created_at")
    search_fields = ("student__username", "note__title")
