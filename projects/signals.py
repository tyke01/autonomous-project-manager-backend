from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from django.utils import timezone
from .models import Task


@receiver(pre_save, sender=Task)
def auto_set_task_timestamps(sender, instance, **kwargs):
    """
    Automatically set started_at and completed_at based on status changes.
    """
    # Only run if task already exists in database
    if instance.pk:
        try:
            # Get the old version of the task from database
            old_task = Task.objects.get(pk=instance.pk)
            old_status = old_task.status
            new_status = instance.status
            
            # Auto-set started_at when status changes to 'in_progress'
            if new_status == 'in_progress' and old_status != 'in_progress':
                if not instance.started_at:
                    instance.started_at = timezone.now()
            
            # Auto-set completed_at when status changes to 'completed'
            if new_status == 'completed' and old_status != 'completed':
                if not instance.completed_at:
                    instance.completed_at = timezone.now()
                    
                    # Calculate actual_days if we have started_at
                    if instance.started_at:
                        delta = instance.completed_at - instance.started_at
                        instance.actual_days = max(1, delta.days)
                    else:
                        # Fallback: use estimated_days if no start time
                        instance.actual_days = instance.estimated_days
        
        except Task.DoesNotExist:
            # Task is being created for the first time
            pass
    else:
        # New task being created - set started_at if status is in_progress
        if instance.status == 'in_progress' and not instance.started_at:
            instance.started_at = timezone.now()
            
@receiver(post_save, sender=Task)
def update_project_totals_on_task_save(sender, instance, created, **kwargs):
    """
    Automatically recalculate project totals when tasks are created or updated.
    """
    project = instance.project
    project.calculate_total_estimated_days()


@receiver(post_delete, sender=Task)
def update_project_totals_on_task_delete(sender, instance, **kwargs):
    """
    Automatically recalculate project totals when tasks are deleted.
    """
    project = instance.project
    project.calculate_total_estimated_days()