import hashlib
import secrets
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from .models import EmailOTP


def generate_secure_otp() -> str:
    """Generates a cryptographically random 6-digit numeric OTP."""
    return f"{secrets.randbelow(900000) + 100000:06d}"


def hash_otp(email: str, otp: str) -> str:
    """Hashes the OTP combined with normalized email and SECRET_KEY."""
    salt = getattr(settings, 'SECRET_KEY', 'otp-salt-key')
    return hashlib.sha256(f"{email.strip().lower()}:{otp.strip()}:{salt}".encode('utf-8')).hexdigest()


def create_and_send_otp(email: str) -> tuple[bool, str]:
    """
    Rate-limits, generates, stores hashed OTP, and sends email to user.
    Returns (success: bool, message: str).
    """
    email = email.strip().lower()
    now = timezone.now()

    # Rate limiting: max 1 OTP request every 60 seconds
    recent_otp = EmailOTP.objects.filter(
        email=email,
        created_at__gte=now - timedelta(seconds=60)
    ).first()
    if recent_otp:
        return False, "A verification code was already sent recently. Please wait 60 seconds before requesting a new one."

    # Invalidate previous unused OTPs for this email
    EmailOTP.objects.filter(email=email, is_used=False).update(is_used=True)

    raw_otp = generate_secure_otp()
    hashed = hash_otp(email, raw_otp)
    expires_at = now + timedelta(minutes=10)

    EmailOTP.objects.create(
        email=email,
        otp_hash=hashed,
        expires_at=expires_at,
        attempts=0,
        is_used=False
    )

    subject = "Your LearnFlow Access Verification Code"
    message = (
        f"Hello,\n\n"
        f"Your one-time verification code is: {raw_otp}\n\n"
        f"This code will expire in 10 minutes. Enter this code to access your purchased courses.\n\n"
        f"If you did not request this code, please ignore this email.\n\n"
        f"— LearnFlow Academy"
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'LearnFlow Academy <noreply@learnflow.com>')

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=False
        )
    except Exception as e:
        # In DEBUG mode, email may print to console if console backend or fall back gracefully
        if not getattr(settings, 'DEBUG', False):
            return False, "Failed to send verification email. Please try again."

    return True, "Verification code sent to your email."


def verify_otp_code(email: str, otp: str) -> tuple[bool, str]:
    """
    Validates the OTP code against stored hash, enforcing expiration and attempt limits.
    Returns (success: bool, message: str).
    """
    email = email.strip().lower()
    otp = str(otp).strip()
    now = timezone.now()

    otp_record = EmailOTP.objects.filter(
        email=email,
        is_used=False,
        expires_at__gt=now
    ).order_by('-created_at').first()

    if not otp_record:
        return False, "Verification code has expired or is invalid. Please request a new code."

    if otp_record.attempts >= 5:
        otp_record.is_used = True
        otp_record.save(update_fields=['is_used'])
        return False, "Too many failed attempts. This code is now invalid. Please request a new one."

    expected_hash = hash_otp(email, otp)
    if otp_record.otp_hash != expected_hash:
        otp_record.attempts += 1
        otp_record.save(update_fields=['attempts'])
        remaining = 5 - otp_record.attempts
        return False, f"Invalid verification code. {remaining} attempt{'s' if remaining != 1 else ''} remaining."

    # Mark as used (single use)
    otp_record.is_used = True
    otp_record.save(update_fields=['is_used'])
    return True, "Code verified successfully."
