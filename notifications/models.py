from django.db import models
from django.contrib.auth.models import User
from tasks.models import Task


class Notification(models.Model):
    """
    A notification for a user. Created when:
    - A task is assigned to them (task_assigned)
    - Someone comments on their task (comment_added)

    Pushed in real-time via WebSocket to the user's notification group.
    """
    TYPE_CHOICES = [
        ('task_assigned', 'Task Assigned'),
        ('comment_added', 'Comment Added'),
        ('task_submitted', 'Task Submitted for Review'),
        ('task_approved', 'Task Approved'),
        ('task_rejected', 'Task Sent Back'),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_notifications'
    )
    notif_type = models.CharField(
        max_length=30,
        choices=TYPE_CHOICES,
        default='task_assigned'
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications'
    )
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f'[{self.notif_type}] → {self.recipient.username}: {self.message[:60]}'

    def mark_read(self):
        """Mark this notification as read."""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])
