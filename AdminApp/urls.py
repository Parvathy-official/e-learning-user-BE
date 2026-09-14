from django.urls import path, re_path
from . import views

urlpatterns = [
    # --- Auth endpoints ---
    path('auth/login/', views.admin_login, name='admin_auth_login'),
    path('auth/login', views.admin_login, name='admin_auth_login_noslash'),
    path('login/', views.admin_login, name='admin_login'),
    path('login', views.admin_login, name='admin_login_noslash'),
    path('auth/logout/', views.admin_logout, name='admin_auth_logout'),
    path('auth/logout', views.admin_logout, name='admin_auth_logout_noslash'),
    path('auth/me/', views.admin_me, name='admin_auth_me'),
    path('auth/me', views.admin_me, name='admin_auth_me_noslash'),
    path('auth/token/refresh/', views.admin_token_refresh, name='admin_auth_token_refresh'),
    path('auth/token/refresh', views.admin_token_refresh, name='admin_auth_token_refresh_noslash'),

    # --- Dashboard ---
    path('dashboard/stats/', views.admin_dashboard_stats, name='admin_dashboard_stats'),
    path('dashboard/stats', views.admin_dashboard_stats, name='admin_dashboard_stats_noslash'),

    # --- Courses CRUD & Toggles ---
    path('courses/', views.admin_courses, name='admin_courses'),
    path('courses', views.admin_courses, name='admin_courses_noslash'),
    path('courses/<int:id>/', views.admin_course_detail, name='admin_course_detail'),
    path('courses/<int:id>', views.admin_course_detail, name='admin_course_detail_noslash'),
    path('courses/<int:id>/toggle-publish/', views.admin_course_toggle_publish, name='admin_course_toggle_publish'),
    path('courses/<int:id>/toggle-publish', views.admin_course_toggle_publish, name='admin_course_toggle_publish_noslash'),
    path('courses/<int:id>/toggle-featured/', views.admin_course_toggle_featured, name='admin_course_toggle_featured'),
    path('courses/<int:id>/toggle-featured', views.admin_course_toggle_featured, name='admin_course_toggle_featured_noslash'),
    path('courses/<int:id>/toggle-bestseller/', views.admin_course_toggle_bestseller, name='admin_course_toggle_bestseller'),
    path('courses/<int:id>/toggle-bestseller', views.admin_course_toggle_bestseller, name='admin_course_toggle_bestseller_noslash'),

    # --- Curriculum: Modules & Lessons ---
    path('courses/<int:course_id>/curriculum/', views.admin_course_curriculum, name='admin_course_curriculum'),
    path('courses/<int:course_id>/curriculum', views.admin_course_curriculum, name='admin_course_curriculum_noslash'),
    path('courses/<int:course_id>/modules/', views.admin_course_modules, name='admin_course_modules'),
    path('courses/<int:course_id>/modules', views.admin_course_modules, name='admin_course_modules_noslash'),
    path('courses/<int:course_id>/modules/reorder/', views.admin_modules_reorder, name='admin_modules_reorder'),
    path('courses/<int:course_id>/modules/reorder', views.admin_modules_reorder, name='admin_modules_reorder_noslash'),
    path('modules/<int:module_id>/', views.admin_module_detail, name='admin_module_detail'),
    path('modules/<int:module_id>', views.admin_module_detail, name='admin_module_detail_noslash'),
    path('modules/<int:module_id>/lessons/', views.admin_module_lessons, name='admin_module_lessons'),
    path('modules/<int:module_id>/lessons', views.admin_module_lessons, name='admin_module_lessons_noslash'),
    path('modules/<int:module_id>/lessons/reorder/', views.admin_lessons_reorder, name='admin_lessons_reorder'),
    path('modules/<int:module_id>/lessons/reorder', views.admin_lessons_reorder, name='admin_lessons_reorder_noslash'),
    path('lessons/<int:lesson_id>/', views.admin_lesson_detail, name='admin_lesson_detail'),
    path('lessons/<int:lesson_id>', views.admin_lesson_detail, name='admin_lesson_detail_noslash'),

    # --- Students / Users Management ---
    path('students/', views.admin_students, name='admin_students'),
    path('students', views.admin_students, name='admin_students_noslash'),
    path('students/<int:user_id>/', views.admin_student_detail, name='admin_student_detail'),
    path('students/<int:user_id>', views.admin_student_detail, name='admin_student_detail_noslash'),

    # --- Instructors ---
    path('instructors/', views.admin_instructors, name='admin_instructors'),
    path('instructors', views.admin_instructors, name='admin_instructors_noslash'),
    path('instructors/<int:id>/', views.admin_instructor_detail, name='admin_instructor_detail'),
    path('instructors/<int:id>', views.admin_instructor_detail, name='admin_instructor_detail_noslash'),

    # --- Enrollments ---
    path('enrollments/', views.admin_enrollments, name='admin_enrollments'),
    path('enrollments', views.admin_enrollments, name='admin_enrollments_noslash'),
    path('enrollments/<int:id>/', views.admin_enrollment_detail, name='admin_enrollment_detail'),
    path('enrollments/<int:id>', views.admin_enrollment_detail, name='admin_enrollment_detail_noslash'),

    # --- Payments ---
    path('payments/', views.admin_payments, name='admin_payments'),
    path('payments', views.admin_payments, name='admin_payments_noslash'),
    path('payments/<int:id>/', views.admin_payment_detail, name='admin_payment_detail'),
    path('payments/<int:id>', views.admin_payment_detail, name='admin_payment_detail_noslash'),

    # --- Settings & Profile ---
    path('profile/', views.admin_profile, name='admin_profile'),
    path('profile', views.admin_profile, name='admin_profile_noslash'),
    path('change-password/', views.admin_change_password, name='admin_change_password'),
    path('change-password', views.admin_change_password, name='admin_change_password_noslash'),
]
