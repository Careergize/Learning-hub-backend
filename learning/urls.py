
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CertificateDetailView,
    CertificateShareView,
    CertificateVerifyView,
    CertificatePDFView,
    LessonCompleteView,
    MyLearningViewSet,
    ScheduleViewSet,
    AttendanceCheckInView,
    ChecklistItemView,
    ChecklistItemDetailView,
    ScheduleStatsView,
    StudentDashboardView,
    AchievementListView,
    CertificateListView,
    TranscriptView,
    
)

router = DefaultRouter()

router.register(
    "my-courses",
    MyLearningViewSet,
    basename="my-courses",
)

router.register(
    "schedule",
    ScheduleViewSet,
    basename="schedule",
)

urlpatterns = [
    path(
    "certificates/",
    CertificateListView.as_view(),
    name="certificate-list",
),
 path(
    "transcript/",
    TranscriptView.as_view(),
    name="student-transcript",
),
    path("achievements/", AchievementListView.as_view(), name="achievement-list"),
    path(
        "lessons/<int:lesson_id>/complete/",
        LessonCompleteView.as_view(),
        name="lesson-complete",
    ),

    path(
        "certificates/verify/<str:certificate_id>/",
        CertificateVerifyView.as_view(),
        name="certificate-verify",
    ),

    path(
        "certificates/<str:certificate_id>/share/",
        CertificateShareView.as_view(),
        name="certificate-share",
    ),

    path(
    "certificates/<str:certificate_id>/download/",
    CertificatePDFView.as_view(),
    name="certificate-pdf",
),
 path(
    "certificates/<str:certificate_id>/verify/",
    CertificateVerifyView.as_view(),
    name="certificate-verify",
),

    path(
        "certificates/<str:certificate_id>/",
        CertificateDetailView.as_view(),
        name="certificate-detail",
    ),

    path(
        "schedule/<int:session_id>/check-in/",
        AttendanceCheckInView.as_view(),
        name="schedule-check-in",
    ),

    path(
        "schedule/<int:session_id>/checklist/",
        ChecklistItemView.as_view(),
        name="schedule-checklist",
    ),

    path(
        "schedule/checklist/<int:item_id>/",
        ChecklistItemDetailView.as_view(),
        name="schedule-checklist-detail",
    ),

    path(
        "schedule/stats/",
        ScheduleStatsView.as_view(),
        name="schedule-stats",
    ),
    path(
    "dashboard/",
    StudentDashboardView.as_view(),
    name="student-dashboard",
),
    

    # Keep router URLs LAST
    path(
        "",
        include(router.urls),
    ),
]

