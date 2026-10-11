from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication

from .models import Category, Course, Instructor
from .serializers import AdminCourseSerializer


class AdminCourseViewSet(viewsets.ModelViewSet):
    """Admin-only course management; deletion is disabled to preserve enrollments."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminCourseSerializer
    queryset = Course.objects.select_related(
        "category", "instructor"
    ).prefetch_related(
        "lessons", "enrollments__student__student_profile",
        "enrollments__lesson_progress",
    )
    http_method_names = ["get", "post", "patch", "head", "options"]

    @action(detail=False, methods=["get"], url_path="options")
    def options(self, request):
        return Response({
            "categories": list(Category.objects.order_by("name").values("id", "name")),
            "instructors": list(Instructor.objects.order_by("name").values("id", "name")),
            "levels": list(Course.Level.values),
        })
