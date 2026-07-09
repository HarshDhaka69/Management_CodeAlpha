from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notification


@login_required
def notification_list(request):
    """Show all notifications for the current user."""
    notifications = Notification.objects.filter(
        recipient=request.user
    ).select_related('sender', 'task', 'task__project')

    unread_count = notifications.filter(is_read=False).count()

    context = {
        'notifications': notifications,
        'unread_count': unread_count,
    }
    return render(request, 'notifications/notification_list.html', context)


@login_required
def mark_read(request, pk):
    """Mark a single notification as read and redirect to the related task."""
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.mark_read()

    # Redirect to the related task if it exists
    if notification.task:
        return redirect('tasks:task_detail', pk=notification.task.pk)
    return redirect('notifications:notification_list')


@login_required
def mark_all_read(request):
    """Mark all of the current user's notifications as read."""
    if request.method == 'POST':
        Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True)

    return redirect('notifications:notification_list')


@login_required
def unread_count_api(request):
    """JSON endpoint: returns the current unread notification count."""
    count = Notification.objects.filter(
        recipient=request.user,
        is_read=False
    ).count()
    return JsonResponse({'count': count})
