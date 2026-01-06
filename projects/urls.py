from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProjectListAPIView,
    ProjectCreateAPIView,
    ProjectDetailAPIView,
    TaskUpdateAPIView,
    TaskGuidanceAPIView,
    TaskConversationAPIView,
    TaskConversationClearAPIView,
)


urlpatterns = [
    path('projects/', ProjectListAPIView.as_view(), name='project-list'),
    path('projects/new/', ProjectCreateAPIView.as_view(), name='project-create'),
    path('projects/<int:pk>/', ProjectDetailAPIView.as_view(), name='project-detail'),
    path('tasks/<int:pk>/', TaskUpdateAPIView.as_view(), name='task-update'),
    path('tasks/ai-guidance/', TaskGuidanceAPIView.as_view(), name='task-guidance'),
    path('tasks/<int:task_id>/conversation/',
         TaskConversationAPIView.as_view(), name='task-conversation'),
    path('tasks/<int:task_id>/conversation/clear/',
         TaskConversationClearAPIView.as_view(), name='task-conversation-clear'),
]
