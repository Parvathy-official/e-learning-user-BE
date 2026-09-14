from django.urls import path
from . import views
from . import admin_views

urlpatterns = [
    # --- Authentication (Student/General) ---
    path('auth/register/', views.auth_register, name='auth_register'),
    path('auth/login/', views.auth_login, name='auth_login'),
    path('auth/logout/', views.auth_logout, name='auth_logout'),
    path('auth/me/', views.auth_me, name='auth_me'),
    path('auth/token/refresh/', views.auth_token_refresh, name='auth_token_refresh'),

    # --- Courses (Public/Student) ---
    path('courses/', views.course_list, name='course_list'),
    path('courses/<int:id>/', views.course_detail, name='course_detail'),
    path('courses/<slug:id>/', views.course_detail, name='course_detail_slug'),
    path('courses/<int:id>/access/', views.course_access, name='course_access'),
    path('courses/<slug:id>/access/', views.course_access, name='course_access_slug'),

    # --- Protected Video & Progress ---
    path('courses/<int:course_id>/lessons/<int:lesson_id>/video/', views.lesson_video, name='lesson_video'),
    path('courses/<int:course_id>/lessons/<int:lesson_id>/progress/', views.lesson_progress, name='lesson_progress'),
    path('courses/<int:course_id>/lessons/<int:lesson_id>/complete/', views.lesson_complete, name='lesson_complete'),

    # --- Enrollments (Student) ---
    path('enrollments/my/', views.my_enrollments, name='my_enrollments'),

    # --- Payments (Razorpay) ---
    path('payments/create-order/', views.payment_create_order, name='payment_create_order'),
    path('payments/verify/', views.payment_verify, name='payment_verify'),
    path('payments/webhook/', views.payment_webhook, name='payment_webhook'),
    path('payments/webhook', views.payment_webhook, name='payment_webhook_noslash'),
    path('payments/status/<str:order_id>/', views.payment_status, name='payment_status'),

    # --- User Profile & Activity ---
    path('users/profile/', views.user_profile, name='user_profile'),
    path('users/change-password/', views.user_change_password, name='user_change_password'),
    path('users/activity/', views.user_activity, name='user_activity'),

    # =========================================================
    #  ADMIN REST API ENDPOINTS
    # =========================================================

    # 1. Admin Dashboard
    path('admin/dashboard/stats/', admin_views.admin_dashboard_stats, name='admin_dashboard_stats'),

    # 2. Admin Courses
    path('admin/courses/', admin_views.admin_courses, name='admin_courses'),
    path('admin/courses/<int:id>/', admin_views.admin_course_detail, name='admin_course_detail'),
    path('admin/courses/<int:id>/toggle-publish/', admin_views.admin_course_toggle_publish, name='admin_course_toggle_publish'),
    path('admin/courses/<int:id>/toggle-featured/', admin_views.admin_course_toggle_featured, name='admin_course_toggle_featured'),
    path('admin/courses/<int:id>/toggle-bestseller/', admin_views.admin_course_toggle_bestseller, name='admin_course_toggle_bestseller'),

    # 3. Admin Curriculum (Modules & Lessons)
    path('admin/courses/<int:course_id>/curriculum/', admin_views.admin_course_curriculum, name='admin_course_curriculum'),
    path('admin/courses/<int:course_id>/modules/', admin_views.admin_course_modules, name='admin_course_modules'),
    path('admin/courses/<int:course_id>/modules/reorder/', admin_views.admin_modules_reorder, name='admin_modules_reorder'),
    path('admin/modules/<int:module_id>/', admin_views.admin_module_detail, name='admin_module_detail'),
    path('admin/modules/<int:module_id>/lessons/', admin_views.admin_module_lessons, name='admin_module_lessons'),
    path('admin/modules/<int:module_id>/lessons/reorder/', admin_views.admin_lessons_reorder, name='admin_lessons_reorder'),
    path('admin/lessons/<int:lesson_id>/', admin_views.admin_lesson_detail, name='admin_lesson_detail'),

    # 4. Admin Students
    path('admin/students/', admin_views.admin_students, name='admin_students'),
    path('admin/students/<int:user_id>/', admin_views.admin_student_detail, name='admin_student_detail'),

    # 5. Admin Instructors
    path('admin/instructors/', admin_views.admin_instructors, name='admin_instructors'),
    path('admin/instructors/<int:id>/', admin_views.admin_instructor_detail, name='admin_instructor_detail'),

    # 6. Admin Enrollments
    path('admin/enrollments/', admin_views.admin_enrollments, name='admin_enrollments'),
    path('admin/enrollments/<int:id>/', admin_views.admin_enrollment_detail, name='admin_enrollment_detail'),

    # 7. Admin Payments
    path('admin/payments/', admin_views.admin_payments, name='admin_payments'),
    path('admin/payments/<int:id>/', admin_views.admin_payment_detail, name='admin_payment_detail'),

    # 8. Admin Profile & Settings
    path('admin/profile/', admin_views.admin_profile, name='admin_profile'),
    path('admin/change-password/', admin_views.admin_change_password, name='admin_change_password'),
]
