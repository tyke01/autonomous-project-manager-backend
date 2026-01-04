from rest_framework import serializers
from .models import Project, Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = 'id', 'title', 'description', 'estimated_days', 'status', 'order'


class ProjectSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)

    class Meta:
        model = Project
        fields = 'title', 'goal', 'start_date', 'deadline', 'status', 'tasks'
