from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from rest_framework import permissions, serializers, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response

from courses.models import Course, Instructor
from .models import Achievement, Enrollment, ScheduleSession

User = get_user_model()


class AdminScheduleSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)
    instructor_name = serializers.CharField(source="instructor.name", read_only=True)
    enrolled_students = serializers.SerializerMethodField()

    class Meta:
        model = ScheduleSession
        fields = [
            "id", "course", "course_title", "topic", "date", "start_time",
            "end_time", "instructor", "instructor_name", "platform", "meet_url",
            "enrolled_students",
        ]

    def get_enrolled_students(self, obj):
        annotated_count = getattr(obj, "enrolled_students", None)
        if annotated_count is not None:
            return annotated_count
        return Enrollment.objects.filter(
            course=obj.course,
            student__is_staff=False,
            student__is_superuser=False,
        ).count()

    def validate(self, attrs):
        start_time = attrs.get("start_time", getattr(self.instance, "start_time", None))
        end_time = attrs.get("end_time", getattr(self.instance, "end_time", None))
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return attrs


class AdminScheduleViewSet(viewsets.ModelViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAdminUser]
    serializer_class = AdminScheduleSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        return ScheduleSession.objects.select_related("course", "instructor").annotate(
            enrolled_students=Count(
                "course__enrollments__student",
                filter=Q(
                    course__enrollments__student__is_staff=False,
                    course__enrollments__student__is_superuser=False,
                ),
                distinct=True,
            )
        )

    @action(detail=False, methods=["get"], url_path="options")
    def options(self, request):
        courses = Course.objects.order_by("title").values("id", "title")
        instructors = Instructor.objects.order_by("name").values("id", "name")
        return Response({"courses": list(courses), "instructors": list(instructors)})


class AdminAchievementListView(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAdminUser]

    def list(self, request, *args, **kwargs):
        achievements = Achievement.objects.select_related("student").filter(
            student__is_staff=False, student__is_superuser=False,
            student__student_profile__isnull=False,
        ).order_by("student__username", "-earned_at")
        search = request.query_params.get("search", "").strip()
        if search:
            achievements = achievements.filter(
                Q(student__username__icontains=search)
                | Q(student__email__icontains=search)
                | Q(title__icontains=search)
            )
        unlocked = request.query_params.get("unlocked")
        if unlocked in ("true", "false"):
            achievements = achievements.filter(unlocked=(unlocked == "true"))
        return Response([{
            "id": item.id,
            "student_id": item.student_id,
            "student_name": item.student.get_full_name() or item.student.username,
            "student_email": item.student.email,
            "title": item.title,
            "description": item.description,
            "icon": item.icon,
            "category": item.category,
            "tier": item.tier,
            "xp": item.xp,
            "unlocked": item.unlocked,
            "unlocked_date": item.unlocked_date,
            "progress": item.progress,
            "progress_label": item.progress_label,
            "requirement": item.requirement,
            "earned_at": item.earned_at,
        } for item in achievements])
