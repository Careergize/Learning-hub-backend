from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    CertificateDetailView,
    CertificateShareView,
    CertificateVerifyView,
    LessonCompleteView,
    MyLearningViewSet,
)

router = DefaultRouter()
router.register("my-courses", MyLearningViewSet, basename="my-courses")

urlpatterns = [
    path("", include(router.urls)),
    path("lessons/<int:lesson_id>/complete/", LessonCompleteView.as_view(), name="lesson-complete"),
    path("certificates/verify/<str:certificate_id>/", CertificateVerifyView.as_view(), name="certificate-verify"),
    path("certificates/<str:certificate_id>/share/", CertificateShareView.as_view(), name="certificate-share"),
    path("certificates/<str:certificate_id>/", CertificateDetailView.as_view(), name="certificate-detail"),
]
