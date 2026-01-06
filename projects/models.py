from django.db import models
from django.utils import timezone

class Project(models.Model):
    STATUS_CHOICES = [
        ('planning', 'Planning'),
        ('active', 'Active'),
        ('completed', 'Completed'),
    ]
    
    title = models.CharField(max_length=255)
    goal = models.TextField()
    start_date = models.DateField(auto_now_add=True)
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planning'
    )
    
    total_estimated_days = models.IntegerField(default=0) 
    actual_days_spent = models.IntegerField(default=0)
    

    def __str__(self):
        return self.title
    
    def calculate_total_estimated_days(self):
        """Calculate total estimated days from all tasks"""
        total = self.tasks.aggregate(
            models.Sum('estimated_days')
        )['estimated_days__sum'] or 0
        self.total_estimated_days = total
        self.save()
        return total
    
    def calculate_new_deadline(self):
        """Calculate deadline based on remaining tasks"""
        remaining_days = self.tasks.filter(
            status__in=['pending', 'in_progress', 'blocked']
        ).aggregate(
            models.Sum('estimated_days')
        )['estimated_days__sum'] or 0
        
        # Add buffer (10% extra time for safety)
        remaining_days = int(remaining_days * 1.1)
        
        new_deadline = timezone.now().date() + timezone.timedelta(days=remaining_days)
        return new_deadline, remaining_days
    

class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('blocked', 'Blocked'),
        ('completed', 'Completed'),
    ]
    
    project = models.ForeignKey(
        Project,
        related_name='tasks',
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    estimated_days = models.IntegerField(default=1)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    order = models.IntegerField(default=0)
    
    # NEW FIELDS
    actual_days = models.IntegerField(null=True, blank=True)  # Actual time taken
    completed_at = models.DateTimeField(null=True, blank=True)  # When completed
    started_at = models.DateTimeField(null=True, blank=True)    # When started
    
    def __str__(self):
        return f"{self.project.title} - {self.title}"
    
    class Meta:
        ordering = ['order']  # Always return tasks in order
        

class TaskConversation(models.Model):
    """
    Stores AI assistant conversations for a specific task.
    """
    task = models.OneToOneField(
        'Task',
        on_delete=models.CASCADE,
        related_name='conversation'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Conversation for {self.task.title}"


class ChatMessage(models.Model):
    """
    Individual message in a conversation.
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    
    conversation = models.ForeignKey(
        TaskConversation,
        on_delete=models.CASCADE,
        related_name='messages'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Optional: Store metadata (model used, tokens, etc.)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."