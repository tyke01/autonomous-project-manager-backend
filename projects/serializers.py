from rest_framework import serializers
from .models import Project, Task


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = (
            'id',
            'title',
            'description',
            'estimated_days',
            'actual_days',
            'status',
            'order',
            'started_at',
            'completed_at',
        )
        read_only_fields = ('id', 'actual_days', 'started_at', 'completed_at')


class ProjectSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)
    remaining_days = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = (
            'id',
            'title',
            'goal',
            'start_date',
            'deadline',
            'status',
            'total_estimated_days',
            'actual_days_spent',
            'remaining_days',
            'tasks'
        )
        read_only_fields = ('id', 'start_date',
                            'total_estimated_days', 'actual_days_spent')

    def get_remaining_days(self, obj):
        """Calculate remaining days from incomplete tasks"""
        # Simple Python sum instead of Django ORM aggregate
        incomplete_tasks = obj.tasks.filter(
            status__in=['pending', 'in_progress', 'blocked']
        )
        return sum(task.estimated_days for task in incomplete_tasks)
