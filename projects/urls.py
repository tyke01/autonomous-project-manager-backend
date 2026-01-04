from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectListAPIView,
    ProjectCreateAPIView,
    ProjectDetailAPIView,
)


urlpatterns = [
    path('projects/', ProjectListAPIView.as_view(), name='project-list'),
    path('projects/new/', ProjectCreateAPIView.as_view(), name='project-create'),
    path('projects/<int:pk>/', ProjectDetailAPIView.as_view(), name='project-detail'),
]