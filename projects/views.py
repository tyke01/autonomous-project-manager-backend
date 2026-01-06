from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
from datetime import timedelta

from .models import Project, Task, TaskConversation, ChatMessage
from .serializers import ProjectSerializer, TaskSerializer, TaskConversationSerializer
from .agents.planner import generate_task_plan
from .agents.scheduler import recalculate_timeline
from .agents.task_assistant import generate_task_guidance


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
    
    
class TaskGuidanceAPIView(APIView):
    """
    POST /api/tasks/ai-guidance/ - Get AI guidance for a specific task
    """
    def post(self, request):
        task_title = request.data.get('task_title')
        task_description = request.data.get('task_description')
        project_goal = request.data.get('project_goal')
        
        if not all([task_title, task_description, project_goal]):
            return Response(
                {"error": "task_title, task_description, and project_goal are required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            guidance = generate_task_guidance(task_title, task_description, project_goal)
            return Response(
                {"guidance": guidance},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
class TaskConversationAPIView(APIView):
    """
    GET /api/tasks/<task_id>/conversation/ - Get conversation history
    POST /api/tasks/<task_id>/conversation/ - Send a new message
    """
    
    def get(self, request, task_id):
        """Get conversation history for a task"""
        task = get_object_or_404(Task, pk=task_id)
        
        # Get or create conversation
        conversation, created = TaskConversation.objects.get_or_create(task=task)
        
        serializer = TaskConversationSerializer(conversation)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def post(self, request, task_id):
        """Send a new message in the conversation"""
        task = get_object_or_404(Task, pk=task_id)
        user_message = request.data.get('message')
        
        if not user_message:
            return Response(
                {"error": "message is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Get or create conversation
            conversation, created = TaskConversation.objects.get_or_create(task=task)
            
            # Save user message
            ChatMessage.objects.create(
                conversation=conversation,
                role='user',
                content=user_message
            )
            
            # Get conversation history
            history = [
                {"role": msg.role, "content": msg.content}
                for msg in conversation.messages.all()
            ]
            
            # If this is the first message, include task context
            if len(history) == 1:
                result = generate_task_guidance(
                    task.title,
                    task.description,
                    task.project.goal,
                    conversation_history=None  # Initial request
                )
            else:
                # Follow-up question
                result = generate_task_guidance(
                    task.title,
                    task.description,
                    task.project.goal,
                    conversation_history=history
                )
            
            # Save assistant response
            ChatMessage.objects.create(
                conversation=conversation,
                role='assistant',
                content=result['content'],
                metadata=result['metadata']
            )
            
            # Return updated conversation
            serializer = TaskConversationSerializer(conversation)
            return Response(serializer.data, status=status.HTTP_200_OK)
        
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TaskConversationClearAPIView(APIView):
    """
    DELETE /api/tasks/<task_id>/conversation/clear/ - Clear conversation history
    """
    def delete(self, request, task_id):
        task = get_object_or_404(Task, pk=task_id)
        
        try:
            conversation = TaskConversation.objects.get(task=task)
            conversation.delete()
            return Response(
                {"message": "Conversation cleared"},
                status=status.HTTP_204_NO_CONTENT
            )
        except TaskConversation.DoesNotExist:
            return Response(
                {"message": "No conversation to clear"},
                status=status.HTTP_204_NO_CONTENT
            )