from django.db.models import Exists, OuterRef, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from learning.models import Enrollment

from .models import CourseNote, NoteBookmark
from .serializers import CourseNoteDetailSerializer, CourseNoteListSerializer


class CourseNoteViewSet(viewsets.ReadOnlyModelViewSet):
    """Backs the 'Course Notes & PDF Study Materials' section: only shows
    notes for courses the current student is actually enrolled in, with the
    same filters the frontend UI offers (course tab, type, search, saved-only)."""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CourseNoteDetailSerializer
        return CourseNoteListSerializer

    def get_queryset(self):
        user = self.request.user
        enrolled_course_ids = Enrollment.objects.filter(student=user).values_list("course_id", flat=True)

        qs = CourseNote.objects.filter(course_id__in=enrolled_course_ids).select_related(
            "course", "instructor"
        ).prefetch_related("sections", "code_snippets")

        # Annotate bookmark state in one query instead of N+1 .exists() calls.
        qs = qs.annotate(
            _bookmarked_by_user=Exists(
                NoteBookmark.objects.filter(student=user, note=OuterRef("pk"))
            )
        )

        params = self.request.query_params

        course_id = params.get("course")
        if course_id and course_id != "all":
            qs = qs.filter(course_id=course_id)

        note_type = params.get("type")
        if note_type and note_type != "all":
            qs = qs.filter(note_type=note_type)

        if params.get("bookmarked") in ("true", "1"):
            qs = qs.filter(bookmarks__student=user)

        search = params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(module_number__icontains=search)
                | Q(course__title__icontains=search)
                | Q(topics__icontains=search)
                | Q(instructor__name__icontains=search)
            ).distinct()

        return qs

    @action(detail=True, methods=["post"])
    def bookmark(self, request, pk=None):
        """Toggle the 'save note' bookmark for the current student."""
        note = get_object_or_404(self.get_queryset(), pk=pk)
        bookmark, created = NoteBookmark.objects.get_or_create(student=request.user, note=note)
        if not created:
            bookmark.delete()
        return Response({
            "noteId": note.id,
            "isBookmarked": created,
            "bookmarkCount": note.bookmarks.count(),
        })

    @action(detail=True, methods=["post"])
    def download(self, request, pk=None):
        """Bumps the download counter and returns the full note payload
        (including previewContent) so the client can generate/save the file."""
        note = get_object_or_404(self.get_queryset(), pk=pk)
        note.download_count += 1
        note.save(update_fields=["download_count"])
        data = CourseNoteDetailSerializer(note, context={"request": request}).data
        return Response(data)
