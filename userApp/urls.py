from django.urls import path
from . import views

urlpatterns = [
    # --- Authentication ---
    path('auth/register/', views.auth_register, name='auth_register'),
    path('auth/login/', views.auth_login, name='auth_login'),
    path('auth/logout/', views.auth_logout, name='auth_logout'),
    path('auth/me/', views.auth_me, name='auth_me'),
    path('auth/token/refresh/', views.auth_token_refresh, name='auth_token_refresh'),

    # --- Courses ---
    path('courses/', views.course_list, name='course_list'),
    path('courses/<int:id>/', views.course_detail, name='course_detail'),
    path('courses/<slug:id>/', views.course_detail, name='course_detail_slug'),
    path('courses/<int:id>/access/', views.course_access, name='course_access'),
    path('courses/<slug:id>/access/', views.course_access, name='course_access_slug'),

    # --- Protected Video & Progress ---
    path('courses/<int:course_id>/lessons/<int:lesson_id>/video/', views.lesson_video, name='lesson_video'),
    path('courses/<int:course_id>/lessons/<int:lesson_id>/progress/', views.lesson_progress, name='lesson_progress'),
    path('courses/<int:course_id>/lessons/<int:lesson_id>/complete/', views.lesson_complete, name='lesson_complete'),

    # --- Enrollments ---
    path('enrollments/my/', views.my_enrollments, name='my_enrollments'),

    # --- Payments (Razorpay) ---
    path('payments/create-order/', views.payment_create_order, name='payment_create_order'),
    path('payments/verify/', views.payment_verify, name='payment_verify'),
    path('payments/status/<str:order_id>/', views.payment_status, name='payment_status'),

    # --- User Profile & Activity ---
    path('users/profile/', views.user_profile, name='user_profile'),
    path('users/change-password/', views.user_change_password, name='user_change_password'),
    path('users/activity/', views.user_activity, name='user_activity'),
]
