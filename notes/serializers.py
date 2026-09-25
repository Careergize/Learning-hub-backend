from rest_framework import serializers

from .models import CourseNote, NoteCodeSnippet, NoteSection


class NoteSectionSerializer(serializers.ModelSerializer):
    bulletPoints = serializers.JSONField(source="bullet_points")
    keyHighlight = serializers.CharField(source="key_highlight", allow_blank=True)

    class Meta:
        model = NoteSection
        fields = ["heading", "content", "bulletPoints", "keyHighlight"]


class NoteCodeSnippetSerializer(serializers.ModelSerializer):
    class Meta:
        model = NoteCodeSnippet
        fields = ["title", "language", "code"]


class CourseNoteListSerializer(serializers.ModelSerializer):
    """Shaped to match the frontend's `CourseNote` card fields (no nested
    previewContent — that's added in CourseNoteDetailSerializer)."""

    courseId = serializers.IntegerField(source="course.id", read_only=True)
    courseTitle = serializers.CharField(source="course.title", read_only=True)
    courseIcon = serializers.CharField(source="course.icon", read_only=True)
    accentColor = serializers.CharField(source="course.accent_color", read_only=True)
    moduleNumber = serializers.CharField(source="module_number", read_only=True)
    instructor = serializers.SerializerMethodField()
    fileSize = serializers.CharField(source="file_size_display", read_only=True)
    updatedDate = serializers.CharField(source="edition", read_only=True)
    type = serializers.CharField(source="note_type", read_only=True)
    isBookmarked = serializers.SerializerMethodField()
    downloadUrl = serializers.SerializerMethodField()
    downloadCount = serializers.IntegerField(source="download_count", read_only=True)

    class Meta:
        model = CourseNote
        fields = [
            "id", "courseId", "courseTitle", "courseIcon", "accentColor",
            "moduleNumber", "title", "description", "instructor", "pages",
            "fileSize", "updatedDate", "type", "topics", "isBookmarked",
            "downloadUrl", "downloadCount",
        ]

    def get_instructor(self, obj):
        return obj.effective_instructor.name if obj.effective_instructor else ""

    def get_isBookmarked(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        # Prefetched on the queryset as `_bookmarked_by_user` when available.
        if hasattr(obj, "_bookmarked_by_user"):
            return obj._bookmarked_by_user
        return obj.bookmarks.filter(student=request.user).exists()

    def get_downloadUrl(self, obj):
        request = self.context.get("request")
        if obj.pdf_file and request:
            return request.build_absolute_uri(obj.pdf_file.url)
        return None


class CourseNoteDetailSerializer(CourseNoteListSerializer):
    """Adds the nested `previewContent` block the in-app PDF reader modal needs."""

    previewContent = serializers.SerializerMethodField()

    class Meta(CourseNoteListSerializer.Meta):
        fields = CourseNoteListSerializer.Meta.fields + ["previewContent"]

    def get_previewContent(self, obj):
        sections = obj.sections.all()
        snippets = obj.code_snippets.all()
        return {
            "summary": obj.summary,
            "tableOfContents": obj.table_of_contents,
            "keyTakeaways": obj.key_takeaways,
            "codeSnippets": NoteCodeSnippetSerializer(snippets, many=True).data,
            "sections": NoteSectionSerializer(sections, many=True).data,
        }
