from typing import List, TypedDict
from django.core.management.base import BaseCommand
from django.db import transaction
from userApp.models import User, Instructor, Course, Module, Lesson, FAQ, Enrollment, LessonProgress, Payment


class LessonData(TypedDict):
    title: str
    duration: str
    duration_seconds: int
    is_preview: bool
    order: int


class ModuleData(TypedDict):
    title: str
    order: int
    lessons: List[LessonData]


class Command(BaseCommand):
    help = 'Seeds initial course and demo user data for Create & Sell Your First Digital Product With AI'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding digital product masterclass data...')

        with transaction.atomic():
            # 1. Create Instructor
            instructor, _ = Instructor.objects.get_or_create(
                name='AI Digital Product Academy',
                defaults={
                    'title': 'Digital Entrepreneur & AI Creator',
                    'bio': 'Helping creators, professionals, and freelancers monetize their knowledge and launch profitable digital assets.',
                    'avatar': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&q=80',
                }
            )

            # 2. Create Digital Product Masterclass
            course, created = Course.objects.get_or_create(
                slug='create-sell-digital-product-ai',
                defaults={
                    'title': 'Create & Sell Your First Digital Product With AI',
                    'short_description': 'A 3-Hour Practical Session to Take You From Idea to Your First Digital Product.',
                    'description': 'Learn how to find the right niche, identify a real problem, create a digital product with AI, host it online, create promotional content, and launch Meta Ads.',
                    'thumbnail': 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&q=80',
                    'instructor': instructor,
                    'category': 'Digital Products & AI',
                    'price': 499.00,
                    'original_price': 2499.00,
                    'duration': '3 Hours',
                    'level': 'Beginner-Friendly',
                    'language': 'English',
                    'is_published': True,
                    'is_bestseller': True,
                    'is_featured': True,
                    'rating': 4.98,
                    'total_ratings': 2840,
                    'total_students': 12500,
                    'learning_outcomes': [
                        'Find your profitable niche that fits your skills, interests, and goals',
                        'Identify a real problem that people actively pay to solve',
                        'Use AI to generate and package high-value digital products in hours',
                        'Host your product online and set up seamless automated delivery',
                        'Create high-converting video and graphic promo content with AI',
                        'Set up and launch high-ROI Meta Ads from scratch',
                        'Scale from an MVP product into recurring digital sales',
                    ],
                    'requirements': [
                        'No technical knowledge or coding needed',
                        'No physical inventory or business setup required',
                        'A computer or smartphone with an internet connection',
                    ],
                }
            )

            # 3. Create 7 Modules & Lessons
            modules_data: List[ModuleData] = [
                {
                    'title': 'Module 1 — Introduction to Digital Products',
                    'order': 1,
                    'lessons': [
                        {'title': 'Lesson 1.1 — The Power of Digital Assets & Zero Inventory Economics', 'duration': '12:30', 'duration_seconds': 750, 'is_preview': True, 'order': 1},
                        {'title': 'Lesson 1.2 — The 5-Step Formula: Problem → Solution → Package → Promote → Sell', 'duration': '14:20', 'duration_seconds': 860, 'is_preview': True, 'order': 2},
                    ]
                },
                {
                    'title': 'Module 2 — Niche Discovery',
                    'order': 2,
                    'lessons': [
                        {'title': 'Lesson 2.1 — Discovering Your Profitable Knowledge Niche', 'duration': '15:40', 'duration_seconds': 940, 'is_preview': False, 'order': 3},
                        {'title': 'Lesson 2.2 — AI Prompts for Market & Competitor Analysis', 'duration': '18:15', 'duration_seconds': 1095, 'is_preview': False, 'order': 4},
                    ]
                },
                {
                    'title': 'Module 3 — Solve Problems with Digital Products',
                    'order': 3,
                    'lessons': [
                        {'title': 'Lesson 3.1 — Identifying High-Pain Urgent Problems Customers Pay For', 'duration': '16:10', 'duration_seconds': 970, 'is_preview': False, 'order': 5},
                        {'title': 'Lesson 3.2 — Structuring Your High-Value Solution & Offer', 'duration': '14:50', 'duration_seconds': 890, 'is_preview': False, 'order': 6},
                    ]
                },
                {
                    'title': 'Module 4 — Create Your Digital Product with AI',
                    'order': 4,
                    'lessons': [
                        {'title': 'Lesson 4.1 — AI-Powered Research, Planning & Outlining SOPs', 'duration': '22:40', 'duration_seconds': 1360, 'is_preview': False, 'order': 7},
                        {'title': 'Lesson 4.2 — Generating Ebooks, Guides, Templates & Toolkits Fast', 'duration': '25:10', 'duration_seconds': 1510, 'is_preview': False, 'order': 8},
                    ]
                },
                {
                    'title': 'Module 5 — Host Your Digital Product',
                    'order': 5,
                    'lessons': [
                        {'title': 'Lesson 5.1 — Instant Hosting & Zero-Code Landing Pages', 'duration': '17:30', 'duration_seconds': 1050, 'is_preview': False, 'order': 9},
                        {'title': 'Lesson 5.2 — Automated Checkout, Payments & Digital File Delivery', 'duration': '19:40', 'duration_seconds': 1180, 'is_preview': False, 'order': 10},
                    ]
                },
                {
                    'title': 'Module 6 — Create Content & Sell Your Digital Product',
                    'order': 6,
                    'lessons': [
                        {'title': 'Lesson 6.1 — AI Prompts for Viral Video Scripts, Hooks & Posters', 'duration': '20:15', 'duration_seconds': 1215, 'is_preview': False, 'order': 11},
                        {'title': 'Lesson 6.2 — Organic Audience Building & Content Distribution', 'duration': '18:00', 'duration_seconds': 1080, 'is_preview': False, 'order': 12},
                    ]
                },
                {
                    'title': 'Module 7 — Set Up & Launch Meta Ads',
                    'order': 7,
                    'lessons': [
                        {'title': 'Lesson 7.1 — Beginner-Friendly Meta Ads Setup & Campaign Architecture', 'duration': '24:20', 'duration_seconds': 1460, 'is_preview': False, 'order': 13},
                        {'title': 'Lesson 7.2 — Launching, Testing & Scaling Profitable ₹499 Ad Sets', 'duration': '26:30', 'duration_seconds': 1590, 'is_preview': False, 'order': 14},
                    ]
                },
            ]

            for m_info in modules_data:
                module, _ = Module.objects.get_or_create(
                    course=course,
                    title=m_info['title'],
                    defaults={'order': m_info['order']}
                )
                for l_info in m_info['lessons']:
                    Lesson.objects.get_or_create(
                        module=module,
                        title=l_info['title'],
                        defaults={
                            'duration': l_info['duration'],
                            'duration_seconds': l_info['duration_seconds'],
                            'is_preview': l_info['is_preview'],
                            'order': l_info['order'],
                            'video_url': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
                        }
                    )

            # 4. Create FAQs
            faqs_data = [
                {'q': 'Is this suitable for beginners?', 'a': 'Yes. The session starts from the basics and takes you through the complete process step by step.'},
                {'q': 'Do I need technical knowledge?', 'a': 'No. The session is designed to be beginner-friendly.'},
                {'q': 'What type of digital product can I create?', 'a': 'You can create ebooks, guides, templates, checklists, workbooks, toolkits, prompt packs, courses, and other digital resources.'},
                {'q': 'Will I learn how to use AI?', 'a': 'Yes. You\'ll get practical AI prompts and learn how AI can help you with niche discovery, product creation, and marketing.'},
                {'q': 'Will I learn Meta Ads?', 'a': 'Yes. The session covers the basic setup and process for launching Meta Ads to promote your digital product.'},
                {'q': 'How long is the session?', 'a': 'The complete session is approximately 3 hours.'},
                {'q': 'How much does it cost?', 'a': 'The session is available for just ₹499 as a one-time payment.'},
            ]

            for idx, f in enumerate(faqs_data, start=1):
                FAQ.objects.get_or_create(
                    course=course,
                    question=f['q'],
                    defaults={'answer': f['a'], 'order': idx}
                )

            # 5. Create Demo User & Enrolled State
            demo_user, u_created = User.objects.get_or_create(
                email='creator@digitalproduct.ai',
                defaults={
                    'name': 'Digital Creator',
                    'avatar': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=400&q=80',
                    'is_active': True,
                }
            )
            if u_created or not demo_user.check_password('creator123'):
                demo_user.set_password('creator123')
                demo_user.save()

            # Create demo enrollment
            first_lesson = Lesson.objects.filter(module__course=course).first()
            payment, _ = Payment.objects.get_or_create(
                razorpay_order_id='ord_digital_product_demo_01',
                defaults={
                    'user': demo_user,
                    'course': course,
                    'amount': 49900,
                    'currency': 'INR',
                    'status': 'paid',
                }
            )

            enrollment, _ = Enrollment.objects.get_or_create(
                user=demo_user,
                course=course,
                defaults={
                    'payment': payment,
                    'status': 'active',
                    'progress_percentage': 15,
                    'last_watched_lesson': first_lesson,
                    'last_watched_position': 180,
                }
            )

            # 6. Create / Update Master Admin
            admin_user, a_created = User.objects.get_or_create(
                email='admin@learnflow.com',
                defaults={
                    'name': 'Master Admin',
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True,
                }
            )
            admin_user.is_staff = True
            admin_user.is_superuser = True
            admin_user.is_active = True
            admin_user.set_password('admin123')
            admin_user.save()

        self.stdout.write(self.style.SUCCESS('Successfully seeded digital product masterclass and admin data!'))

