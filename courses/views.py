from django.shortcuts import render

# Create your views here.
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, permissions, viewsets

from .models import Category, Course
from .serializers import CategorySerializer, CourseDetailSerializer, CourseListSerializer


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    """Public course catalog — powers 'Explore Catalog'. Read-only; enrolling
    happens through learning.MyLearningViewSet so progress stays in one place.
    """

    queryset = Course.objects.filter(is_published=True).select_related(
        "category", "instructor"
    ).prefetch_related("skills", "lessons")
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["category__slug", "level"]
    search_fields = ["title", "short_description", "instructor__name", "skills__name"]
    ordering_fields = ["created_at", "title", "duration_weeks"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return CourseDetailSerializer
        return CourseListSerializer


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]
