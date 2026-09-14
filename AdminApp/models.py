from django.db import models
from userApp.models import (
    User,
    Instructor,
    Course,
    Module,
    Lesson,
    FAQ,
    Payment,
    Enrollment,
    LessonProgress,
)

# Re-exporting models for seamless access across AdminApp
__all__ = [
    'User',
    'Instructor',
    'Course',
    'Module',
    'Lesson',
    'FAQ',
    'Payment',
    'Enrollment',
    'LessonProgress',
    'AdminActivityLog',
]


class AdminActivityLog(models.Model):
    """
    Optional audit log recording administrative actions.
    """
    admin_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='admin_activity_logs'
    )
    action = models.CharField(max_length=255)
    target_model = models.CharField(max_length=100, blank=True, default='')
    target_id = models.CharField(max_length=100, blank=True, default='')
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Admin Activity Log'
        verbose_name_plural = 'Admin Activity Logs'

    def __str__(self):
        user_name = self.admin_user.email if self.admin_user else 'System'
        return f"[{self.created_at.strftime('%Y-%m-%d %H:%M')}] {user_name} - {self.action}"
