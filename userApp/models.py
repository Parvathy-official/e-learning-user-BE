
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone


# =========================================================
#  1. Custom User Manager & Model
# =========================================================

class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name='Admin', password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email=email, name=name, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True, db_index=True)
    name = models.CharField(max_length=255)
    avatar = models.URLField(blank=True, null=True)
    bio = models.TextField(blank=True, default='')
    is_active = models.BooleanField(default=True)  # type: ignore
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.name} ({self.email})"


# =========================================================
# =========================================================
#  2. Instructor Model
# =========================================================

class Instructor(models.Model):
    name = models.CharField(max_length=255)
    title = models.CharField(max_length=255, blank=True, default='')
    bio = models.TextField(blank=True, default='')
    avatar = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    def __str__(self):
        return self.name


# =========================================================
#  3. Course Model
# =========================================================

class Course(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, db_index=True)
    short_description = models.TextField(blank=True, default='')
    description = models.TextField(blank=True, default='')
    thumbnail = models.URLField(blank=True, null=True)
    instructor = models.ForeignKey(Instructor, on_delete=models.SET_NULL, null=True, blank=True, related_name='courses')
    category = models.CharField(max_length=100, default='Performance Marketing')
    
    # Pricing: price is selling price (discounted), original_price is strike-through
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Selling price in INR")
    original_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Original price in INR")
    
    duration = models.CharField(max_length=50, blank=True, default='18h 45m')
    level = models.CharField(max_length=50, default='Intermediate to Advanced')
    language = models.CharField(max_length=50, default='English')
    
    is_published = models.BooleanField(default=True, db_index=True)
    is_bestseller = models.BooleanField(default=False)
    is_featured = models.BooleanField(default=False)
    
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=4.95)
    total_ratings = models.IntegerField(default=1240)
    total_students = models.IntegerField(default=5890)
    
    learning_outcomes = models.JSONField(default=list, blank=True, help_text="List of learning outcomes")
    requirements = models.JSONField(default=list, blank=True, help_text="List of requirements")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def price_in_paise(self):
        return int(float(self.price) * 100)


# =========================================================
#  4. Module Model
# =========================================================

class Module(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} — {self.title}"


# =========================================================
#  5. Lesson Model
# =========================================================

class Lesson(models.Model):
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=255)
    duration = models.CharField(max_length=50, default='15:00')
    duration_seconds = models.PositiveIntegerField(default=900)
    video_url = models.URLField(blank=True, null=True, help_text="Video source file URL or key")
    is_preview = models.BooleanField(default=False, help_text="Free preview lesson available to unauthenticated users")
    order = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.module.title} — Lesson: {self.title}"


# =========================================================
#  6. FAQ Model
# =========================================================

class FAQ(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=1)

    objects = models.Manager()

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} — FAQ: {self.question[:40]}"


# =========================================================
#  7. Payment Model
# =========================================================

class Payment(models.Model):
    STATUS_CHOICES = [
        ('created', 'Order Created'),
        ('paid', 'Payment Successful'),
        ('failed', 'Payment Failed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='payments')
    razorpay_order_id = models.CharField(max_length=255, unique=True, db_index=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    amount = models.PositiveIntegerField(help_text="Amount in paise")
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment {self.razorpay_order_id} — {self.user.email} — {self.status}"


# =========================================================
#  8. Enrollment Model
# =========================================================

class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enrollments')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='enrollments')
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='enrollments')
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    progress_percentage = models.PositiveIntegerField(default=0)
    last_watched_lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True, blank=True)
    last_watched_position = models.PositiveIntegerField(default=0, help_text="Last position in seconds")

    objects = models.Manager()

    class Meta:
        unique_together = ('user', 'course')
        ordering = ['-enrolled_at']

    def __str__(self):
        return f"Enrollment: {self.user.email} -> {self.course.title}"


# =========================================================
#  9. Lesson Progress Model
# =========================================================

class LessonProgress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lesson_progresses')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='progresses')
    watched_seconds = models.PositiveIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)
    progress_percentage = models.PositiveIntegerField(default=0)
    completed = models.BooleanField(default=False)
    last_watched_at = models.DateTimeField(auto_now=True)

    objects = models.Manager()

    class Meta:
        unique_together = ('user', 'lesson')
        ordering = ['-last_watched_at']

    def __str__(self):
        return f"{self.user.email} — {self.lesson.title}: {self.progress_percentage}%"


# =========================================================
#  10. Razorpay Webhook Event Idempotency Model
# =========================================================

class RazorpayWebhookEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True, db_index=True)
    event_type = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=50, default='processed')
    processed_at = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        ordering = ['-processed_at']
        verbose_name = 'Razorpay Webhook Event'
        verbose_name_plural = 'Razorpay Webhook Events'

    def __str__(self):
        return f"Webhook {self.event_id} ({self.event_type}) - {self.status}"


