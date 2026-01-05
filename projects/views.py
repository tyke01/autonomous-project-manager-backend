from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from datetime import timedelta

from .models import Project, Task
from .serializers import ProjectSerializer, TaskSerializer
from .agents.planner import generate_task_plan
from .agents.scheduler import recalculate_timeline


class ProjectListAPIView(APIView):
    """
    GET /api/projects/ - List all projects
    """
    def get(self, request):
        projects = Project.objects.all().order_by('-start_date')  # Newest first
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProjectCreateAPIView(APIView):
    """
    POST /api/projects/new - Create a new project with AI-generated tasks
    """
    def post(self, request):
        serializer = ProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            with transaction.atomic():  # ← Start transaction
                # Everything inside this block is grouped
                
                # Step 1: Save project
                project = serializer.save(status='planning')
                
                # Step 2: Generate tasks
                task_plan = generate_task_plan(project.goal)
                
                # Step 3: Create tasks
                for index, task_data in enumerate(task_plan):
                    Task.objects.create(
                        project=project,
                        title=task_data["title"],
                        description=task_data["description"],
                        estimated_days=task_data["estimated_days"],
                        order=index
                        )
                project.calculate_total_estimated_days()
                
                if not project.deadline:
                    buffer_days = int(project.total_estimated_days * 1.1)  # 10% buffer
                    project.deadline = project.start_date + timedelta(days=buffer_days)
                
                project.status = 'active'
                project.save()
                
                # If we reach here, COMMIT all changes
        
        except Exception as e:
            # If ANY error occurs, ROLLBACK everything
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        return Response(
            ProjectSerializer(project).data,
            status=status.HTTP_201_CREATED
        )


class ProjectDetailAPIView(APIView):
    """
    GET /api/projects/<id>/ - Retrieve a single project
    DELETE /api/projects/<id>/ - Delete a project
    """
    
    def get(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        serializer = ProjectSerializer(project)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def delete(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        project_title = project.title
        project.delete()  # Tasks are deleted automatically (CASCADE)
        
        return Response(
            {"message": f"Project '{project_title}' deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )
        


class TaskUpdateAPIView(APIView):
    """
    PATCH /api/tasks/<id>/ - Update task status
    """
    def patch(self, request, pk):
        task = get_object_or_404(Task, pk=pk)
        old_status = task.status
        new_status = request.data.get('status')
        
        if not new_status:
            return Response(
                {"error": "Status is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        with transaction.atomic():
            # Update task status
            task.status = new_status
            
            # Timestamps are now set automatically by signals! 🎉
            task.save()
            
            # Update project's actual days spent if task was completed
            if new_status == 'completed' and old_status != 'completed':
                if task.actual_days:
                    project = task.project
                    project.actual_days_spent += task.actual_days
                    project.save()
            
            # Recalculate timeline if task was completed
            recalculation_result = None
            if new_status == 'completed':
                recalculation_result = recalculate_timeline(task.project)
        
        response_data = {
            'task': TaskSerializer(task).data,
            'message': f"Task '{task.title}' marked as {new_status}",
        }
        
        if recalculation_result:
            response_data['timeline_update'] = recalculation_result
        
        return Response(response_data, status=status.HTTP_200_OK)