from django.shortcuts import render

# Create your views here.
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from courses.models import Lesson

from .models import Certificate, Enrollment, LessonProgress
from .serializers import CertificateSerializer, EnrolledCourseSerializer, EnrollmentCreateSerializer


class MyLearningViewSet(viewsets.ModelViewSet):
    """Backs the entire 'My Learning' page: filtered/sorted enrolled-course
    list, quick-stats cards, resume, review, and enrollment creation."""

    serializer_class = EnrolledCourseSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        qs = Enrollment.objects.filter(student=self.request.user).select_related(
            "course", "course__category", "course__instructor", "certificate"
        ).prefetch_related("course__skills", "lesson_progress")

        params = self.request.query_params

        status_filter = params.get("status")  # "in_progress" | "completed"
        if status_filter in (Enrollment.Status.IN_PROGRESS, Enrollment.Status.COMPLETED):
            qs = qs.filter(status=status_filter)

        category = params.get("category")
        if category and category != "All Categories":
            qs = qs.filter(course__category__name=category)

        search = params.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(course__title__icontains=search)
                | Q(course__category__name__icontains=search)
                | Q(course__instructor__name__icontains=search)
                | Q(course__skills__name__icontains=search)
            ).distinct()

        sort_by = params.get("sort", "recent")
        if sort_by == "alphabetical":
            qs = qs.order_by("course__title")
        elif sort_by != "progress":  # "recent" (default): in-progress first, then most recently touched
            qs = qs.order_by("status", "-last_accessed")
        # "progress" sort needs the computed property, applied after fetch:
        if sort_by == "progress":
            qs = sorted(qs, key=lambda e: e.progress_percent, reverse=True)

        return qs

    def create(self, request, *args, **kwargs):
        """POST {course: <id>} — enroll the current student in a course."""
        serializer = EnrollmentCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        enrollment = serializer.save()
        out = self.get_serializer(enrollment)
        return Response(out.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        """'Resume Learning' button — bumps last_accessed, returns the next lesson."""
        enrollment = self.get_object()
        enrollment.save(update_fields=["last_accessed"])  # auto_now bumps the timestamp
        nxt = enrollment.next_lesson
        return Response({
            "enrollmentId": enrollment.id,
            "nextLesson": {"id": nxt.id, "title": nxt.title} if nxt else None,
        })

    @action(detail=True, methods=["get"])
    def review(self, request, pk=None):
        """'Review' button on a completed course — archive material."""
        enrollment = self.get_object()
        lessons = enrollment.course.lessons.order_by("order").values(
            "id", "title", "order", "resource_url", "video_url"
        )
        return Response({
            "courseTitle": enrollment.course.title,
            "totalLessons": enrollment.total_lessons,
            "lessons": list(lessons),
        })

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Top quick-stats cards: enrolled / in-progress / completed / certificates."""
        qs = Enrollment.objects.filter(student=request.user)
        return Response({
            "totalEnrolled": qs.count(),
            "inProgressCount": qs.filter(status=Enrollment.Status.IN_PROGRESS).count(),
            "completedCount": qs.filter(status=Enrollment.Status.COMPLETED).count(),
            "certificatesEarned": Certificate.objects.filter(enrollment__student=request.user).count(),
        })


class LessonCompleteView(APIView):
    """POST — mark a lesson complete for the current student. Recomputes
    enrollment progress/status and auto-issues a certificate at 100%."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, lesson_id):
        lesson = get_object_or_404(Lesson, id=lesson_id)
        enrollment = get_object_or_404(Enrollment, student=request.user, course=lesson.course)
        progress, _ = LessonProgress.objects.get_or_create(enrollment=enrollment, lesson=lesson)
        progress.mark_complete()
        return Response(EnrolledCourseSerializer(enrollment).data)


class CertificateDetailView(APIView):
    """Powers the certificate preview modal."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, certificate_id):
        cert = get_object_or_404(Certificate, certificate_id=certificate_id, enrollment__student=request.user)
        data = CertificateSerializer(cert).data
        data.update({
            "studentName": request.user.get_full_name() or request.user.username,
            "courseTitle": cert.enrollment.course.title,
        })
        return Response(data)


class CertificateShareView(APIView):
    """'Share Credential' button — bumps a share counter, returns the link to copy."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, certificate_id):
        cert = get_object_or_404(Certificate, certificate_id=certificate_id, enrollment__student=request.user)
        cert.share_count += 1
        cert.save(update_fields=["share_count"])
        return Response({"verificationUrl": cert.verification_url, "shareCount": cert.share_count})


class CertificateVerifyView(APIView):
    """Public, unauthenticated endpoint for anyone who opens a shared
    verification link to confirm a certificate is genuine."""

    permission_classes = [permissions.AllowAny]

    def get(self, request, certificate_id):
        cert = get_object_or_404(Certificate, certificate_id=certificate_id)
        return Response({
            "valid": True,
            "certificateId": cert.certificate_id,
            "studentName": cert.enrollment.student.get_full_name() or cert.enrollment.student.username,
            "courseTitle": cert.enrollment.course.title,
            "issuedDate": cert.issued_date,
        })
