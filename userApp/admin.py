from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Instructor, Course, Module, Lesson, FAQ, Payment, Enrollment, LessonProgress, RazorpayWebhookEvent


@admin.register(RazorpayWebhookEvent)
class RazorpayWebhookEventAdmin(admin.ModelAdmin):
    list_display = ('id', 'event_id', 'event_type', 'status', 'processed_at')
    list_filter = ('event_type', 'status', 'processed_at')
    search_fields = ('event_id', 'event_type')
    readonly_fields = ('event_id', 'event_type', 'payload', 'status', 'processed_at')



@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('name', 'email')
    list_filter = ('is_staff', 'is_active')
    ordering = ('-date_joined',)
    readonly_fields = ('date_joined',)


@admin.register(Instructor)
class InstructorAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'title', 'created_at')
    search_fields = ('name', 'title')


class ModuleInline(admin.TabularInline):
    model = Module
    extra = 1


class FAQInline(admin.TabularInline):
    model = FAQ
    extra = 1


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'slug', 'category', 'price', 'is_published', 'is_bestseller', 'is_featured', 'created_at')
    search_fields = ('title', 'slug', 'description')
    list_filter = ('is_published', 'is_bestseller', 'is_featured', 'category')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [ModuleInline, FAQInline]


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'title', 'order')
    list_filter = ('course',)
    search_fields = ('title',)
    inlines = [LessonInline]


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('id', 'module', 'title', 'duration', 'is_preview', 'order')
    list_filter = ('module__course', 'is_preview')
    search_fields = ('title', 'module__title')


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'question', 'order')
    list_filter = ('course',)
    search_fields = ('question', 'answer')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'razorpay_order_id', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('razorpay_order_id', 'razorpay_payment_id', 'user__email', 'course__title')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'status', 'progress_percentage', 'enrolled_at')
    list_filter = ('status', 'enrolled_at')
    search_fields = ('user__email', 'course__title')
    readonly_fields = ('enrolled_at',)


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'lesson', 'progress_percentage', 'completed', 'last_watched_at')
    list_filter = ('completed', 'last_watched_at')
    search_fields = ('user__email', 'lesson__title')
