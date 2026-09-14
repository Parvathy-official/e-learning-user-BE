from .auth_views import (
    admin_login,
    admin_logout,
    admin_me,
    admin_token_refresh,
)
from .dashboard_views import (
    admin_dashboard_stats,
)
from .course_views import (
    admin_courses,
    admin_course_detail,
    admin_course_toggle_publish,
    admin_course_toggle_featured,
    admin_course_toggle_bestseller,
)
from .curriculum_views import (
    admin_course_curriculum,
    admin_course_modules,
    admin_module_detail,
    admin_modules_reorder,
    admin_module_lessons,
    admin_lesson_detail,
    admin_lessons_reorder,
)
from .student_views import (
    admin_students,
    admin_student_detail,
)
from .instructor_views import (
    admin_instructors,
    admin_instructor_detail,
)
from .enrollment_views import (
    admin_enrollments,
    admin_enrollment_detail,
)
from .payment_views import (
    admin_payments,
    admin_payment_detail,
)
from .settings_views import (
    admin_profile,
    admin_change_password,
)

__all__ = [
    'admin_login',
    'admin_logout',
    'admin_me',
    'admin_token_refresh',
    'admin_dashboard_stats',
    'admin_courses',
    'admin_course_detail',
    'admin_course_toggle_publish',
    'admin_course_toggle_featured',
    'admin_course_toggle_bestseller',
    'admin_course_curriculum',
    'admin_course_modules',
    'admin_module_detail',
    'admin_modules_reorder',
    'admin_module_lessons',
    'admin_lesson_detail',
    'admin_lessons_reorder',
    'admin_students',
    'admin_student_detail',
    'admin_instructors',
    'admin_instructor_detail',
    'admin_enrollments',
    'admin_enrollment_detail',
    'admin_payments',
    'admin_payment_detail',
    'admin_profile',
    'admin_change_password',
]
