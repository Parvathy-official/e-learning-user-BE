import os
import hashlib
import secrets
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from .models import EmailOTP

logger = logging.getLogger(__name__)


def _send_otp_email_smtp(subject: str, message: str, from_email: str, recipient_list: list[str], raw_otp: str = None, custom_html: str = None) -> tuple[bool, str]:
    """
    Sends email via Django SMTP email backend (Gmail SMTP).
    Returns (success: bool, error_msg: str).
    """
    html_content = custom_html
    if not html_content and raw_otp:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"></head>
        <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #030708; color: #F1F5F9; margin: 0; padding: 32px 16px;">
          <div style="max-width: 480px; margin: 0 auto; background-color: #0B1116; border: 1px solid rgba(6, 182, 212, 0.3); border-radius: 14px; padding: 32px; box-shadow: 0 10px 30px rgba(0,0,0,0.8);">
            <div style="text-align: center; margin-bottom: 24px;">
              <h2 style="color: #06B6D4; margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px;">Flair Academy</h2>
              <p style="color: #94A3B8; font-size: 13px; margin: 4px 0 0;">Course Access Verification</p>
            </div>
            <p style="color: #E2E8F0; font-size: 15px; line-height: 1.5; margin: 0 0 16px;">Hello,</p>
            <p style="color: #94A3B8; font-size: 14px; line-height: 1.5; margin: 0 0 20px;">Your one-time verification code to access your enrolled masterclass is:</p>
            <div style="background: rgba(6, 182, 212, 0.1); border: 1.5px solid #06B6D4; border-radius: 10px; text-align: center; padding: 18px; margin: 0 0 24px;">
              <span style="font-size: 34px; font-weight: 800; letter-spacing: 8px; color: #38BDF8; font-family: 'Courier New', Courier, monospace;">{raw_otp}</span>
            </div>
            <p style="color: #94A3B8; font-size: 13px; line-height: 1.5; margin: 0 0 20px;">This code will expire in <strong>15 minutes</strong>. If you did not request this code, you can safely ignore this email.</p>
            <hr style="border: none; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 24px 0 16px;">
            <p style="color: #64748B; font-size: 12px; text-align: center; margin: 0;">&copy; Flair Academy • Digital Product & Marketing Masterclass</p>
          </div>
        </body>
        </html>
        """

    sender = from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', None) or getattr(settings, 'EMAIL_HOST_USER', 'noreply@flairacademy.com')
    try:
        logger.info("OTP FLOW: email send started")
        send_mail(
            subject=subject,
            message=message,
            from_email=sender,
            recipient_list=recipient_list,
            html_message=html_content,
            fail_silently=False
        )
        logger.info("OTP FLOW: email send completed")
        return True, ""
    except Exception as e:
        logger.error(f"OTP FLOW: email send failed: {type(e).__name__} - {e}", exc_info=True)
        return False, f"{type(e).__name__}: {str(e)}"


def generate_secure_otp() -> str:
    """Generates a cryptographically random 6-digit numeric OTP."""
    return f"{secrets.randbelow(900000) + 100000:06d}"


def compute_otp_hashes(email: str, otp: str) -> list[str]:
    """
    Computes possible valid hashes for the given email and OTP to be resilient across
    salt configurations (settings.SECRET_KEY, fixed salt, or default fallback).
    """
    email_clean = email.strip().lower()
    otp_clean = str(otp).strip().replace(' ', '').replace('-', '')

    salts = [
        getattr(settings, 'SECRET_KEY', 'learnflow-secure-otp-salt-v1'),
        'django-insecure-default-key-change-in-prod',
        'learnflow-secure-otp-salt-v1',
        'otp-salt-key',
        '',
    ]

    hashes = set()
    for s in salts:
        hashes.add(hashlib.sha256(f"{email_clean}:{otp_clean}:{s}".encode('utf-8')).hexdigest())
        hashes.add(hashlib.sha256(f"{email_clean}:{otp_clean}".encode('utf-8')).hexdigest())
    return list(hashes)


def hash_otp(email: str, otp: str) -> str:
    """Hashes the OTP combined with normalized email and SECRET_KEY."""
    salt = getattr(settings, 'SECRET_KEY', 'learnflow-secure-otp-salt-v1')
    return hashlib.sha256(f"{email.strip().lower()}:{str(otp).strip()}:{salt}".encode('utf-8')).hexdigest()


def create_and_send_otp(email: str) -> tuple[bool, str]:
    """
    Rate-limits, generates, stores hashed OTP, sends email via Gmail SMTP,
    and returns (success: bool, message: str).
    If email delivery fails, cleans up the un-sent OTP record so rate limiting does not lock the user out.
    """
    logger.info("OTP FLOW: entered create_and_send_otp")
    email = email.strip().lower()
    now = timezone.now()

    # Rate limiting: max 1 OTP request every 45 seconds
    recent_otp = EmailOTP.objects.filter(
        email=email,
        created_at__gte=now - timedelta(seconds=45)
    ).first()
    if recent_otp:
        logger.info("OTP FLOW: rate limit hit")
        return False, "A verification code was already sent recently. Please wait 45 seconds before requesting a new one."

    raw_otp = generate_secure_otp()
    logger.info("OTP FLOW: OTP generated")

    hashed = hash_otp(email, raw_otp)
    expires_at = now + timedelta(minutes=15)

    otp_record = EmailOTP.objects.create(
        email=email,
        otp_hash=hashed,
        expires_at=expires_at,
        attempts=0,
        is_used=False
    )
    logger.info("OTP FLOW: database record created")

    # Unique subject with code prevents Gmail from collapsing new messages into old threads
    subject = f"Your Flair Academy Access Code is {raw_otp}"
    message = (
        f"Hello,\n\n"
        f"Your one-time verification code is: {raw_otp}\n\n"
        f"This code will expire in 15 minutes. Enter this code to access your purchased courses.\n\n"
        f"If you did not request this code, please ignore this email.\n\n"
        f"— Flair Academy"
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Flair Academy <noreply@flairacademy.com>')
    logger.info("OTP FLOW: email message constructed")

    # Send verification email via configured SMTP backend
    success, err_msg = _send_otp_email_smtp(
        subject=subject,
        message=message,
        from_email=from_email,
        recipient_list=[email],
        raw_otp=raw_otp
    )

    if not success:
        # If email fails, immediately delete the created OTP record so user can retry without being locked out
        otp_record.delete()
        logger.warning(f"OTP FLOW: OTP database record removed due to email dispatch failure for {email}")
        return False, "Failed to send verification code. Please check your email address or try again in a few moments."

    return True, "Verification code sent to your email."


def verify_otp_code(email: str, otp: str) -> tuple[bool, str]:
    """
    Validates the OTP code against stored hashes of any unexpired, unused OTP record for this email.
    Enforces expiration and attempt limits.
    Returns (success: bool, message: str).
    """
    email = email.strip().lower()
    otp = str(otp).strip().replace(' ', '').replace('-', '')
    now = timezone.now()

    if not otp:
        return False, "Verification code is required."

    active_records = list(
        EmailOTP.objects.filter(
            email=email,
            is_used=False,
            expires_at__gt=now,
            attempts__lt=5
        ).order_by('-created_at')
    )

    if not active_records:
        logger.warning(f"No active unused OTP found for {email} (expired or already used).")
        return False, "Verification code has expired or is invalid. Please request a new code."

    valid_hashes = set(compute_otp_hashes(email, otp))

    matched_record = None
    for rec in active_records:
        if rec.otp_hash in valid_hashes:
            matched_record = rec
            break

    if not matched_record:
        # Increment attempt counter on the latest active record
        latest_rec = active_records[0]
        latest_rec.attempts += 1
        latest_rec.save(update_fields=['attempts'])
        remaining = max(0, 5 - latest_rec.attempts)

        if remaining == 0:
            latest_rec.is_used = True
            latest_rec.save(update_fields=['is_used'])
            logger.warning(f"OTP for {email} exceeded max 5 attempts. Invalidated.")
            return False, "Too many failed attempts. This code is now invalid. Please request a new code."

        logger.warning(f"Invalid OTP entered for {email}. {remaining} attempts remaining.")
        return False, f"Invalid verification code. {remaining} attempt{'s' if remaining != 1 else ''} remaining."

    # Mark ALL active OTPs for this email as used so none can be reused
    EmailOTP.objects.filter(email=email, is_used=False).update(is_used=True)
    logger.info(f"OTP verified successfully for {email}.")
    return True, "Code verified successfully."


_SENT_ENROLLMENT_EMAILS = set()


def send_enrollment_confirmation_email(user, course, payment=None):
    """
    Dispatches an enrollment confirmation email to the user with a direct access link
    to their enrolled course and My Learning dashboard.
    Uses standard Django SMTP asynchronously.
    """
    if not user or not getattr(user, 'email', None):
        return False, "User email is missing."

    email = user.email.strip().lower()
    course_title = getattr(course, 'title', 'Masterclass')
    course_id = getattr(course, 'id', '1')
    user_name = getattr(user, 'name', '') or email.split('@')[0]

    # De-duplicate: Ensure only 1 welcome email is dispatched per payment / enrollment session
    dedup_key = f"{payment.id if payment else 'no_pay'}_{user.id}_{course_id}"
    if dedup_key in _SENT_ENROLLMENT_EMAILS:
        return True, "Email already dispatched."
    _SENT_ENROLLMENT_EMAILS.add(dedup_key)

    frontend_url = getattr(settings, 'USER_FRONTEND_URL', 'https://e-learning-user.netlify.app')
    if getattr(settings, 'DEBUG', False) and not os.getenv('USER_FRONTEND_URL'):
        frontend_url = 'http://localhost:5173'
    frontend_url = str(frontend_url).rstrip('/')

    course_url = f"{frontend_url}/course/{course_id}/learn"
    my_learning_url = f"{frontend_url}/my-learning"

    amount_str = f"₹{payment.amount / 100:.0f}" if (payment and getattr(payment, 'amount', None)) else "₹499"
    order_id_str = getattr(payment, 'razorpay_order_id', 'N/A') if payment else 'N/A'

    subject = f"🎉 Access Confirmed: {course_title}"
    message = (
        f"Hello {user_name},\n\n"
        f"Congratulations! Your payment of {amount_str} was successful, and your enrollment for '{course_title}' is now active.\n\n"
        f"You have lifetime access to the masterclass. Click the link below to start learning immediately:\n"
        f"{course_url}\n\n"
        f"You can also access all your courses anytime at: {my_learning_url}\n\n"
        f"Order ID: {order_id_str}\n\n"
        f"Happy learning!\n"
        f"— Flair Academy"
    )

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #030708; color: #F1F5F9; margin: 0; padding: 32px 16px;">
      <div style="max-width: 520px; margin: 0 auto; background-color: #0B1116; border: 1px solid rgba(6, 182, 212, 0.35); border-radius: 16px; padding: 32px; box-shadow: 0 15px 40px rgba(0,0,0,0.8), 0 0 25px rgba(6,182,212,0.15);">
        
        <div style="text-align: center; margin-bottom: 24px;">
          <h2 style="color: #06B6D4; margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px;">Flair Academy</h2>
          <span style="display: inline-block; background: rgba(6, 182, 212, 0.12); border: 1px solid rgba(6, 182, 212, 0.4); color: #38BDF8; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em; padding: 3px 10px; border-radius: 9999px; margin-top: 8px;">
            ● Enrolled Student Confirmation
          </span>
        </div>

        <p style="color: #F8FAFC; font-size: 16px; font-weight: 700; margin: 0 0 12px;">Welcome, {user_name}!</p>
        
        <p style="color: #CBD5E1; font-size: 14px; line-height: 1.6; margin: 0 0 20px;">
          Your payment was successful and you now have <strong>full lifetime access</strong> to:
        </p>

        <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 18px; margin: 0 0 24px;">
          <h3 style="color: #FFFFFF; font-size: 16px; font-weight: 700; margin: 0 0 6px;">{course_title}</h3>
          <p style="color: #94A3B8; font-size: 13px; margin: 0 0 12px;">3-Hour Practical Masterclass • AI-Powered Curriculum</p>
          <div style="border-top: 1px dashed rgba(255, 255, 255, 0.1); padding-top: 10px; font-size: 12px; color: #94A3B8;">
            <span>Amount Paid: <strong style="color: #38BDF8;">{amount_str}</strong></span> &nbsp;•&nbsp; 
            <span>Order ID: <span style="font-family: monospace; color: #E2E8F0;">{order_id_str}</span></span>
          </div>
        </div>

        <div style="text-align: center; margin: 0 0 28px;">
          <a href="{course_url}" style="display: inline-block; background: linear-gradient(135deg, #06B6D4 0%, #0EA5E9 100%); color: #030708; font-size: 15px; font-weight: 800; text-decoration: none; padding: 14px 32px; border-radius: 10px; box-shadow: 0 0 20px rgba(6, 182, 212, 0.4); letter-spacing: 0.02em;">
            ▶ START LEARNING NOW &rarr;
          </a>
        </div>

        <p style="color: #94A3B8; font-size: 13px; line-height: 1.5; margin: 0 0 20px; text-align: center;">
          You can pick up right where you left off anytime at your <a href="{my_learning_url}" style="color: #38BDF8; text-decoration: underline;">My Learning Dashboard</a>.
        </p>

        <hr style="border: none; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 24px 0 16px;">
        <p style="color: #64748B; font-size: 12px; text-align: center; margin: 0;">&copy; Flair Academy • Digital Product & Marketing Masterclass</p>
      </div>
    </body>
    </html>
    """

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Flair Academy <noreply@flairacademy.com>')

    import threading
    email_thread = threading.Thread(
        target=_send_otp_email_smtp,
        args=(subject, message, from_email, [email]),
        kwargs={"raw_otp": None, "custom_html": html_content},
        daemon=True
    )
    email_thread.start()

    logger.info(f"[Email] Dispatched course enrollment confirmation email to {email} for course #{course_id}")
    return True, "Enrollment confirmation email dispatched."
