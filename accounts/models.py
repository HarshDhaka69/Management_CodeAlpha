from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Extends the built-in Django User with avatar and bio.
    Created automatically via signal when a User registers.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        null=True,
        blank=True,
        help_text='Profile picture (optional)'
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        help_text='Short bio about yourself'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_avatar_url(self):
        """Returns avatar URL or a default placeholder."""
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return None
