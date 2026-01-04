import logging
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger('agents.scheduler')


def recalculate_timeline(project):
    """
    Recalculate project timeline after task completion.
    Returns a dict with updated estimates and reasoning.
    """
    logger.info(f"📊 Recalculating timeline for project #{project.id}")
    
    # Get all completed tasks
    completed_tasks = project.tasks.filter(status='completed')
    
    # Calculate performance ratio (actual vs estimated)
    total_estimated = 0
    total_actual = 0
    
    for task in completed_tasks:
        if task.actual_days:
            total_estimated += task.estimated_days
            total_actual += task.actual_days
    
    if total_estimated > 0:
        performance_ratio = total_actual / total_estimated
        logger.info(f"Performance ratio: {performance_ratio:.2f} (1.0 = on track)")
    else:
        performance_ratio = 1.0  # Default: assume on track
    
    # Adjust remaining tasks based on performance
    remaining_tasks = project.tasks.filter(status__in=['pending', 'in_progress', 'blocked'])
    
    adjustments = []
    new_total_days = 0
    
    for task in remaining_tasks:
        old_estimate = task.estimated_days
        # Apply performance ratio to future estimates
        new_estimate = int(old_estimate * performance_ratio)
        
        # Don't go below 1 day
        new_estimate = max(1, new_estimate)
        
        if new_estimate != old_estimate:
            task.estimated_days = new_estimate
            task.save()
            
            adjustments.append({
                'task_id': task.id,
                'task_title': task.title,
                'old_estimate': old_estimate,
                'new_estimate': new_estimate,
            })
            
            logger.debug(f"Task '{task.title}': {old_estimate}d → {new_estimate}d")
        
        new_total_days += new_estimate
    
    # Calculate new deadline
    new_deadline, remaining_days = project.calculate_new_deadline()
    old_deadline = project.deadline
    
    # Update project
    project.calculate_total_estimated_days()
    project.deadline = new_deadline
    project.save()
    
    result = {
        'performance_ratio': round(performance_ratio, 2),
        'adjustments': adjustments,
        'old_deadline': old_deadline.isoformat() if old_deadline else None,
        'new_deadline': new_deadline.isoformat(),
        'remaining_days': remaining_days,
        'reasoning': _generate_reasoning(performance_ratio, len(adjustments)),
    }
    
    logger.info(f"✅ Timeline recalculated: {len(adjustments)} tasks adjusted")
    return result


def _generate_reasoning(performance_ratio, adjustment_count):
    """Generate human-readable explanation of changes"""
    if performance_ratio < 0.9:
        return (
            f"You're ahead of schedule! Tasks are being completed {int((1 - performance_ratio) * 100)}% "
            f"faster than estimated. I've adjusted {adjustment_count} remaining tasks to reflect this pace."
        )
    elif performance_ratio > 1.2:
        return (
            f"Tasks are taking longer than estimated (about {int((performance_ratio - 1) * 100)}% slower). "
            f"I've updated {adjustment_count} remaining tasks and extended the deadline accordingly."
        )
    else:
        return (
            f"You're on track! The project is progressing as planned. "
            f"Made {adjustment_count} minor adjustments to remaining tasks."
        )