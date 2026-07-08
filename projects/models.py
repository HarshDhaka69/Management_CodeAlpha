from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    """
    A project that groups tasks together.
    Has one owner and can have many members via ProjectMember.
    """
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='owned_projects'
    )
    members = models.ManyToManyField(
        User,
        through='ProjectMember',
        related_name='projects',
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'

    def __str__(self):
        return self.name

    def get_member_count(self):
        return self.projectmember_set.count()

    def get_task_count(self):
        return self.tasks.count()

    def is_member(self, user):
        """Check if a user is a member of this project."""
        return self.projectmember_set.filter(user=user).exists()

    def is_owner_or_admin(self, user):
        """Check if user is owner or admin of this project."""
        return self.projectmember_set.filter(
            user=user,
            role__in=['owner', 'admin']
        ).exists()


class ProjectMember(models.Model):
    """
    Through model connecting Users to Projects with a role.
    """
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('member', 'Member'),
    ]

    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='member')
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('project', 'user')
        ordering = ['joined_at']
        verbose_name = 'Project Member'
        verbose_name_plural = 'Project Members'

    def __str__(self):
        return f'{self.user.username} — {self.project.name} ({self.role})'
