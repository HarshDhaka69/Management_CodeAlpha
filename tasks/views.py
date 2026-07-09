from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from projects.models import Project, ProjectMember
from .models import Task, Comment
from .forms import TaskForm, CommentForm


def _check_project_member(request, project):
    """Utility: verify user is a project member. Returns True/False."""
    return project.is_member(request.user)


@login_required
def task_create(request, project_pk):
    """Create a new task inside a project."""
    project = get_object_or_404(Project, pk=project_pk)

    if not _check_project_member(request, project):
        messages.error(request, 'You must be a project member to create tasks.')
        return redirect('projects:project_list')

    is_owner_or_admin = project.is_owner_or_admin(request.user)
    initial_status = request.GET.get('status', 'todo')

    if request.method == 'POST':
        form = TaskForm(project, request.POST, is_owner_or_admin=is_owner_or_admin)
        if form.is_valid():
            task = form.save(commit=False)
            task.project = project
            task.created_by = request.user
            task.save()

            # Send notification if task is assigned to someone else
            if task.assigned_to and task.assigned_to != request.user:
                _notify(
                    recipient=task.assigned_to,
                    sender=request.user,
                    notif_type='task_assigned',
                    task=task,
                    message=f'{request.user.username} assigned you the task: "{task.title}"',
                )

            messages.success(request, f'Task "{task.title}" created!')
            return redirect('projects:project_detail', pk=project.pk)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = TaskForm(project, initial={'status': initial_status}, is_owner_or_admin=is_owner_or_admin)

    return render(request, 'tasks/task_form.html', {
        'form': form,
        'project': project,
        'action': 'Create',
        'title': 'New Task',
    })


@login_required
def task_detail(request, pk):
    """View a task's full details + comment thread."""
    task = get_object_or_404(Task, pk=pk)
    project = task.project

    if not _check_project_member(request, project):
        messages.error(request, 'Access denied.')
        return redirect('projects:project_list')

    comments = task.comments.select_related('author', 'author__profile').all()
    comment_form = CommentForm()

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()

            # Notify task creator when someone else comments
            if task.created_by != request.user:
                _notify(
                    recipient=task.created_by,
                    sender=comment.author,
                    notif_type='comment_added',
                    task=task,
                    message=f'{comment.author.username} commented on your task: "{task.title}"',
                )

            messages.success(request, 'Comment posted!')
            return redirect('tasks:task_detail', pk=task.pk)
        else:
            messages.error(request, 'Comment cannot be empty.')

    context = {
        'task': task,
        'project': project,
        'comments': comments,
        'comment_form': comment_form,
        'is_owner_or_admin': project.is_owner_or_admin(request.user),
    }
    return render(request, 'tasks/task_detail.html', context)


@login_required
def task_edit(request, pk):
    """Edit an existing task."""
    task = get_object_or_404(Task, pk=pk)
    project = task.project

    if not _check_project_member(request, project):
        messages.error(request, 'Access denied.')
        return redirect('projects:project_list')

    old_assigned_to = task.assigned_to
    is_owner_or_admin = project.is_owner_or_admin(request.user)

    if request.method == 'POST':
        form = TaskForm(project, request.POST, instance=task, is_owner_or_admin=is_owner_or_admin)
        if form.is_valid():
            task = form.save()

            # If assignment changed, send notification
            new_assigned = task.assigned_to
            if new_assigned and new_assigned != old_assigned_to and new_assigned != request.user:
                _notify(
                    recipient=new_assigned,
                    sender=request.user,
                    notif_type='task_assigned',
                    task=task,
                    message=f'{request.user.username} assigned you the task: "{task.title}"',
                )

            messages.success(request, 'Task updated!')
            return redirect('tasks:task_detail', pk=task.pk)
        else:
            messages.error(request, 'Please fix the errors.')
    else:
        form = TaskForm(project, instance=task, is_owner_or_admin=is_owner_or_admin)

    return render(request, 'tasks/task_form.html', {
        'form': form,
        'project': project,
        'task': task,
        'action': 'Edit',
        'title': f'Edit — {task.title}',
    })


@login_required
def task_delete(request, pk):
    """Delete a task (project owner/admin, or task creator)."""
    task = get_object_or_404(Task, pk=pk)
    project = task.project

    can_delete = (
        task.created_by == request.user or
        project.is_owner_or_admin(request.user)
    )

    if not can_delete:
        messages.error(request, 'You do not have permission to delete this task.')
        return redirect('tasks:task_detail', pk=pk)

    if request.method == 'POST':
        project_pk = project.pk
        task.delete()
        messages.success(request, 'Task deleted.')
        return redirect('projects:project_detail', pk=project_pk)

    return render(request, 'tasks/task_confirm_delete.html', {
        'task': task,
        'project': project,
    })


@login_required
def comment_delete(request, pk):
    """Delete a comment (author only)."""
    comment = get_object_or_404(Comment, pk=pk)

    if comment.author != request.user:
        messages.error(request, 'You can only delete your own comments.')
        return redirect('tasks:task_detail', pk=comment.task.pk)

    if request.method == 'POST':
        task_pk = comment.task.pk
        comment.delete()
        messages.success(request, 'Comment deleted.')
        return redirect('tasks:task_detail', pk=task_pk)

    return redirect('tasks:task_detail', pk=comment.task.pk)


@login_required
def task_status_update(request, pk):
    """
    AJAX endpoint for MANUAL status changes (owner/admin only).

    Regular members move tasks through the workflow via the dedicated
    task_accept / task_submit / task_approve / task_reject actions below,
    which enforce who is allowed to make each transition. This endpoint
    is the "override" tool for owners/admins who need to correct a status
    directly (e.g. reopen a Done task, or fix a mistake).
    """
    if request.method == 'POST':
        task = get_object_or_404(Task, pk=pk)
        project = task.project

        if not project.is_owner_or_admin(request.user):
            return JsonResponse({'error': 'Only the project owner or an admin can set a status directly.'}, status=403)

        new_status = request.POST.get('status')
        valid_statuses = [s[0] for s in Task.STATUS_CHOICES]

        if new_status in valid_statuses:
            task.status = new_status
            task.save(update_fields=['status', 'updated_at'])
            return JsonResponse({'success': True, 'status': task.status, 'status_label': task.get_status_display()})

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def task_accept(request, pk):
    """
    The assignee accepts a To Do task, which automatically moves it
    to In Progress. Only the assigned member can do this.
    """
    task = get_object_or_404(Task, pk=pk)

    if request.method == 'POST' and task.can_accept(request.user):
        task.status = 'inprogress'
        task.save(update_fields=['status', 'updated_at'])

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': task.status, 'status_label': task.get_status_display()})

        messages.success(request, f'You accepted "{task.title}" — it\u2019s now In Progress.')
        return redirect('tasks:task_detail', pk=task.pk)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'You cannot accept this task.'}, status=403)
    messages.error(request, 'You cannot accept this task.')
    return redirect('tasks:task_detail', pk=pk)


@login_required
def task_submit(request, pk):
    """
    The assignee submits an In Progress task for review.
    Notifies the task creator (the reviewer) that it's ready to check.
    """
    task = get_object_or_404(Task, pk=pk)

    if request.method == 'POST' and task.can_submit(request.user):
        task.status = 'review'
        task.save(update_fields=['status', 'updated_at'])

        if task.created_by != request.user:
            _notify(
                recipient=task.created_by,
                sender=request.user,
                notif_type='task_submitted',
                task=task,
                message=f'{request.user.username} submitted "{task.title}" for review',
            )

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': task.status, 'status_label': task.get_status_display()})

        messages.success(request, f'"{task.title}" was submitted for review.')
        return redirect('tasks:task_detail', pk=task.pk)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'You cannot submit this task.'}, status=403)
    messages.error(request, 'You cannot submit this task.')
    return redirect('tasks:task_detail', pk=pk)


@login_required
def task_approve(request, pk):
    """Owner/admin approves a submitted task, marking it Done."""
    task = get_object_or_404(Task, pk=pk)

    if request.method == 'POST' and task.can_review(request.user):
        task.status = 'done'
        task.save(update_fields=['status', 'updated_at'])

        if task.assigned_to and task.assigned_to != request.user:
            _notify(
                recipient=task.assigned_to,
                sender=request.user,
                notif_type='task_approved',
                task=task,
                message=f'{request.user.username} approved "{task.title}" \u2705',
            )

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': task.status, 'status_label': task.get_status_display()})

        messages.success(request, f'"{task.title}" approved and marked Done!')
        return redirect('tasks:task_detail', pk=task.pk)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Only the project owner or an admin can approve this task.'}, status=403)
    messages.error(request, 'Only the project owner or an admin can approve this task.')
    return redirect('tasks:task_detail', pk=pk)


@login_required
def task_reject(request, pk):
    """
    Owner/admin sends a submitted task back to In Progress.
    An optional 'feedback' message is posted as a comment so the
    assignee knows what to change.
    """
    task = get_object_or_404(Task, pk=pk)

    if request.method == 'POST' and task.can_review(request.user):
        task.status = 'inprogress'
        task.save(update_fields=['status', 'updated_at'])

        feedback = request.POST.get('feedback', '').strip()
        if feedback:
            Comment.objects.create(task=task, author=request.user, content=feedback)

        if task.assigned_to and task.assigned_to != request.user:
            _notify(
                recipient=task.assigned_to,
                sender=request.user,
                notif_type='task_rejected',
                task=task,
                message=f'{request.user.username} requested changes on "{task.title}"',
            )

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'status': task.status, 'status_label': task.get_status_display()})

        messages.info(request, f'"{task.title}" was sent back to In Progress.')
        return redirect('tasks:task_detail', pk=task.pk)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Only the project owner or an admin can request changes.'}, status=403)
    messages.error(request, 'Only the project owner or an admin can request changes.')
    return redirect('tasks:task_detail', pk=pk)


# ─── Notification Helper ────────────────────────────────────────────────────

def _notify(recipient, sender, notif_type, task, message):
    """Create a Notification and push it to the recipient's browser via WebSocket."""
    from notifications.models import Notification
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    notif = Notification.objects.create(
        recipient=recipient,
        sender=sender,
        notif_type=notif_type,
        task=task,
        message=message,
    )

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{recipient.pk}',
        {
            'type': 'send_notification',
            'notification_id': notif.pk,
            'message': notif.message,
            'notif_type': notif.notif_type,
        }
    )
