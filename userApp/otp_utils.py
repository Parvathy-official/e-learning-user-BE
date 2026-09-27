import os
import hashlib
import secrets
import threading
import logging
import requests
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from .models import EmailOTP

logger = logging.getLogger(__name__)


def _send_otp_email_worker(subject: str, message: str, from_email: str, recipient_list: list[str]):
    # 1. Resend HTTPS REST API (Port 443 - Recommended for Render)
    resend_api_key = os.getenv('RESEND_API_KEY') or getattr(settings, 'RESEND_API_KEY', None)
    if resend_api_key:
        try:
            resend_from = os.getenv('RESEND_FROM_EMAIL') or getattr(settings, 'RESEND_FROM_EMAIL', None) or "LearnFlow Academy <onboarding@resend.dev>"
            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": resend_from,
                    "to": recipient_list,
                    "subject": subject,
                    "text": message,
                },
                timeout=10,
            )
            if resp.status_code in (200, 201):
                logger.info(f"Successfully sent OTP via Resend API to {recipient_list}")
                return
            else:
                logger.error(f"Resend API error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Resend HTTPS dispatch failed: {e}")

    # 2. Brevo HTTPS REST API (Port 443)
    brevo_api_key = os.getenv('BREVO_API_KEY') or getattr(settings, 'BREVO_API_KEY', None)
    if brevo_api_key:
        try:
            sender_email = os.getenv('EMAIL_HOST_USER') or "noreply@learnflow.com"
            resp = requests.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": brevo_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "sender": {"name": "LearnFlow Academy", "email": sender_email},
                    "to": [{"email": r} for r in recipient_list],
                    "subject": subject,
                    "textContent": message,
                },
                timeout=10,
            )
            if resp.status_code in (200, 201):
                logger.info(f"Successfully sent OTP via Brevo API to {recipient_list}")
                return
            else:
                logger.error(f"Brevo API error ({resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Brevo HTTPS dispatch failed: {e}")

    # 3. Fallback to standard Django send_mail (SMTP/Console)
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False
        )
        logger.info(f"Successfully sent OTP via standard send_mail to {recipient_list}")
    except Exception as e:
        logger.error(f"Failed to send OTP email to {recipient_list}: {e}")


def generate_secure_otp() -> str:
    """Generates a cryptographically random 6-digit numeric OTP."""
    return f"{secrets.randbelow(900000) + 100000:06d}"


def hash_otp(email: str, otp: str) -> str:
    """Hashes the OTP combined with normalized email and SECRET_KEY."""
    salt = getattr(settings, 'SECRET_KEY', 'otp-salt-key')
    return hashlib.sha256(f"{email.strip().lower()}:{otp.strip()}:{salt}".encode('utf-8')).hexdigest()


def create_and_send_otp(email: str) -> tuple[bool, str]:
    """
    Rate-limits, generates, stores hashed OTP, and sends email to user in background.
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

    # Dispatch email asynchronously in background thread so API response is instant (<100ms)
    email_thread = threading.Thread(
        target=_send_otp_email_worker,
        args=(subject, message, from_email, [email]),
        daemon=True
    )
    email_thread.start()

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
