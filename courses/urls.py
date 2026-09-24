from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import CategoryViewSet, CourseViewSet

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("", CourseViewSet, basename="course")

urlpatterns = [path("", include(router.urls))]
