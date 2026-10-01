
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CertificateDetailView,
    CertificateShareView,
    CertificateVerifyView,
    LessonCompleteView,
    MyLearningViewSet,
    ScheduleViewSet,
    AttendanceCheckInView,
    ChecklistItemView,
    ChecklistItemDetailView,
    ScheduleStatsView,
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

    # Keep router URLs LAST
    path(
        "",
        include(router.urls),
    ),
]

