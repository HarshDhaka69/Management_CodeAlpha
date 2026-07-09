from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from projects.models import Project


class Task(models.Model):
    """
    A task within a project. Can be assigned to a member,
    has status (kanban column), priority, and due date.
    """
    STATUS_CHOICES = [
        ('todo', 'To Do'),
        ('inprogress', 'In Progress'),
        ('review', 'In Review'),
        ('done', 'Done'),
    ]
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ]

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_tasks'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='todo'
    )
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='medium'
    )
    due_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Task'
        verbose_name_plural = 'Tasks'

    def __str__(self):
        return self.title

    def is_overdue(self):
        """Returns True if the task has a due date that has passed and isn't done."""
        if self.due_date and self.status != 'done':
            return self.due_date < timezone.now().date()
        return False

    def get_priority_class(self):
        """Bootstrap badge class for priority."""
        classes = {
            'low': 'badge-priority-low',
            'medium': 'badge-priority-medium',
            'high': 'badge-priority-high',
        }
        return classes.get(self.priority, 'bg-secondary')

    def get_comment_count(self):
        return self.comments.count()

    # ── Workflow permission helpers ─────────────────────────────────────
    # Kept on the model so views and templates always agree on the rules.

    def can_accept(self, user):
        """Assignee can accept a To Do task, moving it to In Progress."""
        return self.status == 'todo' and self.assigned_to_id == user.pk

    def can_submit(self, user):
        """Assignee can submit an In Progress task for review."""
        return self.status == 'inprogress' and self.assigned_to_id == user.pk

    def can_review(self, user):
        """Only the project owner/admin can approve or reject a submitted task."""
        return self.status == 'review' and self.project.is_owner_or_admin(user)


class Comment(models.Model):
    """
    A comment on a task. Author can delete their own comment.
    """
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Comment'
        verbose_name_plural = 'Comments'

    def __str__(self):
        return f'Comment by {self.author.username} on {self.task.title}'
